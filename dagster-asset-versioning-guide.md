# Dagster Asset Versioning & Staleness for ML Pipelines

## 1. `code_version`: Manually Set, Not Auto-Hashed

**`code_version` is a manually assigned string** on the `@asset` decorator or `AssetSpec`. Dagster does **not** automatically hash your function source code.

```python
import dagster as dg

@dg.asset(code_version="1.0.0")
def trained_model(features):
    ...
```

There is an [open feature request (dagster-io/dagster#15242)](https://github.com/dagster-io/dagster/issues/15242) for automatic source-code hashing (e.g. `CodeVersion.auto()`), but it was **not implemented**. Dagster maintainers intentionally chose not to build this because:

- Simple `inspect.getsource()` hashing is fragile — it misses imported functions, package version changes, and external dependencies.
- False negatives: a real code change in an imported utility wouldn't bump the version.
- False positives: a cosmetic change (whitespace, comment) would invalidate all downstream assets.

### DIY Auto-Hashing (Use With Caution)

You can build your own, but understand the limitations:

```python
import hashlib, inspect

def auto_code_version(fn):
    """Derive code_version from function source hash. Only captures the
    function body itself — NOT imports, called helpers, or package versions."""
    return hashlib.md5(inspect.getsource(fn).encode()).hexdigest()[:8]
```

**What triggers a change with this approach:**
- Any edit to the function body (logic, constants, comments, whitespace)

**What does NOT trigger a change:**
- Changes to imported modules or helper functions called by the asset
- Dependency/package version upgrades
- Changes to configuration or environment variables
- Changes to data schemas in external systems

**Bottom line:** Manual `code_version` strings (e.g. semver or date-based) are the recommended and most reliable approach.

---

## 2. How Dagster Computes Versions Internally

Dagster has two version concepts:

| Concept | Who Sets It | What It Represents |
|---------|-------------|--------------------|
| **`code_version`** | You (manually) | Version of the computation logic |
| **`data_version`** | Dagster (auto-generated) or you (via `DataVersion`) | Fingerprint of the asset's output value |

### Data Version (Logical Version)

Dagster auto-generates a **data version** (also called "logical version") by hashing together:

1. The asset's `code_version`
2. The `data_version` of each input (upstream asset)

This means: if neither your code nor your inputs changed, the data version stays the same, and Dagster knows the output would be identical — **enabling caching/skip behavior**.

---

## 3. The "Unsynced" Label — Manual Staleness Detection in the UI

### What Causes an Asset to Show "Unsynced"

An asset is marked **Unsynced** in the Dagster UI when any of these are true:

1. **Code version changed** — the `code_version` on the asset definition differs from the `code_version` recorded during its last materialization.
2. **Dependencies changed** — an upstream dependency was added or removed since the last materialization.
3. **Upstream data changed** — a direct parent asset was re-materialized (producing a new data version) after the downstream asset's last materialization.

### Non-Transitive Propagation (v1.8.0+)

As of Dagster 1.8.0, **Unsynced is NOT transitive**. This is a deliberate design choice:

```
A (code_version changed → Unsynced)
└── B (direct child → Unsynced, because A was re-materialized after B)
    └── C (grandchild → NOT Unsynced, until B is actually re-materialized)
```

- Only direct children of a changed/re-materialized asset show as Unsynced.
- Grandchildren and deeper descendants do **not** cascade to Unsynced automatically.
- This prevents "Unsynced label fatigue" across large graphs and improves UI performance.

### Using "Materialize Unsynced" in the UI

The Dagster UI provides a **"Materialize Unsynced"** button that selects all assets currently labeled Unsynced and launches a materialization run for them. This is the manual workflow for selective re-computation:

1. Change `code_version` on Step 4 (e.g. `"1.0.0"` → `"1.1.0"`)
2. Redeploy your code location
3. Open the asset graph in the Dagster UI
4. Step 4 shows the **Unsynced** label; Steps 1–3 do not
5. Click **"Materialize Unsynced"** — only Step 4 runs

---

## 4. Observable Source Assets and `DataVersion`

For external data sources (files, APIs, databases you don't control), use **observable source assets** to report data versions:

```python
import dagster as dg
import hashlib

@dg.observable_source_asset
def raw_training_data():
    """Observe an external CSV file and report its data version."""
    content = open("/data/training.csv", "rb").read()
    version = hashlib.sha256(content).hexdigest()[:16]
    return dg.DataVersion(version)
```

- Click **"Observe Sources"** in the UI (or run via a sensor/schedule) to check for new data versions.
- If the returned `DataVersion` differs from the last observation, downstream assets are marked **Unsynced**.
- This is how Dagster detects upstream data changes for external sources without re-materializing them.

---

## 5. Using Versioning with Jobs and Schedules (`stale_assets_only`)

Declarative Automation isn't the only option. You can use traditional **jobs + schedules** with the `stale_assets_only` parameter on `RunRequest`:

```python
import dagster as dg

ml_pipeline_job = dg.define_asset_job(
    "ml_pipeline_job",
    selection=[raw_data, features, trained_model, evaluation],
)

@dg.schedule(
    cron_schedule="0 2 * * *",  # Daily at 2 AM
    job=ml_pipeline_job,
)
def nightly_ml_refresh():
    """Only re-materialize assets that are actually stale."""
    return dg.RunRequest(stale_assets_only=True)
```

### How `stale_assets_only=True` Works

- The schedule fires on the cron tick as usual.
- Dagster evaluates which assets in the job's selection are **stale** (Unsynced).
- Only stale assets are included in the run. Non-stale assets are skipped entirely.
- If no assets are stale, no run is launched.
- If passed without an asset selection, all stale assets in the job are materialized.

### Combining With Observable Source Assets

For a full ML pipeline with external data detection:

```python
@dg.observable_source_asset
def training_data_source():
    version = compute_hash_of_external_data()
    return dg.DataVersion(version)

@dg.asset(code_version="1.0.0")
def features(training_data_source): ...

@dg.asset(code_version="1.0.0")
def trained_model(features): ...

@dg.asset(code_version="1.0.0")
def evaluation(trained_model): ...

# Observe sources on a schedule, then materialize stale downstream
observe_job = dg.define_asset_job(
    "observe_sources", selection=dg.AssetSelection.all_asset_checks()
)

ml_job = dg.define_asset_job(
    "ml_pipeline", selection=[features, trained_model, evaluation]
)

@dg.schedule(cron_schedule="0 1 * * *", job=observe_job)
def observe_schedule():
    return dg.RunRequest()

@dg.schedule(cron_schedule="0 2 * * *", job=ml_job)
def ml_schedule():
    return dg.RunRequest(stale_assets_only=True)
```

---

## 6. Comparison: Dagster vs ZenML Caching

| Aspect | ZenML | Dagster |
|--------|-------|---------|
| **Version detection** | Automatic hash of inputs + code | Manual `code_version` + auto `data_version` |
| **Granularity** | Step-level within a pipeline run | Asset-level across the entire graph |
| **Skip mechanism** | Cached output returned mid-run | Non-stale assets excluded from run entirely |
| **Trigger** | Automatic on every run | `stale_assets_only`, Declarative Automation, or manual "Materialize Unsynced" |
| **External data** | Materializer-level caching | Observable source assets with `DataVersion` |
| **Propagation** | Full transitive | Non-transitive (direct children only, as of v1.8.0) |
| **Auto code hashing** | Built-in | Not built-in (DIY possible but not recommended) |

### Key Dagster Advantage

Dagster's approach is **graph-aware at the orchestration level**, not just within a single run. The Unsynced status and `stale_assets_only` work across independent runs and schedules — you don't need to re-run the entire pipeline to get selective execution.

### Key Dagster Limitation

The non-transitive Unsynced propagation means that after re-materializing Step 4, you may need to check again whether deeper downstream assets need updating. In practice for linear ML pipelines this is rarely an issue, but for wide DAGs it requires iterative materialization or Declarative Automation with `eager()` to propagate changes automatically.

---

## 7. Recommended Pattern for ML Pipelines

```python
import dagster as dg

@dg.observable_source_asset
def training_data():
    """Check if training data has changed."""
    return dg.DataVersion(compute_data_fingerprint())

@dg.asset(
    code_version="1.0.0",
    automation_condition=dg.AutomationCondition.eager(),
)
def features(training_data):
    """Feature engineering — reruns if training data or code changes."""
    ...

@dg.asset(
    code_version="1.0.0",
    automation_condition=dg.AutomationCondition.eager(),
)
def trained_model(features):
    """Model training — reruns only if features change."""
    ...

@dg.asset(
    code_version="1.1.0",  # <-- bumped: only this asset is stale
    automation_condition=dg.AutomationCondition.eager(),
)
def evaluation(trained_model):
    """Evaluation — code changed, so this auto-rematerializes."""
    ...
```

With `eager()` on all assets:
- Changing `evaluation`'s `code_version` triggers only `evaluation`.
- If `training_data` observation detects new data, `features` → `trained_model` → `evaluation` cascade automatically.
- No unnecessary re-computation of unchanged steps.

---

## Sources

- [Asset Versioning and Caching — Dagster Docs](https://docs.dagster.io/guides/build/assets/asset-versioning-and-caching)
- [Unsynced Status Propagation Discussion (dagster-io/dagster#25248)](https://github.com/dagster-io/dagster/discussions/25248)
- [Auto Code Versioning Feature Request (dagster-io/dagster#15242)](https://github.com/dagster-io/dagster/issues/15242)
- [Materialize Stale Assets on Schedule (dagster-io/dagster#14755)](https://github.com/dagster-io/dagster/discussions/14755)
- [Support Rematerialization of Stale Assets in Schedules (dagster-io/dagster#10726)](https://github.com/dagster-io/dagster/issues/10726)
- [Partitioned Assets and code_version (dagster-io/dagster#22704)](https://github.com/dagster-io/dagster/issues/22704)
- [Declarative Scheduling Blog Post](https://dagster.io/blog/declarative-scheduling)
