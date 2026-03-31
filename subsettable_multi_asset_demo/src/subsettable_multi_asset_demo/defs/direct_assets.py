"""Direct standalone assets — each is an independent @asset.

Materialize any subset by selecting them individually in the UI.
"""

import time

import dagster as dg


def _do_work(name: str, duration: float = 0.5) -> dict:
    """Simulate some work (e.g. an API call or query)."""
    start = time.time()
    time.sleep(duration)
    elapsed = time.time() - start
    return {"asset": name, "elapsed_seconds": round(elapsed, 3)}


@dg.asset(group_name="direct", tags={"step": "A"})
def direct_step_a() -> dg.MaterializeResult:
    result = _do_work("direct_step_a")
    return dg.MaterializeResult(metadata={"info": dg.MetadataValue.json(result)})


@dg.asset(group_name="direct", tags={"step": "B"})
def direct_step_b() -> dg.MaterializeResult:
    result = _do_work("direct_step_b")
    return dg.MaterializeResult(metadata={"info": dg.MetadataValue.json(result)})


@dg.asset(group_name="direct", tags={"step": "C"})
def direct_step_c() -> dg.MaterializeResult:
    result = _do_work("direct_step_c")
    return dg.MaterializeResult(metadata={"info": dg.MetadataValue.json(result)})


@dg.asset(group_name="direct", tags={"step": "D"})
def direct_step_d() -> dg.MaterializeResult:
    result = _do_work("direct_step_d")
    return dg.MaterializeResult(metadata={"info": dg.MetadataValue.json(result)})


@dg.asset(group_name="direct", tags={"step": "E"})
def direct_step_e() -> dg.MaterializeResult:
    result = _do_work("direct_step_e")
    return dg.MaterializeResult(metadata={"info": dg.MetadataValue.json(result)})


@dg.asset(group_name="direct", tags={"step": "F"})
def direct_step_f() -> dg.MaterializeResult:
    result = _do_work("direct_step_f")
    return dg.MaterializeResult(metadata={"info": dg.MetadataValue.json(result)})
