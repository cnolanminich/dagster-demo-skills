---
name: consolidate-defs-yaml
description: Consolidate related component instance YAML files into single defs.yaml files using YAML document separators (---). Groups related components (e.g., Fivetran + dbt + Looker + schedules) into logical pipelines for better organization.
license: MIT
---

# Consolidate Component Definitions into Single YAML Files

## Overview

This skill consolidates multiple component instance YAML files into single `defs.yaml` files using the YAML document separator (`---`). This improves organization by grouping related components (data ingestion, transformation, BI, and schedules) into logical pipeline units.

## What This Skill Does

When invoked, this skill will:

1. ✅ Scan all existing `defs/*/defs.yaml` files in the project
2. ✅ Analyze relationships between components (based on asset dependencies, kinds, tags)
3. ✅ Group related components into logical pipelines
4. ✅ Create consolidated `defs.yaml` files using `---` separators
5. ✅ Create new directory names that reflect the pipeline purpose
6. ✅ Remove old component instance directories after consolidation
7. ✅ Validate that consolidated definitions load correctly with `dg check defs`

## Why Consolidate?

### Benefits

1. **Logical Grouping**: Keep related components together (ingestion → transformation → BI → scheduling)
2. **Reduced Directory Clutter**: Fewer directories to navigate
3. **Easier Maintenance**: Update related components in one file
4. **Better Documentation**: File structure reflects data pipelines
5. **Pipeline-Centric Organization**: Aligns with how data flows through your system

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
  hourly_sync_schedule/
    defs.yaml         # Another schedule
```

**After:**
```
defs/
  salesforce_analytics_pipeline/
    defs.yaml         # Fivetran + dbt + Looker + schedules (all in one file)
```

## Skill Workflow

### Step 1: Discover Existing Component Instances

Scan the project for all component instance YAML files:

```bash
# Find all defs.yaml files
find defs -name "defs.yaml" -type f
```

For each YAML file, extract:
- Component type
- Component attributes
- Asset keys/selections (if available)
- Related kinds, tags, groups

### Step 2: Analyze Relationships

Build a dependency graph to understand how components relate:

1. **By Asset Dependencies**:
   - dbt models depend on Fivetran/Sling sources
   - BI tools depend on dbt models
   - Schedules target specific asset selections

2. **By Kind**:
   - Group components that work with the same kinds (fivetran → dbt → powerbi)

3. **By Domain Tags**:
   - Group components tagged with the same domain (finance, marketing, operations)

4. **By Schedule Targets**:
   - Group schedules with the components they target

### Step 3: Ask User for Consolidation Strategy

Present the user with grouping options:

1. **Pipeline-Based**: Group by data flow (source → transform → BI)
2. **Domain-Based**: Group by business domain (finance, marketing, operations)
3. **Schedule-Based**: Group by scheduling pattern (daily, hourly, weekly)
4. **Custom**: User specifies which components to group together

**Ask the user:**
- Which consolidation strategy they prefer
- What to name the consolidated pipelines
- Whether to keep any components separate

### Step 4: Create Consolidated YAML Files

For each group, create a new directory with a consolidated `defs.yaml`:

**Example Consolidated File Structure:**

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

**CRITICAL: The filename MUST be `defs.yaml`**

### Step 5: Create Directory Structure

For each consolidated group:

```bash
# Create new directory with descriptive name
mkdir -p defs/<pipeline_name>

# Write consolidated defs.yaml
# (contains multiple YAML documents separated by ---)
```

**Directory Naming Conventions:**

Use descriptive names that reflect the pipeline purpose:
- `salesforce_analytics_pipeline/` - Salesforce → dbt → Looker
- `marketing_data_platform/` - Multiple sources → dbt → Census/Hightouch
- `finance_reporting/` - Finance sources → dbt → PowerBI
- `operations_dashboard/` - Ops sources → dbt → Tableau
- `data_quality_monitoring/` - Quality checks and schedules

### Step 6: Handle Special Cases

#### Case 1: Standalone Components

Some components should remain separate:
- Shared resources (e.g., `defs/resources.py`)
- Cross-cutting concerns (e.g., `defs/data_quality_checks.py`)
- General schedules that target multiple pipelines

**Action**: Keep these in separate directories/files

#### Case 2: Multi-Pipeline Components

If a component is used by multiple pipelines:
- Option A: Duplicate the component definition in each pipeline
- Option B: Keep it separate and reference it

**Ask the user** which approach they prefer.

#### Case 3: Non-YAML Component Files

If a component directory contains additional files (e.g., `replication.yaml` for Sling, `component.py` for custom components):

**Action**: Move all related files to the new consolidated directory

Example:
```
defs/
  data_ingestion_pipeline/
    defs.yaml           # Consolidated component instances
    replication.yaml    # Sling replication config
    component.py        # Custom component logic
```

### Step 7: Migrate Files and Clean Up

For each consolidation:

1. **Copy additional files** (if any):
   ```bash
   # Copy non-defs.yaml files to new directory
   cp defs/old_component/*.yaml defs/new_pipeline/
   cp defs/old_component/*.py defs/new_pipeline/
   ```

2. **Create consolidated defs.yaml**:
   - Concatenate related YAML files
   - Add `---` separator between each component instance
   - Preserve comments and structure

3. **Validate** the new structure:
   ```bash
   uv run dg check defs
   ```

4. **If validation passes**, remove old directories:
   ```bash
   rm -rf defs/old_component_1
   rm -rf defs/old_component_2
   # etc.
   ```

5. **If validation fails**, investigate errors and fix YAML syntax

### Step 8: Validate Consolidated Structure

Run comprehensive validation:

```bash
# Check definitions load correctly
uv run dg check defs

# Verify all assets are still present
uv run dg list defs

# Verify schedules are still present
uv run dg list schedules

# Verify jobs are still present
uv run dg list jobs
```

Compare asset counts before and after:
```bash
# Before consolidation (save to file)
uv run dg list defs --json > /tmp/before.json

# After consolidation
uv run dg list defs --json > /tmp/after.json

# Compare counts
uv run python -c "
import json
with open('/tmp/before.json') as f:
    before = json.load(f)
with open('/tmp/after.json') as f:
    after = json.load(f)

print(f'Assets before: {len(before.get(\"assets\", []))}')
print(f'Assets after: {len(after.get(\"assets\", []))}')
print(f'Schedules before: {len(before.get(\"schedules\", []))}')
print(f'Schedules after: {len(after.get(\"schedules\", []))}')
"
```

**Success criteria:**
- ✅ Asset count matches before and after
- ✅ Schedule count matches before and after
- ✅ Job count matches before and after
- ✅ No errors from `dg check defs`

## Common Consolidation Patterns

### Pattern 1: Full Pipeline (Source → Transform → BI → Schedule)

**Components**: Fivetran/Sling → dbt → PowerBI/Looker → Schedule

**Directory**: `<domain>_analytics_pipeline/`

**Example**:
```yaml
# defs/finance_analytics_pipeline/defs.yaml

type: my_project.components.FivetranComponent
attributes:
  connector_id: "netsuite_connector"
  tables: [transactions, accounts]
---
type: dagster_dbt.DbtProjectComponent
attributes:
  project:
    project_dir: finance_dbt
---
type: dagster_powerbi.PowerBIWorkspaceComponent
attributes:
  workspace_id: "finance_workspace"
---
type: my_project.components.ScheduledJobComponent
attributes:
  job_name: "daily_finance_pipeline"
  cron_schedule: "0 6 * * *"
  asset_selection: "tag:domain=finance"
```

### Pattern 2: Multi-Source Pipeline (Multiple Sources → Single Transform)

**Components**: Fivetran + Sling + API → dbt

**Directory**: `<domain>_unified_data/`

**Example**:
```yaml
# defs/customer_360_pipeline/defs.yaml

type: my_project.components.FivetranComponent
attributes:
  connector_id: "salesforce_connector"
---
type: dagster_sling.SlingReplicationCollectionComponent
attributes:
  replications:
    - path: postgres_replication.yaml
---
type: my_project.components.APIIngestionComponent
attributes:
  api_endpoint: "https://api.company.com/events"
---
type: dagster_dbt.DbtProjectComponent
attributes:
  project:
    project_dir: customer_360_dbt
---
type: my_project.components.ScheduledJobComponent
attributes:
  job_name: "hourly_customer_sync"
  cron_schedule: "0 * * * *"
  asset_selection: "tag:pipeline=customer_360"
```

### Pattern 3: BI-Only Pipeline (Transform → Multiple BI Tools)

**Components**: dbt → PowerBI + Looker + Tableau

**Directory**: `<domain>_dashboards/`

**Example**:
```yaml
# defs/executive_dashboards/defs.yaml

type: dagster_dbt.DbtProjectComponent
attributes:
  project:
    project_dir: executive_dbt
---
type: dagster_powerbi.PowerBIWorkspaceComponent
attributes:
  workspace_id: "executive_workspace"
---
type: dagster_looker.LookerComponent
attributes:
  base_url: "https://company.looker.com"
---
type: dagster_tableau.TableauWorkspaceComponent
attributes:
  site_name: "executive_site"
---
type: my_project.components.ScheduledJobComponent
attributes:
  job_name: "daily_dashboard_refresh"
  cron_schedule: "0 7 * * *"
  asset_selection: "kind:powerbi | kind:looker | kind:tableau"
```

### Pattern 4: Reverse ETL Pipeline (Transform → Sync to SaaS)

**Components**: dbt → Census/Hightouch → Schedule

**Directory**: `<domain>_reverse_etl/`

**Example**:
```yaml
# defs/marketing_reverse_etl/defs.yaml

type: dagster_dbt.DbtProjectComponent
attributes:
  project:
    project_dir: marketing_dbt
---
type: dagster_census.CensusComponent
attributes:
  syncs:
    - sync_id: "salesforce_leads_sync"
    - sync_id: "hubspot_contacts_sync"
---
type: my_project.components.ScheduledJobComponent
attributes:
  job_name: "hourly_crm_sync"
  cron_schedule: "0 * * * *"
  asset_selection: "kind:dbt kind:census"
```

### Pattern 5: Schedule Consolidation

**Components**: Multiple schedules for the same pipeline

**Directory**: Keep in the main pipeline directory

**Example**:
```yaml
# defs/data_platform/defs.yaml

type: dagster_fivetran.FivetranComponent
attributes:
  connector_id: "main_connector"
---
type: dagster_dbt.DbtProjectComponent
attributes:
  project:
    project_dir: main_dbt
---
# Multiple schedules for different cadences
type: my_project.components.ScheduledJobComponent
attributes:
  job_name: "hourly_critical_assets"
  cron_schedule: "0 * * * *"
  asset_selection: "tag:priority=critical"
---
type: my_project.components.ScheduledJobComponent
attributes:
  job_name: "daily_standard_assets"
  cron_schedule: "0 6 * * *"
  asset_selection: "tag:schedule=daily"
---
type: my_project.components.ScheduledJobComponent
attributes:
  job_name: "weekly_reports"
  cron_schedule: "0 8 * * 1"
  asset_selection: "tag:schedule=weekly"
```

## Consolidation Strategy Decision Tree

```
START: Analyze component relationships

1. Do components share asset dependencies?
   YES → Group them together
   NO → Continue

2. Do components share the same domain tag?
   YES → Group by domain
   NO → Continue

3. Is there a schedule that targets these components?
   YES → Include schedule in the group
   NO → Continue

4. Do components form a logical pipeline?
   (e.g., source → transform → destination)
   YES → Group as a pipeline
   NO → Keep separate

5. Are components used across multiple pipelines?
   YES → Ask user: duplicate or keep separate?
   NO → Continue to consolidation
```

## Implementation Steps

### Step-by-Step Process

1. **Scan existing structure**:
   ```bash
   find defs -type d -mindepth 1 -maxdepth 1
   find defs -name "defs.yaml" -type f
   ```

2. **Read and parse each YAML file**:
   ```python
   import yaml

   def read_component_yaml(path):
       with open(path) as f:
           doc = yaml.safe_load(f)
       return {
           'path': path,
           'type': doc.get('type'),
           'attributes': doc.get('attributes', {}),
       }
   ```

3. **Identify relationships**:
   - Check for asset_selection in schedules
   - Check for kinds in component configs
   - Check for domain tags
   - Check for project references (e.g., dbt project_dir)

4. **Group components**:
   ```python
   pipelines = {
       'pipeline_name': [
           {'type': 'FivetranComponent', 'yaml': '...'},
           {'type': 'DbtProjectComponent', 'yaml': '...'},
           {'type': 'ScheduledJobComponent', 'yaml': '...'},
       ]
   }
   ```

5. **Create consolidated files**:
   ```python
   def create_consolidated_yaml(pipeline_name, components):
       yaml_content = []
       for i, component in enumerate(components):
           if i > 0:
               yaml_content.append('---')
           yaml_content.append(component['yaml'])

       os.makedirs(f'defs/{pipeline_name}', exist_ok=True)
       with open(f'defs/{pipeline_name}/defs.yaml', 'w') as f:
           f.write('\n'.join(yaml_content))
   ```

6. **Migrate additional files**:
   ```bash
   # Copy any non-defs.yaml files
   for old_dir in old_component_dirs:
       for file in find old_dir -type f ! -name "defs.yaml":
           cp file new_pipeline_dir/
   ```

7. **Validate**:
   ```bash
   uv run dg check defs
   ```

8. **Clean up** (only after validation passes):
   ```bash
   rm -rf defs/old_component_1
   rm -rf defs/old_component_2
   ```

## Success Criteria

The consolidation is complete when:

- ✅ Related components are grouped in single `defs.yaml` files
- ✅ YAML documents are separated with `---`
- ✅ Directory names reflect pipeline/domain purpose
- ✅ All additional files (replication configs, component.py) are migrated
- ✅ `uv run dg check defs` passes without errors
- ✅ Asset count matches before and after consolidation
- ✅ Schedule count matches before and after consolidation
- ✅ Old component directories are removed
- ✅ Project structure is cleaner and more maintainable

## Best Practices

1. **Name directories by purpose**: Use names that describe what the pipeline does
   - ✅ `salesforce_analytics_pipeline/`
   - ✅ `finance_reporting/`
   - ❌ `pipeline1/`
   - ❌ `group_a/`

2. **Keep related components together**: If they share assets or domains, consolidate them

3. **Add comments in YAML**: Explain what each component does
   ```yaml
   # Daily Salesforce sync - runs at 2 AM
   type: FivetranComponent
   attributes:
     ...
   ---
   # Analytics models - depends on Salesforce sync
   type: DbtProjectComponent
   attributes:
     ...
   ```

4. **Preserve logical order**: List components in execution order
   - First: Data ingestion (Fivetran, Sling, APIs)
   - Second: Transformation (dbt)
   - Third: Data activation (BI tools, reverse ETL)
   - Last: Schedules

5. **Don't over-consolidate**: Keep unrelated components separate
   - ❌ Don't put all schedules in one file if they target different pipelines
   - ❌ Don't combine finance and marketing pipelines just because they use the same tools

6. **Backup before consolidation**: Create a git commit before running this skill

7. **Test incrementally**: Consolidate one pipeline at a time and validate

## Troubleshooting

### YAML parsing errors after consolidation

**Problem**: `dg check defs` fails with YAML syntax errors

**Solution**:
1. Verify `---` separator is on its own line
2. Check for proper indentation (use spaces, not tabs)
3. Ensure each document starts at column 0
4. Look for special characters that need quoting

### Assets missing after consolidation

**Problem**: Asset count decreased after consolidation

**Solution**:
1. Check that all YAML files were included in consolidation
2. Verify no YAML documents were accidentally deleted
3. Look for components that weren't properly grouped
4. Check for duplicate component instances (which may be intentional)

### Schedules not working

**Problem**: Schedules don't appear or don't select assets

**Solution**:
1. Verify schedule asset_selection still matches component kinds/tags
2. Check that scheduled components are in the same or accessible defs
3. Ensure schedule cron_schedule is still valid
4. Run `uv run dg list assets --job <job_name>` to verify selection

### Components in wrong group

**Problem**: Component was consolidated with wrong pipeline

**Solution**:
1. Move the component YAML document to the correct file
2. Add `---` separator if needed
3. Re-validate with `dg check defs`

## Next Steps

After completion, inform the user:

1. ✅ Number of component instances consolidated
2. 📁 New directory structure and pipeline names
3. 🔍 Asset/schedule counts before and after (should match)
4. ✅ Validation status from `dg check defs`
5. 🗑️ Old directories that were removed
6. 📝 Suggestions for further organization improvements
7. 💡 How to maintain the consolidated structure going forward

## Additional Resources

- YAML Multi-Document Syntax: https://yaml.org/spec/1.2.2/#22-structures
- Dagster Components Guide: https://docs.dagster.io/guides/build/components
- Asset Selection Syntax: https://docs.dagster.io/concepts/assets/software-defined-assets#asset-selection-syntax
- Dagster Project Structure: https://docs.dagster.io/guides/build/project-structure
