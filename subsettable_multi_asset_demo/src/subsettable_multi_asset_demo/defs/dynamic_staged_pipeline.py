"""Dynamic staged pipeline — multi-level dependencies with DynamicOut.

Demonstrates two patterns for dependencies between dynamic steps:

1. Chained .map(): each dynamic branch runs step1 → step2 sequentially,
   branches execute in parallel. Good for per-item pipelines.

2. Fan-out → collect → fan-out: stage 1 runs in parallel, results are
   collected, then stage 2 fans out again. Good for the user's use case
   where stages have different steps that depend on prior stages completing.

Config example for staged approach:
  {"stages": [["A", "C"], ["B"], ["D", "F"]]}
  - Stage 1: A and C run in parallel
  - Stage 2: B runs after stage 1 completes
  - Stage 3: D and F run after stage 2 completes
"""

import time

import dagster as dg

STEPS = ["A", "B", "C", "D", "E", "F"]


def _do_work(name: str, stage: int, duration: float = 0.5) -> dict:
    """Simulate some work."""
    start = time.time()
    time.sleep(duration)
    elapsed = time.time() - start
    return {"step": name, "stage": stage, "elapsed_seconds": round(elapsed, 3)}


STEP_FUNCTIONS = {s: (lambda s=s: _do_work(s, stage=0)) for s in STEPS}


# ---------------------------------------------------------------------------
# Pattern 1: Chained .map() — sequential steps within each parallel branch
# ---------------------------------------------------------------------------


class ChainedConfig(dg.Config):
    """Each item goes through process → validate → finalize sequentially."""

    items: list[str] = ["A", "C", "D"]


@dg.op(out=dg.DynamicOut())
def fan_out_items(config: ChainedConfig):
    for item in config.items:
        yield dg.DynamicOutput(item, mapping_key=item)


@dg.op
def process_item(item: str) -> dict:
    """Stage 1: process each item."""
    time.sleep(0.5)
    return {"item": item, "stage": "process", "status": "processed"}


@dg.op
def validate_item(result: dict) -> dict:
    """Stage 2: validate — depends on process_item completing first."""
    time.sleep(0.3)
    result["stage"] = "validate"
    result["status"] = "validated"
    return result


@dg.op
def finalize_item(result: dict) -> dict:
    """Stage 3: finalize — depends on validate_item completing first."""
    time.sleep(0.2)
    result["stage"] = "finalize"
    result["status"] = "finalized"
    return result


@dg.op
def gather_chained(results: list[dict]) -> dict:
    return {"completed": len(results), "results": results}


@dg.graph_asset(group_name="dynamic_staged")
def chained_map_pipeline():
    """Chained .map(): each branch runs process → validate → finalize.

    Branches run in parallel; steps within a branch run sequentially.
    Config: {"items": ["A", "C", "D"]}
    Result: A, C, D each go through 3 stages independently.
    """
    items = fan_out_items()
    processed = items.map(process_item)
    validated = processed.map(validate_item)
    finalized = validated.map(finalize_item)
    return gather_chained(finalized.collect())


# ---------------------------------------------------------------------------
# Pattern 2: Fan-out → collect → fan-out (staged execution)
# ---------------------------------------------------------------------------


class StagedConfig(dg.Config):
    """Define stages as a list of lists. Each inner list is a parallel group.

    Example: {"stages": [["A", "C"], ["B"], ["D", "F"]]}
    Stage 1: A and C in parallel → wait for both →
    Stage 2: B → wait →
    Stage 3: D and F in parallel
    """

    stages: list[list[str]] = [["A", "C"], ["B"], ["D", "F"]]


@dg.op(out=dg.DynamicOut())
def plan_stage_1(config: StagedConfig):
    """Yield DynamicOutputs for stage 1 steps."""
    if len(config.stages) < 1:
        return
    for step in config.stages[0]:
        yield dg.DynamicOutput(
            {"step": step, "stage": 1}, mapping_key=f"s1_{step}"
        )


@dg.op
def run_staged_step(step_info: dict) -> dict:
    """Execute a single step. Reused across all stages."""
    name = step_info["step"]
    stage = step_info["stage"]
    return _do_work(name, stage)


@dg.op(out=dg.DynamicOut())
def plan_stage_2(config: StagedConfig, stage_1_results: list[dict]):
    """Yield DynamicOutputs for stage 2. Depends on stage 1 completing."""
    if len(config.stages) < 2:
        return
    for step in config.stages[1]:
        yield dg.DynamicOutput(
            {"step": step, "stage": 2}, mapping_key=f"s2_{step}"
        )


@dg.op(out=dg.DynamicOut())
def plan_stage_3(config: StagedConfig, stage_2_results: list[dict]):
    """Yield DynamicOutputs for stage 3. Depends on stage 2 completing."""
    if len(config.stages) < 3:
        return
    for step in config.stages[2]:
        yield dg.DynamicOutput(
            {"step": step, "stage": 3}, mapping_key=f"s3_{step}"
        )


@dg.op
def gather_staged(
    s1: list[dict], s2: list[dict], s3: list[dict]
) -> dict:
    all_results = s1 + s2 + s3
    return {"total_steps": len(all_results), "results": all_results}


@dg.graph_asset(group_name="dynamic_staged")
def staged_pipeline():
    """Staged fan-out: stage 1 → collect → stage 2 → collect → stage 3.

    Config: {"stages": [["A", "C"], ["B"], ["D", "F"]]}
    - Stage 1: A, C run in parallel
    - Stage 2: B runs after stage 1 completes
    - Stage 3: D, F run in parallel after stage 2 completes

    Each step is its own op with independent retries. Stages enforce ordering.
    """
    # Stage 1: fan-out → run → collect
    s1_items = plan_stage_1()
    s1_results = s1_items.map(run_staged_step).collect()

    # Stage 2: depends on stage 1 results → fan-out → run → collect
    s2_items = plan_stage_2(stage_1_results=s1_results)
    s2_results = s2_items.map(run_staged_step).collect()

    # Stage 3: depends on stage 2 results → fan-out → run → collect
    s3_items = plan_stage_3(stage_2_results=s2_results)
    s3_results = s3_items.map(run_staged_step).collect()

    return gather_staged(s1=s1_results, s2=s2_results, s3=s3_results)
