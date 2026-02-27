---
name: create-scheduled-jobs
description: Create a ScheduledJobComponent and add multiple scheduled job instances using asset selection syntax (tags, groups, owners, keys) for flexible scheduling patterns. Demonstrates cron scheduling with various selection criteria.
license: MIT
---

# Create Scheduled Jobs Component and Instances

## Overview

This skill creates a ScheduledJobComponent that enables flexible scheduling of assets using Dagster's asset selection syntax. Instead of hardcoding asset keys, this approach uses selection strings (tags, groups, owners, kinds) to dynamically select which assets to run on each schedule.

When invoked, this skill will:

1. Create a ScheduledJobComponent using `dg scaffold component ScheduledJobComponent`
2. Fill in the component with scheduling logic that accepts cron schedules and asset selections
3. Create 3-5 scheduled job instances with different selection patterns
4. Validate that all schedules load correctly using `dg check defs` and `dg list schedules`

## Asset Selection Syntax Reference

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
| `(a \| b) c` | Complex combinations | `(tag:domain=finance \| tag:domain=ops) tag:priority=high` |

## Skill Workflow

### Step 1: Ask User for Scheduling Requirements

Ask what scheduling patterns they need, what asset tags/groups/kinds exist in their project, and whether they want example assets created for demonstration.

### Step 2: Create ScheduledJobComponent

```bash
uv run dg scaffold component ScheduledJobComponent
```

This creates `defs/components/scheduled_job_component.py`. Fill in the component:

```python
"""Scheduled job component for flexible asset scheduling."""

import dagster as dg
from dagster.components import Component, ComponentLoadContext, Resolvable
from dataclasses import dataclass


@dataclass
class ScheduledJobComponent(Component, Resolvable):
    """Component for scheduling assets using flexible selection syntax.

    Adds a Dagster schedule for a given asset selection string and cron schedule.
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

**Important:** Use `@dataclass` decorator (required for Resolvable). All dataclass fields automatically become the YAML schema.

### Step 3: Create Scheduled Job Instances

For each schedule, scaffold an instance and edit its `defs.yaml`:

```bash
uv run dg scaffold defs <project_name>.components.ScheduledJobComponent daily_finance_job
```

```yaml
# defs/daily_finance_job/defs.yaml
type: <project_name>.components.ScheduledJobComponent

attributes:
  job_name: "daily_finance_job"
  cron_schedule: "0 6 * * *"  # 6 AM UTC daily
  asset_selection: "tag:schedule=daily tag:domain=finance"
```

Create 3-5 instances with varied selection patterns (by tag, group, kind, owner) and cron schedules. Use meaningful job names that indicate purpose and timing.

### Step 4: Create Example Assets (Optional)

If the user doesn't have assets yet, scaffold example assets with appropriate tags, groups, kinds, and owners so the scheduled jobs have something to select.

### Step 5: Validate

```bash
# Check definitions load correctly
uv run dg check defs

# Verify all schedules were created
uv run dg list schedules

# Verify jobs and their asset selections
uv run dg list jobs
uv run dg list assets --job daily_finance_job
```

## Success Criteria

- ScheduledJobComponent is created and implemented
- 3-5 scheduled job instances use asset selection syntax (not hardcoded keys)
- `uv run dg check defs` passes without errors
- `uv run dg list schedules` shows all expected schedules
- `uv run dg list assets --job <job_name>` shows correct asset selections

## Additional Resources

- Dagster Schedules: https://docs.dagster.io/concepts/partitions-schedules-sensors/schedules
- Asset Selection Syntax: https://docs.dagster.io/concepts/assets/software-defined-assets#asset-selection-syntax
- Component Guide: https://docs.dagster.io/guides/build/components
- Cron Reference: https://crontab.guru/
