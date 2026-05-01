"""Top-level job factories for ``dg.execute_job(reconstructable(...))``.

The multiprocess executor needs to spawn workers that re-import the job
definition, so the job has to live at module scope and be addressable as
``lifecycle_demo.jobs.<callable>``. We also have to give the jobs explicit
names — the implicit ``__ASSET_JOB`` name is reserved and rejected when a
reconstructable job is hydrated in a worker.

Each factory builds a ``Definitions`` with a named asset job, then returns
that job by name so resources are resolved correctly.
"""

from __future__ import annotations

import dagster as dg

from .assets import ALL_ASSETS, baz, bar_via_secondary, foo
from .io_managers import (
    StepBoundaryIOManager,
    UpsertingIOManager,
    legacy_upserting_io_manager,
)
from .resources import ConfigurableSessionResource, cm_session_resource


def _build_defs(
    *,
    assets,
    resources,
    job_name: str,
    multiprocess: bool,
) -> dg.Definitions:
    job = dg.define_asset_job(name=job_name)
    return dg.Definitions(
        assets=assets,
        jobs=[job],
        resources=resources,
        executor=dg.multiprocess_executor if multiprocess else dg.in_process_executor,
    )


def shared_session_job_multiprocess() -> dg.JobDefinition:
    session_resource = ConfigurableSessionResource()
    defs = _build_defs(
        assets=ALL_ASSETS,
        resources={
            "session_resource": session_resource,
            "io_manager": UpsertingIOManager(
                name="default", session_resource=session_resource
            ),
        },
        job_name="shared_session_job",
        multiprocess=True,
    )
    return defs.resolve_job_def("shared_session_job")


def two_iomanagers_one_session_job_multiprocess() -> dg.JobDefinition:
    session_resource = ConfigurableSessionResource()
    primary = UpsertingIOManager(name="primary", session_resource=session_resource)
    secondary = UpsertingIOManager(
        name="secondary", session_resource=session_resource
    )
    defs = _build_defs(
        assets=[foo, bar_via_secondary, baz],
        resources={
            "session_resource": session_resource,
            "io_manager": primary,
            "secondary_io": secondary,
        },
        job_name="two_iomanagers_job",
        multiprocess=True,
    )
    return defs.resolve_job_def("two_iomanagers_job")


def self_deduping_two_iomanagers_job_multiprocess() -> dg.JobDefinition:
    """Same shape as two_iomanagers_one_session_job_multiprocess, but using
    the SharedSessionResource patch from tests/test_self_deduping_resource.py
    so that nestings in the same worker share one session.
    """
    from tests.test_self_deduping_resource import (
        SharedIOManager,
        SharedSessionResource,
    )

    shared = SharedSessionResource()
    defs = _build_defs(
        assets=[foo, bar_via_secondary, baz],
        resources={
            "session_resource": shared,
            "io_manager": SharedIOManager(name="primary", session_resource=shared),
            "secondary_io": SharedIOManager(
                name="secondary", session_resource=shared
            ),
        },
        job_name="self_deduping_two_iomanagers_job",
        multiprocess=True,
    )
    return defs.resolve_job_def("self_deduping_two_iomanagers_job")
