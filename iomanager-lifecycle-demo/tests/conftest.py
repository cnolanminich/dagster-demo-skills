"""Shared fixtures + helpers for the lifecycle tests.

Each test runs Dagster jobs that produce events into a per-test JSONL log
(see ``lifecycle_demo.tracker``). The fixtures here own the log file and
hand back the parsed events.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Iterator

import pytest

from lifecycle_demo.tracker import read_events


@pytest.fixture
def event_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    log = tmp_path / "events.jsonl"
    log.write_text("")
    monkeypatch.setenv("LIFECYCLE_DEMO_LOG", str(log))
    yield log


def events() -> list[dict[str, Any]]:
    return read_events()


def session_ids_from(events_: list[dict[str, Any]], event_name: str) -> list[str]:
    return [e["session_id"] for e in events_ if e["event"] == event_name]


def events_named(events_: list[dict[str, Any]], event_name: str) -> list[dict[str, Any]]:
    return [e for e in events_ if e["event"] == event_name]


def pids_from(events_: list[dict[str, Any]]) -> set[int]:
    return {e["pid"] for e in events_}
