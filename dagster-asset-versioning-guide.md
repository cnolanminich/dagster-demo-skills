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

### DIY Auto-Hashing — Three Strategies (see `auto_code_version.py`)

We provide a utility module `auto_code_version.py` with three strategies of increasing coverage. Each trades off convenience against false-positive/false-negative risk.

#### Strategy 1: Shallow hash (`auto_code_version`)

Hashes raw function source via `inspect.getsource()` — the simplest approach.

```python
from auto_code_version import auto_code_version

def _train_impl(features):
    model = fit(features)
    return model

@dg.asset(code_version=auto_code_version(_train_impl))
def trained_model(features):
    return _train_impl(features)
```

| Triggers a change | Does NOT trigger a change |
|---|---|
| Any edit to the function body | Changes to imported helpers (`from mylib import preprocess`) |
| Whitespace / comment changes (false positive) | Package version upgrades (`sklearn 1.4→1.5`) |
| Renamed variables | Environment variable / config changes |
| | External schema changes |

#### Strategy 2: Normalized hash (`auto_code_version_normalized`)

Parses the function into an AST, strips docstrings and whitespace, then hashes the canonical tree. Avoids false positives from formatting-only changes.

```python
from auto_code_version import auto_code_version_normalized

@dg.asset(code_version=auto_code_version_normalized(my_func))
def my_asset(): ...
```

| Triggers a change | Does NOT trigger a change |
|---|---|
| Logic changes, new/removed statements | Whitespace, comment, docstring edits |
| Renamed variables | Changes to imported helpers |
| Changed constants/literals | Package upgrades |

#### Strategy 3: Deep hash (`auto_code_version_deep`)

Hashes the function **plus** explicitly listed dependency callables and an arbitrary salt string. This is the closest analog to ZenML's full cache key.

```python
from auto_code_version import auto_code_version_deep
from mylib import preprocess, build_features
import sklearn

@dg.asset(
    code_version=auto_code_version_deep(
        _train_impl,
        deps=[preprocess, build_features],
        extra=sklearn.__version__,
    )
)
def trained_model(features):
    return _train_impl(features)
```

| Triggers a change | Does NOT trigger a change |
|---|---|
| Edit to main function body | Unlisted helper changes (false negative) |
| Edit to any listed `deps` function | C-extension functions (falls back to `repr()`) |
| Change in `extra` string (e.g. package version) | Env vars, config, external schemas |

#### Caveat Summary For All Strategies

- **Evaluated at import time** — the hash is computed when the module loads, not at materialization time.
- **`inspect.getsource()` requires source files** — won't work on functions defined in a REPL, compiled `.pyc`-only distributions, or C extensions.
- **Dynamic functions** (e.g. generated inside a factory loop) may produce unstable hashes across interpreter restarts.
- **For production**, Dagster maintainers recommend manual `code_version` strings (semver or date-based) as the most reliable approach — see [dagster-io/dagster#15242](https://github.com/dagster-io/dagster/issues/15242) for the full rationale.

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

## 6. Deep Comparison: Dagster vs ZenML Caching

### How ZenML's Cache Key Works (internals)

ZenML computes an **MD5 hash** that incorporates all of the following:

| Component | What it captures |
|-----------|-----------------|
| Workspace ID | Isolates caches per workspace/tenant |
| Artifact store ID + path | Ties the cache to a specific storage backend |
| **Step source code** | `inspect.getsource()` of the `@step` function |
| Step parameters | All parameters passed to the step |
| Input artifact names + IDs | The exact artifact versions consumed |
| Output artifact names + source codes | Output materializer definitions |
| Output materializer source codes | How outputs will be serialized |
| Custom cache key (optional) | Artifact-store-specific salt (e.g. `LocalArtifactStore` includes client ID) |

If this composite hash matches a previous step run, ZenML **skips execution entirely** and reuses the cached output artifacts. This happens transparently within a pipeline run — the step appears as "cached" in the run DAG.

**Key ZenML behaviors:**
- Caching is **on by default** (`enable_cache=True`)
- Every step is checked independently — if Step 3 is cached but Step 4 is not, only Step 4 runs
- The source code hash means **any edit to the function body** (including whitespace) invalidates the cache
- External artifacts currently **invalidate caching** for the step and all downstream steps (value-based caching is being added)

### Side-by-Side Comparison

| Aspect | ZenML | Dagster |
|--------|-------|---------|
| **Code change detection** | Automatic `inspect.getsource()` hash, built-in | Manual `code_version` string (DIY auto-hash possible via `auto_code_version.py`) |
| **Input change detection** | Automatic — input artifact IDs in the hash | Automatic — `data_version` = hash(`code_version` + input `data_version`s) |
| **Parameter change detection** | Automatic — step params in the hash | Manual — fold into `code_version` or use `extra` salt in `auto_code_version_deep` |
| **Cache key scope** | Workspace + artifact store + code + inputs + outputs | `code_version` + upstream `data_version`s |
| **Granularity** | Step-level within a single pipeline run | Asset-level across the entire graph and across runs |
| **Skip mechanism** | Step skipped mid-run, cached output artifact returned | Non-stale assets never selected for execution |
| **When is the check done?** | At the start of each step execution | Before the run is even launched (`stale_assets_only`) or continuously (Declarative Automation) |
| **Cross-run awareness** | Yes — cache persists across runs in the artifact store | Yes — Unsynced status persists in the Dagster instance |
| **External data sources** | External artifacts invalidate caching (known limitation) | Observable source assets with `DataVersion` — first-class support |
| **Staleness propagation** | Transitive — if Step 2 reruns, Step 3 cache is invalidated via new input artifact IDs | Non-transitive (v1.8.0+) — only direct children show Unsynced |
| **Default behavior** | Caching on, zero config | No caching unless `code_version` is set |
| **Disable caching** | `@step(enable_cache=False)` | Omit `code_version` (or don't use `stale_assets_only`) |

### What ZenML Gets Right That Dagster Doesn't (Out of the Box)

1. **Zero-config code change detection** — ZenML hashes step source automatically. In Dagster, you must manually set/bump `code_version` or wire up `auto_code_version.py`.
2. **Parameter-aware caching** — ZenML includes step parameters in the hash. Dagster's `code_version` is static at definition time and doesn't incorporate runtime config.
3. **Transitive invalidation** — When ZenML re-runs Step 2 with a new output artifact, Step 3's cache key changes automatically (different input artifact ID). Dagster's Unsynced label stops at direct children.

### What Dagster Gets Right That ZenML Doesn't

1. **Graph-level orchestration** — Dagster can skip assets *before a run starts* (`stale_assets_only`, "Materialize Unsynced"). ZenML must start the pipeline run and check each step sequentially.
2. **External data as first-class citizens** — Observable source assets with `DataVersion` cleanly detect upstream data changes. ZenML's external artifacts currently break caching entirely.
3. **Selective execution across runs** — You can materialize a single stale asset without re-running the entire pipeline. ZenML ties caching to pipeline runs.
4. **Declarative Automation** — `AutomationCondition.eager()` propagates changes automatically without any pipeline definition. ZenML requires explicit pipeline execution.
5. **Explicit over implicit** — Manual `code_version` avoids false positives from cosmetic edits and false negatives from helper changes. The trade-off is more work for the developer.

### Scenario: "Only Step 4 code changed" — Both Systems

**ZenML:**
```
Run pipeline →
  Step 1: cache HIT (same code + same inputs) → skip, reuse output
  Step 2: cache HIT → skip, reuse output
  Step 3: cache HIT → skip, reuse output
  Step 4: cache MISS (source code hash changed) → execute
```
All four steps are *attempted* but three are skipped via cache lookup. The pipeline run still appears with all four steps, three marked "cached."

**Dagster (with `stale_assets_only`):**
```
Schedule fires →
  Dagster checks staleness: only Step 4 is Unsynced
  Run is launched with ONLY Step 4 in the selection
  Steps 1–3 are not part of the run at all
```
Steps 1–3 never enter a run. The run contains only Step 4.

---

## 7. Making Dagster Behave Like ZenML: `@cached_asset`

The gap between Dagster and ZenML boils down to two missing defaults:
1. **No auto code hashing** — you must set `code_version` manually
2. **No auto propagation** — the Unsynced label doesn't cascade transitively

We can close both gaps with the `@cached_asset` decorator (see `auto_code_version.py`), which combines auto-hashed `code_version` with `AutomationCondition.eager()`:

### Before (manual Dagster)

```python
import dagster as dg

@dg.asset(code_version="1.0.0")  # must remember to bump
def features(raw_data): ...

@dg.asset(code_version="1.0.0")
def trained_model(features): ...

@dg.asset(code_version="1.1.0")  # forgot to bump? silent staleness
def evaluation(trained_model): ...
```

### After (`@cached_asset` — ZenML-like)

```python
from auto_code_version import cached_asset

@cached_asset
def features(raw_data):
    return engineer_features(raw_data)

@cached_asset
def trained_model(features):
    return fit_model(features)

@cached_asset
def evaluation(trained_model):
    return evaluate(trained_model)
```

That's it. No manual version strings. Under the hood, each asset gets:
- `code_version` = AST-normalized hash of the function source
- `automation_condition` = `AutomationCondition.eager()`

### How This Achieves ZenML-Like Behavior

| ZenML behavior | How `@cached_asset` replicates it |
|---|---|
| Code change → cache miss | Source hash changes → `code_version` changes → asset marked Unsynced |
| Upstream reruns → downstream cache miss | `eager()` fires when any upstream re-materializes → transitive propagation |
| No change → skip | Code hash unchanged + no upstream update → asset stays synced, not executed |
| Zero config | Just `@cached_asset` — no version strings to manage |

### The Transitive Propagation Solution

The Unsynced UI label is non-transitive (stops at direct children). But **`eager()` Declarative Automation IS effectively transitive** because it works in a chain:

```
A changes → A re-materializes
         → B sees upstream update → eager() fires → B re-materializes
                                 → C sees upstream update → eager() fires → C re-materializes
```

Each hop takes ~30 seconds (the automation sensor evaluation interval), so a 4-step pipeline cascades in ~90 seconds. This is slower than ZenML (which resolves within a single run), but the result is the same: only changed assets and their true downstream dependents re-execute.

### Advanced: Adding Helper Deps and Package Versions

```python
from auto_code_version import cached_asset
from mylib import preprocess, build_features
import sklearn

@cached_asset(deps=[preprocess, build_features], extra=sklearn.__version__)
def trained_model(features):
    preprocessed = preprocess(features)
    X = build_features(preprocessed)
    return sklearn.ensemble.RandomForestClassifier().fit(X, y)
```

Now changes to `preprocess`, `build_features`, **or** an sklearn upgrade all trigger re-materialization.

### Prerequisites

- **Enable the automation sensor**: Toggle on `default_automation_condition_sensor` in the Dagster UI under **Automation → Sensors**. Without this, `eager()` conditions are never evaluated.
- **Assets must be in the same code location** for same-run grouping. Cross-location assets cascade via separate runs.

### Remaining Gaps vs ZenML

Even with `@cached_asset`, Dagster still differs from ZenML in these ways:

| Gap | Why it exists | Workaround |
|-----|---------------|------------|
| **Parameters not in hash** | Dagster `code_version` is static at import time; ZenML hashes runtime params | Pass config values in the `extra` salt |
| **~30s delay per hop** | `eager()` evaluates on a sensor tick interval | Acceptable for ML pipelines (training takes minutes/hours anyway) |
| **`inspect.getsource` limitations** | Can't hash C extensions, dynamic code | Use `extra` for package `__version__` strings |
| **No artifact-store-aware isolation** | ZenML scopes cache to workspace + artifact store | Dagster's Unsynced is scoped to the instance; use separate deployments for isolation |

---

## 8. When Should an ML Specialist Prefer Each?

### Choose Dagster when:

**You have a production data platform, not just an ML pipeline.**

- Your ML pipeline is part of a larger data ecosystem (ingestion, transformation, analytics, ML) and you want **one orchestrator for everything**.
- You need **cross-run selective execution** — e.g., "just re-train the model" without re-running the entire pipeline, even ad-hoc from the UI.
- Your data sources are external (S3 files, databases, APIs) and you want **first-class change detection** via observable source assets + `DataVersion`.
- You care about **asset-level lineage and observability** — every materialization is tracked, versioned, and visible in the asset graph UI.
- You want **multiple automation strategies**: some assets on cron, some eager, some manual — mixed within the same graph.
- Your pipeline has **shared assets** consumed by multiple downstream pipelines (e.g. a feature store used by 5 models). Dagster's asset graph handles fan-out naturally; ZenML's pipeline-scoped caching doesn't.
- You're already using Dagster for data engineering and want to **add ML without a second orchestrator**.

**Dagster's sweet spot:** Platform teams running mixed data + ML workloads where assets are the primary abstraction and selective execution across the entire graph matters more than zero-config caching within a single pipeline.

### Choose ZenML when:

**You are an ML team that wants pipeline caching to "just work."**

- Your primary concern is **experiment iteration speed** — change code, re-run, and only wait for what actually changed.
- You want **zero configuration** — no version strings, no decorators, no automation conditions. Caching is on by default and covers code + params + inputs automatically.
- Your pipeline is a **linear ML workflow** (preprocess → train → evaluate → deploy) and you don't need cross-pipeline asset sharing.
- You want **infrastructure flexibility** — ZenML's stack abstraction lets you swap orchestrators (Airflow, Kubeflow, Vertex AI, local) while keeping the same caching behavior.
- You value **automatic parameter-aware caching** — hyperparameter changes invalidate only the affected step and downstream, without manual version management.
- Your team is **ML-first** and doesn't want to learn data-engineering concepts (asset graphs, declarative automation, sensors).

**ZenML's sweet spot:** ML teams iterating on experiments where the pipeline structure is relatively stable and automatic, comprehensive caching is more valuable than fine-grained orchestration control.

### Decision Matrix

| Scenario | Recommendation |
|----------|---------------|
| "We have a data platform and ML is one workload" | **Dagster** |
| "We just need ML pipelines with fast iteration" | **ZenML** |
| "We need to re-run one model without touching the rest" | **Dagster** (`stale_assets_only` or UI selection) |
| "We want caching without configuring anything" | **ZenML** |
| "Our data sources are external systems (S3, DBs, APIs)" | **Dagster** (observable source assets) |
| "We run on Kubeflow/Vertex and want portable pipelines" | **ZenML** (stack abstraction) |
| "We share features across multiple models" | **Dagster** (asset graph fan-out) |
| "We frequently change hyperparameters" | **ZenML** (params in cache key) |
| "We need mixed scheduling (some cron, some event-driven)" | **Dagster** (declarative automation) |
| "We want the simplest possible ML pipeline caching" | **ZenML**, or **Dagster with `@cached_asset`** |

### Can You Use Both?

Yes. Some teams use ZenML for ML experimentation (fast iteration with automatic caching) and Dagster for production orchestration (scheduling, monitoring, data platform integration). ZenML pipelines can write outputs that Dagster observes via `@observable_source_asset`, bridging the two systems. This is a pragmatic choice when your ML and data engineering teams have different needs.

---

## 9. Complete Example: ZenML-Like ML Pipeline in Dagster

```python
import dagster as dg
from auto_code_version import cached_asset

# ── External data source ──────────────────────────────────────────
@dg.observable_source_asset
def training_data():
    """Detect when the training CSV changes."""
    import hashlib
    content = open("/data/training.csv", "rb").read()
    return dg.DataVersion(hashlib.sha256(content).hexdigest()[:16])

# ── Pipeline steps — all auto-versioned + eager ───────────────────
@cached_asset
def features(training_data):
    """Feature engineering. Auto-rematerializes if training data or
    this function's code changes."""
    df = load(training_data)
    return engineer_features(df)

@cached_asset
def trained_model(features):
    """Model training. Only re-runs if features change."""
    return fit_model(features)

@cached_asset
def evaluation(trained_model):
    """Evaluation. Only re-runs if the model or this code changes."""
    metrics = evaluate(trained_model)
    return dg.MaterializeResult(
        metadata={"accuracy": metrics["accuracy"]},
    )

@cached_asset
def deployed_model(trained_model, evaluation):
    """Deploy. Only re-runs if model or evaluation changes."""
    deploy_to_endpoint(trained_model)

# ── Scheduled observation (detect upstream data changes) ──────────
observe_job = dg.define_asset_job(
    "observe_training_data",
    selection=dg.AssetSelection.assets(training_data),
)

@dg.schedule(cron_schedule="*/30 * * * *", job=observe_job)
def observe_schedule():
    return dg.RunRequest()

# ── Definitions ───────────────────────────────────────────────────
defs = dg.Definitions(
    assets=[training_data, features, trained_model, evaluation, deployed_model],
    schedules=[observe_schedule],
)
```

**Behavior:**
- Every 30 minutes, the observation schedule checks if `training_data` has changed.
- If it has → `features` fires (eager) → `trained_model` fires → `evaluation` fires → `deployed_model` fires. Full cascade, ~2 min of automation delay.
- If you edit `evaluation`'s code and redeploy → only `evaluation` and `deployed_model` re-run. `features` and `trained_model` are untouched.
- If nothing changes → nothing runs. Zero wasted compute.

---

## Sources

### Dagster
- [Asset Versioning and Caching — Dagster Docs](https://docs.dagster.io/guides/build/assets/asset-versioning-and-caching)
- [Unsynced Status Propagation Discussion (dagster-io/dagster#25248)](https://github.com/dagster-io/dagster/discussions/25248)
- [Auto Code Versioning Feature Request (dagster-io/dagster#15242)](https://github.com/dagster-io/dagster/issues/15242)
- [Materialize Stale Assets on Schedule (dagster-io/dagster#14755)](https://github.com/dagster-io/dagster/discussions/14755)
- [Support Rematerialization of Stale Assets in Schedules (dagster-io/dagster#10726)](https://github.com/dagster-io/dagster/issues/10726)
- [Partitioned Assets and code_version (dagster-io/dagster#22704)](https://github.com/dagster-io/dagster/issues/22704)
- [Declarative Scheduling Blog Post](https://dagster.io/blog/declarative-scheduling)

### ZenML
- [ZenML Caching — Control Caching Behavior](https://docs.zenml.io/how-to/build-pipelines/control-caching-behavior)
- [ZenML Advanced Step/Pipeline Features](https://docs.zenml.io/concepts/steps_and_pipelines/advanced_features)
- [ZenML Artifacts Concepts](https://docs.zenml.io/concepts/artifacts)
- [Why You Should Be Using Caching in ML Pipelines — ZenML Blog](https://www.zenml.io/blog/why-you-should-be-using-caching-in-your-machine-learning-pipelines)
- [ZenML Steps SDK Reference (cache key internals)](https://sdkdocs.zenml.io/0.65.0/core_code_docs/core-steps/)
