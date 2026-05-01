"""Cross-process event log for the lifecycle demo.

Every meaningful lifecycle event (resource enter, resource exit, IOManager
load_input, IOManager handle_output, asset body) is appended as a single
JSON line to a file. Using a file lets the multiprocess executor's child
processes contribute events to the same log that the parent test reads.
"""

from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


_ENV_VAR = "LIFECYCLE_DEMO_LOG"


def log_path() -> Path:
    p = os.environ.get(_ENV_VAR)
    if not p:
        raise RuntimeError(f"{_ENV_VAR} must be set before running a Dagster job")
    return Path(p)


def record(event: str, **fields: Any) -> None:
    payload = {
        "event": event,
        "pid": os.getpid(),
        "ts": time.time(),
        **fields,
    }
    with log_path().open("a") as fh:
        fh.write(json.dumps(payload, default=str) + "\n")


def read_events() -> list[dict[str, Any]]:
    path = log_path()
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


@contextmanager
def fresh_log(tmp_dir: Path) -> Iterator[Path]:
    path = tmp_dir / f"events-{os.getpid()}-{time.time_ns()}.jsonl"
    path.write_text("")
    prev = os.environ.get(_ENV_VAR)
    os.environ[_ENV_VAR] = str(path)
    try:
        yield path
    finally:
        if prev is None:
            os.environ.pop(_ENV_VAR, None)
        else:
            os.environ[_ENV_VAR] = prev
