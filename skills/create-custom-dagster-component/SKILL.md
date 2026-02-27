---
name: create-custom-dagster-component
description: Create a custom Dagster Component with realistic asset structure and optional custom scaffolder using the dg CLI. Use this skill if there is no Component included in an existing integration or if Dagster does not have the integration.
license: MIT
---

# Create a Custom Component

## Overview

This skill creates a new custom Dagster component using the `dg` CLI tool. Use it when no existing Dagster integration component covers your use case.

**Prerequisites:** Use the **dagster-expert** skill for CLI commands (`dg scaffold`, `dg check defs`, `dg list defs`), to check if an existing component already covers your use case, and for asset key design patterns.

**Reference documentation:**
- Creating components: https://docs.dagster.io/guides/build/components/creating-new-components/creating-and-registering-a-component
- Complex component example: https://github.com/dagster-io/dagster/blob/master/python_modules/libraries/dagster-dbt/dagster_dbt/components/dbt_project/component.py
- Multi-asset integration guide: https://docs.dagster.io/integrations/guides/multi-asset-integration

## Skill Workflow

### Step 1: Get Requirements

Ask the user for:
1. A component name (starts with letter, alphanumeric/hyphens/underscores)
2. Whether they want demo mode support (default: yes for demonstration projects)
3. Whether they want a custom scaffolder

### Step 2: Scaffold Component

```bash
uv run dg scaffold component <ComponentName>
```

Creates a component file in `defs/components/`.

### Step 3: Implement Component Logic

Fill in `build_defs()`. Follow these configuration principles:

- **All configuration in YAML, not hardcoded in Python** (demo mode assets are the exception)
- **Resources configured externally** in `defs/resources.py` using `dg scaffold defs dagster.resource resources.py`
- **Pipeline/API components** that trigger multiple assets should allow an `assets` field in YAML — see https://dagster.io/blog/dsls-to-the-rescue
- **Reference architectures**: [dbt component](https://github.com/dagster-io/dagster/blob/master/python_modules/libraries/dagster-dbt/dagster_dbt/components/dbt_project/component.py), [Fivetran component](https://github.com/dagster-io/dagster/blob/master/python_modules/libraries/dagster-fivetran/dagster_fivetran/components/workspace_component/component.py)

Create 3-5 realistic assets with proper dependencies and technology kinds. Example structure: raw ingestion → transformation → business logic → analytics/ML → output/export.

#### Example: API Ingestion Component

```python
import dagster as dg
from dagster.components import Component, ComponentLoadContext, Resolvable
from dataclasses import dataclass

@dataclass
class APIIngestionComponent(Component, Resolvable):
    """Ingests data from REST APIs."""

    api_endpoint: str
    tables: list[str]
    demo_mode: bool = False

    def build_defs(self, context: ComponentLoadContext) -> dg.Definitions:
        assets = []
        for table in self.tables:
            @dg.asset(
                key=dg.AssetKey(["api_raw", table]),
                kinds={"api", "python"},
            )
            def ingest_table(context: dg.AssetExecutionContext, _table=table):
                if self.demo_mode:
                    context.log.info(f"Demo mode: Mocking API call for {_table}")
                    return {"status": "demo", "rows": 100}
                else:
                    import requests
                    response = requests.get(f"{self.api_endpoint}/{_table}")
                    return response.json()

            assets.append(ingest_table)
        return dg.Definitions(assets=assets)
```

#### Demo Mode Guidelines

- **Asset keys must be identical** in demo and production mode — only the function body differs
- Demo mode should use local/mocked behavior, no external dependencies
- Non-demo mode should use realistic connections to databases or APIs

### Step 4: Create Component Instance YAML

```bash
uv run dg scaffold defs my_module.components.ComponentName my_component
```

```yaml
type: my_module.components.ComponentName
attributes:
  demo_mode: true
  api_endpoint: "https://api.example.com"
  tables:
    - customers
    - orders
```

### Step 5: Create Custom Scaffolder (Optional)

If requested, follow: https://docs.dagster.io/guides/build/components/creating-new-components/component-customization#customizing-scaffolding-behavior

### Step 6: Validate

```bash
uv run dg check defs
uv run dg list defs
```

Verify all expected assets are listed, component instance is configured, and asset keys are consistent between demo and production mode.

## Success Criteria

- Component created with `build_defs()` implemented
- 3-5 realistic assets with proper dependencies and `kinds` metadata
- Demo mode working if applicable (non-demo mode has real connections)
- Component YAML instance created and configured
- `dg check defs` passes
- `dg list defs` shows all expected assets
- Asset keys designed for downstream consumption (see dagster-expert `asset-key-design` reference)
