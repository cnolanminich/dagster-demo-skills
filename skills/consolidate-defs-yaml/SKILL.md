---
name: consolidate-defs-yaml
description: Consolidate related component instance YAML files into single defs.yaml files using YAML document separators (---). Groups related components (e.g., Fivetran + dbt + Looker + schedules) into logical pipelines for better organization.
license: MIT
---

# Consolidate Component Definitions into Single YAML Files

## Overview

This skill consolidates multiple component instance YAML files into single `defs.yaml` files using the YAML document separator (`---`). This improves organization by grouping related components (data ingestion, transformation, BI, and schedules) into logical pipeline units.

### Example Consolidation

**Before:**
```
defs/
  fivetran_salesforce/
    defs.yaml         # Fivetran sync
  dbt_analytics/
    defs.yaml         # dbt models
  looker_dashboards/
    defs.yaml         # Looker dashboards
  daily_pipeline_schedule/
    defs.yaml         # Schedule
```

**After:**
```
defs/
  salesforce_analytics_pipeline/
    defs.yaml         # Fivetran + dbt + Looker + schedule (all in one file)
```

**Consolidated file:**
```yaml
# defs/salesforce_analytics_pipeline/defs.yaml

# Fivetran sync for Salesforce data
type: my_project.components.FivetranComponent
attributes:
  demo_mode: true
  connector_id: "salesforce_connector"
  tables:
    - accounts
    - opportunities
    - contacts
---
# dbt analytics models
type: dagster_dbt.DbtProjectComponent
attributes:
  project:
    project_dir: salesforce_dbt
---
# Looker dashboards
type: dagster_looker.LookerComponent
attributes:
  demo_mode: true
  looker_resource:
    base_url: "https://company.looker.com"
    client_id: "demo_client_id"
    client_secret: "demo_client_secret"
---
# Daily refresh schedule
type: my_project.components.ScheduledJobComponent
attributes:
  job_name: "daily_salesforce_pipeline"
  cron_schedule: "0 6 * * *"
  asset_selection: "kind:fivetran kind:dbt kind:looker"
```

**CRITICAL: The filename MUST be `defs.yaml`.**

## Skill Workflow

### Step 1: Discover and Analyze

Scan all `defs/*/defs.yaml` files. For each, extract the component type, attributes, asset keys/selections, kinds, and tags.

Build a relationship graph by looking at:
- **Asset dependencies**: dbt depends on Fivetran/Sling sources; BI tools depend on dbt models
- **Shared kinds or domain tags**: components tagged with the same domain
- **Schedule targets**: schedules that select assets from specific components

### Step 2: Ask User for Consolidation Strategy

Present grouping options:
1. **Pipeline-Based**: Group by data flow (source → transform → BI)
2. **Domain-Based**: Group by business domain (finance, marketing, operations)
3. **Custom**: User specifies which components to group

Ask the user which strategy they prefer, what to name the consolidated pipelines, and whether any components should stay separate.

### Step 3: Create Consolidated YAML Files

For each group:
1. Create a new directory with a descriptive name (e.g., `salesforce_analytics_pipeline/`)
2. Write a single `defs.yaml` with all components separated by `---`
3. Order components logically: ingestion → transformation → BI → schedules
4. Add a comment above each component explaining what it does

### Step 4: Handle Special Cases

- **Companion files** (e.g., `replication.yaml` for Sling, `component.py` for custom components): move them into the new consolidated directory
- **Shared components** used by multiple pipelines: ask the user whether to duplicate or keep separate
- **Standalone components** (shared resources, cross-cutting concerns): leave in their own directories

### Step 5: Validate and Clean Up

```bash
# Validate definitions load correctly
uv run dg check defs

# Verify asset and schedule counts match before/after
uv run dg list defs
uv run dg list schedules
uv run dg list jobs
```

Only remove old directories after validation passes. If validation fails, check:
- `---` separator is on its own line
- Each YAML document starts at column 0 with proper indentation (spaces, not tabs)
- All YAML files were included in the consolidation

## Success Criteria

- Related components are grouped in single `defs.yaml` files with `---` separators
- Directory names reflect pipeline/domain purpose
- All companion files are migrated
- `uv run dg check defs` passes
- Asset, schedule, and job counts match before and after
- Old component directories are removed

## Additional Resources

- YAML Multi-Document Syntax: https://yaml.org/spec/1.2.2/#22-structures
- Dagster Components Guide: https://docs.dagster.io/guides/build/components
- Asset Selection Syntax: https://docs.dagster.io/concepts/assets/software-defined-assets#asset-selection-syntax
