# Implementation Plan: dbt Cloud v2 Partition Support (Approach 1)

## Goal

Add partition support to the `dbt_cloud_assets` decorator (v2) following the dbt Core pattern, where users get full control over mapping partition keys to dbt variables in their decorated function body.

---

## Step 1: Extend the `dbt_cloud_assets` Decorator

**File:** `dagster_dbt/cloud_v2/asset_decorator.py`

### Changes:
- Add `partitions_def: Optional[PartitionsDefinition] = None` parameter
- Add `backfill_policy: Optional[BackfillPolicy] = None` parameter
- When `partitions_def` is a `TimeWindowPartitionsDefinition` and no `backfill_policy` is provided, default to `BackfillPolicy.single_run()`
- Pass both parameters through to the internal `multi_asset()` call that constructs the asset definition

### Acceptance Criteria:
- `dbt_cloud_assets` accepts `partitions_def` and `backfill_policy` without error
- Assets created with `partitions_def` show partitions in Dagster UI
- `context.partition_key` and `context.partition_time_window` are accessible inside the decorated function

---

## Step 2: Support Variable Injection via `steps_override` in the Client

**File:** `dagster_dbt/cloud_v2/client.py`

### Changes:
- No new parameters needed on the client if we follow the pure dbt Core approach — the user constructs `steps_override` themselves in the function body
- However, consider adding a convenience helper `inject_vars_into_steps(steps: List[str], vars: Dict) -> List[str]` that appends `--vars '{...}'` to each dbt command in a steps list
- Ensure `trigger_job_run()` correctly passes `steps_override` to the dbt Cloud API (verify this already works; if not, add support)

### Acceptance Criteria:
- `steps_override` with `--vars` is correctly sent to dbt Cloud API
- dbt Cloud job executes with the overridden variables
- Helper utility (if added) correctly appends vars to step commands

---

## Step 3: Make Event Handling Partition-Aware

**File:** `dagster_dbt/cloud_v2/run_handler.py`

### Changes:
- Modify `DbtCloudJobRunResults.to_default_asset_events()` to accept an optional `partition_key: Optional[str] = None` parameter
- When `partition_key` is provided, attach it to each `AssetMaterialization` and `AssetCheckResult` event
- This ensures Dagster correctly records which partition was materialized

### Acceptance Criteria:
- Materialization events include the partition key when provided
- Asset check results include the partition key when provided
- Non-partitioned usage (no `partition_key` passed) continues to work unchanged

---

## Step 4: Wire Partition Context Through the Run/Stream API

**File:** `dagster_dbt/cloud_v2/resources.py`

### Changes:
- In the `run()` / `stream()` method path that the user calls from inside their decorated function, ensure the partition key from `context` is threaded through to the event generation in Step 3
- If the user passes `context` to `dbt_cloud.run(context=context, ...)`, extract `context.partition_key` (if `context.has_partition_key`) and forward it to `to_default_asset_events()`

### Acceptance Criteria:
- Partition key is automatically extracted from context and included in events
- No extra user code needed beyond passing `context` (which they already do)

---

## Step 5: Update Exports

**File:** `dagster_dbt/cloud_v2/__init__.py`

### Changes:
- Ensure any new public utilities (e.g., `inject_vars_into_steps` helper) are exported
- No changes needed if we only modify existing function signatures

### Acceptance Criteria:
- All new public API surfaces are importable from `dagster_dbt`

---

## Step 6: Add Tests

**Files:** `dagster_dbt/cloud_v2/tests/` (new test files)

### Test Cases:

1. **Decorator accepts partition params** — `dbt_cloud_assets` with `partitions_def` creates assets with correct partition definition
2. **Backfill policy defaults** — `TimeWindowPartitionsDefinition` without explicit `backfill_policy` defaults to `single_run()`
3. **Partition key accessible in function** — `context.partition_key` works inside decorated function
4. **Steps override with vars** — dbt Cloud API receives correct `steps_override` with `--vars`
5. **Partition-aware events** — Materialization events include partition key
6. **Non-partitioned backward compat** — Existing non-partitioned usage is unaffected
7. **Daily, weekly, monthly partitions** — Various partition types work correctly
8. **Static partitions** — Non-time-window partitions (e.g., `StaticPartitionsDefinition`) work

### Acceptance Criteria:
- All tests pass
- No regressions in existing test suite

---

## Step 7: Add Documentation / Examples

### User-Facing API (final shape):

```python
from dagster import AssetExecutionContext, DailyPartitionsDefinition
from dagster_dbt import dbt_cloud_assets, DbtCloudWorkspace
import json

@dbt_cloud_assets(
    workspace=dbt_cloud,
    partitions_def=DailyPartitionsDefinition(start_date="2024-01-01"),
)
def my_dbt_cloud_assets(context: AssetExecutionContext, dbt_cloud: DbtCloudWorkspace):
    # Map partition to dbt vars — user has full control
    partition_key = context.partition_key
    dbt_vars = {"run_date": partition_key}

    # Trigger job with vars override
    yield from dbt_cloud.run(
        context=context,
        steps_override=[f"dbt run --vars '{json.dumps(dbt_vars)}'"],
    ).stream()
```

### With time windows:

```python
@dbt_cloud_assets(
    workspace=dbt_cloud,
    partitions_def=DailyPartitionsDefinition(start_date="2024-01-01"),
)
def my_dbt_cloud_assets(context: AssetExecutionContext, dbt_cloud: DbtCloudWorkspace):
    time_window = context.partition_time_window
    dbt_vars = {
        "min_date": time_window.start.isoformat(),
        "max_date": time_window.end.isoformat(),
    }

    yield from dbt_cloud.run(
        context=context,
        steps_override=[f"dbt run --vars '{json.dumps(dbt_vars)}'"],
    ).stream()
```

---

## Summary of Files to Modify

| # | File | Change |
|---|---|---|
| 1 | `cloud_v2/asset_decorator.py` | Add `partitions_def` and `backfill_policy` params, pass to `multi_asset()` |
| 2 | `cloud_v2/client.py` | Verify `steps_override` support, optionally add vars helper |
| 3 | `cloud_v2/run_handler.py` | Add `partition_key` param to event generation |
| 4 | `cloud_v2/resources.py` | Thread partition key from context to event generation |
| 5 | `cloud_v2/__init__.py` | Export any new public APIs |
| 6 | `cloud_v2/tests/` | Add partition-specific test cases |

## Risks & Considerations

- **dbt Cloud API `steps_override`**: Confirm the v2 API supports this field — the v1 API does, but v2 behavior should be verified
- **Multi-partition support**: The initial implementation targets single-dimension partitions; multi-dimensional partitions can be added later
- **Backfill behavior**: Large backfills will trigger many dbt Cloud jobs; document rate limiting considerations
- **Existing users**: All changes are additive — no breaking changes to existing non-partitioned usage
