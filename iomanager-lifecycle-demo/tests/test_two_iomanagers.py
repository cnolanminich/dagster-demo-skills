"""Two IOManager instances per run, in-process executor.

Demonstrates the "modern Pythonic" gotcha: passing the SAME
ConfigurableSessionResource Python object into two ConfigurableIOManagers
does NOT result in one shared underlying session. Dagster nests it twice,
initialises it twice, and each IOManager sees its own session.
"""

from __future__ import annotations

from pathlib import Path

import dagster as dg

from lifecycle_demo.definitions import two_iomanagers_one_session_defs

from .conftest import events, events_named


def test_modern_nesting_initialises_session_resource_twice(event_log: Path) -> None:
    defs = two_iomanagers_one_session_defs()
    job = defs.resolve_implicit_global_asset_job_def()
    result = job.execute_in_process(
        instance=dg.DagsterInstance.ephemeral(),
    )
    assert result.success

    ev = events()
    enters = events_named(ev, "resource_enter")
    # GOTCHA: 2 enters, even though we constructed only one Python session
    # object and passed it to both IOManagers. Each IOManager carries its
    # OWN copy of the nested ConfigurableSessionResource graph.
    assert len(enters) == 2, (
        f"expected 2 (the gotcha), got {len(enters)}: {[e['session_id'] for e in enters]}"
    )

    iomanager_calls = [
        e for e in ev if e["event"] in ("iomanager_handle_output", "iomanager_load_input")
    ]
    iomanagers_used = {c["iomanager"] for c in iomanager_calls}
    assert iomanagers_used == {"primary", "secondary"}

    # Two distinct session ids end up in use across the run, partitioned by
    # which IOManager made the call.
    primary_sids = {c["session_id"] for c in iomanager_calls if c["iomanager"] == "primary"}
    secondary_sids = {c["session_id"] for c in iomanager_calls if c["iomanager"] == "secondary"}
    assert len(primary_sids) == 1
    assert len(secondary_sids) == 1
    assert primary_sids.isdisjoint(secondary_sids), (
        "Each IOManager owns its own session — they do not share."
    )
