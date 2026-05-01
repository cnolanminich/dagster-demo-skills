"""Workaround: the legacy ``required_resource_keys`` mechanism DOES share.

When two IOManagers each declare ``required_resource_keys={"session_resource"}``
and ``session_resource`` is registered once at the top level of
``Definitions``, both IOManagers resolve through the same registered key
and observe the same underlying session.

This is the supported path for "I want every IOManager in a step to share
one session object". The ergonomic cost is going back to the function-style
``@io_manager`` factory + legacy ``IOManager`` subclass instead of
``ConfigurableIOManager`` + nested resource fields.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import dagster as dg

from lifecycle_demo.assets import baz, foo
from lifecycle_demo.fake_session import FakeSession
from lifecycle_demo.io_managers import LegacyUpsertingIOManager
from lifecycle_demo.resources import cm_session_resource
from lifecycle_demo.tracker import record

from .conftest import events, events_named


@dg.io_manager(required_resource_keys={"session_resource"})
def primary_legacy_io_manager(_ctx) -> "LegacyUpsertingIOManager":
    return LegacyUpsertingIOManager(name="primary")


@dg.io_manager(required_resource_keys={"session_resource"})
def secondary_legacy_io_manager(_ctx) -> "LegacyUpsertingIOManager":
    return LegacyUpsertingIOManager(name="secondary")


@dg.asset(name="bar", io_manager_key="secondary_io")
def bar_via_secondary_legacy(foo: str) -> str:
    record("asset_body", asset="bar", phase="start", foo_arg=foo)
    out = "bar-value"
    record("asset_body", asset="bar", phase="end")
    return out


def test_legacy_required_resource_keys_shares_session(event_log: Path) -> None:
    defs = dg.Definitions(
        assets=[foo, bar_via_secondary_legacy, baz],
        resources={
            "session_resource": cm_session_resource,
            "io_manager": primary_legacy_io_manager,
            "secondary_io": secondary_legacy_io_manager,
        },
    )
    job = defs.resolve_implicit_global_asset_job_def()
    result = job.execute_in_process(
        instance=dg.DagsterInstance.ephemeral(),
    )
    assert result.success

    ev = events()
    enters = events_named(ev, "resource_enter")
    # ONE enter, even with two IOManager keys — both depend on the same
    # registered session_resource by KEY, so it's initialised once.
    assert len(enters) == 1, [e["session_id"] for e in enters]

    iomanager_calls = [
        e for e in ev if e["event"] in ("iomanager_handle_output", "iomanager_load_input")
    ]
    iomanagers_used = {c["iomanager"] for c in iomanager_calls}
    assert iomanagers_used == {"primary", "secondary"}

    sids = {c["session_id"] for c in iomanager_calls}
    assert len(sids) == 1, (
        "With required_resource_keys, both IOManagers share the single "
        "registered session_resource. Got sids=" + str(sids)
    )
