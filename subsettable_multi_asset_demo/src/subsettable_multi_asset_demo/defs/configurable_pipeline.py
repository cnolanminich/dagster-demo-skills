"""Config-driven subsettable multi-asset — ordering and selection via Launchpad config.

The user sets ONE config field: steps (e.g. ["C", "B", "A"]).
This controls both which assets materialize and in what order.
Assets not listed in the config are simply skipped — skippable=True
means Dagster won't complain about missing MaterializeResults.
"""

import time

import dagster as dg

STEPS = ["A", "B", "C", "D", "E", "F"]

STEP_FUNCTIONS: dict[str, callable] = {}


def _do_work(name: str, duration: float = 0.5) -> dict:
    """Simulate some work (e.g. an API call or query)."""
    start = time.time()
    time.sleep(duration)
    elapsed = time.time() - start
    return {"asset": name, "elapsed_seconds": round(elapsed, 3)}


def _step_a() -> dict:
    return _do_work("step_a")


def _step_b() -> dict:
    return _do_work("step_b")


def _step_c() -> dict:
    return _do_work("step_c")


def _step_d() -> dict:
    return _do_work("step_d")


def _step_e() -> dict:
    return _do_work("step_e")


def _step_f() -> dict:
    return _do_work("step_f")


STEP_FUNCTIONS = {
    "A": _step_a,
    "B": _step_b,
    "C": _step_c,
    "D": _step_d,
    "E": _step_e,
    "F": _step_f,
}


class StepConfig(dg.Config):
    """Configure which steps run and in what order via the Launchpad.

    Example: {"steps": ["C", "B", "A"]} runs C first, then B, then A.
    Only listed steps are materialized; unlisted steps are skipped.
    """

    steps: list[str] = ["C", "B", "A"]


@dg.multi_asset(
    specs=[
        dg.AssetSpec(
            f"configurable_step_{s.lower()}",
            group_name="configurable",
            tags={"step": s},
            skippable=True,
        )
        for s in STEPS
    ],
    can_subset=True,
)
def configurable_pipeline(context: dg.AssetExecutionContext, config: StepConfig):
    """A config-driven pipeline where Launchpad config controls selection AND ordering.

    Set config to {"steps": ["C", "B"]} to run C then B.
    Steps not in the list are skipped with zero overhead.
    """
    valid_steps = set(STEPS)
    for step_name in config.steps:
        if step_name not in valid_steps:
            raise dg.Failure(
                description=f"Unknown step '{step_name}'. Valid steps: {STEPS}"
            )

    for step_name in config.steps:
        context.log.info(f"Running step {step_name}")
        result = STEP_FUNCTIONS[step_name]()
        yield dg.MaterializeResult(
            asset_key=dg.AssetKey(f"configurable_step_{step_name.lower()}"),
            metadata={"info": dg.MetadataValue.json(result)},
        )

    skipped = [s for s in STEPS if s not in config.steps]
    if skipped:
        context.log.info(f"Skipped steps (not in config): {skipped}")
