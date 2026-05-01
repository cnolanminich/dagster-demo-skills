"""Verify there is no per-step setup/teardown hook on a resource or IOManager.

The write-up asks: "is there a step-is-starting / step-is-finishing hook
the IOManager (or resource) could use?". The public APIs are:

* ``ConfigurableResource.setup_for_execution(context)`` — fires at resource
  init time. Under the in-process executor that is once per run.
* ``ConfigurableResource.teardown_after_execution(context)`` — fires at
  resource teardown. Once per run, in a finally after the whole plan.
* ``ConfigurableResource.yield_for_execution(context)`` — generator
  alternative covering both. Same scope as setup/teardown.
* ``ConfigurableIOManager.setup_for_execution`` / ``teardown_after_execution``
  / ``yield_for_execution`` — same scope: run, not step.

There is no ``before_step`` / ``after_step`` hook. ``@op_hooks`` (success_hook
/ failure_hook) DO fire per op, but they fire AFTER the op's outputs have
already been handled, so they can't open the session the IOManager uses.
This test pins that ordering.
"""

from __future__ import annotations

from pathlib import Path

import dagster as dg

from lifecycle_demo.assets import ALL_ASSETS
from lifecycle_demo.io_managers import UpsertingIOManager
from lifecycle_demo.resources import ConfigurableSessionResource
from lifecycle_demo.tracker import record

from .conftest import events, events_named


@dg.success_hook
def record_success_hook(context: dg.HookContext) -> None:
    record("op_success_hook", op=context.op.name)


def test_op_success_hook_fires_after_handle_output(event_log: Path) -> None:
    session_resource = ConfigurableSessionResource()
    defs = dg.Definitions(
        assets=[a.with_hooks({record_success_hook}) for a in ALL_ASSETS],
        resources={
            "session_resource": session_resource,
            "io_manager": UpsertingIOManager(
                name="default", session_resource=session_resource
            ),
        },
    )
    job = defs.resolve_implicit_global_asset_job_def()
    result = job.execute_in_process(
        instance=dg.DagsterInstance.ephemeral(),
    )
    assert result.success

    ev = events()
    # For each asset, the order is:
    #   asset_body(start) -> asset_body(end) -> iomanager_handle_output -> op_success_hook
    # i.e. the success hook can observe a completed step but cannot influence
    # what the IOManager did before it.
    for asset_name in ("foo", "bar", "baz"):
        asset_body_end = next(
            i
            for i, e in enumerate(ev)
            if e["event"] == "asset_body"
            and e["asset"] == asset_name
            and e["phase"] == "end"
        )
        handle_idx = next(
            i
            for i, e in enumerate(ev)
            if e["event"] == "iomanager_handle_output"
            and e["asset_key"] == asset_name
        )
        hook_idx = next(
            i
            for i, e in enumerate(ev)
            if e["event"] == "op_success_hook" and e["op"] == asset_name
        )
        assert asset_body_end < handle_idx < hook_idx, (
            f"{asset_name}: expected body_end < handle_output < success_hook, "
            f"got {asset_body_end} < {handle_idx} < {hook_idx}"
        )

    # And only ONE resource_enter for the whole run — the success_hook
    # firing per-op did not cause the resource to re-init per-step.
    enters = events_named(ev, "resource_enter")
    assert len(enters) == 1
