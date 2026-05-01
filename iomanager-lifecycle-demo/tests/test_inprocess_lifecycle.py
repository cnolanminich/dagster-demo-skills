"""In-process executor: prove resources are run-scoped, not step-scoped.

Single resource definition + single IOManager. The job runs all three steps
(foo, bar, baz). If resources were per-step we'd see three resource_enter /
resource_exit pairs and three distinct session ids; if they're per-run we'd
see one of each.
"""

from __future__ import annotations

from pathlib import Path

import dagster as dg

from lifecycle_demo.definitions import shared_session_defs

from .conftest import events, events_named, session_ids_from


def _materialize(defs: dg.Definitions) -> dg.ExecuteInProcessResult:
    job = defs.resolve_implicit_global_asset_job_def()
    return job.execute_in_process(
        instance=dg.DagsterInstance.ephemeral(),
        resources=defs.resources,
    )


def test_single_resource_init_per_run_inprocess(event_log: Path) -> None:
    defs = shared_session_defs()
    result = _materialize(defs)
    assert result.success

    ev = events()
    enters = events_named(ev, "resource_enter")
    exits_ = events_named(ev, "resource_exit")

    # ONE enter/exit pair for the whole run, despite three steps.
    assert len(enters) == 1, f"expected 1 resource_enter, got {len(enters)}: {enters}"
    assert len(exits_) == 1, f"expected 1 resource_exit, got {len(exits_)}: {exits_}"
    assert enters[0]["session_id"] == exits_[0]["session_id"]
    assert exits_[0]["committed"] is True
    assert exits_[0]["rolled_back"] is False


def test_every_iomanager_call_sees_same_session_inprocess(event_log: Path) -> None:
    defs = shared_session_defs()
    result = _materialize(defs)
    assert result.success

    ev = events()
    handle_ids = session_ids_from(ev, "iomanager_handle_output")
    load_ids = session_ids_from(ev, "iomanager_load_input")

    # 3 outputs (foo, bar, baz) and 2 inputs (bar<-foo, baz<-bar)
    assert len(handle_ids) == 3
    assert len(load_ids) == 2
    assert len(set(handle_ids + load_ids)) == 1, (
        "Run-scoped resource means every load/handle saw the same session id"
    )


def test_step_failure_does_NOT_propagate_into_resource_generator(event_log: Path) -> None:
    """Surprise finding: a step exception is NOT thrown into the resource generator.

    The naive assumption is that a context-managed resource will see the step
    failure and rollback in its `except` block. It does not. Dagster exits the
    generator normally (commit branch taken) even when the run fails, because
    by the time teardown runs the exception has already been recorded against
    the step and the plan has moved on. This means a `try/except` based commit
    /rollback inside a `@dg.resource` generator is **not** a reliable hook for
    transactional integrity tied to step success.
    """
    import dagster as dg

    from lifecycle_demo.assets import foo
    from lifecycle_demo.io_managers import UpsertingIOManager
    from lifecycle_demo.resources import ConfigurableSessionResource
    from lifecycle_demo.tracker import record

    @dg.asset
    def boom(foo: str) -> str:
        record("asset_body", asset="boom", phase="start", foo_arg=foo)
        raise RuntimeError("step failure")

    session_resource = ConfigurableSessionResource()
    defs = dg.Definitions(
        assets=[foo, boom],
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
        raise_on_error=False,
    )
    assert not result.success

    ev = events()
    exits_ = events_named(ev, "resource_exit")
    assert len(exits_) == 1
    # The headline: even though the run failed, the resource generator
    # exited via its `yield` cleanly, so it took the commit path.
    assert exits_[0]["committed"] is True
    assert exits_[0]["rolled_back"] is False, (
        "Step failure did NOT propagate into the resource generator. "
        "Don't rely on try/except in a @dg.resource for rollback semantics."
    )
