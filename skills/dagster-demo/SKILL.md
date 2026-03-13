---
name: dagster-demo
description: Build and modify Dagster demo components using subclassing, demo_mode toggling, and full integration verification.
---

# Dagster Demo Skill

Use the `dagster-expert` skill every time.

## Rules

1. **Always subclass existing components** — never create a custom component from scratch when modifying one that already exists. Find the existing component class and extend it.

2. **Use `demo_mode` to switch code paths** — never comment code out. All integrations must have both a production implementation and a demo implementation, selected at runtime via `demo_mode`.

   ```python
   if demo_mode:
       # demo/mock implementation
   else:
       # production implementation
   ```

3. **All integrations must have production implementations built in** — demo mode is an overlay, not a replacement. Production code must always be present and functional.

4. **Verify lineage across integrations** — check that asset dependencies and lineage are correct across all integrations using `dg list defs`. The dependency graph should reflect the intended data flow end-to-end.

5. Create Jobs and Schedules

Use the **create-scheduled-jobs** skill to create scheduled jobs for these assets.

6. Consolidate YAML

Use the **consolidate-defs-yaml** skill to combine related component YAML files.

## Sub-Skill Reference

| Skill | Purpose |
|-------|---------|
| **create-scheduled-jobs** | Create scheduled job instances using asset selection syntax |
| **consolidate-defs-yaml** | Consolidate related YAML files into single defs.yaml using `---` separators |