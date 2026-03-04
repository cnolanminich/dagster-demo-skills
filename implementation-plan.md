# Implementation Plan: dbt Cloud v2 Partition Support

## Goal

Add partition support to the `dbt_cloud_assets` decorator (v2) following the dbt Core pattern, where users get full control over mapping partition keys to dbt variables in their decorated function body.

## Confirmed: Variable Passing Mechanism

**`steps_override` with `--vars` is the correct approach.** Verified through the full code path:

1. `DbtCloudWorkspace.cli(args=["run", "--vars", json.dumps(vars)])` — accepts `args: Sequence[str]`
2. Internally joins args: `steps_override = [" ".join(["dbt", *args])]` → `["dbt run --vars {...}"]`
3. `client.trigger_job_run(job_id=..., steps_override=[...])` sends to dbt Cloud API
4. dbt Cloud API `POST /api/v2/accounts/{id}/jobs/{id}/run/` accepts `steps_override` as an array of dbt CLI command strings

The dbt Cloud API documentation confirms `steps_override` accepts any valid dbt CLI commands. Since `--vars` is standard dbt CLI syntax, it flows through naturally. This is also the pattern used by Airflow, Prefect, and GitHub Actions integrations with dbt Cloud.

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

## Step 2: Pass Variables via `cli()` Using `--vars`

**File:** `dagster_dbt/cloud_v2/resources.py` (no changes needed — mechanism already works)

### How it works (already implemented in Dagster source):

```python
# In DbtCloudWorkspace.cli():
full_dbt_args = [*args, *selection_args, *indirect_selection_args]

# In DbtCloudCliInvocation.run():
steps_override = [" ".join(["dbt", *args])]

# Sent to API:
client.trigger_job_run(job_id=job_id, steps_override=steps_override)
```

Users pass `--vars` through the existing `cli(args=[...])` interface:

```python
dbt_cloud.cli(
    args=["run", "--vars", json.dumps({"run_date": partition_key})],
    context=context,
)
```

### What to verify:
- No code changes needed in `resources.py` or `client.py` for variable passing
- The `cli()` → `steps_override` → API pipeline handles `--vars` correctly end-to-end
- Confirm via integration test that dbt Cloud receives and uses the variables

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
- In the `cli()` / `run()` / `stream()` method path, ensure the partition key from `context` is threaded through to event generation in Step 3
- If the user passes `context` to `dbt_cloud.cli(context=context, ...)`, extract `context.partition_key` (if `context.has_partition_key`) and forward it to `to_default_asset_events()`

### Acceptance Criteria:
- Partition key is automatically extracted from context and included in events
- No extra user code needed beyond passing `context` (which they already do)

---

## Step 5: Update Exports

**File:** `dagster_dbt/cloud_v2/__init__.py`

### Changes:
- No new public utilities needed — the approach uses existing `cli(args=[...])` interface
- Ensure any type changes are exported if needed

---

## Step 6: Add Tests

**Files:** `dagster_dbt/cloud_v2/tests/` (new test files)

### Test Plan

#### 6.1 Decorator Parameter Tests

| Test | Description |
|---|---|
| `test_dbt_cloud_assets_accepts_partitions_def` | Verify `dbt_cloud_assets` accepts a `partitions_def` parameter and the resulting asset definitions have the correct partition definition attached |
| `test_dbt_cloud_assets_accepts_backfill_policy` | Verify explicit `backfill_policy` is passed through to the underlying `multi_asset` |
| `test_dbt_cloud_assets_default_backfill_policy_for_time_window` | When `partitions_def` is `TimeWindowPartitionsDefinition` and no `backfill_policy` given, assert it defaults to `BackfillPolicy.single_run()` |
| `test_dbt_cloud_assets_no_default_backfill_for_static_partitions` | When `partitions_def` is `StaticPartitionsDefinition`, assert no default `backfill_policy` is set |
| `test_dbt_cloud_assets_without_partitions_unchanged` | Existing non-partitioned usage continues to work identically (regression test) |

#### 6.2 Variable Passing / `steps_override` Tests

| Test | Description |
|---|---|
| `test_cli_args_flow_to_steps_override` | Call `cli(args=["run", "--vars", '{"run_date": "2024-01-15"}'])` and assert the resulting `steps_override` sent to the API is `["dbt run --vars {\"run_date\": \"2024-01-15\"}"]` |
| `test_cli_args_with_select_and_vars` | Verify `--vars` coexists with `--select` flags in the same command, both appearing in the final `steps_override` |
| `test_vars_json_special_characters` | Verify that JSON with special characters (spaces, quotes, nested objects) is correctly serialized and passed through |
| `test_trigger_job_run_sends_steps_override` | Mock the HTTP client and verify `trigger_job_run()` sends the correct POST body with `steps_override` to the dbt Cloud API endpoint |

#### 6.3 Partition-Aware Event Tests

| Test | Description |
|---|---|
| `test_materialization_events_include_partition_key` | When `partition_key` is provided to event generation, all `AssetMaterialization` events have `partition=partition_key` set |
| `test_asset_check_events_include_partition_key` | When `partition_key` is provided, all `AssetCheckResult` events include the partition key |
| `test_events_without_partition_key_unchanged` | When no `partition_key` is provided (non-partitioned case), events have no partition set (regression) |

#### 6.4 Context-to-Event Wiring Tests

| Test | Description |
|---|---|
| `test_partition_key_extracted_from_context` | When `context.has_partition_key` is True, the partition key is automatically extracted and attached to emitted events |
| `test_no_partition_key_when_context_not_partitioned` | When `context.has_partition_key` is False, no partition key is attached to events |

#### 6.5 End-to-End Integration Tests

| Test | Description |
|---|---|
| `test_daily_partitioned_dbt_cloud_assets_e2e` | Full execution flow: define a `dbt_cloud_assets` with `DailyPartitionsDefinition`, execute for a specific partition, mock the dbt Cloud API, and verify: (1) `steps_override` contains `--vars` with the correct date, (2) materialization events have the correct partition key |
| `test_static_partitioned_dbt_cloud_assets_e2e` | Same as above but with `StaticPartitionsDefinition` (e.g., regions: `["us", "eu", "apac"]`), verifying the partition key flows through to `--vars` and events |
| `test_weekly_partitioned_dbt_cloud_assets_e2e` | With `WeeklyPartitionsDefinition`, verify `context.partition_time_window` provides correct start/end dates that can be passed as `--vars` |
| `test_backfill_multiple_partitions` | Trigger materialization for multiple partitions and verify each produces separate API calls with correct per-partition `--vars` |

#### 6.6 Edge Case Tests

| Test | Description |
|---|---|
| `test_empty_vars_dict` | Passing `--vars '{}'` works without error |
| `test_partition_key_with_special_characters` | Partition keys containing special characters (e.g., `/`, `:`) are handled correctly |
| `test_cli_called_without_context` | When `cli()` is called without `context`, no partition logic is triggered (backward compat) |

---

## Step 7: Documentation / Examples

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
    partition_key = context.partition_key
    dbt_vars = {"run_date": partition_key}

    yield from dbt_cloud.cli(
        args=["run", "--vars", json.dumps(dbt_vars)],
        context=context,
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

    yield from dbt_cloud.cli(
        args=["run", "--vars", json.dumps(dbt_vars)],
        context=context,
    ).stream()
```

### With static partitions (e.g., by region):

```python
@dbt_cloud_assets(
    workspace=dbt_cloud,
    partitions_def=StaticPartitionsDefinition(["us", "eu", "apac"]),
)
def my_dbt_cloud_assets(context: AssetExecutionContext, dbt_cloud: DbtCloudWorkspace):
    region = context.partition_key
    dbt_vars = {"target_region": region}

    yield from dbt_cloud.cli(
        args=["run", "--vars", json.dumps(dbt_vars)],
        context=context,
    ).stream()
```

---

## Summary of Files to Modify

| # | File | Change |
|---|---|---|
| 1 | `cloud_v2/asset_decorator.py` | Add `partitions_def` and `backfill_policy` params, pass to `multi_asset()` |
| 2 | `cloud_v2/run_handler.py` | Add `partition_key` param to event generation |
| 3 | `cloud_v2/resources.py` | Thread partition key from context to event generation |
| 4 | `cloud_v2/__init__.py` | Export any new public APIs if needed |
| 5 | `cloud_v2/tests/` | Add partition-specific test cases (see Step 6) |

**Note:** No changes needed to `cloud_v2/client.py` — the existing `trigger_job_run(steps_override=...)` already supports the mechanism. The `cli()` method in `resources.py` already converts `args` to `steps_override`.

## Risks & Considerations

- **Multi-partition support**: Initial implementation targets single-dimension partitions; multi-dimensional partitions can be added later
- **Backfill behavior**: Large backfills will trigger many dbt Cloud jobs; document rate limiting considerations
- **Existing users**: All changes are additive — no breaking changes to existing non-partitioned usage
- **`steps_override` replaces all job steps**: Users must include the full dbt command (including `run` or `build`) — this is standard dbt Cloud API behavior, not a limitation of our implementation
