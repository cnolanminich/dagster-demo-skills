# Consolidate Component YAML Files

Combine multiple `defs/*/defs.yaml` files into single files using `---` YAML document separators. Groups related components (ingestion -> transformation -> BI -> schedules) into logical pipeline units.

## Process

1. Scan `defs/*/defs.yaml` files
2. Group by data flow dependencies, domain, or schedule targets
3. Create new directory with descriptive name (e.g., `salesforce_analytics_pipeline/`)
4. Concatenate YAML with `---` separators, preserving execution order
5. Move any extra files (replication.yaml, component.py) to new directory
6. Validate with `uv run dg check defs`
7. Remove old directories only after validation passes

## Consolidated File Example

```yaml
# defs/finance_pipeline/defs.yaml

type: my_project.components.FivetranComponent
attributes:
  connector_id: "netsuite_connector"
---
type: dagster_dbt.DbtProjectComponent
attributes:
  project:
    project_dir: finance_dbt
---
type: my_project.components.ScheduledJobComponent
attributes:
  job_name: "daily_finance"
  cron_schedule: "0 6 * * *"
  asset_selection: "tag:domain=finance"
```

## Rules

- Filename MUST be `defs.yaml`
- `---` separator on its own line between documents
- Order: ingestion first, then transformation, then BI/activation, then schedules
- Name directories by purpose (`finance_reporting/`, not `pipeline1/`)
- Don't combine unrelated domains
- Keep cross-cutting components (shared resources, multi-pipeline schedules) separate

## Validation

```bash
uv run dg check defs
uv run dg list defs
```

Compare asset/schedule counts before and after — they must match.
