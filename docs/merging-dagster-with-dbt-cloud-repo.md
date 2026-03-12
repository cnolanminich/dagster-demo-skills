# Merging an Existing Dagster Cloud Repo with an Existing dbt Cloud Repo

## Overview

This guide walks through how to **merge two existing GitHub repositories** — one running
Dagster Cloud and one running dbt Cloud — into a single monorepo while retaining
**independent deployment paths** for each:

- **dbt Cloud** continues to deploy models via its native CI/CD
- **Dagster Cloud** continues to deploy its orchestration layer independently
- Neither system blocks the other during development or deployment

---

## Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.10 – 3.13 |
| [uv](https://docs.astral.sh/uv/) | latest |
| git | 2.x+ |
| Dagster Cloud account | with API token |
| dbt Cloud account | with API token |

---

## Step 1 — Understand the Two Starting Repos

### Existing dbt Cloud Repo

```
dbt-cloud-repo/                        # github.com/myorg/dbt-cloud-repo
├── .github/
│   └── workflows/
│       └── dbt_cloud_deploy.yml       # dbt Cloud CI/CD
├── dbt_project.yml
├── profiles.yml                       # (or managed in dbt Cloud UI)
├── packages.yml
├── models/
│   ├── staging/
│   │   ├── stg_customers.sql
│   │   └── stg_orders.sql
│   └── marts/
│       ├── dim_customers.sql
│       └── fct_orders.sql
├── macros/
│   └── generate_schema_name.sql
├── seeds/
│   └── country_codes.csv
├── tests/
│   └── assert_positive_revenue.sql
├── snapshots/
│   └── scd_customers.sql
└── README.md
```

### Existing Dagster Cloud Repo

```
dagster-cloud-repo/                    # github.com/myorg/dagster-cloud-repo
├── .github/
│   └── workflows/
│       ├── dagster_cloud_deploy.yml   # Dagster Cloud CI/CD
│       └── dagster_tests.yml          # PR test checks
├── my_dagster_project/
│   ├── pyproject.toml
│   └── my_dagster_project/
│       ├── __init__.py
│       └── defs/
│           ├── __init__.py
│           ├── ingestion/
│           │   ├── defs.yaml          # e.g., Sling or Fivetran component
│           │   └── replication.yaml
│           ├── ml_models/
│           │   ├── train_model.py
│           │   └── serve_predictions.py
│           ├── exports/
│           │   └── export_customers.py
│           └── schedules/
│               └── daily_pipeline.py
├── dagster_cloud.yaml                 # Dagster Cloud location config
└── README.md
```

---

## Step 2 — Choose a Merge Strategy

You have two options for which repo becomes the "home" repo:

| Strategy | When to Use |
|----------|-------------|
| **A. dbt repo absorbs Dagster** | dbt Cloud repo is the primary codebase; Dagster is the newer addition |
| **B. Dagster repo absorbs dbt** | Dagster Cloud repo is the primary codebase; dbt models are being brought in |

Both produce the same final structure. This guide uses **Strategy A** (dbt repo as the base)
since it is the more common scenario. For Strategy B, simply reverse the roles.

---

## Step 3 — Merge the Repos with Git History Preserved

This moves the Dagster project into the dbt Cloud repo while **preserving full git history**
for both repos.

```bash
# 1. Clone the dbt Cloud repo (the base repo)
git clone git@github.com:myorg/dbt-cloud-repo.git merged-repo
cd merged-repo

# 2. Add the Dagster repo as a remote
git remote add dagster-origin git@github.com:myorg/dagster-cloud-repo.git
git fetch dagster-origin

# 3. Merge the Dagster repo into the dbt repo (allow unrelated histories)
git merge dagster-origin/main --allow-unrelated-histories --no-edit
```

If there are merge conflicts (e.g., both repos have a `README.md` or `.github/` files), resolve
them manually:

```bash
# Common conflicts to expect:
#   - README.md              → combine both into one
#   - .github/workflows/     → keep both sets of workflows (no overlap)
#   - .gitignore             → merge entries from both

# After resolving:
git add .
git commit -m "Merge dagster-cloud-repo into dbt-cloud-repo"
```

Clean up the remote:

```bash
git remote remove dagster-origin
```

---

## Step 4 — Reorganize into the Monorepo Structure

After the merge, both projects' files exist at the repo root. Move the dbt project into its
own subdirectory so the repo has clear top-level boundaries:

```bash
# Create a subdirectory for the dbt project
mkdir dbt_project

# Move all dbt-specific files into it
git mv dbt_project.yml dbt_project/
git mv profiles.yml dbt_project/ 2>/dev/null   # may not exist if managed by dbt Cloud
git mv packages.yml dbt_project/ 2>/dev/null
git mv models/ dbt_project/
git mv macros/ dbt_project/
git mv seeds/ dbt_project/
git mv tests/ dbt_project/
git mv snapshots/ dbt_project/
git mv analyses/ dbt_project/ 2>/dev/null

git commit -m "Move dbt project files into dbt_project/ subdirectory"
```

### Folder Structure After Reorganization

```
merged-repo/
├── .github/
│   └── workflows/
│       ├── dbt_cloud_deploy.yml           # from dbt Cloud repo (update paths — see Step 5)
│       ├── dagster_cloud_deploy.yml       # from Dagster Cloud repo
│       └── dagster_tests.yml              # from Dagster Cloud repo
│
├── dbt_project/                           # ── dbt Cloud project ──
│   ├── dbt_project.yml
│   ├── profiles.yml
│   ├── packages.yml
│   ├── models/
│   │   ├── staging/
│   │   │   ├── stg_customers.sql
│   │   │   └── stg_orders.sql
│   │   └── marts/
│   │       ├── dim_customers.sql
│   │       └── fct_orders.sql
│   ├── macros/
│   │   └── generate_schema_name.sql
│   ├── seeds/
│   │   └── country_codes.csv
│   ├── tests/
│   │   └── assert_positive_revenue.sql
│   └── snapshots/
│       └── scd_customers.sql
│
├── my_dagster_project/                    # ── Dagster Cloud project ──
│   ├── pyproject.toml
│   └── my_dagster_project/
│       ├── __init__.py
│       └── defs/
│           ├── __init__.py
│           ├── ingestion/
│           │   ├── defs.yaml
│           │   └── replication.yaml
│           ├── ml_models/
│           │   ├── train_model.py
│           │   └── serve_predictions.py
│           ├── exports/
│           │   └── export_customers.py
│           └── schedules/
│               └── daily_pipeline.py
│
├── dagster_cloud.yaml                     # Dagster Cloud location config
├── .gitignore
└── README.md
```

---

## Step 5 — Update dbt Cloud to Point at the Subdirectory

Since dbt files moved from the repo root into `dbt_project/`, update dbt Cloud:

### In dbt Cloud UI

1. Go to **Account Settings > Projects > your project**
2. Change **Project Subdirectory** to `dbt_project`
3. This tells dbt Cloud to look for `dbt_project.yml` inside that folder

### Update the GitHub Actions Workflow

Edit `.github/workflows/dbt_cloud_deploy.yml` to reflect the new paths:

```yaml
on:
  push:
    branches: [main]
    paths:
      - "dbt_project/models/**"
      - "dbt_project/macros/**"
      - "dbt_project/seeds/**"
      - "dbt_project/snapshots/**"
      - "dbt_project/tests/**"
      - "dbt_project/analyses/**"
      - "dbt_project/dbt_project.yml"
      - "dbt_project/packages.yml"
  pull_request:
    branches: [main]
    paths:
      - "dbt_project/models/**"
      - "dbt_project/macros/**"
      - "dbt_project/seeds/**"
      - "dbt_project/snapshots/**"
      - "dbt_project/tests/**"
      - "dbt_project/analyses/**"
      - "dbt_project/dbt_project.yml"
      - "dbt_project/packages.yml"
```

---

## Step 6 — Connect Dagster to the Colocated dbt Project

Now that both projects live in the same repo, wire Dagster to the dbt models. You have two
options depending on how you want dbt to run:

### Option A: dbt Core via Dagster (Dagster compiles and runs dbt directly)

Install the dbt integration and scaffold a component that points at the colocated dbt project:

```bash
cd my_dagster_project

# Add dagster-dbt and your warehouse adapter
uv add dagster-dbt
uv add dbt-snowflake   # or dbt-bigquery, dbt-duckdb, etc.

# Scaffold a DbtProjectComponent pointing at the dbt project
dg scaffold defs dagster_dbt.DbtProjectComponent my_dbt \
  --project-path ../../dbt_project
```

This creates `my_dagster_project/my_dagster_project/defs/my_dbt/defs.yaml`:

```yaml
type: dagster_dbt.DbtProjectComponent

attributes:
  project_dir: ../../../dbt_project    # relative path to dbt project root
```

### Option B: dbt Cloud API (dbt Cloud remains the execution engine — recommended for dual deployment)

If dbt Cloud should keep running dbt models, configure Dagster to orchestrate via the API instead:

Create `my_dagster_project/my_dagster_project/defs/dbt_cloud_assets.py`:

```python
import dagster as dg
from dagster_dbt import DbtCloudCredentials, DbtCloudWorkspace, dbt_cloud_assets


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
    """Dagster assets backed by dbt Cloud — triggers dbt Cloud job runs."""
    ...


defs = dg.Definitions(
    assets=[my_dbt_cloud_models],
    resources={"dbt_cloud": dbt_cloud},
)
```

### Wire Existing Dagster Assets as Downstream Dependencies

Update any existing Dagster assets to declare dependencies on the dbt models. For example,
in `defs/exports/export_customers.py`:

```python
import dagster as dg


@dg.asset(
    deps=[dg.AssetKey(["my_dbt", "dim_customers"])],
    group_name="exports",
)
def customer_export(context: dg.AssetExecutionContext):
    """Export dim_customers to CRM after dbt builds it."""
    context.log.info("Exporting customers to CRM...")
```

---

## Step 7 — Update Dagster Cloud Configuration

Edit `dagster_cloud.yaml` to ensure the code location points to the correct directory:

```yaml
locations:
  - location_name: my-dagster-project
    code_source:
      package_name: my_dagster_project
    working_directory: my_dagster_project
```

---

## Step 8 — Verify Everything Works

```bash
cd my_dagster_project

# Verify Dagster can load all definitions (including dbt models)
dg list defs

# Launch the Dagster UI locally
dg dev
```

Check that:
- All existing Dagster assets still appear
- dbt models appear as Dagster assets (via Option A or B)
- Dependency lineage connects dbt models to downstream assets
- Schedules and sensors are intact

---

## Step 9 — Final Merged Repository Structure

```
merged-repo/
├── .github/
│   └── workflows/
│       ├── dbt_cloud_deploy.yml           # dbt Cloud CI/CD (paths updated)
│       ├── dagster_cloud_deploy.yml       # Dagster Cloud CI/CD
│       └── dagster_tests.yml              # Dagster PR checks
│
├── dbt_project/                           # ── dbt Cloud project ──
│   ├── dbt_project.yml
│   ├── profiles.yml
│   ├── packages.yml
│   ├── models/
│   │   ├── staging/
│   │   │   ├── stg_customers.sql
│   │   │   └── stg_orders.sql
│   │   └── marts/
│   │       ├── dim_customers.sql
│   │       └── fct_orders.sql
│   ├── macros/
│   │   └── generate_schema_name.sql
│   ├── seeds/
│   │   └── country_codes.csv
│   ├── tests/
│   │   └── assert_positive_revenue.sql
│   └── snapshots/
│       └── scd_customers.sql
│
├── my_dagster_project/                    # ── Dagster Cloud project ──
│   ├── pyproject.toml
│   └── my_dagster_project/
│       ├── __init__.py
│       └── defs/
│           ├── __init__.py
│           ├── my_dbt/                    # dbt integration (Option A)
│           │   └── defs.yaml
│           ├── dbt_cloud_assets.py        # OR dbt Cloud API (Option B)
│           ├── ingestion/
│           │   ├── defs.yaml
│           │   └── replication.yaml
│           ├── ml_models/
│           │   ├── train_model.py
│           │   └── serve_predictions.py
│           ├── exports/
│           │   └── export_customers.py
│           └── schedules/
│               └── daily_pipeline.py
│
├── dagster_cloud.yaml
├── .gitignore
└── README.md
```

---

## Key Design Decisions

### When to Use Option A (dbt Core via Dagster) vs Option B (dbt Cloud API)

| Criteria | Option A — dbt Core | Option B — dbt Cloud API |
|----------|---------------------|--------------------------|
| dbt execution engine | Dagster runs dbt directly | dbt Cloud runs dbt |
| dbt Cloud still needed? | No (can decommission) | Yes (required) |
| Model lineage in Dagster | Full (from compiled manifest) | Full (from Cloud metadata) |
| Dual deployment | Redundant (Dagster replaces dbt Cloud) | Clean separation of concerns |
| Best for | Consolidating onto Dagster as single orchestrator | Keeping both platforms running independently |

**For the dual-deployment scenario described in this guide, Option B is recommended** — it keeps
dbt Cloud as the dbt execution engine and uses Dagster Cloud for higher-level orchestration,
observability, and non-dbt workloads.

### Why a Monorepo?

| Benefit | Detail |
|---------|--------|
| **Single source of truth** | dbt model changes and Dagster pipeline changes are reviewed together |
| **Atomic PRs** | A dbt model rename + Dagster dependency update ship in one PR |
| **Shared CI** | One repo = one set of branch protections, CODEOWNERS, and review rules |
| **Independent deploys** | Path-based GitHub Actions ensure each system only deploys when its files change |

---

## Next Steps

- See [GitHub Actions for Independent Deployment](../github-actions-examples/) for complete workflow files
- See the dagster-dbt reference in `.claude/skills/dagster-expert/references/integrations/dagster-dbt/` for advanced configuration
