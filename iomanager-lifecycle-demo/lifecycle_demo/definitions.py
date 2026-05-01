"""Definition factories for the various scenarios the tests exercise."""

from __future__ import annotations

import dagster as dg

from .assets import ALL_ASSETS, bar_via_secondary, baz, foo
from .io_managers import (
    StepBoundaryIOManager,
    UpsertingIOManager,
    legacy_upserting_io_manager,
)
from .resources import ConfigurableSessionResource, cm_session_resource


def shared_session_defs() -> dg.Definitions:
    """A single ConfigurableSessionResource shared by a single IOManager."""
    session_resource = ConfigurableSessionResource()
    return dg.Definitions(
        assets=ALL_ASSETS,
        resources={
            "session_resource": session_resource,
            "io_manager": UpsertingIOManager(
                name="default", session_resource=session_resource
            ),
        },
    )


def two_iomanagers_one_session_defs() -> dg.Definitions:
    """Two IOManager *instances* but one underlying session resource.

    foo writes through the primary IOManager, bar writes through the secondary
    IOManager, baz reads bar through the secondary IOManager. Both IOManagers
    point at the same session resource, so the test can assert that the
    session id seen is identical across both managers within a single step.
    """
    session_resource = ConfigurableSessionResource()
    primary = UpsertingIOManager(name="primary", session_resource=session_resource)
    secondary = UpsertingIOManager(
        name="secondary", session_resource=session_resource
    )
    return dg.Definitions(
        assets=[
            foo,
            bar_via_secondary,
            baz,
        ],
        resources={
            "session_resource": session_resource,
            "io_manager": primary,
            "secondary_io": secondary,
        },
    )


def legacy_session_defs() -> dg.Definitions:
    """Legacy @io_manager + function-style cm_session_resource."""
    return dg.Definitions(
        assets=ALL_ASSETS,
        resources={
            "session_resource": cm_session_resource,
            "io_manager": legacy_upserting_io_manager,
        },
    )


def step_boundary_defs() -> dg.Definitions:
    """The naive "open a session per call" anti-pattern."""
    return dg.Definitions(
        assets=ALL_ASSETS,
        resources={
            "io_manager": StepBoundaryIOManager(),
        },
    )
