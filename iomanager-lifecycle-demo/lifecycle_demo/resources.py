"""Two flavours of session resource so we can compare them empirically.

* ``cm_session_resource`` is the canonical "context-managed resource" pattern:
  a ``@dg.resource`` that yields a freshly-built ``FakeSession`` and records
  every enter/exit. Whatever lifecycle Dagster gives this thing is the
  lifecycle every other resource gets.

* ``ConfigurableSessionResource`` is the same idea expressed as a
  ``ConfigurableResource`` with ``yield_for_execution``. Same lifecycle, just
  the modern surface.
"""

from __future__ import annotations

from contextlib import contextmanager
from collections.abc import Iterator

import dagster as dg

from .fake_session import FakeSession
from .tracker import record


@dg.resource
@contextmanager
def cm_session_resource(context: dg.InitResourceContext) -> Iterator[FakeSession]:
    session = FakeSession()
    record(
        "resource_enter",
        kind="cm_session_resource",
        session_id=session.session_id,
        run_id=context.run_id,
    )
    try:
        yield session
        session.commit()
    except BaseException:
        session.rollback()
        raise
    finally:
        session.close()
        record(
            "resource_exit",
            kind="cm_session_resource",
            session_id=session.session_id,
            committed=session._committed,
            rolled_back=session._rolled_back,
        )


class ConfigurableSessionResource(dg.ConfigurableResource):
    """Same semantics as ``cm_session_resource`` via the modern API."""

    @contextmanager
    def yield_for_execution(
        self, context: dg.InitResourceContext
    ) -> Iterator["ConfigurableSessionResource"]:
        session = FakeSession()
        record(
            "resource_enter",
            kind="ConfigurableSessionResource",
            session_id=session.session_id,
            run_id=context.run_id,
        )
        self._session = session
        try:
            yield self
            session.commit()
        except BaseException:
            session.rollback()
            raise
        finally:
            session.close()
            record(
                "resource_exit",
                kind="ConfigurableSessionResource",
                session_id=session.session_id,
                committed=session._committed,
                rolled_back=session._rolled_back,
            )

    @property
    def session(self) -> FakeSession:
        return self._session
