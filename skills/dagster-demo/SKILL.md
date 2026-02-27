---
name: dagster-demo
description: Create Dagster Demo Project
license: MIT
---

# Create Dagster Demo Project

## Overview

This skill orchestrates the creation of a complete Dagster demonstration project for a prospective client. It delegates to sub-skills for each phase: component creation, scheduling, YAML consolidation, and validation.

## Skill Workflow

### Step 1: Initialize Dagster Project

Use the **dagster-expert** skill to create a new Dagster project in the provided demo directory.

### Step 2: Generate and Customize Demo Assets

Use the **use-or-subclass-existing-component** skill for integrations that Dagster already has. If no existing component covers the use case, use the **create-custom-dagster-component** skill.

Each component should have:
- 3-5 realistic assets with proper dependencies and descriptive names
- Both a real implementation and a `demo_mode` implementation (runnable locally without external access, activated by a `demo_mode` boolean in component YAML)
- Asset keys designed for downstream consumption (see dagster-expert `asset-key-design` reference)

After creating all components, validate and verify dependency alignment:

```bash
uv run dg check defs
uv run dg list defs
```

Ensure the `deps` field for downstream assets includes the upstream assets. This can be especially tricky for integrations like Sling and dbt.

### Step 3: Create Jobs and Schedules

Use the **create-scheduled-jobs** skill to create scheduled jobs for these assets.

### Step 4: Consolidate YAML

Use the **consolidate-defs-yaml** skill to combine related component YAML files.

### Step 5: Final Validation

- Ensure components use real connections to databases or APIs (not merely "passing")
- Ensure lineage matches expectations

## Success Criteria

- Dagster project initializes and `dg check defs` passes
- 3-5 realistic assets exist with proper dependencies
- Both real and demo_mode implementations are present
- Scheduled jobs are configured with asset selection syntax
- YAML files are consolidated into logical pipelines
- `dg list defs` shows all expected assets, schedules, and jobs

## Sub-Skill Reference

| Skill | Purpose |
|-------|---------|
| **use-or-subclass-existing-component** | Use or subclass existing Dagster integration components with demo_mode support |
| **create-custom-dagster-component** | Create a custom component when no existing integration exists |
| **create-scheduled-jobs** | Create scheduled job instances using asset selection syntax |
| **consolidate-defs-yaml** | Consolidate related YAML files into single defs.yaml using `---` separators |
