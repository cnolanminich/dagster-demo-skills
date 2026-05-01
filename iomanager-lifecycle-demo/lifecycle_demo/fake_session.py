"""A stand-in for a SQLAlchemy `Session` that records its identity.

The real question we're investigating is "do multiple steps share a Session?",
not "does SQLAlchemy work?". A toy object with a stable `id` and a small set of
ORM-like methods is enough to answer that, and avoids needing a live database.
"""

from __future__ import annotations

import itertools
import os
import uuid
from typing import Any

from .tracker import record


_id_counter = itertools.count()


class FakeSession:
    """Mimics the parts of `sqlalchemy.orm.Session` we care about."""

    def __init__(self) -> None:
        self.session_id = f"session-{os.getpid()}-{next(_id_counter)}-{uuid.uuid4().hex[:6]}"
        self._committed = False
        self._rolled_back = False
        self._closed = False
        self._writes: list[dict[str, Any]] = []
        self._reads: list[dict[str, Any]] = []

    def execute(self, stmt: Any) -> None:
        self._writes.append({"stmt": str(stmt)})
        record("session_execute", session_id=self.session_id, stmt=str(stmt))

    def get_one(self, model_cls: type, pk: Any) -> Any:
        self._reads.append({"model": model_cls.__name__, "pk": pk})
        record(
            "session_get_one",
            session_id=self.session_id,
            model=model_cls.__name__,
            pk=str(pk),
        )
        return model_cls(pk=pk)

    def commit(self) -> None:
        self._committed = True
        record("session_commit", session_id=self.session_id)

    def rollback(self) -> None:
        self._rolled_back = True
        record("session_rollback", session_id=self.session_id)

    def close(self) -> None:
        self._closed = True
        record("session_close", session_id=self.session_id)
