---
name: create-dagster-demo
description: Create Dagster Demo Project
license: MIT
---

# Create Dagster Demo Project

## Overview

This skill guides the creation of a complete Dagster demonstration project for a prospective client. It orchestrates multiple sub-skills to initialize a project, create components, add schedules, consolidate YAML, and validate the result.

## What This Skill Does

When invoked, this skill will:

1. ✅ Create integration components using `use-or-subclass-existing-component` or `create-custom-dagster-component` skills
2. ✅ Add scheduled jobs using the `create-scheduled-jobs` skill
3. ✅ Consolidate YAML files using the `consolidate-defs-yaml` skill
4. ✅ Validate that all definitions load, dependencies align, and the project is demo-ready

## Prerequisites

Before running this skill, ensure:

- `uv` is installed (check with `uv --version`)
- The demo requirements (technologies, client context) are provided
- A target directory path for the demo project is known

## Skill Workflow

### Step 1: Initialize Dagster Project

Use the **dagster-init** skill to create a new Dagster project in the provided demo directory.

### Step 2: Generate and Customize Demo Assets

Use the **use-or-subclass-existing-component** skill to find and create components for integrations that Dagster already has. If there isn't one, use the **create-custom-dagster-component** skill to create those.

The goal of the demo Dagster project is to have:

- 3-5 realistic assets based on the chosen technologies
- Proper dependencies between assets
- Descriptive names
- **Asset keys designed for downstream consumption** (see below)

There should be both a real implementation and a `demo_mode` implementation that is runnable locally without access to the system and is activated by a `demo_mode` boolean flag in a component YAML.

Example asset structure:

- Raw data ingestion asset
- Data transformation/cleaning asset
- Business logic/aggregation asset
- ML model or analytics asset (if applicable)
- Output/export asset

#### Critical: Design Asset Keys for Integration

When creating components, **design asset keys so downstream components can reference them naturally**:

1. **If dbt will consume assets**: Use flat, 2-level keys like `["source_name", "table"]`
   - Example: `["fivetran_raw", "customers"]` allows dbt to use `source('fivetran_raw', 'customers')`
   - Avoid: `["fivetran", "raw", "customers"]` requires extra configuration

2. **For dbt models consumed by reverse ETL**: Use simple model names
   - Example: `["customer_lifetime_value"]` is easy for Hightouch to reference
   - dbt naturally creates these from model file names

3. **For custom processing chains**: Use consistent 2-level patterns
   - Example: `["raw", "table"]` → `["processed", "table"]` → `["enriched", "table"]`

After creating all the components, validate that Dagster loads by running:

```bash
uv run dg check defs
```

and then use:

```bash
uv run dg list defs
```

to make sure that all expected dependencies line up. This means that the deps field for a downstream asset should have the upstream asset as part of it. This can be especially tricky for integrations like sling and dbt.

#### Verify Asset Key Alignment

Run this command to check dependencies are correct:

```bash
uv run dg list defs --json | uv run python -c "
import sys, json
data = json.load(sys.stdin)
assets = data.get('assets', [])
print('Asset Dependencies:\n')
for asset in assets:
    key = asset.get('key', 'unknown')
    deps = asset.get('deps', [])
    if deps:
        print(f'{key}')
        for dep in deps:
            print(f'  <- {dep}')
    else:
        print(f'{key} (no dependencies)')
    print()
"
```

**What to verify:**
- Downstream assets list upstream assets in their `deps` array
- No missing dependencies (e.g., dbt models should depend on their sources)
- Asset keys are simple and descriptive (typically 2 levels: `["category", "name"]`)
- Dependencies work in both demo mode and production mode

If dependencies are missing or incorrect:
- For **dbt models**: Ensure they use `{{ source('source_name', 'table') }}` in SQL
- For **custom components**: Check that `deps=[...]` or `@asset(deps=[...])` is set correctly
- For **Fivetran/API components**: Verify asset keys match what dbt sources expect

### Step 3: Create Jobs and Schedules (Always)

Use the **create-scheduled-jobs** skill to create a few scheduled jobs for these assets in the project.

### Step 4: Consolidate YAML (Always)

Combine YAML using the **consolidate-defs-yaml** skill.

### Step 5: Validate Code

- Ensure that the components are using real connections to database or API systems and not merely "passing."
- Ensure that lineage matches expectations

## Success Criteria

The demo project is complete when:

- ✅ Dagster project initializes and `dg check defs` passes
- ✅ 3-5 realistic assets exist with proper dependencies
- ✅ Both real and demo_mode implementations are present
- ✅ Scheduled jobs are configured with asset selection syntax
- ✅ YAML files are consolidated into logical pipelines
- ✅ Asset key alignment is verified across all components
- ✅ `dg list defs` shows all expected assets, schedules, and jobs

## References

This skill delegates to the following sub-skills. Each handles a specific phase of demo creation:

| Skill | Purpose | Used In |
|-------|---------|---------|
| **use-or-subclass-existing-component** | Discover, use, or subclass existing Dagster integration components (dbt, Fivetran, PowerBI, Looker, Sling, etc.) with demo_mode support | Step 1 |
| **create-custom-dagster-component** | Create a custom Dagster Component when no existing integration component exists | Step 2 |
| **create-scheduled-jobs** | Create a ScheduledJobComponent with multiple scheduled job instances using asset selection syntax | Step 3 |
| **consolidate-defs-yaml** | Consolidate related component instance YAML files into single defs.yaml files using YAML document separators | Step 4 |
