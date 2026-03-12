# Create Scheduled Jobs

## ScheduledJobComponent

Scaffold then implement:

```bash
uv run dg scaffold component ScheduledJobComponent
```

Component at `defs/components/scheduled_job_component.py`:

```python
import dagster as dg
from dagster.components import Component, ComponentLoadContext, Resolvable
from dataclasses import dataclass

@dataclass
class ScheduledJobComponent(Component, Resolvable):
    job_name: str
    cron_schedule: str
    asset_selection: str

    def build_defs(self, context: ComponentLoadContext) -> dg.Definitions:
        job = dg.define_asset_job(name=self.job_name, selection=self.asset_selection)
        schedule = dg.ScheduleDefinition(job=job, cron_schedule=self.cron_schedule)
        return dg.Definitions(schedules=[schedule], jobs=[job])
```

## Creating Instances

```bash
uv run dg scaffold defs <project>.components.ScheduledJobComponent <instance_name>
```

Example `defs.yaml`:
```yaml
type: my_project.components.ScheduledJobComponent
attributes:
  job_name: "daily_finance_job"
  cron_schedule: "0 6 * * *"
  asset_selection: "tag:schedule=daily tag:domain=finance"
```

## Asset Selection Syntax

| Pattern | Description |
|---------|-------------|
| `tag:key=value` | Assets with tag |
| `group:name` | Assets in group |
| `kind:type` | Assets of kind |
| `owner:email` | Assets by owner |
| `*pattern*` | Key pattern match |
| `tag:a=1 tag:b=2` | AND (space-separated) |
| `group:a \| group:b` | OR (pipe) |
| `*asset*+` | Asset + downstream |
| `sel1 - sel2` | Exclusion |

## Common Cron Patterns

| Schedule | Cron |
|----------|------|
| Hourly | `0 * * * *` |
| Every 6h | `0 */6 * * *` |
| Daily 6AM | `0 6 * * *` |
| Weekdays 6AM | `0 6 * * 1-5` |
| Monday 8AM | `0 8 * * 1` |
| Monthly | `0 0 1 * *` |

## Validation

```bash
uv run dg check defs
uv run dg list defs
```
