"""IOManagers that delegate persistence to a session resource.

Two flavours:

* ``UpsertingIOManager`` — modern ``ConfigurableIOManager``. Declares a
  ``ResourceDependency`` on a ``ConfigurableSessionResource`` and records
  the session id seen at every ``handle_output`` / ``load_input`` call.

* ``LegacyUpsertingIOManager`` — function-style ``@io_manager`` factory that
  pulls a session out of ``context.resources`` instead. Uses the legacy
  ``required_resource_keys`` mechanism. Same observable lifecycle.

* ``StepBoundaryIOManager`` — counter-example that opens a fresh
  ``FakeSession`` on every call. Demonstrates the failure mode the write-up
  describes.
"""

from __future__ import annotations

from typing import Any

import dagster as dg

from .fake_session import FakeSession
from .resources import ConfigurableSessionResource
from .tracker import record


class UpsertingIOManager(dg.ConfigurableIOManager):
    """Persists outputs / loads inputs through a shared session resource."""

    name: str = "default"
    session_resource: ConfigurableSessionResource

    def handle_output(self, context: dg.OutputContext, obj: Any) -> None:
        session = self.session_resource.session
        record(
            "iomanager_handle_output",
            iomanager=self.name,
            asset_key=context.asset_key.to_user_string(),
            session_id=session.session_id,
            obj_repr=repr(obj),
        )
        session.execute(f"upsert {context.asset_key.to_user_string()} = {obj!r}")

    def load_input(self, context: dg.InputContext) -> Any:
        session = self.session_resource.session
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
            session_id=session.session_id,
        )
        return f"value-from-{upstream}"


@dg.io_manager(required_resource_keys={"session_resource"})
def legacy_upserting_io_manager(
    init_context: dg.InitResourceContext,
) -> "LegacyUpsertingIOManager":
    return LegacyUpsertingIOManager(name="legacy")


class LegacyUpsertingIOManager(dg.IOManager):
    def __init__(self, name: str) -> None:
        self.name = name

    def handle_output(self, context: dg.OutputContext, obj: Any) -> None:
        session: FakeSession = context.resources.session_resource
        record(
            "iomanager_handle_output",
            iomanager=self.name,
            asset_key=context.asset_key.to_user_string(),
            session_id=session.session_id,
            obj_repr=repr(obj),
        )
        session.execute(f"upsert {context.asset_key.to_user_string()} = {obj!r}")

    def load_input(self, context: dg.InputContext) -> Any:
        session: FakeSession = context.resources.session_resource
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
            session_id=session.session_id,
        )
        return f"value-from-{upstream}"


class StepBoundaryIOManager(dg.ConfigurableIOManager):
    """Anti-pattern: opens a new FakeSession on every call.

    Demonstrates the failure mode the write-up describes — every load_input
    and every handle_output gets a different identity-map / transaction.
    """

    name: str = "step-boundary"

    def handle_output(self, context: dg.OutputContext, obj: Any) -> None:
        s = FakeSession()
        record(
            "iomanager_handle_output",
            iomanager=self.name,
            asset_key=context.asset_key.to_user_string(),
            session_id=s.session_id,
            obj_repr=repr(obj),
        )
        s.execute(f"upsert {context.asset_key.to_user_string()} = {obj!r}")
        s.commit()
        s.close()

    def load_input(self, context: dg.InputContext) -> Any:
        s = FakeSession()
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
        s.close()
        return f"value-from-{upstream}"
