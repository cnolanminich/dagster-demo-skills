---
title: Integration libraries index for 40+ tools and technologies (dbt, Fivetran, Snowflake, AWS, etc.).
type: index
triggers:
  - "integration, external tool, dagster-\\*"
  - "dbt, fivetran, airbyte, snowflake, bigquery, sling, aws, gcp"
---

# Integrations Reference

Dagster provides integration libraries for a range of tools and technologies. This reference directory contains detailed information about specific integrations.

Integration libraries are typically named `dagster-<technology>`, where `<technology>` is the name of the tool or technology being integrated. Integrations marked as _(community)_ are maintained by the community rather than the Dagster team.

All integration reference files contain a link to the official documentation for the integration library, which can be referenced in cases where the local documentation does not provide sufficient information.

## Component vs. Pythonic Integrations

**IMPORTANT**: If an integration library offers a Component, **ALWAYS** prefer this over the Pythonic integration unless there is an explicit reason to prefer the Pythonic integration. Components have a simpler, more deterministic interface and are easier to understand and manage.

### Discovery Workflow (library exists)


```bash
# Install the integration library
uv add dagster-<technology>

# List the available components
uv run dg list components --json

# [Optional] If a component exists, inspect its scaffolding or defs yaml schema
uv run dg utils inspect-component <ComponentType> --scaffold-params-schema
uv run dg utils inspect-component <ComponentType> --defs-yaml-schema

# Scaffold an instance of the component
uv run dg scaffold defs <ComponentType> <instance_name>
```

**NEVER skip this workflow.** Do not write Pythonic integration code (e.g. `FivetranWorkspace`, `@dbt_assets`, `CensusResource`) when a component is available. The `dg list components` command is the authoritative source for what components exist — do not guess or assume from memory.

### Custom Integration Workflow (no library exists)

If the desired external tool has **no published `dagster-*` library** (e.g. custom REST API), do NOT fall back to raw `@dg.asset` or `@dg.sensor` definitions. Instead, **create a custom component**:

```bash
# Scaffold a new component type
uv run dg scaffold component MyToolComponent

# Verify registration and get the full type path
uv run dg list components

# Scaffold an instance of your new component
uv run dg scaffold defs my_project.lib.my_tool_component.MyToolComponent my_instance
```

See [Designing Component Integrations](../components/designing-component-integrations.md) for patterns on structuring the component (definition-only, observing via sensors, or orchestrating via execution). Components are the standard unit of integration in Dagster — even for tools without a published library.

## Reference Files Index

<!-- BEGIN GENERATED INDEX -->

- [dagster-airbyte](./dagster-airbyte/INDEX.md) — Airbyte extract-load syncs as Dagster assets
- [dagster-airflow](./dagster-airflow/INDEX.md) — airflow, apache airflow, DAG
- [dagster-airlift](./dagster-airlift/INDEX.md) — migrating or co-orchestrating Airflow DAGs with Dagster
- [dagster-aws](./dagster-aws/INDEX.md) — AWS services (S3, ECS, Lambda) from Dagster
- [dagster-azure](./dagster-azure/INDEX.md) — Azure services (ADLS, Blob Storage) from Dagster
- [dagster-celery](./dagster-celery/INDEX.md) — distributed task execution with Celery
- [dagster-celery-docker](./dagster-celery-docker/INDEX.md) — celery docker, distributed container execution
- [dagster-celery-k8s](./dagster-celery-k8s/INDEX.md) — celery kubernetes, celery k8s, distributed orchestration
- [dagster-census](./dagster-census/INDEX.md) — reverse ETL syncs with Census
- [dagster-dask](./dagster-dask/INDEX.md) — parallel and distributed computing with Dask
- [dagster-databricks](./dagster-databricks/INDEX.md) — Spark-based data processing on Databricks
- [dagster-datadog](./dagster-datadog/INDEX.md) — monitoring and observability with Datadog
- [dagster-datahub](./dagster-datahub/INDEX.md) — metadata management and data cataloging with DataHub
- [dagster-dbt](./dagster-dbt/INDEX.md) — integrating dbt Core or dbt Cloud with Dagster
- [dagster-deltalake](./dagster-deltalake/INDEX.md) — lakehouse storage with Delta Lake
- [dagster-deltalake-pandas](./dagster-deltalake-pandas/INDEX.md) — delta lake pandas, deltalake dataframe
- [dagster-deltalake-polars](./dagster-deltalake-polars/INDEX.md) — delta lake polars, deltalake dataframe
- [dagster-dlt](./dagster-dlt/INDEX.md) — dlt, data load tool, declarative pipelines
- [dagster-docker](./dagster-docker/INDEX.md) — containerized execution with Docker
- [dagster-duckdb](./dagster-duckdb/INDEX.md) — in-process analytical queries with DuckDB
- [dagster-duckdb-pandas](./dagster-duckdb-pandas/INDEX.md) — duckdb pandas, duckdb dataframe
- [dagster-duckdb-polars](./dagster-duckdb-polars/INDEX.md) — duckdb polars, duckdb dataframe
- [dagster-duckdb-pyspark](./dagster-duckdb-pyspark/INDEX.md) — duckdb pyspark, duckdb spark
- [dagster-embedded-elt](./dagster-embedded-elt/INDEX.md) — embedded elt, sling, dlt, extract load transform
- [dagster-fivetran](./dagster-fivetran/INDEX.md) — managed extract-load connectors with Fivetran
- [dagster-gcp](./dagster-gcp/INDEX.md) — Google Cloud Platform (BigQuery, GCS) from Dagster
- [dagster-gcp-pandas](./dagster-gcp-pandas/INDEX.md) — gcp pandas, bigquery pandas, bigquery dataframe
- [dagster-gcp-pyspark](./dagster-gcp-pyspark/INDEX.md) — gcp pyspark, bigquery pyspark, bigquery spark
- [dagster-github](./dagster-github/INDEX.md) — GitHub repository event handling from Dagster
- [dagster-great-expectations](./dagster-great-expectations/INDEX.md) — data validation and testing with Great Expectations
- [dagster-hightouch](./dagster-hightouch/INDEX.md) — reverse ETL and data activation with Hightouch
- [dagster-iceberg](./dagster-iceberg/INDEX.md) — Apache Iceberg table format management
- [dagster-jupyter](./dagster-jupyter/INDEX.md) — notebook-based assets with Jupyter
- [dagster-k8s](./dagster-k8s/INDEX.md) — Kubernetes container orchestration and execution
- [dagster-looker](./dagster-looker/INDEX.md) — Looker BI dashboard assets
- [dagster-mlflow](./dagster-mlflow/INDEX.md) — ML experiment tracking and model management with MLflow
- [dagster-msteams](./dagster-msteams/INDEX.md) — Microsoft Teams notifications and alerts from Dagster
- [dagster-mysql](./dagster-mysql/INDEX.md) — MySQL as a Dagster storage backend
- [dagster-omni](./dagster-omni/INDEX.md) — analytics and BI with Omni
- [dagster-openai](./dagster-openai/INDEX.md) — LLM-powered assets with OpenAI
- [dagster-pagerduty](./dagster-pagerduty/INDEX.md) — incident management alerts with PagerDuty
- [dagster-pandas](./dagster-pandas/INDEX.md) — Pandas DataFrame type checking and validation
- [dagster-pandera](./dagster-pandera/INDEX.md) — DataFrame schema validation with Pandera
- [dagster-papertrail](./dagster-papertrail/INDEX.md) — log management with Papertrail
- [dagster-polars](./dagster-polars/INDEX.md) — fast DataFrame processing with Polars
- [dagster-polytomic](./dagster-polytomic/INDEX.md) — polytomic, data sync
- [dagster-postgres](./dagster-postgres/INDEX.md) — PostgreSQL as a Dagster storage backend
- [dagster-powerbi](./dagster-powerbi/INDEX.md) — Power BI dashboard assets
- [dagster-prometheus](./dagster-prometheus/INDEX.md) — metrics collection with Prometheus
- [dagster-pyspark](./dagster-pyspark/INDEX.md) — distributed data processing with PySpark
- [dagster-sigma](./dagster-sigma/INDEX.md) — BI and analytics assets with Sigma
- [dagster-slack](./dagster-slack/INDEX.md) — Slack notifications or alerts from Dagster
- [dagster-sling](./dagster-sling/INDEX.md) — EL data replication with Sling
- [dagster-snowflake](./dagster-snowflake/INDEX.md) — interacting with Snowflake from Dagster
- [dagster-snowflake-pandas](./dagster-snowflake-pandas/INDEX.md) — snowflake pandas, snowflake dataframe
- [dagster-snowflake-polars](./dagster-snowflake-polars/INDEX.md) — snowflake polars, snowflake dataframe
- [dagster-snowflake-pyspark](./dagster-snowflake-pyspark/INDEX.md) — snowflake pyspark, snowflake spark
- [dagster-spark](./dagster-spark/INDEX.md) — distributed data processing with Apache Spark
- [dagster-ssh](./dagster-ssh/INDEX.md) — remote command execution via SSH
- [dagster-tableau](./dagster-tableau/INDEX.md) — Tableau BI dashboard assets
- [dagster-twilio](./dagster-twilio/INDEX.md) — SMS and communication with Twilio
- [dagster-wandb](./dagster-wandb/INDEX.md) — ML experiment tracking with Weights & Biases
<!-- END GENERATED INDEX -->
