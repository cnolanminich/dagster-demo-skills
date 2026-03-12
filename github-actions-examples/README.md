# GitHub Actions: Independent dbt Cloud + Dagster Deployments

This directory contains example GitHub Actions workflows that enable **independent deployments**
of dbt Cloud and Dagster from a single monorepo.

## How Independent Deployment Works

The key mechanism is **path-based triggering**. Each workflow only fires when files in its
respective domain change:

```
Repository Root
├── dbt_project/                         → triggers dbt_cloud_deploy.yml ONLY
├── my_dagster_project/                  → triggers dagster_deploy.yml ONLY
└── (both change in same PR)             → BOTH workflows run independently
```

### Workflow Summary

| Workflow | File | Triggers On | What It Does |
|----------|------|-------------|--------------|
| **dbt Cloud Deploy** | `dbt_cloud_deploy.yml` | `dbt_project/models/`, `dbt_project/macros/`, etc. | Lints SQL, triggers dbt Cloud CI/deploy jobs via API |
| **Dagster Deploy** | `dagster_deploy.yml` | `my_dagster_project/`, `dagster_cloud.yaml` | Validates definitions, runs tests, deploys to Dagster Cloud |

### Scenarios

| Change Made | dbt Cloud Workflow | Dagster Workflow |
|-------------|-------------------|------------------|
| Edit `dbt_project/models/marts/dim_customers.sql` | Runs | Skipped |
| Edit `my_dagster_project/defs/exports/export.py` | Skipped | Runs |
| Edit both a dbt model and a Dagster asset | Runs | Runs (in parallel) |
| Edit `README.md` only | Skipped | Skipped |

## Setup Instructions

### 1. Copy the workflows

```bash
# From your repo root
mkdir -p .github/workflows
cp github-actions-examples/dbt_cloud_deploy.yml .github/workflows/
cp github-actions-examples/dagster_deploy.yml .github/workflows/
```

### 2. Configure GitHub Secrets

#### For dbt Cloud

| Secret | Description |
|--------|-------------|
| `DBT_CLOUD_API_TOKEN` | Service account token from dbt Cloud |
| `DBT_CLOUD_ACCOUNT_ID` | Your dbt Cloud account ID |
| `DBT_CLOUD_CI_JOB_ID` | Job ID for the CI/PR job |
| `DBT_CLOUD_DEPLOY_JOB_ID` | Job ID for the production deploy job |

#### For Dagster Cloud

| Secret | Description |
|--------|-------------|
| `DAGSTER_CLOUD_API_TOKEN` | Agent token from Dagster Cloud settings |
| `DAGSTER_CLOUD_ORGANIZATION` | Your Dagster Cloud organization name |

#### For dbt manifest compilation (Option A only)

| Secret | Description |
|--------|-------------|
| `SNOWFLAKE_ACCOUNT` | Warehouse account (adapt to your DWH) |
| `SNOWFLAKE_USER` | Warehouse user |
| `SNOWFLAKE_PASSWORD` | Warehouse password |

### 3. Adjust paths

Update the `paths` filters in each workflow if your directory structure differs from the example.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────┐
│                   GitHub Repository                  │
│                                                     │
│  ┌──────────────┐          ┌──────────────────────┐ │
│  │  dbt project │          │  Dagster project     │ │
│  │  dbt_project/│          │  my_dagster_project/ │ │
│  │              │          │                      │ │
│  └──────┬───────┘          └──────────┬───────────┘ │
│         │                             │              │
└─────────┼─────────────────────────────┼──────────────┘
          │                             │
    path filter:                  path filter:
    dbt_project/**              my_dagster_project/**
          │                             │
          ▼                             ▼
┌─────────────────┐          ┌──────────────────────┐
│  dbt Cloud CI   │          │  Dagster Cloud CI    │
│  (lint + run)   │          │  (validate + test)   │
└────────┬────────┘          └──────────┬───────────┘
         │                              │
    on merge to main              on merge to main
         │                              │
         ▼                              ▼
┌─────────────────┐          ┌──────────────────────┐
│  dbt Cloud      │          │  Dagster Cloud       │
│  Production Job │          │  Production Deploy   │
└─────────────────┘          └──────────────────────┘
```

## Interaction Between Systems

Even though they deploy independently, Dagster and dbt Cloud can interact at runtime:

- **Dagster triggers dbt Cloud jobs** via the `dbt_cloud_assets` decorator and the dbt Cloud API
- **Dagster observes dbt Cloud runs** via `build_dbt_cloud_polling_sensor()`
- **dbt Cloud runs independently** on its own schedule, and Dagster can optionally monitor those runs

This means:
1. A dbt model change deploys to dbt Cloud immediately
2. Dagster's asset graph automatically reflects the updated models (metadata syncs on next run)
3. Neither system blocks the other during deployment
