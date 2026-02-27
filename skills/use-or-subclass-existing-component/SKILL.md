---
name: use-or-subclass-existing-component
description: Discover, use, or subclass existing Dagster integration components (dbt, Looker, PowerBI, Fivetran, etc.). Handles configuration-file-based components (dbt, Sling) and API-based components (Fivetran, PowerBI) appropriately. Use only when an existing Dagster component exists within Dagster's integration libraries. For discovering integrations and CLI usage, use dagster-expert.
license: MIT
---

# Use or Subclass Existing Dagster Component

## Overview

This skill helps you work with existing Dagster integration components by using them directly or subclassing them. It covers when to subclass, how to override key methods, and how to align asset keys across multi-component pipelines.

**Prerequisites:** Use the **dagster-expert** skill for discovering integrations, CLI commands (`dg scaffold`, `dg check defs`, `dg list defs`), and asset key design patterns.

Subclassing docs: https://docs.dagster.io/guides/build/components/creating-new-components/subclassing-components

## When to Switch Skills

If the integration package exists but has no Component class:
```bash
uv run dg list components --json
```
Will not have the package listed in the keys, then **use the `create-custom-dagster-component` skill instead**.

## Determine Component Type

**Configuration-file-based** (read local files, no API credentials):
- `DbtProjectComponent` — reads dbt project files
- `SlingReplicationCollectionComponent` — reads replication YAML files
- **Do NOT implement demo_mode** — these work with local files naturally

**API-based** (call external services, require credentials):
- `FivetranAccountComponent`, `PowerBIWorkspaceComponent`, `LookerComponent`, `AirbyteComponent`, `CensusComponent`
- **Implement demo_mode** to mock external API calls
- Provide dummy credentials in YAML (ignored when demo_mode is true)

## Decide Your Approach

1. **Use directly** — Load the component with default behavior. Skip to YAML configuration.
2. **Subclass for demo mode** (API-based only) — Add demo_mode to mock external calls
3. **Subclass for custom behavior** — Override `build_defs()`, `get_asset_spec()`, or `execute()`

## Subclassing Pattern

Most Dagster integration components use `@dataclass` with `Resolvable`. Check with:
```bash
uv run python -c "from <package> import <Component>; import dataclasses; print(dataclasses.is_dataclass(<Component>))"
```

### Dataclass-Based (Most Common)

```python
from dataclasses import dataclass
import dagster as dg
from <integration_package> import <BaseComponentClass>

@dataclass
class Custom<ComponentName>(BaseComponentClass):
    """Customized component with demo mode support."""

    demo_mode: bool = False

    def build_defs(self, context: dg.ComponentLoadContext) -> dg.Definitions:
        if self.demo_mode:
            return self._build_demo_defs(context)
        return super().build_defs(context)

    def _build_demo_defs(self, context: dg.ComponentLoadContext) -> dg.Definitions:
        @dg.asset(
            key=dg.AssetKey(["mock_asset"]),
            kinds={"integration_name"},
        )
        def mock_asset(context: dg.AssetExecutionContext):
            context.log.info("Demo mode: simulating asset execution")
            return {"status": "demo_mode"}

        return dg.Definitions(assets=[mock_asset])
```

**Key points:**
1. Use `@dataclass` decorator on your subclass
2. Fields with type annotations automatically become YAML schema fields via `Resolvable`
3. Use `field(default_factory=...)` for mutable defaults (lists, dicts)
4. All fields with defaults must come after fields without defaults

For **Pydantic-based** components (rare): inherit from `dg.Model` instead, use `model_config = ConfigDict(extra="allow")`. For **legacy execute()-based** components: override `execute()` instead of `build_defs()`.

### Override get_asset_spec() for Key Alignment

When asset keys from the parent component don't match downstream expectations (e.g., dbt sources), override `get_asset_spec()`:

```python
from dagster_fivetran import FivetranAccountComponent
from dagster_fivetran.translator import FivetranConnectorTableProps
import dagster as dg

class CustomFivetranComponent(FivetranAccountComponent):
    def get_asset_spec(self, props: FivetranConnectorTableProps) -> dg.AssetSpec:
        base_spec = super().get_asset_spec(props)
        original_key = base_spec.key.path
        flattened_key = dg.AssetKey(["fivetran_raw", original_key[-1]])
        return base_spec.replace_attributes(key=flattened_key)
```

See dagster-expert's `asset-key-design` reference for detailed patterns and when to use this.

### Custom Templating with get_additional_scope()

Add custom YAML templating functions by overriding `get_additional_scope()`:

```python
@classmethod
def get_additional_scope(cls) -> Mapping[str, Any]:
    def _custom_cron(cron_schedule: str) -> dg.AutomationCondition:
        return dg.AutomationCondition.on_cron(cron_schedule) & ~dg.AutomationCondition.in_progress()
    return {"custom_cron": _custom_cron}
```

## Component YAML Configuration

```yaml
type: <project_name>.defs.<instance_name>.component.Custom<ComponentName>

attributes:
  demo_mode: true
  <parent_field>: <value>
```

**For API-based components with demo_mode:** provide dummy values for all required parent fields — they must be present for schema validation even though demo_mode ignores them:

```yaml
type: my_project.defs.looker_dashboards.component.CustomLookerComponent

attributes:
  demo_mode: true
  looker_resource:
    base_url: "https://demo.looker.com"
    client_id: "demo_client_id"
    client_secret: "demo_client_secret"
```

To switch to real mode: set `demo_mode: false` and replace dummy values with real credentials.

## Validation

```bash
uv run dg check defs
uv run dg list defs
```

**Common issues:**
- **Schema validation errors**: Provide dummy values for all required parent fields, keep them uncommented
- **Import errors**: Install the integration package with `uv add dagster-<integration>`
- **Type reference errors**: Verify the fully qualified type in `defs.yaml` matches your Python path

## Success Criteria

- Integration component used directly or subclass created with proper inheritance
- Demo mode implemented for API-based components (not for config-file-based)
- Component YAML configured with fully qualified type and all required attributes
- `dg check defs` passes
- `dg list defs` shows all expected assets
- Asset keys align with downstream component expectations
