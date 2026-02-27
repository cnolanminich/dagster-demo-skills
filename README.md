# dagster-demo-skills

Claude Code skills for creating Dagster demo projects. Includes skills for scaffolding integration components, custom components, scheduled jobs, and YAML consolidation.

## Skills

| Skill | Description |
|-------|-------------|
| `dagster-demo` | Orchestrates full demo project creation — initializes a Dagster project, creates components, adds schedules, consolidates YAML, and validates the result |
| `use-or-subclass-existing-component` | Discovers, uses, or subclasses existing Dagster integration components (dbt, Fivetran, PowerBI, Looker, Sling, etc.) with demo mode support |
| `create-custom-dagster-component` | Creates a custom Dagster component with demo mode, realistic assets, and optional custom scaffolder when no existing integration component fits |
| `create-scheduled-jobs` | Creates a `ScheduledJobComponent` with multiple scheduled job instances using asset selection syntax (tags, groups, owners, keys) |
| `consolidate-defs-yaml` | Consolidates multiple component instance YAML files into single `defs.yaml` files using YAML document separators (`---`) |

## Installation

Add the marketplace and install the plugin:

```
/plugin marketplace add cnolanminich/dagster-demo-skills
/plugin install dagster-demo-skills
```

## Usage

Once installed, invoke skills in Claude Code with the `/` prefix:

```
/dagster-demo-skills:dagster-demo
/dagster-demo-skills:use-or-subclass-existing-component
/dagster-demo-skills:create-custom-dagster-component
/dagster-demo-skills:create-scheduled-jobs
/dagster-demo-skills:consolidate-defs-yaml
```

### Creating a full demo project

The `dagster-demo` skill is the main entry point. Tell Claude what technologies the demo should cover and it will orchestrate the other skills to build the project end-to-end.

```
/dagster-demo-skills:dagster-demo

Create a demo for a prospect that uses Fivetran, dbt, and Looker.
```

### Using individual skills

Each skill can also be used on its own inside an existing Dagster project:

```
/dagster-demo-skills:create-custom-dagster-component

Create a Monte Carlo data quality component.
```

## Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI installed
- [uv](https://docs.astral.sh/uv/) package manager installed (`uv --version`)
- For `dagster-demo`, an empty directory or existing Dagster project to work in

## Local development

To test the plugin locally without installing it:

```bash
claude --plugin-dir /path/to/dagster-demo-skills
```

## License

MIT
