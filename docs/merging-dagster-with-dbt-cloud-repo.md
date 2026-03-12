# Merging a Dagster Project with an Existing dbt Cloud GitHub Repository

## Overview

This guide walks through how to add Dagster to an **existing dbt Cloud GitHub repository** so
that both tools share a single codebase while retaining **independent deployment paths**:

- **dbt Cloud** continues to deploy models via its native CI/CD (triggered by push / PR to the dbt
  project directory).
- **Dagster** deploys its own orchestration layer (Dagster Cloud or self-hosted) independently.

The two systems coexist in the same repo but do not block each other.

---

## Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.10 – 3.13 |
| [uv](https://docs.astral.sh/uv/) | latest |
| [dg CLI](https://docs.dagster.io/guides/labs/dg) | latest (installed via `uv`) |
| dbt Cloud account | with API token |
| GitHub repository | your existing dbt Cloud repo |

---

## Step 1 — Understand the Starting Point

A typical dbt Cloud repo looks like this:

```
my-dbt-cloud-repo/
├── .github/
│   └── workflows/
│       └── dbt_cloud_deploy.yml      # existing dbt Cloud CI
├── dbt_project.yml
├── profiles.yml                       # (or managed in dbt Cloud)
├── models/
│   ├── staging/
│   │   ├── stg_customers.sql
│   │   └── stg_orders.sql
│   └── marts/
│       ├── dim_customers.sql
│       └── fct_orders.sql
├── macros/
├── seeds/
├── tests/
├── snapshots/
└── README.md
```

dbt Cloud is configured to track this repo and run jobs when code changes.

---

## Step 2 — Initialize Dagster Alongside dbt

From the repository root, scaffold a Dagster project using `dg`:

```bash
# Install the dg CLI
uv tool install dagster-components[dg]

# Initialize a new Dagster project at the repo root
# This creates pyproject.toml, a defs/ directory, and component scaffolding
dg init my_dagster_project --use-workspace
```

This creates a workspace layout. Your repo now looks like:

```
my-dbt-cloud-repo/
├── .github/
│   └── workflows/
│       └── dbt_cloud_deploy.yml
├── dbt_project.yml                    # existing dbt project (untouched)
├── models/ ...                        # existing dbt models (untouched)
├── macros/ ...
├── seeds/ ...
├── my_dagster_project/                # NEW — Dagster project root
│   ├── pyproject.toml
│   └── my_dagster_project/
│       └── defs/
│           └── __init__.py
├── workspace.yaml                     # NEW — Dagster workspace config
└── README.md
```

---

## Step 3 — Add the dbt Integration to Dagster

```bash
cd my_dagster_project

# Add dagster-dbt and your warehouse adapter
uv add dagster-dbt
uv add dbt-snowflake   # or dbt-bigquery, dbt-duckdb, etc.
```

### Option A: Point Dagster at the Colocated dbt Project (dbt Core mode)

If you want Dagster to compile and run dbt models **locally** (not via dbt Cloud):

```bash
dg scaffold defs dagster_dbt.DbtProjectComponent my_dbt \
  --project-path ../           # path to dbt_project.yml relative to defs/
```

This creates `defs/my_dbt/defs.yaml`:

```yaml
type: dagster_dbt.DbtProjectComponent

attributes:
  project_dir: ../../           # resolves to the dbt project at repo root
```

### Option B: Use the dbt Cloud API (dbt Cloud mode — recommended for dual deployment)

If dbt Cloud should remain the execution engine for dbt models, configure Dagster to orchestrate
dbt Cloud jobs via the API:

Create the file `my_dagster_project/my_dagster_project/defs/dbt_cloud_assets.py`:

```python
import dagster as dg
from dagster_dbt import DbtCloudCredentials, DbtCloudWorkspace, dbt_cloud_assets


# Credentials pulled from environment variables (set in Dagster Cloud or CI)
dbt_cloud_credentials = DbtCloudCredentials(
    account_id=dg.EnvVar.int("DBT_CLOUD_ACCOUNT_ID"),
    token=dg.EnvVar("DBT_CLOUD_API_TOKEN"),
    access_url="https://cloud.getdbt.com",
)

dbt_cloud = DbtCloudWorkspace(
    credentials=dbt_cloud_credentials,
    project_id=dg.EnvVar.int("DBT_CLOUD_PROJECT_ID"),
    environment_id=dg.EnvVar.int("DBT_CLOUD_ENVIRONMENT_ID"),
)


@dbt_cloud_assets(workspace=dbt_cloud)
def my_dbt_cloud_models(context: dg.AssetExecutionContext):
    """Assets representing dbt Cloud models — triggers dbt Cloud job runs."""
    ...


defs = dg.Definitions(
    assets=[my_dbt_cloud_models],
    resources={"dbt_cloud": dbt_cloud},
)
```

---

## Step 4 — Add Non-dbt Dagster Assets

Add additional orchestration assets that depend on or complement dbt models.

Example — `defs/downstream/export_customers.py`:

```python
import dagster as dg


@dg.asset(
    deps=[dg.AssetKey(["my_dbt", "dim_customers"])],
    group_name="exports",
)
def customer_export(context: dg.AssetExecutionContext):
    """Export the dim_customers table to an external system after dbt builds it."""
    context.log.info("Exporting customers to CRM...")
    # Your export logic here
```

---

## Step 5 — Add Schedules

Create a schedule that runs the full pipeline (dbt + downstream):

`defs/schedules/daily_pipeline.py`:

```python
import dagster as dg

daily_job = dg.define_asset_job(
    name="daily_pipeline",
    selection=dg.AssetSelection.groups("default", "exports"),
)

daily_schedule = dg.ScheduleDefinition(
    job=daily_job,
    cron_schedule="0 6 * * *",  # 6 AM UTC daily
)
```

---

## Step 6 — Verify Locally

```bash
cd my_dagster_project

# Check that Dagster can see all definitions
dg list defs

# Launch the Dagster UI for local testing
dg dev
```

---

## Step 7 — Final Repository Structure

```
my-dbt-cloud-repo/
├── .github/
│   └── workflows/
│       ├── dbt_cloud_deploy.yml       # dbt Cloud CI (existing, unchanged)
│       ├── dagster_deploy.yml         # Dagster CI (new)
│       └── dagster_tests.yml          # Dagster PR checks (new)
│
├── dbt_project.yml                    # dbt project root
├── models/
│   ├── staging/
│   │   ├── stg_customers.sql
│   │   └── stg_orders.sql
│   └── marts/
│       ├── dim_customers.sql
│       └── fct_orders.sql
├── macros/
├── seeds/
├── tests/
│
├── my_dagster_project/                # Dagster project
│   ├── pyproject.toml
│   └── my_dagster_project/
│       └── defs/
│           ├── __init__.py
│           ├── my_dbt/
│           │   └── defs.yaml          # DbtProjectComponent config
│           ├── dbt_cloud_assets.py    # OR dbt Cloud API assets
│           ├── downstream/
│           │   └── export_customers.py
│           └── schedules/
│               └── daily_pipeline.py
│
├── workspace.yaml
└── README.md
```

---

## Key Design Decisions

### When to Use Option A (dbt Core via Dagster) vs Option B (dbt Cloud API)

| Criteria | Option A — dbt Core | Option B — dbt Cloud API |
|----------|---------------------|--------------------------|
| dbt execution engine | Dagster runs dbt directly | dbt Cloud runs dbt |
| dbt Cloud still needed? | No (can remove) | Yes (required) |
| Model lineage in Dagster | Full (from manifest) | Full (from Cloud metadata) |
| Dual deployment possible? | Yes, but redundant | Yes, cleanly separated |
| Best for | Migrating away from dbt Cloud | Keeping dbt Cloud + adding Dagster |

**For the dual-deployment scenario described in this guide, Option B is recommended** — it keeps
dbt Cloud as the dbt execution engine and uses Dagster for higher-level orchestration,
observability, and additional non-dbt workloads.

---

## Next Steps

- See [GitHub Actions for Independent Deployment](../github-actions/) for CI/CD examples
- See the [dagster-dbt reference](../.claude/skills/dagster-expert/references/integrations/dagster-dbt/) for advanced configuration
