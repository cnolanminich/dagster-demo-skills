---
name: create-custom-dagster-component
description: Create a custom Dagster Component with demo mode support, realistic asset structure, and optional custom scaffolder using the dg CLI. Use this skill if there is no Component included in an existing integration or if Dagster does not have the integration.
license: MIT
---

# Create a Custom Component

## Overview

This skill automates the creation and validation of a new custom Dagster component using the `dg` CLI tool. It incorporates demo mode functionality for creating realistic demonstrations that can run locally without external dependencies.

**Prerequisites:** Use the **dagster-expert** skill for CLI commands (`dg scaffold`, `dg check defs`, `dg list defs`). Use the **dagster-integrations** skill to check if an existing component already covers your use case.

**Reference documentation:**
- Creating components: https://docs.dagster.io/guides/build/components/creating-new-components/creating-and-registering-a-component
- Complex component example: https://github.com/dagster-io/dagster/blob/master/python_modules/libraries/dagster-dbt/dagster_dbt/components/dbt_project/component.py
- Multi-asset integration guide: https://docs.dagster.io/integrations/guides/multi-asset-integration

## What This Skill Does

1. Create a new Dagster Component using `dg scaffold component ComponentName`
2. Fill in the `build_defs()` function with both real and demo mode implementations
3. Create 3-5 realistic assets with proper dependencies and technology kinds
4. Create and configure component instance YAML
5. Optionally create a custom scaffolder
6. Validate with `dg check defs` and `dg list defs`

## Skill Workflow

### Step 1: Get Component Name and Demo Mode Preference

Ask the user for:

1. A component name (validate: starts with letter, alphanumeric/hyphens/underscores only)
2. Whether they want demo mode support (default: yes for demonstration projects)
3. Whether they want a custom scaffolder (see Step 5)

### Step 2: Scaffold Component

```bash
uv run dg scaffold component <ComponentName>
```

This creates a component file in `defs/components/`.

### Step 3: Implement Component Logic

Fill in the `build_defs()` function. The component should:

1. **Accept a `demo_mode` parameter** (default: False)
2. **Create 3-5 realistic assets** based on the chosen technologies
3. **Implement dual logic paths:**
   - Real implementation: connects to actual systems
   - Demo mode: uses local/mocked behavior
4. **Follow configuration best practices:**
   - All configuration should be in the Component YAML, not hard coded in Python. **Demo mode assets are the exception.**
   - All Resources should be configured outside the Component in `defs/resources.py` using `dg scaffold defs dagster.resource resources.py`
   - Components that invoke a pipeline or API triggering multiple assets should allow an `assets` field in YAML. See https://dagster.io/blog/dsls-to-the-rescue for DSL best practices.
   - Reference architectures: [dbt component](https://github.com/dagster-io/dagster/blob/master/python_modules/libraries/dagster-dbt/dagster_dbt/components/dbt_project/component.py) and [Fivetran component](https://github.com/dagster-io/dagster/blob/master/python_modules/libraries/dagster-fivetran/dagster_fivetran/components/workspace_component/component.py)
5. **Set proper asset metadata** — use `kinds` for technology categorization, add descriptions, establish dependencies
6. **Design asset keys for downstream integration** (see section below)

Example asset structure:
- Raw data ingestion asset
- Data transformation/cleaning asset
- Business logic/aggregation asset
- ML model or analytics asset (if applicable)
- Output/export asset

### Design Asset Keys for Integration

**CRITICAL:** Consider what will consume your component's assets. Keys should align with downstream expectations to avoid per-asset configuration.

#### Key Principle: Upstream Defines, Downstream Consumes

Your component should generate asset keys that downstream components naturally reference.

#### Common Downstream Consumers

**If dbt will consume your assets:**
- Use pattern: `["<source_name>", "<table_name>"]`
- Example: `["fivetran_raw", "customers"]` or `["api_raw", "users"]`
- dbt sources reference naturally: `source('fivetran_raw', 'customers')`

**If custom Dagster assets will consume them:**
- Match the key structure those assets expect in their `deps`
- Prefer 2 levels: `["category", "name"]`

**If another integration component will consume them:**
- Check that component's expected input key structure
- Align your keys to match

**If your assets are intermediate:**
- Use hierarchical keys reflecting data flow: `["raw", "table"]` → `["processed", "table"]` → `["enriched", "table"]`

#### Example: API Ingestion Component

```python
import dagster as dg

class APIIngestionComponent(dg.Component, dg.Model, dg.Resolvable):
    """Ingests data from REST APIs."""

    api_endpoint: str
    tables: list[str]
    demo_mode: bool = False

    def build_defs(self, context: dg.ComponentLoadContext) -> dg.Definitions:
        assets = []

        for table in self.tables:
            @dg.asset(
                key=dg.AssetKey(["api_raw", table]),
                kinds={"api", "python"},
            )
            def ingest_table(context: dg.AssetExecutionContext):
                if self.demo_mode:
                    context.log.info(f"Demo mode: Mocking API call for {table}")
                    return {"status": "demo", "rows": 100}
                else:
                    import requests
                    response = requests.get(f"{self.api_endpoint}/{table}")
                    return response.json()

            assets.append(ingest_table)

        return dg.Definitions(assets=assets)
```

#### Asset Key Anti-Patterns

- **Too deeply nested:** `["company", "team", "project", "environment", "table"]`
- **Inconsistent structure:** Some assets with 2 levels, others with 4
- **Generic names:** `["data", "table1"]`, `["output", "result"]`

**Good patterns:**
- `["source_system", "entity"]`: `["fivetran_raw", "customers"]`
- `["integration", "object"]`: `["salesforce", "accounts"]`
- `["stage", "table"]`: `["staging", "orders"]`

#### Asset Keys Must Be Identical in Demo and Production Mode

**IMPORTANT:** Asset keys must be the same whether `demo_mode` is True or False. Only the function body should differ.

**CORRECT:**
```python
def build_defs(self, context: dg.ComponentLoadContext) -> dg.Definitions:
    @dg.asset(
        key=dg.AssetKey(["fivetran_raw", "customers"]),  # Same key in both modes
        kinds={"fivetran"},
    )
    def customers_sync(context: dg.AssetExecutionContext):
        if self.demo_mode:
            context.log.info("Demo mode: Creating empty table")
        else:
            context.log.info("Production: Syncing from Fivetran")

    return dg.Definitions(assets=[customers_sync])
```

**INCORRECT:**
```python
# DON'T create different keys per mode — breaks downstream dependencies
if self.demo_mode:
    key = dg.AssetKey(["demo", "customers"])    # Different key!
else:
    key = dg.AssetKey(["fivetran_raw", "customers"])  # Different key!
```

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

Verify:
- All expected assets are listed
- Component instance is properly configured
- `demo_mode` flag toggles between implementations correctly
- `demo_mode: false` implementation uses realistic resources
- Asset keys are consistent between demo and production mode

## Success Criteria

- Component scaffolding created
- `build_defs()` implemented with proper asset logic
- Demo mode flag working (if applicable)
- Non-demo mode has realistic connections to databases or APIs
- 3-5 realistic assets with proper dependencies
- Assets have appropriate `kinds` metadata
- Component YAML instance created and configured
- Custom scaffolder implemented (if requested)
- `dg check defs` passes
- `dg list defs` shows all expected assets
