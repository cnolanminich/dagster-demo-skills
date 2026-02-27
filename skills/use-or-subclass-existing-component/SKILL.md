---
name: use-or-subclass-existing-component
description: Subclass existing Dagster integration components to add custom behavior (demo mode, asset key alignment, custom metadata). Use only when an existing Dagster component exists within Dagster's integration libraries. For discovering integrations, use dagster-integrations. For CLI usage, use dagster-expert.
license: MIT
---

# Use or Subclass Existing Dagster Component

## Overview

This skill helps you work with existing Dagster integration components by using them directly or subclassing them to add custom functionality. It focuses on the **subclassing patterns** — when to subclass, how to override key methods, and how to align asset keys across multi-component pipelines.

**Prerequisites:** Use the **dagster-integrations** skill to discover which integration to use. Use the **dagster-expert** skill for CLI commands (`dg scaffold`, `dg check defs`, `dg list defs`).

The documentation for subclassing components can be found here: https://docs.dagster.io/guides/build/components/creating-new-components/subclassing-components

## When to Switch Skills

If the integration package exists but has NO Component class:
- Run: `uv run python -c "import dagster_<integration>; print([x for x in dir(dagster_<integration>) if 'Component' in x])"`
- If result is `[]`, the integration doesn't have a Component class
- **STOP and use the `create-custom-dagster-component` skill instead**

This skill is ONLY for integrations that have existing Component classes to subclass.

## Determine Component Type and Use Case

**IMPORTANT:** First determine if this is a configuration-file-based or API-based component:

### Configuration-File-Based Components
These components read from local configuration files and do NOT require external API credentials:
- `DbtProjectComponent` - Reads from dbt project files
- `SlingReplicationCollectionComponent` - Reads from replication YAML files

**For configuration-file-based components:**
- Use the component directly or subclass for custom behavior
- **DO NOT** implement demo_mode — these work with local files naturally

### API-Based Components
These components call out to external services and require API credentials:
- `FivetranAccountComponent` - Calls Fivetran API
- `PowerBIWorkspaceComponent` - Calls PowerBI API
- `LookerComponent` - Calls Looker API
- `AirbyteComponent` - Calls Airbyte API
- `CensusComponent` - Calls Census API

**For API-based components:**
- Implement demo_mode to mock external API calls
- Provide dummy credentials in YAML (ignored when demo_mode is true)

### Decide Your Approach

1. **Use directly** — Load the component with default behavior. Skip to the YAML configuration section.
2. **Subclass for demo mode (API-based only)** — Add demo_mode to mock external API calls
3. **Subclass for custom behavior** — Override `build_defs()`, `get_asset_spec()`, or `execute()`

## Subclassing Patterns

### Identifying the Parent Component Type

First, check if the parent uses dataclass or Pydantic:

```python
uv run python -c "from <package> import <Component>; import dataclasses; print(dataclasses.is_dataclass(<Component>))"
```

Most Dagster integration components use **dataclass** with the `Resolvable` interface.

### Pattern for Dataclass-Based Components (Most Common)

```python
from dataclasses import dataclass
import dagster as dg
from <integration_package> import <BaseComponentClass>

@dataclass
class Custom<ComponentName>(BaseComponentClass):
    """Customized component with demo mode support."""

    demo_mode: bool = False

    def build_defs(self, context: dg.ComponentLoadContext) -> dg.Definitions:
        """Build definitions, using demo mode if enabled."""
        if self.demo_mode:
            return self._build_demo_defs(context)
        return super().build_defs(context)

    def _build_demo_defs(self, context: dg.ComponentLoadContext) -> dg.Definitions:
        """Build demo mode definitions with mocked assets."""
        @dg.asset(
            key=dg.AssetKey(["mock_asset"]),
            kinds={"integration_name"},
        )
        def mock_asset(context: dg.AssetExecutionContext):
            context.log.info("Demo mode: simulating asset execution")
            return {"status": "demo_mode"}

        return dg.Definitions(assets=[mock_asset])
```

**Key points for dataclass components:**
1. Use `@dataclass` decorator on your subclass
2. Add fields with type annotations — they automatically become YAML schema fields
3. Use `field(default_factory=...)` for mutable defaults (lists, dicts)
4. The `Resolvable` interface (inherited from parent) handles YAML schema generation
5. All fields with defaults must come after fields without defaults

**Example with multiple custom fields:**

```python
from dataclasses import dataclass, field
import dagster as dg
from dagster_sling import SlingReplicationCollectionComponent

@dataclass
class CustomSlingComponent(SlingReplicationCollectionComponent):
    """Extended Sling component with additional configuration."""

    demo_mode: bool = False
    enable_notifications: bool = False
    notification_channel: str = "slack"
    custom_tags: list[str] = field(default_factory=list)

    def build_defs(self, context: dg.ComponentLoadContext) -> dg.Definitions:
        if self.demo_mode:
            return self._build_demo_defs(context)
        return super().build_defs(context)
```

### Pattern for Pydantic BaseModel Components (Rare)

```python
import dagster as dg
from <integration_package> import <BaseComponentClass>

class Custom<ComponentName>(BaseComponentClass, dg.Model):
    """Customized component with demo mode support."""

    demo_mode: bool = False

    def build_defs(self, context: dg.ComponentLoadContext) -> dg.Definitions:
        if self.demo_mode:
            return self._build_demo_defs(context)
        return super().build_defs(context)
```

### Pattern for Legacy execute()-based Components

```python
from dataclasses import dataclass
from dagster import AssetExecutionContext
from <integration_package> import <BaseComponentClass>
from collections.abc import Iterator
from typing import Any

@dataclass
class Custom<ComponentName>(BaseComponentClass):
    """Customized component with demo mode support."""

    demo_mode: bool = False

    def execute(
        self,
        context: AssetExecutionContext,
        **kwargs: Any,
    ) -> Iterator:
        if self.demo_mode:
            context.log.info("Running in demo mode with mocked data")
            yield from self._execute_demo_mode(context, **kwargs)
        else:
            yield from super().execute(context, **kwargs)

    def _execute_demo_mode(
        self,
        context: AssetExecutionContext,
        **kwargs: Any,
    ) -> Iterator:
        from dagster import Output
        context.log.info("Simulating integration execution locally")
        yield Output(value=None, output_name="result")
```

### Custom Templating with get_additional_scope()

```python
from dataclasses import dataclass
from collections.abc import Mapping
from typing import Any
import dagster as dg
from <integration_package> import <BaseComponentClass>

@dataclass
class Custom<ComponentName>(BaseComponentClass):
    demo_mode: bool = False

    @classmethod
    def get_additional_scope(cls) -> Mapping[str, Any]:
        """Add custom YAML templating functions."""
        def _custom_cron(cron_schedule: str) -> dg.AutomationCondition:
            return (
                dg.AutomationCondition.on_cron(cron_schedule)
                & ~dg.AutomationCondition.in_progress()
            )
        return {"custom_cron": _custom_cron}
```

## Align Asset Keys for Downstream Components (CRITICAL for Multi-Component Pipelines)

**When to do this:** If other Dagster components in your pipeline will depend on assets from this component, override `get_asset_spec()` to generate asset keys that match downstream expectations.

**This applies when:**
- dbt models will consume these assets
- Custom Dagster assets will reference these assets in their `deps`
- Another integration component expects specific asset key patterns
- You want to simplify multi-level nested keys

### Why This Matters

By default, integration components generate asset keys in their own structure:
- Fivetran: `["fivetran", "raw", "customers"]`
- Sling: `["sling", "replications", "sync_name", "table"]`
- dbt: `["analytics", "marts", "customer_360"]`

Downstream components may expect different key structures, leading to broken dependencies.

### Pattern: Override get_asset_spec()

```python
def get_asset_spec(self, props) -> dg.AssetSpec:
    """Override to generate asset keys matching downstream expectations."""
    base_spec = super().get_asset_spec(props)
    original_key = base_spec.key.path
    custom_key = dg.AssetKey([...])  # Your key transformation logic
    return base_spec.replace_attributes(key=custom_key)
```

### Example: Fivetran → dbt Pipeline

**Problem:** Fivetran creates `["fivetran", "raw", "customers"]`, but dbt expects `["fivetran_raw", "customers"]`

```python
from dagster_fivetran import FivetranAccountComponent
from dagster_fivetran.translator import FivetranConnectorTableProps
import dagster as dg

class CustomFivetranComponent(FivetranAccountComponent):
    def get_asset_spec(self, props: FivetranConnectorTableProps) -> dg.AssetSpec:
        base_spec = super().get_asset_spec(props)
        original_key = base_spec.key.path
        if len(original_key) >= 2:
            flattened_key = dg.AssetKey(["fivetran_raw", "_".join(original_key[1:])])
        else:
            flattened_key = dg.AssetKey(["fivetran_raw", original_key[-1]])
        return base_spec.replace_attributes(key=flattened_key)
```

### Example: Sling → Custom Processing

**Problem:** Sling creates `["sling", "replications", "sync_name", "table"]`, but processors expect `["raw", "table"]`

```python
from dagster_sling import SlingReplicationCollectionComponent
import dagster as dg

class CustomSlingComponent(SlingReplicationCollectionComponent):
    def get_asset_spec(self, props) -> dg.AssetSpec:
        base_spec = super().get_asset_spec(props)
        original_key = base_spec.key.path
        simplified_key = dg.AssetKey(["raw", original_key[-1]])
        return base_spec.replace_attributes(key=simplified_key)
```

### Key Principles

1. **Upstream defines, downstream consumes**: Generate keys that downstream expects
2. **Configure once, apply to all**: One `get_asset_spec()` override applies to all assets
3. **Minimize downstream configuration**: Eliminate `meta.dagster.asset_key` in downstream
4. **Document your key structure**: Make it clear what pattern your component produces

## Component YAML Configuration

Update `defs.yaml` to reference your custom subclass:

```yaml
type: <project_name>.defs.<instance_name>.component.Custom<ComponentName>

attributes:
  demo_mode: true
  <parent_field>: <value>
```

### API-Based Components: Dummy Credentials

For API-based components with demo_mode, provide dummy values to satisfy schema validation:

```yaml
type: my_project.defs.looker_dashboards.component.CustomLookerComponent

attributes:
  demo_mode: true
  looker_resource:
    base_url: "https://demo.looker.com"
    client_id: "demo_client_id"
    client_secret: "demo_client_secret"
```

**Important:**
- The type must be the fully qualified Python path to your custom component class
- **ALWAYS provide dummy values** for required parent fields — they MUST be present for schema validation
- **Keep dummy values UNCOMMENTED** — required for YAML to load
- Your demo_mode implementation ignores these values

**To switch to real mode:** Set `demo_mode: false` and replace dummy values with real credentials.

## Validation

After creating the component, validate using the dagster-expert CLI commands:

```bash
uv run dg check defs
uv run dg list defs
```

**Verify asset key alignment:**

```bash
uv run dg list defs --json | uv run python -c "
import sys, json
data = json.load(sys.stdin)
assets = data.get('assets', [])
for asset in assets:
    key = asset.get('key', 'unknown')
    deps = asset.get('deps', [])
    if deps:
        print(f'{key}')
        for dep in deps:
            print(f'  <- {dep}')
    else:
        print(f'{key} (no dependencies)')
"
```

**Common issues:**
- **dbt models not depending on sources:** SQL must use `{{ source('source_name', 'table') }}`
- **Asset keys too nested:** Override `get_asset_spec()` to flatten
- **Reverse ETL can't find models:** Use simple model names matching expected keys

## Troubleshooting

**Schema validation errors for missing required fields:**
Provide dummy values for all required parent fields. Keep them uncommented.

**Import errors:**
Ensure the integration package is installed: `uv add dagster-<integration>`

**Type reference errors:**
Verify the fully qualified type in `defs.yaml` matches your Python path. Check that `component.py` is in the correct directory.

**Validation failures:**
Check all required attributes in YAML, verify resource configurations, ensure `model_config = ConfigDict(extra="allow")` is set (if Pydantic).

## Success Criteria

- Integration component subclass created with proper inheritance
- Demo mode implemented (if API-based component)
- Component YAML configured with fully qualified type
- All required attributes specified (dummy values for demo mode)
- `dg check defs` passes without errors
- `dg list defs` shows all expected assets
- Asset keys align with downstream component expectations

## Additional Resources

- Subclassing Components Guide: https://docs.dagster.io/guides/build/components/creating-new-components/subclassing-components
- Integration Libraries: https://docs.dagster.io/integrations/libraries
- Component API Reference: https://docs.dagster.io/llms-full.txt
