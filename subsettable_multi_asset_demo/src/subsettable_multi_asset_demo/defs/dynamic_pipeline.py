"""Dynamic fan-out pipeline — a planner op determines which steps run at runtime.

Uses DynamicOut to yield one DynamicOutput per requested step, then .map()
runs each step as an independent op. Each step gets its own op execution
with independent retries and observability in the Dagster UI.

Tradeoff: .map() runs steps in PARALLEL (not sequentially). If ordering
matters, see configurable_pipeline.py which uses config + multi-asset.
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


STEP_FUNCTIONS = {
    "A": lambda: _do_work("A"),
    "B": lambda: _do_work("B"),
    "C": lambda: _do_work("C"),
    "D": lambda: _do_work("D"),
    "E": lambda: _do_work("E"),
    "F": lambda: _do_work("F"),
}


class DynamicStepConfig(dg.Config):
    """Configure which steps to fan out at runtime.

    Example: {"steps": ["C", "B", "A"]} — each step becomes its own op execution.
    Note: execution order is NOT guaranteed — steps run in parallel via .map().
    """

    steps: list[str] = ["C", "B", "A"]


@dg.op(out=dg.DynamicOut())
def plan_steps(config: DynamicStepConfig):
    """Planner op: reads config and yields a DynamicOutput for each requested step."""
    valid_steps = set(STEPS)
    for step_name in config.steps:
        if step_name not in valid_steps:
            raise dg.Failure(
                description=f"Unknown step '{step_name}'. Valid steps: {STEPS}"
            )
        yield dg.DynamicOutput(step_name, mapping_key=step_name)


@dg.op
def run_step(step_name: str) -> dict:
    """Worker op: runs a single step. Gets cloned for each DynamicOutput via .map()."""
    fn = STEP_FUNCTIONS[step_name]
    return fn()


@dg.op
def collect_results(results: list[dict]) -> dict:
    """Gather all step results after fan-in."""
    return {"completed_steps": len(results), "results": results}


@dg.graph_asset(group_name="dynamic")
def dynamic_pipeline():
    """Dynamic fan-out: planner determines steps, .map() runs each independently.

    Each step is a separate op execution with its own retries and logs.
    Steps run in parallel — order is NOT guaranteed.
    """
    step_names = plan_steps()
    results = step_names.map(run_step)
    return collect_results(results.collect())
