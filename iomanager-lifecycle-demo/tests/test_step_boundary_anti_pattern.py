"""The "open a session per call" anti-pattern.

The write-up calls this out: every load_input / handle_output gets its own
Session, breaking the identity map and giving up cross-call atomicity. This
test pins that behaviour so it can't silently change.
"""

from __future__ import annotations

from pathlib import Path

import dagster as dg

from lifecycle_demo.definitions import step_boundary_defs

from .conftest import events, events_named


def test_anti_pattern_creates_one_session_per_call(event_log: Path) -> None:
    defs = step_boundary_defs()
    job = defs.resolve_implicit_global_asset_job_def()
    result = job.execute_in_process(
        instance=dg.DagsterInstance.ephemeral(),
    )
    assert result.success

    ev = events()
    handle = events_named(ev, "iomanager_handle_output")
    load = events_named(ev, "iomanager_load_input")

    assert len(handle) == 3
    assert len(load) == 2

    # Every call had a different session id — five distinct sessions for a
    # 3-asset graph. No identity map across calls. No atomicity across the
    # input -> body -> output sequence within a single asset, let alone
    # across asset boundaries.
    all_ids = [e["session_id"] for e in handle + load]
    assert len(set(all_ids)) == 5, all_ids
