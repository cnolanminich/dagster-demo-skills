# dbt Cloud Partitions Support in Dagster - Analysis

## Current State

**The v2 dbt Cloud integration (`dbt_cloud_assets` decorator) does NOT support partitions.**

There are two dbt Cloud integrations in `dagster-dbt`:

| Integration | API | Partition Support | Status |
|---|---|---|---|
| `load_assets_from_dbt_cloud_job()` (v1, `cloud/`) | Legacy v1 API | Yes | Deprecated |
| `dbt_cloud_assets` decorator (v2, `cloud_v2/`) | v2 API | **No** | Recommended/Current |

The legacy v1 integration **does** support partitions via `partitions_def` and `partition_key_to_vars_fn` parameters, but it is deprecated in favor of the v2 integration which lacks this capability.

### How the Legacy v1 Handles Partitions

```python
# V1 (legacy) - HAS partition support
from dagster_dbt import load_assets_from_dbt_cloud_job

dbt_cloud_assets = load_assets_from_dbt_cloud_job(
    dbt_cloud=dbt_cloud_resource,
    job_id=12345,
    partitions_def=DailyPartitionsDefinition(start_date="2024-01-01"),
    partition_key_to_vars_fn=lambda partition_key: {
        "run_date": partition_key,
    },
)
```

At execution time, the v1 integration:
1. Gets the partition key from `context.partition_key`
2. Calls `partition_key_to_vars_fn(partition_key)` to map it to dbt variables
3. Appends `--vars '{"run_date": "2024-01-15"}'` to the dbt Cloud job command

### How dbt Core Handles Partitions (for comparison)

```python
# dbt Core - full partition support
@dbt_assets(
    manifest=manifest_path,
    partitions_def=DailyPartitionsDefinition(start_date="2024-01-01"),
)
def my_dbt_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    time_window = context.partition_time_window
    dbt_vars = {
        "min_date": time_window.start.isoformat(),
        "max_date": time_window.end.isoformat(),
    }
    yield from dbt.cli(["run", "--vars", json.dumps(dbt_vars)], context=context).stream()
```

The dbt Core approach gives users full control - they access the partition info from context and pass it as `--vars` to dbt CLI directly.

### What's Missing in V2

The v2 `dbt_cloud_assets` decorator (`cloud_v2/asset_decorator.py`) only accepts:
- `workspace` (DbtCloudWorkspace)
- `select`, `exclude`, `selector` (dbt selection strings)
- `name`, `group_name`
- `dagster_dbt_translator`

No `partitions_def`, `backfill_policy`, or variable-passing mechanism exists.

---

## Suggestions for Adding Partition Support to V2

### Approach 1: Follow the dbt Core Pattern (Recommended)

Add `partitions_def` and `backfill_policy` to `dbt_cloud_assets`, and let users control variable passing in their decorated function body:

**Changes needed:**

#### 1. `cloud_v2/asset_decorator.py` - Add partition parameters

```python
def dbt_cloud_assets(
    *,
    workspace: DbtCloudWorkspace,
    # ... existing params ...
    partitions_def: Optional[PartitionsDefinition] = None,
    backfill_policy: Optional[BackfillPolicy] = None,
) -> Callable[..., Any]:
    # If time-window partitions and no explicit backfill_policy, default to single_run
    if isinstance(partitions_def, TimeWindowPartitionsDefinition) and backfill_policy is None:
        backfill_policy = BackfillPolicy.single_run()

    # Pass partitions_def and backfill_policy through to the internal multi_asset() call
    ...
```

#### 2. `cloud_v2/client.py` - Support `steps_override` with vars

The dbt Cloud API's `steps_override` parameter allows overriding the commands run by a job. This can inject `--vars`:

```python
class DbtCloudWorkspaceClient:
    def trigger_job_run(
        self,
        job_id: int,
        steps_override: Optional[List[str]] = None,
        # Add: allow passing extra vars
        additional_vars: Optional[Mapping[str, Any]] = None,
    ) -> DbtCloudRun:
        if additional_vars:
            # Modify steps_override to append --vars to each dbt command
            vars_json = json.dumps(additional_vars)
            steps_override = [
                f"{step} --vars '{vars_json}'" for step in (steps_override or default_steps)
            ]
        ...
```

#### 3. `cloud_v2/run_handler.py` - Partition-aware events

```python
class DbtCloudJobRunResults:
    def to_default_asset_events(
        self,
        # Add partition_key parameter
        partition_key: Optional[str] = None,
    ) -> Iterator[Union[AssetMaterialization, AssetCheckResult]]:
        for event in self._events:
            # Include partition_key in materialization events
            if partition_key:
                event = event._replace(partition=partition_key)
            yield event
```

#### User-facing API after changes:

```python
@dbt_cloud_assets(
    workspace=dbt_cloud,
    partitions_def=DailyPartitionsDefinition(start_date="2024-01-01"),
)
def my_dbt_cloud_assets(context: AssetExecutionContext, dbt_cloud: DbtCloudWorkspace):
    # User maps partition key to dbt vars
    partition_key = context.partition_key
    dbt_vars = {"run_date": partition_key}

    # Trigger job with vars override
    yield from dbt_cloud.run(
        context=context,
        steps_override=[f"dbt run --vars '{json.dumps(dbt_vars)}'"],
    ).stream()
```

### Approach 2: Callback-Based (Like V1)

Add a `partition_key_to_vars_fn` parameter that automatically injects vars:

```python
@dbt_cloud_assets(
    workspace=dbt_cloud,
    partitions_def=DailyPartitionsDefinition(start_date="2024-01-01"),
    partition_key_to_vars_fn=lambda key: {"run_date": key},
)
def my_dbt_cloud_assets(context: AssetExecutionContext):
    # Partition vars are automatically injected - no user code needed
    ...
```

This is simpler for users but less flexible.

### Approach 3: Hybrid (Best of Both)

Support both patterns - provide `partition_key_to_vars_fn` for simple cases, and allow manual override in the function body for complex cases.

---

## Files That Need Modification

| File | Change |
|---|---|
| `dagster_dbt/cloud_v2/asset_decorator.py` | Add `partitions_def`, `backfill_policy`, optionally `partition_key_to_vars_fn` params |
| `dagster_dbt/cloud_v2/client.py` | Extend `trigger_job_run()` to support `additional_vars` or vars injection via `steps_override` |
| `dagster_dbt/cloud_v2/run_handler.py` | Make `to_default_asset_events()` partition-aware |
| `dagster_dbt/cloud_v2/resources.py` | May need partition-aware job triggering helpers |
| `dagster_dbt/cloud_v2/__init__.py` | Export new parameters |

## Workaround (Today)

Until v2 adds partition support, users can:

1. **Use the legacy v1 API** (`load_assets_from_dbt_cloud_job`) which has full partition support
2. **Wrap dbt Cloud API calls in a regular `@dg.asset`** with manual partition handling:

```python
import dagster as dg
import requests

@dg.asset(
    partitions_def=dg.DailyPartitionsDefinition(start_date="2024-01-01"),
)
def my_dbt_model(context: dg.AssetExecutionContext):
    partition_key = context.partition_key
    # Trigger dbt Cloud job via API with steps_override
    response = requests.post(
        f"https://cloud.getdbt.com/api/v2/accounts/{account_id}/jobs/{job_id}/run/",
        headers={"Authorization": f"Token {token}"},
        json={
            "cause": f"Triggered by Dagster for partition {partition_key}",
            "steps_override": [f"dbt run --vars '{{\"run_date\": \"{partition_key}\"}}'"],
        },
    )
    # Poll for completion...
```
