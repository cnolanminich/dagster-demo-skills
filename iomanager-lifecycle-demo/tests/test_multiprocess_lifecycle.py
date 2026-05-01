"""Multiprocess executor: process boundary turns "run-scoped" into "step-scoped".

This is the key empirical finding for the write-up. Under the multiprocess
executor each step runs in its own worker subprocess; resources are
re-initialised in that subprocess for the subset of the plan that step
needs. The Session-as-resource is therefore born and torn down per step,
even though Dagster's API still calls it "run-scoped".

So the practical answer to "is there per-step scoping?" is: yes, when you
use the multiprocess executor (or any out-of-process executor), via the
process boundary — and the default executor for jobs IS multiprocess.
"""

from __future__ import annotations

import os
from pathlib import Path

import dagster as dg
import pytest

from .conftest import events, events_named, pids_from


def _run_multiprocess(
    fn_name: str, instance: dg.DagsterInstance
) -> dg.ExecuteInProcessResult:
    recon = dg.reconstructable(getattr(__import__("lifecycle_demo.jobs", fromlist=[fn_name]), fn_name))
    return dg.execute_job(recon, instance=instance)


@pytest.fixture
def instance(tmp_path: Path) -> dg.DagsterInstance:
    home = tmp_path / "dagster_home"
    home.mkdir(parents=True, exist_ok=True)
    return dg.DagsterInstance.local_temp(tempdir=str(home))


def test_resource_initialised_per_step_under_multiprocess(
    event_log: Path, instance: dg.DagsterInstance
) -> None:
    # The child workers inherit env vars, so LIFECYCLE_DEMO_LOG propagates.
    assert os.environ.get("LIFECYCLE_DEMO_LOG")
    result = _run_multiprocess("shared_session_job_multiprocess", instance)
    assert result.success

    ev = events()
    enters = events_named(ev, "resource_enter")
    exits_ = events_named(ev, "resource_exit")

    # 3 steps -> 3 enter/exit pairs (one per worker process), each with a
    # distinct session id. This is the "step-scoped resource" the write-up
    # was looking for, achieved via the process boundary.
    assert len(enters) == 3, [e["session_id"] for e in enters]
    assert len(exits_) == 3
    assert len({e["session_id"] for e in enters}) == 3
    assert all(e["committed"] is True and e["rolled_back"] is False for e in exits_)


def test_each_step_runs_in_its_own_pid(
    event_log: Path, instance: dg.DagsterInstance
) -> None:
    result = _run_multiprocess("shared_session_job_multiprocess", instance)
    assert result.success

    ev = events()
    asset_body_events = events_named(ev, "asset_body")
    pids_per_asset: dict[str, set[int]] = {}
    for e in asset_body_events:
        pids_per_asset.setdefault(e["asset"], set()).add(e["pid"])
    for asset, pids in pids_per_asset.items():
        assert len(pids) == 1, f"{asset} body bounced across pids: {pids}"
    distinct_pids = pids_from(asset_body_events)
    assert len(distinct_pids) == 3, distinct_pids


def test_all_iomanager_calls_within_a_step_share_one_session(
    event_log: Path, instance: dg.DagsterInstance
) -> None:
    """The key win: within a single step, every load_input / handle_output
    sees the same session id. That's identity-map coherence + transactional
    atomicity for that step's read+write set.
    """
    result = _run_multiprocess("shared_session_job_multiprocess", instance)
    assert result.success

    ev = events()
    by_pid: dict[int, set[str]] = {}
    for e in ev:
        if e["event"] in ("iomanager_handle_output", "iomanager_load_input"):
            by_pid.setdefault(e["pid"], set()).add(e["session_id"])

    assert len(by_pid) == 3
    for pid, sids in by_pid.items():
        assert len(sids) == 1, f"pid {pid} mixed sessions: {sids}"

    all_step_sessions = {next(iter(sids)) for sids in by_pid.values()}
    assert len(all_step_sessions) == 3


def test_modern_pythonic_nesting_creates_one_session_PER_IOMANAGER(
    event_log: Path, instance: dg.DagsterInstance
) -> None:
    """GOTCHA: Sharing one ``ConfigurableSessionResource()`` Python object
    between two ``ConfigurableIOManager``s does NOT share the underlying
    initialised resource. Dagster nests it twice, initialises it twice, and
    you get two sessions per step — the exact failure mode the write-up
    predicted.

    The bar step uses both IOManagers (primary loads foo as input,
    secondary handles bar's output). Within that single step we observe
    TWO distinct session ids.
    """
    result = _run_multiprocess(
        "two_iomanagers_one_session_job_multiprocess", instance
    )
    assert result.success

    ev = events()
    # Group iomanager calls by pid (one pid == one step under multiprocess).
    by_pid: dict[int, list[dict]] = {}
    for e in ev:
        if e["event"] in ("iomanager_handle_output", "iomanager_load_input"):
            by_pid.setdefault(e["pid"], []).append(e)

    bar_pid_events: list[dict] = []
    for pid, calls in by_pid.items():
        iomanagers = {c["iomanager"] for c in calls}
        if iomanagers == {"primary", "secondary"}:
            bar_pid_events = calls
            break
    assert bar_pid_events, (
        f"expected one step (the bar step) to use both IOManagers, got: "
        f"{ {pid: {c['iomanager'] for c in calls} for pid, calls in by_pid.items()} }"
    )

    sids = {c["session_id"] for c in bar_pid_events}
    assert len(sids) == 2, (
        "Sharing one Python ConfigurableResource object between two "
        "ConfigurableIOManagers does NOT share the resource — each "
        "IOManager nests its own copy. Got sids=" + str(sids)
    )
