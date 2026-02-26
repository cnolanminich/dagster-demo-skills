---
name: create-scheduled-jobs
description: Create a ScheduledJobComponent and add multiple scheduled job instances using asset selection syntax (tags, groups, owners, keys) for flexible scheduling patterns. Demonstrates cron scheduling with various selection criteria.
license: MIT
---

# Create Scheduled Jobs Component and Instances

## Overview

This skill automates the creation of a ScheduledJobComponent that enables flexible scheduling of assets using Dagster's asset selection syntax. Instead of hardcoding asset keys, this approach uses selection strings (tags, groups, owners, kinds) to dynamically select which assets to run on each schedule.

## What This Skill Does

When invoked, this skill will:

1. ✅ Create a ScheduledJobComponent using `dg scaffold component ScheduledJobComponent`
2. ✅ Fill in the component with scheduling logic that accepts cron schedules and asset selections
3. ✅ Create 3-5 scheduled job instances with different selection patterns
4. ✅ Demonstrate various asset selection syntaxes (tags, groups, kinds, owners)
5. ✅ Validate that all schedules load correctly using `dg check defs` and `dg list schedules`

## Prerequisites

Before running this skill, ensure:

- `uv` is installed (check with `uv --version`)
- You're in a Dagster project directory with the dg CLI available
- You have existing assets with tags, groups, or other metadata to schedule
- You understand basic cron syntax for scheduling

## Key Concepts: Asset Selection Syntax

Dagster provides powerful asset selection syntax:

### Selection String Patterns

```python
# By tag
"tag:schedule=daily"
"tag:priority=high"

# By group
"group:marketing_analytics"

# By kind
"kind:dbt"
"kind:fivetran"

# By owner
"owner:data-team@company.com"

# By key pattern
"key:raw/*"
"*customers*"

# Combinations (use spaces for AND, | for OR)
"tag:schedule=daily tag:priority=high"  # AND
"tag:domain=finance | tag:domain=operations"  # OR

# Downstream/upstream
"*customers*+"  # customers and all downstream
"+*customers*"  # customers and all upstream
"*customers*++"  # customers and all descendants
```

## Skill Workflow

### Step 1: Ask User for Scheduling Requirements

Ask the user:

1. What scheduling patterns they need (e.g., daily, hourly, weekly, custom cron)
2. What asset tags/groups/kinds exist in their project to schedule
3. How many scheduled jobs they want to create (default: 3-5 examples)
4. Whether they want to create example assets for demonstration (if they don't have assets yet)

### Step 2: Create ScheduledJobComponent

Use `dg scaffold component` to create the component:

```bash
uv run dg scaffold component ScheduledJobComponent
```

This creates `defs/components/scheduled_job_component.py`.

### Step 3: Implement Component Logic

Fill in the component with the scheduling logic:

```python
"""Scheduled job component for flexible asset scheduling.

This component allows you to create schedules using asset selection syntax
instead of hardcoded asset keys, making schedules maintainable and scalable.
"""

import dagster as dg
from dagster.components import Component, ComponentLoadContext, Resolvable
from dataclasses import dataclass


@dataclass
class ScheduledJobComponent(Component, Resolvable):
    """Component for scheduling assets using flexible selection syntax.

    Adds a Dagster schedule for a given asset selection string and cron schedule.

    Asset selection examples:
    - "tag:schedule=daily" - All assets tagged with schedule=daily
    - "group:marketing" - All assets in the marketing group
    - "kind:dbt" - All dbt assets
    - "owner:team@company.com" - All assets owned by a team
    - "*customers*" - All assets with 'customers' in the key
    - "tag:priority=high tag:domain=finance" - High priority finance assets
    """

    # These fields define the YAML schema via Resolvable
    job_name: str
    cron_schedule: str
    asset_selection: str

    def build_defs(self, context: ComponentLoadContext) -> dg.Definitions:
        """Build a scheduled job with flexible asset selection."""

        job = dg.define_asset_job(
            name=self.job_name,
            selection=self.asset_selection,
        )

        schedule = dg.ScheduleDefinition(
            job=job,
            cron_schedule=self.cron_schedule,
        )

        return dg.Definitions(
            schedules=[schedule],
            jobs=[job],
        )
```

**Important Notes:**

1. **Use `@dataclass` decorator** - Required for the Resolvable interface
2. **Fields become YAML schema** - All dataclass fields automatically appear in YAML
3. **Asset selection is a string** - Dagster parses the selection syntax at runtime
4. **Cron schedule format** - Standard cron format (minute hour day month weekday)

### Step 4: Create Example Assets (Optional)

If the user requested example assets, create a sample assets file to demonstrate scheduling:

```bash
uv run dg scaffold defs dagster.Definitions example_assets
```

Then write example assets to `defs/example_assets/defs.py`:

```python
"""Example assets demonstrating various scheduling patterns."""

import dagster as dg


@dg.asset(
    kinds={"python"},
    tags={"schedule": "daily", "priority": "high", "domain": "finance"},
    group_name="finance_core",
    owners=["data-team@company.com"],
)
def daily_revenue_summary(context: dg.AssetExecutionContext):
    """Daily revenue aggregation - scheduled to run every morning."""
    context.log.info("Processing daily revenue summary")
    return {"revenue": 1000000, "transactions": 5000}


@dg.asset(
    kinds={"python"},
    tags={"schedule": "hourly", "priority": "critical", "domain": "operations"},
    group_name="operations_core",
    owners=["ops-team@company.com"],
)
def inventory_snapshot(context: dg.AssetExecutionContext):
    """Hourly inventory snapshot - scheduled every hour."""
    context.log.info("Capturing inventory snapshot")
    return {"inventory_count": 5000, "low_stock_items": 12}


@dg.asset(
    kinds={"python"},
    tags={"schedule": "weekly", "priority": "medium", "domain": "marketing"},
    group_name="marketing_analytics",
    owners=["marketing-team@company.com"],
)
def weekly_campaign_analysis(context: dg.AssetExecutionContext):
    """Weekly marketing campaign analysis - scheduled Monday mornings."""
    context.log.info("Analyzing weekly campaign performance")
    return {"campaigns_analyzed": 25, "total_spend": 50000}


@dg.asset(
    kinds={"dbt"},
    tags={"schedule": "daily", "priority": "high", "domain": "finance"},
    group_name="finance_core",
    owners=["data-team@company.com"],
    deps=[daily_revenue_summary],
)
def revenue_variance_report(context: dg.AssetExecutionContext):
    """Revenue variance report - depends on daily revenue summary."""
    context.log.info("Generating revenue variance report")
    return {"variance_pct": 5.2, "status": "within_threshold"}


@dg.asset(
    kinds={"python"},
    tags={"schedule": "adhoc", "priority": "low", "domain": "analytics"},
    group_name="exploratory_analysis",
    owners=["analytics-team@company.com"],
)
def experimental_model(context: dg.AssetExecutionContext):
    """Experimental model - no regular schedule, run on demand."""
    context.log.info("Running experimental analysis")
    return {"experiments": 10, "best_accuracy": 0.87}
```

### Step 5: Create Scheduled Job Instances

Create 3-5 scheduled job instances with different selection patterns. For each one:

```bash
uv run dg scaffold defs <project_name>.components.ScheduledJobComponent <instance_name>
```

Example instances to create:

**Instance 1: Daily Finance Job**
```bash
uv run dg scaffold defs <project_name>.components.ScheduledJobComponent daily_finance_job
```

Edit `defs/daily_finance_job/defs.yaml`:
```yaml
type: <project_name>.components.ScheduledJobComponent

attributes:
  job_name: "daily_finance_job"
  cron_schedule: "0 6 * * *"  # 6 AM UTC daily
  asset_selection: "tag:schedule=daily tag:domain=finance"
```

**Instance 2: Hourly Operations Job**
```bash
uv run dg scaffold defs <project_name>.components.ScheduledJobComponent hourly_ops_job
```

Edit `defs/hourly_ops_job/defs.yaml`:
```yaml
type: <project_name>.components.ScheduledJobComponent

attributes:
  job_name: "hourly_ops_job"
  cron_schedule: "0 * * * *"  # Every hour
  asset_selection: "tag:schedule=hourly tag:priority=critical"
```

**Instance 3: Weekly Marketing Job**
```bash
uv run dg scaffold defs <project_name>.components.ScheduledJobComponent weekly_marketing_job
```

Edit `defs/weekly_marketing_job/defs.yaml`:
```yaml
type: <project_name>.components.ScheduledJobComponent

attributes:
  job_name: "weekly_marketing_job"
  cron_schedule: "0 8 * * 1"  # 8 AM UTC every Monday
  asset_selection: "tag:schedule=weekly group:marketing_analytics"
```

**Instance 4: High Priority Job (All Domains)**
```bash
uv run dg scaffold defs <project_name>.components.ScheduledJobComponent high_priority_job
```

Edit `defs/high_priority_job/defs.yaml`:
```yaml
type: <project_name>.components.ScheduledJobComponent

attributes:
  job_name: "high_priority_job"
  cron_schedule: "0 */6 * * *"  # Every 6 hours
  asset_selection: "tag:priority=high"
```

**Instance 5: Data Team Owned Assets**
```bash
uv run dg scaffold defs <project_name>.components.ScheduledJobComponent data_team_job
```

Edit `defs/data_team_job/defs.yaml`:
```yaml
type: <project_name>.components.ScheduledJobComponent

attributes:
  job_name: "data_team_job"
  cron_schedule: "0 7 * * *"  # 7 AM UTC daily
  asset_selection: "owner:data-team@company.com"
```

### Step 6: Validate Setup

Run validation commands to ensure everything works:

```bash
# Check that all definitions load without errors
uv run dg check defs

# List all schedules to verify they were created
uv run dg list schedules

# List all jobs
uv run dg list jobs

# See which assets are selected by a specific job
uv run dg list assets --job daily_finance_job
```

Verify that:

- ✅ All scheduled job instances are listed
- ✅ Each schedule has the correct cron pattern
- ✅ Each job selects the expected assets
- ✅ No errors or warnings are shown

**Verify Asset Selections:**

For each job, check which assets it selects:

```bash
# Check daily finance job selections
uv run dg list assets --job daily_finance_job

# Check hourly ops job selections
uv run dg list assets --job hourly_ops_job

# Check weekly marketing job selections
uv run dg list assets --job weekly_marketing_job
```

**Expected results (if using example assets):**
- `daily_finance_job` should select: `daily_revenue_summary`, `revenue_variance_report`
- `hourly_ops_job` should select: `inventory_snapshot`
- `weekly_marketing_job` should select: `weekly_campaign_analysis`
- `high_priority_job` should select: `daily_revenue_summary`, `revenue_variance_report`, `inventory_snapshot`
- `data_team_job` should select: `daily_revenue_summary`, `revenue_variance_report`

## Advanced Selection Patterns

### Pattern 1: Multiple Tags (AND logic)

```yaml
attributes:
  job_name: "critical_finance_job"
  cron_schedule: "0 5 * * *"
  asset_selection: "tag:domain=finance tag:priority=critical"  # Both tags required
```

### Pattern 2: Multiple Groups (OR logic)

```yaml
attributes:
  job_name: "core_models_job"
  cron_schedule: "0 4 * * *"
  asset_selection: "group:finance_core | group:operations_core"  # Either group
```

### Pattern 3: Kind-Based Selection

```yaml
attributes:
  job_name: "all_dbt_models"
  cron_schedule: "0 3 * * *"
  asset_selection: "kind:dbt"  # All dbt assets
```

### Pattern 4: Key Pattern Matching

```yaml
attributes:
  job_name: "customer_pipeline"
  cron_schedule: "0 2 * * *"
  asset_selection: "*customers*"  # All assets with 'customers' in key
```

### Pattern 5: Downstream Dependencies

```yaml
attributes:
  job_name: "revenue_pipeline_with_deps"
  cron_schedule: "0 6 * * *"
  asset_selection: "*revenue*+"  # revenue assets and all downstream
```

### Pattern 6: Complex Combinations

```yaml
attributes:
  job_name: "complex_selection"
  cron_schedule: "0 8 * * *"
  asset_selection: "(tag:domain=finance | tag:domain=operations) tag:priority=high kind:dbt"
```

### Pattern 7: Exclusion (using minus)

```yaml
attributes:
  job_name: "daily_non_test"
  cron_schedule: "0 5 * * *"
  asset_selection: "tag:schedule=daily - tag:test=true"  # Daily assets excluding tests
```

## Common Cron Patterns

```yaml
# Every hour on the hour
cron_schedule: "0 * * * *"

# Every 6 hours
cron_schedule: "0 */6 * * *"

# Daily at 2 AM UTC
cron_schedule: "0 2 * * *"

# Every Monday at 8 AM UTC
cron_schedule: "0 8 * * 1"

# Every weekday (Mon-Fri) at 6 AM UTC
cron_schedule: "0 6 * * 1-5"

# First day of month at midnight
cron_schedule: "0 0 1 * *"

# Every 15 minutes
cron_schedule: "*/15 * * * *"

# Twice daily: 6 AM and 6 PM UTC
cron_schedule: "0 6,18 * * *"

# Every Sunday at 10 AM UTC
cron_schedule: "0 10 * * 0"
```

## Success Criteria

The scheduled jobs setup is complete when:

- ✅ ScheduledJobComponent is created and implemented
- ✅ 3-5 scheduled job instances are created with different selection patterns
- ✅ Each instance uses asset selection syntax (NOT hardcoded keys)
- ✅ Component YAML files are properly configured
- ✅ `uv run dg check defs` passes without errors
- ✅ `uv run dg list schedules` shows all expected schedules
- ✅ `uv run dg list assets --job <job_name>` shows correct asset selections
- ✅ Example assets are created (if requested)

## Best Practices

1. **Use selection syntax over hardcoded keys**: Makes schedules maintainable as project grows
2. **Tag assets consistently**: Use standard tag names across your project (schedule, priority, domain, owner)
3. **Document cron schedules**: Add comments in YAML to explain timing choices
4. **Test selections before deploying**: Use `dg list assets --job` to verify selections
5. **Use meaningful job names**: Names should indicate purpose and timing (e.g., `daily_finance_job`)
6. **Avoid over-scheduling**: Don't run jobs more frequently than data actually changes
7. **Consider dependencies**: Use `+` suffix to include downstream assets
8. **Group related schedules**: Put schedules for the same domain/team together

## Common Selection Patterns Reference

| Pattern | Description | Example |
|---------|-------------|---------|
| `tag:key=value` | Assets with specific tag | `tag:schedule=daily` |
| `group:name` | Assets in a group | `group:marketing` |
| `kind:type` | Assets of a kind | `kind:dbt` |
| `owner:email` | Assets with owner | `owner:team@co.com` |
| `*pattern*` | Key pattern match | `*customers*` |
| `tag:a=1 tag:b=2` | Multiple tags (AND) | `tag:schedule=daily tag:priority=high` |
| `group:a \| group:b` | Multiple groups (OR) | `group:finance \| group:ops` |
| `*asset*+` | Asset + downstream | `*revenue*+` |
| `+*asset*` | Asset + upstream | `+*orders*` |
| `sel1 - sel2` | Exclusion | `tag:daily - tag:test=true` |

## Troubleshooting

### No assets selected by job

**Problem**: Job runs but selects 0 assets

**Solution**:
1. Run `uv run dg list assets --job <job_name>` to see what's selected
2. Check that assets have the tags/groups/owners you're selecting
3. Verify tag/group names match exactly (case-sensitive)
4. Check for typos in the `asset_selection` string

### Schedule not appearing

**Problem**: Schedule doesn't show in `dg list schedules`

**Solution**:
1. Run `uv run dg check defs` to see validation errors
2. Verify the component type path in YAML is correct
3. Check that `cron_schedule` is a valid cron expression
4. Ensure `job_name` is unique across all jobs

### Syntax errors in asset selection

**Problem**: Error parsing asset selection string

**Solution**:
1. Check for unmatched parentheses in complex selections
2. Use spaces between selection terms for AND logic
3. Use `|` (pipe) for OR logic, not commas
4. Quote the entire selection string in YAML
5. Test selection with `dg list assets --job` before running

### Component not found

**Problem**: `Type '<project>.components.ScheduledJobComponent' not found`

**Solution**:
1. Verify component file is at `defs/components/scheduled_job_component.py`
2. Check that class name matches exactly: `ScheduledJobComponent`
3. Ensure the project name in YAML matches your project structure
4. Verify the component file has no Python syntax errors

## Next Steps

After completion, inform the user:

1. ✅ The ScheduledJobComponent has been created and validated
2. 📁 Location: `defs/components/scheduled_job_component.py`
3. 🗓️ Number of scheduled job instances created and their patterns
4. 🎯 How to verify asset selections using `uv run dg list assets --job <job_name>`
5. ➕ How to add more scheduled jobs by creating new instances with `dg scaffold defs`
6. 🏷️ Best practices for tagging assets to work with selection syntax
7. 🚀 How to test schedules with `uv run dg materialize --job <job_name>`

## Additional Resources

- Dagster Jobs Documentation: https://docs.dagster.io/concepts/ops-jobs-graphs/jobs
- Dagster Schedules Documentation: https://docs.dagster.io/concepts/partitions-schedules-sensors/schedules
- Asset Selection Syntax: https://docs.dagster.io/concepts/assets/software-defined-assets#asset-selection-syntax
- Cron Expression Reference: https://crontab.guru/
- Component Guide: https://docs.dagster.io/guides/build/components
