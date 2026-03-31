# Runtime Step Selection & Ordering in Dagster

A demo project exploring different Dagster patterns for letting users choose **which steps run** and **in what order** at launch time — without creating a separate job for every combination.

## The Problem

You have a fixed set of operations (A, B, C, D, E, F). Different runs need different subsets in different orders: A then B then D, or just C, or C then B, or D then A. Creating a job per combination results in job explosion and user confusion. Ideally, users configure this at runtime via the Launchpad.

## Approaches Compared

The project includes five approaches, each making different tradeoffs:

### 1. Direct Assets (`direct_assets.py`)

Six independent `@asset` definitions. Users select any subset in the Dagster UI and materialize them.

```bash
uv run dg launch --assets direct_step_a,direct_step_c
```

- **Selection**: pick any combination in the UI
- **Ordering**: no control — all run in parallel (no dependencies)
- **Per-step retries**: yes (each is its own op)
- **Best for**: independent steps where ordering doesn't matter

### 2. Subsettable Multi-Asset (`subsettable_multi.py`)

One `@multi_asset(can_subset=True)` with six assets. Users select which to materialize via the asset picker.

```bash
uv run dg launch --assets multi_step_a,multi_step_c
```

- **Selection**: check/uncheck assets in the UI
- **Ordering**: fixed by the `for` loop at definition time
- **Per-step retries**: no (single op)
- **Best for**: steps that share setup and don't need reordering

### 3. Config-Driven Multi-Asset (`configurable_pipeline.py`)

One `@multi_asset(can_subset=True)` where a single config field controls both selection **and** ordering. All specs are `skippable=True`, so unlisted steps are silently skipped.

```bash
uv run dg launch \
  --assets configurable_step_a,configurable_step_b,configurable_step_c,configurable_step_d,configurable_step_e,configurable_step_f \
  --config-json '{"ops": {"configurable_pipeline": {"config": {"steps": ["C", "B", "A"]}}}}'
```

In the Launchpad, set config to `{"steps": ["C", "B", "A"]}` to run C, then B, then A. Steps not listed are skipped with zero overhead.

- **Selection**: config list
- **Ordering**: config list order (sequential)
- **Per-step retries**: no (single op)
- **Best for**: when ordering matters and simplicity is the priority

### 4. Dynamic Fan-Out (`dynamic_pipeline.py`)

A `plan_steps` op reads config and yields a `DynamicOutput` per step. `.map()` runs each as an independent op in its own subprocess.

```bash
uv run dg launch --assets dynamic_pipeline \
  --config-json '{"ops": {"dynamic_pipeline": {"ops": {"plan_steps": {"config": {"steps": ["C", "B", "A"]}}}}}}'
```

- **Selection**: config list
- **Ordering**: no control — `.map()` runs steps in **parallel**
- **Per-step retries**: yes (each mapped step is its own op)
- **Best for**: independent steps where you want per-step retries and observability

### 5. Dynamic Staged Pipeline (`dynamic_staged_pipeline.py`)

Combines DynamicOut with inter-stage dependencies. Steps within a stage run in parallel; stages run sequentially via fan-out -> `.collect()` -> fan-out chains.

```bash
uv run dg launch --assets staged_pipeline \
  --config-json '{"ops": {"staged_pipeline": {"ops": {
    "plan_stage_1": {"config": {"stages": [["A", "C"], ["B"], ["D", "F"]]}},
    "plan_stage_2": {"config": {"stages": [["A", "C"], ["B"], ["D", "F"]]}},
    "plan_stage_3": {"config": {"stages": [["A", "C"], ["B"], ["D", "F"]]}}
  }}}}'
```

This runs:
1. **Stage 1**: A and C in parallel
2. **Stage 2**: B (waits for stage 1 to complete)
3. **Stage 3**: D and F in parallel (waits for stage 2 to complete)

Also includes a **chained `.map()` example** (`chained_map_pipeline`) where each item goes through process -> validate -> finalize sequentially, with items processed in parallel.

- **Selection**: config stages list
- **Ordering**: stages are sequential, steps within a stage are parallel
- **Per-step retries**: yes (each step is its own op)
- **Best for**: when you need both runtime selection AND ordering AND per-step retries

## Comparison Matrix

| Approach | Runtime Selection | Runtime Ordering | Per-Step Retries | Per-Step UI Visibility | Config Complexity |
|----------|:-:|:-:|:-:|:-:|:-:|
| Direct assets | UI picker | None (parallel) | Yes | Yes | None |
| Subsettable multi-asset | UI picker | Fixed (definition time) | No | Materialization events | None |
| Config-driven multi-asset | Config | Config order (sequential) | No | Materialization events | Low |
| Dynamic fan-out | Config | None (parallel) | Yes | Yes (Gantt chart) | Medium |
| Dynamic staged | Config | Stages sequential, within-stage parallel | Yes | Yes (Gantt chart) | High |

## Getting Started

```bash
# Install dependencies
uv sync

# Start the Dagster UI
uv run dg dev
```

Open http://localhost:3000 to explore the asset groups (`direct`, `multi`, `configurable`, `dynamic`, `dynamic_staged`) and experiment with different configurations in the Launchpad.
