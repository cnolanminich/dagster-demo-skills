"""Patching the modern Pythonic API to share a resource across nestings.

The default behaviour (see ``test_two_iomanagers.py``) is that nesting the
same ``ConfigurableResource`` Python object inside two ``ConfigurableIOManager``
fields gives you two independent sessions. You can fix this without
falling back to function-style ``required_resource_keys``: have the
resource itself dedupe via a process-local cache keyed on ``run_id``.

Properties of the patch:

* Process-local cache (a module-level dict) — under the multiprocess
  executor each worker has its own, so cross-step sessions never leak.
* Refcount-based cleanup — Dagster still calls ``yield_for_execution``
  once per nesting; the first call creates the session and owns its
  close, every subsequent call is a fast cache hit.
* Configurable ``cache_key`` field — if you want multiple named "pools"
  (e.g. one Session per database) within a single run, give them
  different cache keys.

Caveats this patch does NOT fix:
* Step-failure rollback. The exception still doesn't propagate into the
  resource generator (see ``test_inprocess_lifecycle.py``), so you still
  need an op ``failure_hook`` (or a wrapper inside the op body) to drive
  rollback on per-step errors.
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import dagster as dg

from lifecycle_demo.assets import baz, bar_via_secondary, foo
from lifecycle_demo.fake_session import FakeSession
from lifecycle_demo.tracker import record

from .conftest import events, events_named


_PROCESS_CACHE: dict[tuple[str, str], FakeSession] = {}
_REFCOUNT: dict[tuple[str, str], int] = {}


class SharedSessionResource(dg.ConfigurableResource):
    """ConfigurableResource that dedupes itself across nestings within a run."""

    cache_key: str = "default"

    @contextmanager
    def yield_for_execution(
        self, context: dg.InitResourceContext
    ) -> Iterator["SharedSessionResource"]:
        key = (context.run_id or "no-run", self.cache_key)

        if key in _PROCESS_CACHE:
            _REFCOUNT[key] += 1
            self._session = _PROCESS_CACHE[key]
            record(
                "resource_enter",
                kind="SharedSessionResource",
                session_id=self._session.session_id,
                shared=True,
            )
            try:
                yield self
            finally:
                _REFCOUNT[key] -= 1
                record(
                    "resource_exit",
                    kind="SharedSessionResource",
                    session_id=self._session.session_id,
                    shared=True,
                )
            return

        session = FakeSession()
        _PROCESS_CACHE[key] = session
        _REFCOUNT[key] = 1
        self._session = session
        record(
            "resource_enter",
            kind="SharedSessionResource",
            session_id=session.session_id,
            shared=False,
        )
        try:
            yield self
            session.commit()
        except BaseException:
            session.rollback()
            raise
        finally:
            session.close()
            _REFCOUNT[key] -= 1
            if _REFCOUNT[key] == 0:
                del _PROCESS_CACHE[key]
                del _REFCOUNT[key]
            record(
                "resource_exit",
                kind="SharedSessionResource",
                session_id=session.session_id,
                shared=False,
            )

    @property
    def session(self) -> FakeSession:
        return self._session


class SharedIOManager(dg.ConfigurableIOManager):
    name: str = "default"
    session_resource: SharedSessionResource

    def handle_output(self, context: dg.OutputContext, obj: Any) -> None:
        s = self.session_resource.session
        record(
            "iomanager_handle_output",
            iomanager=self.name,
            asset_key=context.asset_key.to_user_string(),
            session_id=s.session_id,
            obj_repr=repr(obj),
        )
        s.execute(f"upsert {context.asset_key.to_user_string()} = {obj!r}")

    def load_input(self, context: dg.InputContext) -> Any:
        s = self.session_resource.session
        upstream = (
            context.upstream_output.asset_key.to_user_string()
            if context.upstream_output
            else context.asset_key.to_user_string()
        )
        record(
            "iomanager_load_input",
            iomanager=self.name,
            consumer_asset_key=context.asset_key.to_user_string(),
            upstream_asset_key=upstream,
            session_id=s.session_id,
        )
        return f"value-from-{upstream}"


def test_self_deduping_resource_shares_one_session_under_multiprocess(
    event_log: Path, tmp_path: Path
) -> None:
    """Patch composes correctly with the multiprocess executor.

    Within each worker (== each step) the dedup hits and both IOManagers
    see the same session id. Across workers, sessions are distinct because
    the cache is process-local.
    """
    home = tmp_path / "dagster_home"
    home.mkdir(parents=True, exist_ok=True)
    instance = dg.DagsterInstance.local_temp(tempdir=str(home))

    from lifecycle_demo.jobs import self_deduping_two_iomanagers_job_multiprocess

    recon = dg.reconstructable(self_deduping_two_iomanagers_job_multiprocess)
    result = dg.execute_job(recon, instance=instance)
    assert result.success

    ev = events()
    iomanager_calls = [
        e
        for e in ev
        if e["event"] in ("iomanager_handle_output", "iomanager_load_input")
    ]
    by_pid: dict[int, set[str]] = {}
    for c in iomanager_calls:
        by_pid.setdefault(c["pid"], set()).add(c["session_id"])

    # Within each worker (step), one shared session.
    for pid, sids in by_pid.items():
        assert len(sids) == 1, f"pid {pid} mixed sessions: {sids}"

    # Across workers, sessions differ.
    distinct = {next(iter(s)) for s in by_pid.values()}
    assert len(distinct) == len(by_pid)


def test_self_deduping_resource_shares_one_session(event_log: Path) -> None:
    shared = SharedSessionResource()
    defs = dg.Definitions(
        assets=[foo, bar_via_secondary, baz],
        resources={
            "session_resource": shared,
            "io_manager": SharedIOManager(name="primary", session_resource=shared),
            "secondary_io": SharedIOManager(
                name="secondary", session_resource=shared
            ),
        },
    )
    job = defs.resolve_implicit_global_asset_job_def()
    result = job.execute_in_process(
        instance=dg.DagsterInstance.ephemeral(),
    )
    assert result.success

    ev = events()
    enters = events_named(ev, "resource_enter")
    # Dagster still calls yield_for_execution twice (once per IOManager
    # that nests this resource) — the patch dedupes inside the second call.
    assert len(enters) == 2
    shared_flags = [e["shared"] for e in enters]
    assert shared_flags == [False, True], (
        f"expected first=create, second=cache-hit; got {shared_flags}"
    )
    # Both events report the same session id.
    assert enters[0]["session_id"] == enters[1]["session_id"]

    # Most importantly: every IOManager call across BOTH IOManagers saw
    # the same session id.
    iomanager_calls = [
        e
        for e in ev
        if e["event"] in ("iomanager_handle_output", "iomanager_load_input")
    ]
    iomanagers = {c["iomanager"] for c in iomanager_calls}
    sids = {c["session_id"] for c in iomanager_calls}
    assert iomanagers == {"primary", "secondary"}
    assert len(sids) == 1, (
        "Self-deduping resource: every load_input/handle_output across both "
        "IOManagers shares one session. Got " + str(sids)
    )
