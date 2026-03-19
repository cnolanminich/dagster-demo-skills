# Dagster Release Comparison: 1.12.19 vs 1.12.20

## Overall Stats

| Metric | Value |
|--------|-------|
| Total commits | 81 |
| Files changed | 300 |

---

## New Features in 1.12.20 (not in 1.12.19)

### Core
- **`multi_partition_key` property** — `OpExecutionContext`, `AssetExecutionContext`, and `AssetCheckExecutionContext` now expose a `multi_partition_key` property that returns a `MultiPartitionKey` for multi-partition runs.
- Added **Braze** and **Runpod** kind tags.

### dagster-databricks
- Databricks job run URL is now rendered as a **clickable link** in the Dagster UI.

### dagster-dbt
- **`DbtCloudComponent`** — new component for loading dbt Cloud projects as Dagster assets via the Components API.
- `dbt_cloud_assets` decorator now supports **partitioned assets** via `partitions_def`.

### dagster-fivetran
- **Polling sensor** for Fivetran observability — detects externally-triggered syncs and emits materialization events.
- `FivetranWorkspace` supports **`retry_on_reschedule`** (auto-retry syncs rescheduled due to quota limits) and **`resync`** operations.
- Fivetran translator now includes **sync schedule and custom report metadata** on connector assets.

### dagster-k8s
- Helm charts now support **`k8sApiCaBundlePath`** for custom CA certificate paths for Kubernetes API communication.
- Code location server Kubernetes Services now support **`service_spec_config`** for arbitrary Service spec overrides (e.g., headless services).

## Bugfixes in 1.12.20

- Fixed time window partitions with exclusions creating excess runs during single-run backfills.
- Fixed "Cannot access partition_key for a non-partitioned run" error with mixed partitioned/non-partitioned multi-asset definitions.
- **dagster-aws**: Fixed `s3_pickle_io_manager` failing with dynamic outputs containing bracket characters.
- **dagster-aws**: Fixed `PipesEMRServerlessClient` ignoring custom CloudWatch log group names.
- **UI**: Fixed asset recent updates trend visualization when multiple event types share a run ID.
- **UI**: Fixed text wrapping/spacing in asset event detail view for long partition names.

---

## Recap: What Was New in 1.12.19

### Core
- "Report Execution" dialog added to asset checks detail view for manual check result recording.
- Database pool configuration options (`--db-pool-recycle`, `--db-pool-pre-ping`, etc.) added to `dg dev` and `dagster dev`.
- `dg plus config view` command for inspecting CLI configuration.

### UI
- "Jobless asset materializations" label replaces "Ad hoc materializations" in Usage dialog and Run timeline.
- Planned run events excluded from event count in run log filter.

### dagster-azure
- New components: `AzureBlobStorageResourceComponent` and `ADLS2ResourceComponent` for declarative YAML configuration.

### dagster-databricks
- `DatabricksAssetBundleComponent` is now subsettable at the job level.
- `DatabricksAssetBundleComponent` uses the Databricks CLI for variable reference resolution.
- Databricks jobs are now cancelled when the corresponding Dagster run is terminated in `DatabricksWorkspaceComponent`.

### dagster-dbt
- `dagster-dbt` prefers `dbt-core` for manifest parsing when installed.

### dagster-gcp
- New components: `BigQueryResourceComponent`, `GCSResourceComponent`, `GCSFileManagerResourceComponent`, `DataprocResourceComponent`.
- `BigQueryIOManager` supports configurable `write_mode` (`truncate`, `replace`, `append`).

### Bugfixes (1.12.19)
- Fixed auto-run reexecution attempting to rerun jobs from completed/cancelled backfills.
- Fixed backfill errors remaining incorrectly associated after retry.
- `dg plus pull env` now merges secrets instead of replacing the `.env` file.
- Fixed Databricks `KeyError` for `run_page_url` and asset mapping conflicts.
- Fixed UI rendering of newlines in markdown blockquotes.

### Dagster Plus (1.12.19)
- Agent automatically redeploys local code servers that enter a failure state.

---

## Documentation Changes (1.12.19 → 1.12.20)

### New Pages (4 new files + images)

| File | Description |
|------|-------------|
| `docs/docs/api/clis/dg-cli/configuring-dagster-plus.md` | Guide for configuring Dagster Plus via the `dg` CLI |
| `docs/docs/examples/full-pipelines/multi-workspace-databricks/index.md` | Full pipeline example: multi-workspace Databricks setup (+242 lines) |
| `docs/docs/getting-started/ai-tools.md` | New getting-started guide for AI tools integration (+181 lines), with screenshots for Claude, Codex, Copilot, Cursor, and npx install |
| `docs/docs/partials/_SupersededDagsterCloudCLI.md` | Partial noting `dagster-cloud` CLI is superseded |

### Restructured: Best Practices Directory
- 11 files under `docs/docs/examples/best-practices/` were **renamed/moved** (likely a directory restructure).

### Significantly Modified Pages

| File | Changes | Summary |
|------|---------|---------|
| `integrations/libraries/dbt/dbt-cloud.md` | +91 lines | New DbtCloudComponent documentation |
| `integrations/libraries/fivetran/fivetran-pythonic.md` | +78/-3 | Polling sensor and retry/resync docs |
| `integrations/libraries/fivetran/index.md` | +46 lines | Fivetran overview updates |
| `deployment/dagster-plus/hybrid/kubernetes/configuration.md` | +63 lines | k8sApiCaBundlePath and service_spec_config docs |
| `deployment/dagster-plus/deploying-code/adding-project-to-dagster-plus.md` | +55/-24 | Updated project onboarding guide |
| `deployment/troubleshooting/hybrid-optimizing-troubleshooting.md` | +45 lines | New K8s agent network troubleshooting guide (TCP keepalive) |
| `deployment/dagster-plus/deploying-code/full-deployments/managing-full-deployments.md` | +41/-2 | Updated full deployment management |
| `deployment/dagster-plus/hybrid/amazon-ecs/configuration-reference.md` | +40 lines | ECS configuration additions |
| `deployment/dagster-plus/hybrid/docker/setup.md` | +37 lines | Docker hybrid setup additions |
| SSO docs (Azure AD, Google Workspace, Okta, OneLogin, PingOne) | Various | SSO configuration updates across providers |
| CLI docs (dagster-cloud-cli, dg-cli) | Various | CLI reference updates |
| Sphinx API docs (pipes, internals, dbt, fivetran) | Various | API reference updates for new features |

### Minor Documentation Touches
- Alerts docs, external pipelines, DuckDB integration — small updates.
- `CHANGES.md` — +58 lines for the new changelog entry.

---

## Key Themes

1. **dbt Cloud integration** — Major new `DbtCloudComponent` plus partition support for `dbt_cloud_assets`.
2. **Fivetran enhancements** — Observability polling sensor, retry-on-reschedule, resync, and richer metadata.
3. **Kubernetes configurability** — Custom CA bundles and arbitrary Service spec overrides in Helm charts.
4. **AI tooling** — New docs page for AI tools (Claude, Copilot, Cursor, Codex) getting-started guide.
5. **Multi-partition ergonomics** — `multi_partition_key` property on execution contexts.
6. **Docs restructuring** — Best practices examples reorganized; new full-pipeline Databricks example.
