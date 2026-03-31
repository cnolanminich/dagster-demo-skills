"""Subsettable multi-asset — one @multi_asset(can_subset=True) with 6 assets.

Users select which assets to materialize at launch time in the UI.
Only the selected assets execute; skipped assets have zero computational cost
because the code checks `context.op_execution_context.selected_asset_keys`
and only runs work for selected ones.
"""

import time

import dagster as dg

STEPS = ["A", "B", "C", "D", "E", "F"]


def _do_work(name: str, duration: float = 0.5) -> dict:
    """Simulate some work (e.g. an API call or query)."""
    start = time.time()
    time.sleep(duration)
    elapsed = time.time() - start
    return {"asset": name, "elapsed_seconds": round(elapsed, 3)}


@dg.multi_asset(
    specs=[
        dg.AssetSpec(
            f"multi_step_{s.lower()}",
            group_name="multi",
            tags={"step": s},
            skippable=True,
        )
        for s in STEPS
    ],
    can_subset=True,
)
def subsettable_steps(context: dg.AssetExecutionContext):
    """A single multi-asset whose assets can be independently selected.

    At launch time, pick any combination of multi_step_a..f in the Dagster UI.
    Only selected assets will do real work — skipped assets are never executed.
    """
    selected = context.op_execution_context.selected_asset_keys

    for step in STEPS:
        key = dg.AssetKey(f"multi_step_{step.lower()}")
        if key in selected:
            context.log.info(f"Executing step {step}")
            result = _do_work(f"multi_step_{step.lower()}")
            yield dg.MaterializeResult(
                asset_key=key,
                metadata={"info": dg.MetadataValue.json(result)},
            )
        else:
            context.log.info(f"Skipping step {step} — not selected")
