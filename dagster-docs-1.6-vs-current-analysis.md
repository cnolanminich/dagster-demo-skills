# Dagster Documentation Analysis: 1.6 Release vs. Current (1.12)

*Analysis Date: March 2, 2026*

---

## Executive Summary

Between Dagster 1.6 and the current release (1.12.17, as of February 27, 2026), the documentation has undergone a **fundamental transformation** — not just a cosmetic refresh, but a philosophical and structural overhaul that reflects Dagster's evolution from a flexible orchestration framework into a highly opinionated data platform with prescribed workflows, new abstractions (Components, `dg` CLI), and a dramatically narrower "happy path" for new users.

**The key shifts:**

| Dimension | Dagster 1.6 Docs | Current Docs |
|-----------|------------------|--------------|
| **Core abstraction** | Software-Defined Assets (`@asset`) | Assets (`@dg.asset`) + Components |
| **Project creation** | `dagster project scaffold` | `create-dagster project` |
| **Development CLI** | `dagster dev` | `dg dev` |
| **Configuration** | Pure Python (`Definitions(...)`) | YAML (`defs.yaml`) + auto-discovery |
| **Project structure** | Recommended but flexible | Prescribed and auto-generated |
| **Onboarding philosophy** | "Start with assets, explore from there" | "Follow this exact path" |
| **Automation model** | Schedules + Sensors + Auto-Materialize | Schedules + Sensors + Declarative Automation (GA) |
| **Ops/Graphs positioning** | "Advanced topic, not needed to start" | Virtually absent from onboarding |
| **Package management** | `pip install` | `uv` (recommended) or `pip` |
| **Overall opinionation** | Moderate-high (asset-first but options shown) | Very high (single prescribed path) |

---

## Part 1: Overall Summary of Major Differences

### 1.1 Documentation Architecture

**Dagster 1.6** organized docs into these top-level sections:
- **Getting Started** (Hello Dagster, Create New Project)
- **Tutorial** (7-part asset-focused walkthrough)
- **Concepts** (Assets, Ops/Jobs/Graphs, Resources, Scheduling, etc.)
- **Guides** (including best practices embedded within)
- **Integrations**
- **Deployment**
- **API Reference**

The architecture was a classic **hub-and-spoke model**: a Getting Started hub let users self-select their path with four call-to-action buttons ("Run Hello, Dagster!", "View Tutorials", "Explore Concepts", "Enroll in Dagster University"). Users had agency in choosing their learning journey.

**Current docs** reorganize around:
- **Getting Started** (Installation, Quickstart, Create New Project)
- **Dagster Basics Tutorial** (assets, dependencies, projects, schedules, components)
- **ETL Pipeline Tutorial** (Components-driven real-world pipeline)
- **Concepts** (Assets, Automation, etc.)
- **Guides** (Build, Automate, Deploy, Components)
- **API Reference** (including `dg` CLI and `create-dagster` CLI references)

The architecture is now a **linear funnel**: Install → Quickstart → Basics Tutorial → ETL Tutorial → Concepts/Guides. Users are guided through a prescribed sequence rather than offered a menu of options.

### 1.2 New Abstractions Introduced

Several major abstractions were added between 1.6 and now:

1. **Components** (GA as of 1.11.10) — Higher-level building blocks that generate assets and other definitions from YAML configuration. Built-in components exist for dbt, Sling, Fivetran, Airbyte, dlt, Power BI, Looker, and more. Components are now the headline abstraction in the ETL tutorial and are positioned as the recommended way to build integration-heavy pipelines.

2. **`dg` CLI** (GA as of 1.11.10) — A new CLI that replaces/supplements the `dagster` CLI for development workflows. Commands include `dg dev`, `dg scaffold defs`, `dg check defs`, `dg launch`, `dg scaffold build-artifacts`, and `dg list component`.

3. **`create-dagster` CLI** — Replaces `dagster project scaffold` as the primary project scaffolding tool. Generates a modern project structure with `pyproject.toml`, `src/`, `defs/`, and auto-discovery via `definitions.py`.

4. **Declarative Automation** (GA as of 1.9) — Replaces Auto-Materialize Policies with `AutomationCondition` primitives (`on_cron`, `eager`, `on_missing`). Conditions can be combined and customized. The `@multi_asset_sensor` is now deprecated in favor of this approach.

5. **`defs.yaml`** — YAML configuration files (with Jinja2 templating) that configure component instances and set directory-level attributes (owner, tags, etc.). This represents a shift from "everything in Python" to "configuration in YAML, logic in Python."

6. **Auto-discovery via `definitions.py`** — The new project structure features a `definitions.py` entry point that automatically discovers all definitions in the `defs/` directory. The docs explicitly state: "You should not need to modify this file."

### 1.3 Removed or De-emphasized Concepts

- **Ops and Graphs**: In 1.6, the ops page stated: *"An op is the core unit of computation in Dagster."* In the current docs, the concepts page states: *"Ops have largely been replaced by assets."* Every ops guide page now carries a banner: *"If you are just getting started with Dagster, we strongly recommend you use assets rather than ops to build your data pipelines."*

- **I/O Managers**: The 1.6 tutorial had a dedicated section (Part 6) on "Saving data with I/O managers." Current onboarding materials do not emphasize I/O managers.

- **`setup.py`**: Legacy project scaffolding used `setup.py`. Current projects use `pyproject.toml` exclusively.

- **Auto-Materialize Policies**: Deprecated in favor of Declarative Automation. The `AutoMaterializePolicy` and `AutoMaterializeRule` interfaces are marked as deprecated.

- **`SourceAsset`**: While still supported, the concept is less prominent in current docs. External assets and `AssetSpec` (declarative description without materialization logic) have taken its place.

### 1.4 Tooling Evolution

| Action | Dagster 1.6 | Current |
|--------|-------------|---------|
| Create project | `dagster project scaffold --name my-project` | `uvx create-dagster@latest project my-project` |
| Start from example | `dagster project from-example --example quickstart_etl` | N/A (tutorials are self-contained) |
| Scaffold definitions | Manual Python file creation | `dg scaffold defs dagster.asset <path>` |
| Scaffold components | N/A | `dg scaffold defs dagster_dbt.DbtProjectComponent <path>` |
| Local dev server | `dagster dev` | `dg dev` |
| Validate definitions | N/A (runtime errors) | `dg check defs` |
| Run pipeline | UI or `dagster job launch` | `dg launch --assets` or UI |
| Build for deploy | Manual Dockerfile | `dg scaffold build-artifacts` |
| Install packages | `pip install dagster dagster-webserver` | `uv add dagster` (recommended) |

---

## Part 2: How Opinionated Are the Docs?

### 2.1 The 1.6 Approach: "We Recommend Assets, But Here Are Options"

Dagster 1.6 docs were **moderately to highly opinionated** — they clearly favored the asset-first paradigm, but they acknowledged alternatives and gave users some freedom to explore.

Key evidence:

- **Hello Dagster (1.6)** was built entirely around `@asset`, but explicitly stated at the bottom: *"Dagster also offers ops and jobs, but we recommend starting with assets."* This is a clear recommendation paired with an acknowledgment that alternatives exist.

- **The Tutorial (1.6)** was titled "Building a pipeline using Software-defined Assets" and was 100% asset-focused across all 7 parts. However, the concepts section still devoted full pages to ops, jobs, and graphs as legitimate patterns.

- **The SDA Concepts page (1.6)** contained the key framing statement: *"Behind-the-scenes, the Python function is an op. Ops are an advanced topic that isn't required to get started with Dagster."* This positions ops as real but not necessary — a nuanced middle ground.

- **The Ops page (1.6)** still defined ops as "the core unit of computation" and provided extensive documentation on their use. Ops were not hidden — they were fully documented but clearly labeled as a lower-level abstraction.

- **The "How Assets Relate to Ops and Graphs" guide (1.6)** provided explicit guidance on when ops are appropriate: (1) you're not building a data pipeline, (2) you want to break an asset into multiple steps (graph-backed assets), (3) you're anchored in task-based workflows (migration/legacy path).

- **The Getting Started page (1.6)** was a hub with four buttons letting users self-select. Users could go to "Hello Dagster," "Tutorials," "Concepts," or "Dagster University" — implying that multiple learning paths were valid.

**Verbatim examples of 1.6's "recommend but allow" tone:**

> *"An asset is the easiest way to get started with Dagster, and can be used to model assets that should be materialized by Dagster."*
> — `/concepts/assets/software-defined-assets`

> *"You can group assets using `load_assets_from_package_module` (recommended), or by using the `group_name` argument on each individual asset."*
> — `/concepts/assets/software-defined-assets` (note the "(recommended)" alongside the alternative)

> *"Dagster also offers ops and jobs, but we recommend starting with assets."*
> — `/getting-started/hello-dagster`

> *"Behind-the-scenes, the Python function is an op and the asset is modeled on top of it. Ops are an advanced topic that isn't required to get started with Dagster."*
> — `/concepts/assets/software-defined-assets`

> *"When you define an asset, the same function also produces the op that computes it... In this case, there's no reason to split the logic up into multiple steps. But sometimes you may want to... in this case you may use a graph-backed asset."*
> — `/guides/dagster/how-assets-relate-to-ops-and-graphs`

**Summary (1.6)**: The docs said *"here's the best way, and here's why, but we understand if you need other approaches."* The opinion was strong but not absolute.

### 2.2 The Current Approach: "Follow This Path"

Current docs are **very to extremely opinionated** — they present a single prescribed workflow and rarely acknowledge alternatives in onboarding materials.

Key evidence:

- **The Quickstart** is a step-by-step command sequence with zero branching: `create-dagster` → `dg scaffold defs` → `dg check defs` → `dg dev`. There is exactly one path. The only optionality is `uv` vs `pip` for package management (and even there, `uv` is marked "recommended").

- **The Dagster Basics Tutorial** follows a single prescribed path from project creation through assets, dependencies, resources, checks, automation, and components. There is no "you could also do it this way" branching.

- **The ETL Pipeline Tutorial** is built entirely around Components (`DbtProjectComponent`, `SlingReplicationCollectionComponent`). There is no mention of building the same pipeline without Components. DuckDB, dbt, and Sling are prescribed technology choices.

- **Components are positioned as THE way** to build integration-heavy pipelines: *"Dagster comes with ready-made Components for common integrations... These plug-and-play Components let you spin up new pipelines in minutes by filling out a few config fields, rather than hand-coding new assets from scratch."*

- **The `definitions.py` file** is explicitly hands-off: *"You should not need to modify this file."* This removes a decision point — the user doesn't choose how definitions are organized, the framework handles it.

- **Ops and graphs** are virtually invisible in the onboarding flow. You would have to navigate to deep reference pages to find them.

- **Declarative Automation** is clearly favored over other automation methods. The `@multi_asset_sensor` is deprecated. While schedules and sensors are still documented, the framing suggests Declarative Automation is the forward-looking choice.

**Verbatim examples of the current docs' prescriptive tone:**

> *"If you are just getting started with Dagster, we strongly recommend you use assets rather than ops to build your data pipelines."*
> — Banner on **every** ops-related guide page (`/guides/build/ops`, `/guides/build/ops/graphs`, etc.)

> *"Ops have largely been replaced by assets."*
> — `/getting-started/concepts`

> *"For situations where you are automating execution of assets only, Dagster recommends using Declarative Automation instead."*
> — `/guides/automate/asset-sensors`

> *"The Components framework and the `dg` CLI are now marked as GA... The APIs are fully supported throughout all parts of the product and remain the recommended defaults for new Dagster projects."*
> — `/about/changelog`

> *"Unlike the assets file, which was in Python, components provide a low-code interface in YAML."*
> — `/etl-pipeline-tutorial/transform`

> *"As you develop your Dagster project, it is a good habit to run `dg check` to ensure everything works as expected."*
> — `/tutorial/assets`

### 2.3 Opinionation Comparison Table

| Topic | 1.6 Level | Current Level | Change |
|-------|-----------|---------------|--------|
| Asset-first vs ops/tasks | Strong recommendation | Absolute (ops invisible in onboarding) | ↑↑ |
| Project scaffolding | One recommended CLI | One prescribed CLI + structure | ↑ |
| Project structure | Recommended layout guide | Auto-generated, non-negotiable skeleton | ↑↑ |
| Configuration approach | Pure Python | YAML (`defs.yaml`) prescribed for components | ↑↑ (new) |
| Automation strategy | Multiple options, no clear winner | Declarative Automation clearly favored | ↑ |
| Integration patterns | Manual Python code | Components + `dg scaffold` prescribed | ↑↑ (new) |
| Package manager | `pip` (no opinion) | `uv` recommended, `pip` as fallback | ↑ (new) |
| Learning path | Self-selected hub | Linear funnel | ↑↑ |
| CLI tooling | `dagster` CLI | `dg` CLI (replaces `dagster` for dev workflows) | ↑ (new) |

---

## Part 3: Onboarding a New User to Concepts and Best Practices

### 3.1 The 1.6 Onboarding Experience

**Entry point:** The Getting Started page was a hub with four paths. A new user would likely click "Run Hello, Dagster!"

**Hello Dagster (1.6):**
1. Create a single Python file with two `@asset`-decorated functions
2. `pip install dagster dagster-webserver pandas`
3. `dagster dev -f hello-dagster.py`
4. Click "Materialize All" in the UI

This was **40 lines of code, zero project structure, immediate feedback**. The user went from nothing to a working asset graph in under 5 minutes. The framing was: *"Look, this is what an asset is, and it already does useful things."*

**The exact Hello Dagster file (1.6) — the first code a new user saw:**
```python
import json
import pandas as pd
import requests
from dagster import AssetExecutionContext, MetadataValue, asset

@asset
def hackernews_top_story_ids():
    """Get top stories from the HackerNews top stories endpoint."""
    top_story_ids = requests.get(
        "https://hacker-news.firebaseio.com/v0/topstories.json"
    ).json()
    with open("hackernews_top_story_ids.json", "w") as f:
        json.dump(top_story_ids[:10], f)

@asset(deps=[hackernews_top_story_ids])
def hackernews_top_stories(context: AssetExecutionContext):
    """Get items based on story ids from the HackerNews items endpoint."""
    with open("hackernews_top_story_ids.json", "r") as f:
        hackernews_top_story_ids = json.load(f)
    results = []
    for item_id in hackernews_top_story_ids:
        item = requests.get(
            f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json"
        ).json()
        results.append(item)
    df = pd.DataFrame(results)
    df.to_csv("hackernews_top_stories.csv")
    context.add_output_metadata(metadata={
        "num_records": len(df),
        "preview": MetadataValue.md(df[["title", "by", "url"]].to_markdown()),
    })
```

And the commands to run it:
```bash
pip install dagster dagster-webserver pandas
dagster dev -f hello-dagster.py
```

That's it. One file, two commands, immediate result.

**Tutorial (1.6):**
A 7-part sequential tutorial ("New to Dagster? Start here!"):
1. Intro to assets (what/why)
2. Setup (scaffold from example)
3. Writing your first asset
4. Building an asset graph
5. Scheduling
6. Saving data with I/O managers
7. Managing external services (resources)

The tutorial introduced concepts **incrementally**: start with one asset, then dependencies, then scheduling, then I/O patterns, then external integrations. Each part built on the previous one.

**Concept introduction order (1.6):**
1. `@asset` (first thing a user sees)
2. `deps=[]` / asset dependencies
3. `MetadataValue` / output metadata
4. `Definitions` (implied in project creation)
5. Schedules
6. I/O managers
7. Resources
8. `SourceAsset`, `AssetIn`, `multi_asset` (concepts layer)
9. `@op`, `@graph`, `@job` (concepts layer, clearly secondary)

**Best practices (1.6):**
Best practices were **embedded within the Guides section**, not given a dedicated top-level page. The key best-practices content was:
- **Recommended Project Structure** — the most prescriptive structural guidance, with full file tree examples based on the `project_fully_featured` example
- **Automating Your Pipelines**
- **Building/Managing ML Pipelines**
- **Exploring a Dagster Project**

The project structure guide recommended: assets in `assets/` by business domain, resources in `resources/`, sensors in `sensors/`, and "we don't recommend over-abstracting too early; in most cases, one code location should be sufficient."

**The 1.6 recommended project tree (from the fully-featured example):**
```
project_fully_featured/
├── project_fully_featured/
│   ├── __init__.py
│   ├── assets/
│   │   ├── activity_analytics/
│   │   ├── core/
│   │   └── recommender/
│   ├── resources/
│   ├── sensors/
│   └── jobs.py
├── dbt_project/
├── setup.py
└── pyproject.toml
```

**The current auto-generated project tree:**
```
my-project/
├── src/
│   └── my_project/
│       ├── __init__.py
│       ├── definitions.py         ← auto-discovery
│       └── defs/                  ← all definitions go here
│           └── __init__.py
├── tests/
├── pyproject.toml
└── uv.lock
```

The difference is structural: 1.6 showed you a *recommended* layout for an already-complex project. Current gives you an *auto-generated* skeleton for a new project, with the expectation that `dg scaffold` commands will populate it.

### 3.2 The Current Onboarding Experience

**Entry point:** The Getting Started section directs users to Installation → Quickstart in a linear sequence.

**Quickstart (current):**
1. `uvx create-dagster@latest project my-project`
2. Navigate into the project
3. `dg scaffold defs dagster.asset my_defs/my_asset.py`
4. Write an asset (CSV processing example)
5. `dg check defs` (validate)
6. `dg dev` (run)

This is **more steps, more tooling, more structure from the start**. The user gets a full project scaffold before writing any code. The `dg` CLI validates definitions before running, introducing a compile-check-run cycle.

**The exact quickstart sequence (current) — the first thing a new user does:**
```bash
uvx create-dagster@latest project dagster-quickstart
cd dagster-quickstart
source .venv/bin/activate
uv add pandas
dg scaffold defs dagster.asset assets.py
```

This generates a project tree:
```
dagster-quickstart/
├── pyproject.toml
├── src/
│   └── dagster_quickstart/
│       ├── __init__.py
│       ├── definitions.py      ← auto-discovery, "you should not need to modify"
│       └── defs/
│           └── assets.py       ← scaffolded by `dg scaffold`
├── tests/
└── uv.lock
```

Then the user fills in the asset:
```python
import pandas as pd
import dagster as dg

@dg.asset
def processed_data():
    df = pd.read_csv("src/dagster_quickstart/defs/data/sample_data.csv")
    df["age_group"] = pd.cut(
        df["age"], bins=[0, 30, 40, 100], labels=["Young", "Middle", "Senior"]
    )
    df.to_csv("src/dagster_quickstart/defs/data/processed_data.csv", index=False)
    return "Data loaded successfully"
```

And validates + runs:
```bash
dg check defs    # validates before running
dg dev           # starts the development server
dg launch --assets "*"   # materializes all assets
```

Note: The `definitions.py` file uses auto-discovery and is never touched by the user:
```python
from pathlib import Path
from dagster import definitions, load_from_defs_folder

@definitions
def defs():
    return load_from_defs_folder(project_root=Path(__file__).parent.parent.parent)
```

The contrast is stark: 1.6 started with *a concept* (what is an asset?), current starts with *a workflow* (scaffold, write, check, run).

**Dagster Basics Tutorial (current):**
A progressive tutorial covering:
1. Creating a project with `create-dagster`
2. Defining assets with `@dg.asset`
3. Asset dependencies via `deps`
4. Building the asset graph (DAG)
5. Resources
6. Asset checks (data quality)
7. Automation (schedules)
8. Custom components (introduced at the end)

**ETL Pipeline Tutorial (current):**
A more advanced tutorial built entirely around Components:
1. Extract data using Sling (via `SlingReplicationCollectionComponent`)
2. Transform data using dbt (via `DbtProjectComponent`)
3. Automate with schedules + declarative automation
4. Visualize data

**Concept introduction order (current):**
1. `create-dagster` project scaffold (before any code!)
2. `@dg.asset` decorator
3. `deps` (dependencies)
4. Auto-discovery via `definitions.py`
5. Resources
6. Asset checks
7. Schedules
8. `AutomationCondition` (declarative automation)
9. Components (`DbtProjectComponent`, etc.)
10. `defs.yaml` configuration
11. Custom components (inheriting from `Component`)

**Best practices (current):**
Best practices are now delivered in two ways — partially through an explicit Best Practices section under Guides, and partially baked into the prescribed workflows:

*Explicit best practices section (`/guides/best-practices/`):*
- Structuring your Dagster project
- Building ML pipelines
- Managing ML models
- Fully-featured project example
- Limiting concurrency
- Customizing run queue priority
- Validating data with Dagster Type factories
- Asset versioning and caching

*Implicit best practices (embedded in tooling/workflows):*
- **Project structure**: Automatically generated by `create-dagster`. Two organization strategies offered: by technology (`defs/dbt/`, `defs/sling/`) or by concept (`defs/ingestion/`, `defs/transformation/`).
- **Configuration**: Use `defs.yaml` for component configuration; use directory-level `defs.yaml` for attribute inheritance (owner, tags).
- **Automation**: Declarative Automation is the forward-looking choice; `@multi_asset_sensor` is deprecated.
- **Integrations**: Use Components rather than hand-coding asset definitions.
- **Validation**: Use `dg check defs` before running.
- **Scaling guidance**: Phase 1 (0-400 lines) keep everything in one file; Phase 2 (400+ lines) split into modules under `defs/`; Phase 3 (multiple teams) organize by technology or concept.

### 3.3 Key Differences in Onboarding Philosophy

| Aspect | 1.6 Onboarding | Current Onboarding |
|--------|----------------|-------------------|
| **First interaction** | Single Python file, `dagster dev -f file.py` | Full project scaffold, multiple CLI commands |
| **Time to first asset** | ~2 minutes (copy-paste one file) | ~5 minutes (scaffold project, scaffold defs, write code) |
| **Concept load at start** | Low (just `@asset` and `deps`) | Higher (project structure, `dg` CLI, `definitions.py`, `defs/` folder) |
| **"Magic" vs transparency** | Transparent: you write Python, you see results | More magic: auto-discovery, YAML config, generated scaffolds |
| **Minimum viable knowledge** | What an `@asset` decorator does | What `create-dagster`, `dg scaffold`, `dg check`, and `dg dev` do |
| **When Components appear** | Never (didn't exist) | End of basics tutorial, central to ETL tutorial |
| **When ops/graphs appear** | Concepts layer, with "recommended for some cases" | Essentially never in onboarding |
| **Learning philosophy** | "Learn the primitive, then compose" | "Learn the workflow, then understand the internals" |
| **Best practices delivery** | Explicit guide with file tree examples | Implicit in prescribed project structure |

### 3.4 What a New User Learns First

**In 1.6**, a new user learned:
> "Dagster is about assets — things that exist in your data world. You describe them with Python functions. They have dependencies on each other. You can materialize them. Everything else builds on this."

**In the current docs**, a new user learns:
> "Dagster has a CLI toolchain. You scaffold a project. You scaffold definitions. You validate them. You run them. Assets are the core thing you define, but there's a whole framework around how you define and organize them."

The 1.6 approach was **concept-first**: understand what an asset is, then learn the tooling. The current approach is **workflow-first**: learn the tooling, then understand what you're building.

---

## Part 4: Analysis and Implications

### 4.1 What Improved

1. **Validation before execution**: The `dg check defs` step catches configuration errors before runtime, which is a significant developer experience improvement.

2. **Standardized project structure**: Auto-generated scaffolds reduce decision fatigue and ensure consistency across teams and projects.

3. **Components as force multiplier**: For integration-heavy workloads (dbt, Sling, Fivetran, etc.), Components dramatically reduce boilerplate. A pipeline that might take hours of custom Python can be scaffolded in minutes.

4. **Declarative Automation maturity**: Moving from experimental Auto-Materialize Policies to stable, composable `AutomationCondition` primitives is a significant upgrade for production use.

5. **Deployment workflow**: `dg scaffold build-artifacts` generating Dockerfiles and build configs is a meaningful step toward deployment best practices being built into the toolchain.

### 4.2 Potential Concerns

1. **Higher initial complexity**: The 1.6 "single file" quickstart was arguably more accessible. Current onboarding requires understanding `create-dagster`, `dg` CLI subcommands, project structure conventions, and auto-discovery before writing any data logic.

2. **Reduced flexibility signaling**: By removing visible alternatives from onboarding, the docs may make users with non-standard use cases (non-asset workloads, task-based workflows, etc.) feel unsupported, even if those features still exist.

3. **YAML configuration trade-offs**: The shift from pure Python (`Definitions(...)`) to YAML (`defs.yaml`) introduces a different kind of complexity. YAML with Jinja2 templating can become its own debugging challenge.

4. **Component abstraction gap**: The jump from "here's what an asset is" (basics tutorial) to "here's a `DbtProjectComponent` that generates assets from YAML config" (ETL tutorial) is a large conceptual leap. Users may not understand what Components do under the hood.

5. **Implicit best practices**: In 1.6, the recommended project structure guide was explicit about *why* each recommendation existed. In the current docs, best practices are embedded in auto-generated scaffolds, which users may follow without understanding the reasoning.

### 4.3 The Opinionation Trajectory

```
Dagster 1.6:    "Assets are the right way. Here's why. But we support other patterns."
                Opinionation: ████████░░ (8/10)

Current:        "Use our toolchain. Follow our structure. Build with Components."
                Opinionation: ██████████ (10/10 in onboarding, 7/10 in reference docs)
```

The docs have gone from **strongly opinionated with acknowledged alternatives** to **prescriptive with a single path in onboarding**. This is a deliberate strategy — reducing choices reduces confusion for new users — but it changes the character of the documentation from "here's how to think about data engineering" to "here's how to use Dagster."

---

## Part 5: Prescriptive Guidance Frequency Comparison

To go beyond qualitative assessment, we systematically cataloged every instance of prescriptive guidance across comparable pages in both doc versions. This analysis examines Getting Started, Tutorials, key Concepts pages, and Guides — the pages a new or intermediate user would encounter.

### 5.1 Methodology

For each page, we identified instances where the docs:
- **Prescribe a specific approach**: "you should", "we recommend", "the best way", "the easiest way"
- **Offer a single path**: Step-by-step instructions with no alternatives mentioned
- **Deprecate/discourage**: "deprecated", "legacy", "avoid", "instead use"
- **Present a default choice**: One option marked as default or recommended
- **Offer alternatives** (1.6 only): "you can also", "alternatively", "another approach"
- **Present choices without strong opinion** (1.6 only): Multiple options, no clear favorite

### 5.2 Aggregate Prescriptive Guidance Counts

| Category | Dagster 1.6 (15 pages) | Current (18 pages) |
|----------|------------------------|-------------------|
| **Prescribe a specific approach** | 37 | ~62 |
| **Offer a single path** (no alternatives) | 0 (alternatives always noted) | ~19 |
| **Deprecate/discourage** | 0 | ~5 |
| **Present a default choice** | 0 (implicit only) | ~14 |
| **Offer alternatives** | 13 | ~0 (in onboarding) |
| **Present choices without strong opinion** | 5 | ~0 (in onboarding) |
| **TOTAL prescriptive instances** | **37** | **~100** |

**The current docs contain roughly 2.7x more prescriptive guidance instances** across a comparable set of pages, even before normalizing for the fact that current docs also contain more pages overall.

### 5.3 Key Differences in Prescriptive Language

**Dagster 1.6 prescriptive language was concentrated in two areas:**
1. **Project structure guide** (11 of 37 instances) — the most opinionated single page, repeatedly using "we recommend" for directory layout
2. **Assets concept page** (4 instances) — recommending `@asset` as "the easiest way" and `load_assets_from_package_module` as the "(recommended)" grouping approach

**Current docs prescriptive language is spread across every page:**
- Every onboarding page has 5-9 prescriptive instances
- The ETL tutorial pages each have 5-7 instances
- The guides carry 6-9 instances per page
- The best practices hub alone has 9 instances

**1.6 balanced prescriptions with alternatives.** For 37 prescriptive instances, there were 13 instances of "you can also" and 5 instances of neutral multi-option presentation. That's a **2.1:1 prescription-to-alternative ratio**.

**Current docs offer essentially zero alternatives in onboarding.** For ~100 prescriptive instances, alternatives appear only in deep reference pages (e.g., `pip` as a fallback for `uv`, `--format python` as an alternative to YAML components). In the tutorials and getting started flow, the ratio is effectively **infinite** — prescription without acknowledged alternatives.

### 5.4 Nature of Prescriptive Guidance

**In 1.6, prescriptions were primarily conceptual:**
- "Assets are the main way to create data pipelines"
- "We recommend starting with assets and not worrying about ops"
- "Resources are the recommended way to manage connections"
- "We don't recommend over-abstracting too early"

These tell users *what to think about* — which abstraction to favor, which pattern to adopt.

**Verbatim 1.6 prescription examples:**

> *"We recommend placing your assets in your `assets/` directory, with subdirectories for different business-relevant groupings."*
> — `/guides/dagster/recommended-project-structure`

> *"Resources are the recommended way to manage connections to external services and configuration."*
> — `/tutorial/connecting-to-external-services`

> *"We don't recommend over-abstracting too early; in most cases, one code location should be sufficient."*
> — `/guides/dagster/recommended-project-structure`

Each was paired with explanation of *why*. And the project structure guide offered an alternative:

> *"If you'd prefer to keep things simple, you can start with a single module and refactor later."*

**In the current docs, prescriptions are primarily operational:**
- "Use `uvx create-dagster@latest project`"
- "Use `dg scaffold defs dagster.asset`"
- "Use `dg check defs` before running"
- "Components provide a low-code interface in YAML"
- "Use `dg launch --assets '*'`"

These tell users *what to do* — which command to run, which tool to use, which format to write config in.

**Verbatim current prescription examples:**

> *"Use the `dg scaffold defs` command to generate an assets file on the command line."*
> — `/getting-started/quickstart` (no manual file creation alternative mentioned)

> *"Open your terminal and scaffold a new Dagster project: `uvx create-dagster@latest project dagster-quickstart`"*
> — `/getting-started/quickstart` (`create-dagster` is the only path shown)

> *"In the terminal, navigate to your project's root directory and run: `dg dev`"*
> — `/getting-started/quickstart` (older `dagster dev` not mentioned)

> *"We recommend beginning new components by designing the interface."*
> — `/guides/build/components`

> *"We recommend using asset observations when reporting events from external systems in Dagster instead of asset materializations to avoid consuming credits."*
> — `/guides/build/assets`

### 5.5 Deprecation Language

| | 1.6 | Current |
|---|-----|---------|
| Explicit deprecation notices | 0 | ~5 |
| APIs marked for removal | 0 | `SourceAsset` (→ `AssetSpec`), `AutoMaterializePolicy` (→ `AutomationCondition`), `AutoMaterializeRule`, `@multi_asset_sensor` |
| Discouraged patterns | 0 | Ops for new projects, asset sensors for automation, unit testing external system logic, hard-coding credentials |

The 1.6 docs contained **zero** deprecation or discouragement language. Even ops were described as "the core unit of computation" — just placed under an Advanced section. The current docs actively deprecate multiple APIs and discourage several patterns.

**Verbatim deprecation examples from current docs:**

> *"AutoMaterializePolicy, AutoMaterializeRule, and the auto_materialize_policy arguments to @asset and AssetSpec have been marked as deprecated, and the new AutomationCondition API and automation_condition argument should be used instead."*
> — `/migration/upgrading` (1.8.0 release notes)

> *"SourceAsset is deprecated, in favor of AssetSpec. You can now use AssetSpecs in any of the places you could previously use SourceAssets."*
> — `/migration/upgrading` (1.8.0 release notes)

> *"The experimental @multi_asset_sensor has been marked as deprecated, but will not be removed from the codebase until Dagster 2.0 is released."*
> — `/migration/upgrading` (1.9.0 release notes)

> *"FreshnessPolicy is now deprecated. For monitoring freshness, use freshness checks instead."*
> — `/migration/upgrading` (1.7.0 release notes)

Compare with how 1.6 described ops:
> *"An op is the core unit of computation in Dagster. Individual ops should perform relatively simple tasks."*
> — `/concepts/ops-jobs-graphs/ops` (no deprecation, just positioning as "advanced")

---

## Part 6: Hands-On Code Examples Comparison

### 6.1 Aggregate Code Example Counts

| Example Type | Dagster 1.6 (15 pages) | Current (18 pages) | Change |
|-------------|------------------------|-------------------|--------|
| **Full runnable examples** (copy-paste and run) | 5 | ~27 | **+440%** |
| **Code snippets** (fragments showing a concept) | 49 | ~37 | -24% |
| **CLI commands** | 13 | ~42 | **+223%** |
| **Configuration examples** (YAML, directory trees) | 5 | ~20 | **+300%** |
| **GRAND TOTAL** | **72** | **~126** | **+75%** |

### 6.2 Analysis of the Shift

The numbers tell a clear story about how the docs' teaching philosophy changed:

**1. Full runnable examples increased 5x.** The current docs invest heavily in code you can actually copy-paste and run. In 1.6, most tutorial code was fragments requiring prior context (49 snippets vs 5 full examples). The current docs flip that ratio — more complete examples than fragments.

**2. CLI commands tripled.** This reflects the new `dg` CLI-centric workflow. In 1.6, you ran `dagster dev` and maybe `dagster project scaffold`. In the current docs, every tutorial step involves a `dg` subcommand: `dg scaffold defs`, `dg check defs`, `dg dev`, `dg launch`, `dg scaffold build-artifacts`, plus installation commands for `uv`, `create-dagster`, etc.

**3. Configuration examples quadrupled.** This reflects the shift to YAML-based Components. In 1.6, configuration was pure Python — no YAML files to show. The current docs have `defs.yaml` examples, `pyproject.toml` structures, and directory tree layouts on nearly every page.

**4. Code snippets slightly decreased.** Despite having more total code blocks, the current docs have fewer *fragment* snippets. This is because the docs moved toward showing complete, runnable code rather than illustrative fragments. This is a pedagogical improvement — users can actually run what they see.

### 6.3 Per-Page Code Density

**Dagster 1.6 — code-heavy pages:**
| Page | Total Code Blocks |
|------|-------------------|
| `/concepts/assets/software-defined-assets` | **20** (highest) |
| `/concepts/ops-jobs-graphs/ops` | **11** |
| `/tutorial/saving-your-data` | **8** |
| All other pages | 0-5 each |

**Current — code-heavy pages:**
| Page | Total Code Blocks |
|------|-------------------|
| `/guides/build/components` | **~12** (highest) |
| `/getting-started/quickstart` | **~11** |
| `/guides/build/assets` | **~11** |
| `/tutorial/components` | **~9** |
| `/etl-pipeline-tutorial/extract` | **~9** |
| All other pages | 4-8 each |

In 1.6, code density was concentrated in the concepts layer (the SDA page alone had 20 blocks). In the current docs, code is more evenly distributed across getting started, tutorials, and guides — reflecting the linear funnel approach where every step has executable code.

### 6.4 What the Examples Teach

**In 1.6**, the highest-code-density page (`concepts/assets/software-defined-assets`) showed *many ways* to accomplish things:
- Basic deps, managed-loading deps, explicit `AssetIn` deps, `SourceAsset` deps
- Single output, multi-output, conditional materialization
- Group assignment via decorator vs `load_assets_from_package_module`
- Config via decorator, via run config, via factory

This was a **reference encyclopedia** — "here are all the patterns, pick what fits."

**Concrete 1.6 example — four different ways to declare dependencies on the same SDA page:**

Pattern A — deps list:
```python
@asset(deps=[sugary_cereals])
def shopping_list() -> None:
    execute_query("CREATE TABLE shopping_list AS SELECT * FROM sugary_cereals")
```

Pattern B — managed-loading (function argument):
```python
@asset
def downstream_asset(upstream_asset):
    return upstream_asset + [4]
```

Pattern C — explicit `AssetIn`:
```python
@asset(ins={"upstream": AssetIn("upstream_asset")})
def downstream_asset(upstream):
    return upstream + [4]
```

Pattern D — `SourceAsset` for external data:
```python
my_source_asset = SourceAsset(key=AssetKey("a_source_asset"))

@asset(deps=[my_source_asset])
def my_derived_asset():
    return execute_query("SELECT * from a_source_asset").as_list() + [4]
```

All four patterns were shown on the same page, giving users the power to choose.

**In the current docs**, the highest-code-density pages show *one way* to accomplish each thing:
- One way to scaffold (`dg scaffold defs`)
- One way to define assets (`@dg.asset`)
- One way to configure components (`defs.yaml`)
- One way to automate (`AutomationCondition`)

This is a **recipe book** — "here's the recipe, follow the steps."

**Concrete current example — one way to define and configure a dbt component:**

Step 1: scaffold with a CLI command:
```bash
dg scaffold defs dagster_dbt.DbtProjectComponent transform --project-path transform/jdbt
```

Step 2: configure via YAML (the only mechanism shown):
```yaml
type: dagster_dbt.DbtProjectComponent

attributes:
  project: '{{ context.project_root }}/transform/jdbt'
  translation:
    key: "target/main/{{ node.name }}"
```

Step 3: validate + run:
```bash
dg check defs
dg dev
```

The older `@dbt_assets` Python decorator approach is not mentioned on this tutorial page.

**Concrete current example — the only automation pattern shown in the tutorial:**

```python
import dagster as dg

@dg.asset(
    deps=["upstream"],
    automation_condition=dg.AutomationCondition.on_cron("@hourly"),
)
def hourly_asset() -> None: ...
```

Sensors, custom cron logic, and the older `AutoMaterializePolicy` are not mentioned. The recipe is singular.

**Concrete current example — the Component class that replaces hand-coded assets:**

In the basics tutorial, three nearly-identical hand-coded Python asset functions get replaced by one Component:

```python
class Tutorial(dg.Component, dg.Model, dg.Resolvable):
    duckdb_database: str
    etl_steps: list[ETL]

    def build_defs(self, context: dg.ComponentLoadContext) -> dg.Definitions:
        _etl_assets = []
        for etl in self.etl_steps:
            @dg.asset(name=etl.table)
            def _table(duckdb: DuckDBResource):
                with duckdb.get_connection() as conn:
                    conn.execute(f"create or replace table {etl.table} as ...")
            _etl_assets.append(_table)
        return dg.Definitions(assets=_etl_assets, resources={...})
```

Configured via YAML:
```yaml
type: dagster_tutorial.components.tutorial.Tutorial
attributes:
  duckdb_database: /tmp/jaffle_platform.duckdb
  etl_steps:
    - url_path: https://...raw_customers.csv
      table: customers
    - url_path: https://...raw_orders.csv
      table: orders
    - url_path: https://...raw_payments.csv
      table: payments
```

This is positioned as the natural evolution: *"In this tutorial, you will learn about core Dagster features and use them to build a working data pipeline. We will start with the fundamental concepts and progress to higher level abstractions that showcase the power of Dagster."* (Basics Tutorial intro)

---

## Part 7: Examples, Mini-Examples, and Reference Architectures

The examples ecosystem is one of the most dramatically changed areas between 1.6 and the current docs. In 1.6, examples were CLI-extractable project templates in the monorepo. In the current docs, examples have been elevated to a first-class documentation tier with multi-page tutorials, reference architectures, and domain-specific full pipelines.

### 7.1 Dagster 1.6: CLI-Extractable Example Templates

In 1.6, the primary mechanism was:

```bash
dagster project from-example --example <name> --name <my-project>
dagster project list-examples    # discover available examples
```

All examples lived in the `dagster-io/dagster` monorepo under `/examples/`. There were **27 directories (24 user-facing)** organized into these categories:

| Category | Count | Key Examples |
|----------|-------|-------------|
| **Quickstarts** | 4 | `quickstart_etl` (local), `quickstart_aws` (S3), `quickstart_gcp` (BigQuery), `quickstart_snowflake` |
| **Reference architecture** | 1 | `project_fully_featured` (HN analytics + ML + dbt, **[UNMAINTAINED]**) |
| **Tutorial companions** | 3 | `tutorial`, `tutorial_notebook_assets`, `project_dagster_university_start` |
| **Asset pattern examples** | 5 | `assets_dbt_python`, `assets_modern_data_stack`, `assets_dynamic_partitions`, etc. |
| **Feature demonstrations** | 4 | `assets_smoke_test`, `feature_graph_backed_assets`, `development_to_production`, etc. |
| **Integration examples** | 5 | `with_airflow`, `with_great_expectations`, `with_wandb`, `with_pyspark`, `with_pyspark_emr` |
| **Deployment examples** | 3 | `deploy_docker`, `deploy_ecs`, `deploy_k8s` |

**Key characteristics of 1.6 examples:**

1. **All were self-contained project scaffolds** — you ran `dagster project from-example` and got a working project directory with `setup.py`, assets, resources, schedules, and tests.

2. **The "fully featured" reference was UNMAINTAINED** — `project_fully_featured`, the flagship reference architecture (HN activity data, ML recommender, dbt analytics, multi-environment deploy), was already marked `[UNMAINTAINED]` in 1.6, with users directed to the "Dagster Open Platform" repo.

3. **Examples showed diverse patterns** — the collection included ops-based patterns (`with_pyspark`, `with_great_expectations`), asset-based patterns (`assets_dbt_python`), and mixed patterns. There was no single "right way" enforced.

4. **Quickstarts were interchangeable** — all four quickstarts followed the same HackerNews ETL pattern but with different storage backends (local, S3, BigQuery, Snowflake), letting users pick their cloud.

**Verbatim from the 1.6 "Create New Project" page:**

> *"You can also generate a Dagster project from an official Dagster example, which is useful for learning: `dagster project from-example --name my-dagster-project --example quickstart_etl`"*

This positioned examples as a **learning aid** — something to copy from, not a reference to follow exactly.

### 7.2 Current Docs: Full-Pipeline Tutorials and Reference Architectures

The current docs organize examples into a **three-tier hierarchy** that didn't exist in 1.6:

#### Tier 1: Full Pipeline Tutorials (9 multi-page walkthroughs)

These are the standout addition. Each is a guided, multi-page tutorial building a complete real-world pipeline:

| # | Tutorial | Domain | Tech Stack | Uses Components? | Pages |
|---|----------|--------|------------|-------------------|-------|
| 1 | **ETL Pipeline** | Data engineering | DuckDB + Sling + dbt + Evidence | **Yes** (`DbtProjectComponent`, Sling component) | ~8 |
| 2 | **Dagster + dbt** | Analytics | dbt + DuckDB + `DbtProjectComponent` | **Yes** | ~5 |
| 3 | **Bluesky Analytics** | Social media analytics | Bluesky API + Cloudflare R2 + dbt + Power BI | Mixed (custom resource + BI integration) | ~4 |
| 4 | **RAG with Pinecone** | AI/ML | GitHub API + OpenAI + Pinecone | No (standard Python assets) | ~4 |
| 5 | **Podcast Transcription** | AI/ML | RSS + Modal (serverless) + Dagster Pipes | No (Pipes + factory pattern) | ~3 |
| 6 | **Prompt Engineering** | AI/ML | Anthropic Claude + NREL API + Pydantic | No (standard assets) | ~2 |
| 7 | **LLM Fine-Tuning** | AI/ML | Goodreads dataset + DuckDB + OpenAI | No (standard assets) | ~4 |
| 8 | **DSPy Puzzle Solving** | AI/ML | DSPy + MIPROv2 + custom `DSPyModelBuilder` | **Yes** (custom component authoring) | ~3 |
| 9 | **ML Pipeline (PyTorch)** | ML | MNIST + PyTorch CNN + batch inference | No (standard assets) | ~3 |

**Key observation:** 4 of 9 full pipelines are AI/ML focused, reflecting Dagster's strategic push into AI orchestration. In 1.6, there was only 1 ML-related example (`project_fully_featured`'s recommender, which was unmaintained).

#### Tier 2: Reference Architectures (4 architectural patterns)

These are entirely new — conceptual architecture diagrams with integration patterns, not runnable code:

| # | Architecture | Pattern | Key Technologies |
|---|-------------|---------|-----------------|
| 1 | **ETL / Reverse ETL** | Salesforce → Fivetran → Snowflake → dbt → Hightouch → Salesforce | `FivetranAccountComponent` |
| 2 | **BI (Business Intelligence)** | Shopify/Postgres → Airbyte → warehouse → dbt → BI tools | `AirbyteWorkspaceComponent` |
| 3 | **RAG** | GitHub GraphQL → embeddings (OpenAI) → vector DB | Standard Python patterns |
| 4 | **Real-Time System** | dlt extraction → ClickHouse, Kafka events → materialized views | dlt integration |

Reference architectures had **no equivalent in 1.6**. The closest thing was `project_fully_featured`, which was a runnable project, not an architectural pattern. Additionally, the [hooli-data-eng-pipelines](https://github.com/dagster-io/hooli-data-eng-pipelines) GitHub repo serves as a more advanced reference architecture (multi-project workspace, Dagster+ Hybrid K8s deployment, CI/CD with GitHub Actions, RBAC), but it's not prominently linked from the new docs examples section.

#### Tier 3: Mini Examples (9 focused pattern guides) — NEW

This is a particularly interesting addition. Mini examples are **the one area of the current docs that explicitly presents multiple approaches with trade-offs** — a style much closer to the 1.6 "here are your options" philosophy. They are described as *"focused, pattern-based guides for common Dagster use cases and architectural decisions."*

| # | Mini Example | What It Explores | Approaches Compared |
|---|-------------|-----------------|-------------------|
| 1 | **Dynamic Fanout** | Processing variable numbers of items in parallel | Dynamic outputs vs static |
| 2 | **Dynamic Outputs vs Python Parallelism** | Parallelism strategies | Dagster dynamic outputs vs `concurrent.futures` — trade-offs in observability, performance, resource consumption |
| 3 | **Asset Health Monitoring** | Monitoring critical Tier-0 assets | Materialization tracking, data quality checks, freshness policies |
| 4 | **Resource Caching** | Caching expensive operations in resources | API calls, DB queries, heavy computations |
| 5 | **Sharing Code Across Code Locations** | DRY code across multiple code locations | Shared modules, factories, helpers |
| 6 | **Partition Backfill Strategies** | Three backfill strategies | One-run-per-partition vs batched vs single-run (`BackfillPolicy`) — trade-offs in overhead, fault isolation, resource utilization |
| 7 | **Partitions vs Config** | Parameterizing pipelines | Partitions vs run configuration — trade-offs in tracking, observability, workflow |
| 8 | **PII Redaction in Compute Logs** | Automatic PII redaction | Custom compute log manager approaches |
| 9 | **Lambda Run Launcher** | Serverless run execution | AWS Lambda instead of ECS/containers for lightweight jobs |

**Why this matters for the analysis:** Mini examples are the counterbalance to the prescriptive tutorials. While the Full Pipeline tutorials say "do it this way," mini examples say "here are 2-3 approaches, each with distinct trade-offs in X, Y, and Z." This is the closest the current docs get to the 1.6 "encyclopedia of patterns" style — but mini examples are scoped to operational decisions (how to backfill, how to parallelize), not to fundamental abstractions (assets vs ops). The *what to build with* is prescribed; the *how to tune it* allows choice.

Notably, mini examples do **not** use Components or the `dg` CLI — they focus on core Python-level Dagster patterns. This reinforces that Components are the prescribed path for building, while Python patterns are the flexible layer for optimization.

#### Tier 4: GitHub Examples (still present, evolving)

The `/examples/` directory in the monorepo now contains **~49 directories** (up from 27 in 1.6):

| Category | Count | New Since 1.6 |
|----------|-------|---------------|
| Full pipeline companions (`docs_projects/`) | ~9 | All new |
| Airflow migration (`airlift-*`, `starlift-*`) | 4 | All new |
| Components-era examples | 3 | All new (`components_yaml_checks_dsl`, `ingestion-patterns`, `data-quality-patterns`) |
| Domain examples | 3 | `snowflake_cortex`, `google_drive_factory`, `with_openai` |
| Legacy/unmaintained | ~15 | Carried over from 1.6 |
| Deployment | 3 | Carried over |
| Internal (`docs_snippets`, `experimental`) | 3 | Expanded |

### 7.3 Side-by-Side Comparison

| Dimension | 1.6 Examples | Current Examples |
|-----------|-------------|-----------------|
| **Total count** | 24 user-facing | ~56 (18 on docs site + ~33 on GitHub + ~5 experimental) |
| **Discovery** | `dagster project list-examples` CLI | Browsable on docs site at `/examples/` |
| **Delivery mechanism** | `dagster project from-example` scaffold | Multi-page tutorial on docs site |
| **Reference architectures** | 1 (unmaintained) | 4 (new category, aspirational not runnable) |
| **Full pipeline tutorials** | 0 (tutorial was concept-focused) | 9 multi-page walkthroughs (~36 sub-pages) |
| **Mini examples** | 0 | 9 (pattern-focused, trade-off-oriented) |
| **AI/ML coverage** | 1 (recommender, unmaintained) | 5 full pipelines (RAG, Fine-Tuning, DSPy, PyTorch, Prompt Engineering) |
| **Components-era examples** | 0 | ~7 use Components/`dg` CLI |
| **Airflow migration** | 1 (`with_airflow`) | 4 dedicated examples (`airlift-*`, `starlift-*`) |
| **Unmaintained examples** | ~9 | ~15 (carried over + newly unmaintained) |
| **Quickstart examples** | 4 (one per cloud) | Replaced by `create-dagster` quickstart |
| **Shows multiple approaches** | Most examples showed one approach | Mini examples show 2-3 approaches with trade-offs; full pipelines show one |

### 7.4 What This Means for the Analysis

The examples evolution reinforces the themes from earlier sections — but with one important nuance provided by the mini-examples:

**1. From "copy and adapt" to "follow the tutorial."**

In 1.6, examples were **templates**: you scaffolded a project from an example and modified it. The example itself was a starting point, and users were expected to understand and change the code. The `quickstart_etl` README said:
> *"The purpose of this project is to provide a starting point for your Dagster pipelines."*

In the current docs, examples are **guided walkthroughs**: each has 3-8 pages of step-by-step instructions with exact commands, exact YAML, and exact code to paste. Users follow the tutorial as written. The ETL Pipeline tutorial introduction says:
> *"In this tutorial, you will build a data pipeline that extracts data from files into DuckDB, transforms it with dbt, and visualizes the results."*

The 1.6 framing gives ownership ("your pipelines"). The current framing describes an outcome ("you will build").

**2. Reference architectures are a new opinionation tool.**

The four reference architectures (ETL/Reverse ETL, BI, RAG, Real-Time) are inherently opinionated — they prescribe which tools to use in combination (Fivetran + Snowflake + dbt + Hightouch, or Airbyte + dbt + BI tools). In 1.6, there was no equivalent guidance on technology combinations. The reference architectures answer a question 1.6 never addressed: "What should my overall data platform look like?"

**3. The AI/ML pivot is visible in examples first.**

5 of the 9 full-pipeline tutorials are AI/ML focused (RAG, Prompt Engineering, LLM Fine-Tuning, DSPy, ML Pipeline). This represents a major strategic shift that's more visible in the examples than in the core docs. In 1.6, AI/ML was an afterthought (one unmaintained recommender model). In the current docs, AI/ML is nearly half the showcase material.

### 7.5 How to Categorize Examples in This Analysis

The examples section fits into the analysis framework as follows:

| Analysis Category | How Examples Contribute |
|------------------|----------------------|
| **Opinionation** (Part 2) | Reference architectures prescribe technology stacks. Full pipeline tutorials prescribe exact workflows. This is a **significant increase** in opinionation through examples. |
| **Onboarding** (Part 3) | The ETL Pipeline tutorial is now a core part of the onboarding funnel (it follows the Basics Tutorial). In 1.6, examples were optional side-resources. This makes examples a **primary onboarding tool** rather than supplementary material. |
| **Prescriptive guidance** (Part 5) | Every full-pipeline tutorial page has 5-7 prescriptive instances. With 9 tutorials averaging 4 pages each, that's ~36 pages of prescriptive example content that **didn't exist in 1.6**. |
| **Hands-on code** (Part 6) | The 9 full-pipeline tutorials collectively contain ~200+ code blocks (Python, YAML, CLI, config). This is the single largest source of runnable code in the current docs and **triples** the total hands-on example surface area vs 1.6. |
| **Best practices** (Part 3.2) | Reference architectures implicitly communicate "this is how a Dagster data platform should be structured" — a form of best-practice guidance that goes beyond individual project structure to **platform architecture**. |
| **Counterpoint to opinionation** | Mini examples are the **one area** where the current docs explicitly present multiple approaches with trade-offs. This creates a two-layer model: the tutorials/full pipelines say *"build this way"* while the mini examples say *"once you're building, here are choices to consider."* 1.6 had this flexibility at the foundational level (assets vs ops); the current docs push it up to the operational level (how to backfill, how to parallelize). |

---

## Appendix A: Key Feature Timeline (1.6 → Current)

| Version | Codename | Date | Key Changes |
|---------|----------|------|-------------|
| **1.6** | — | Early 2024 | Baseline: SDA-first docs, `dagster` CLI, ops/graphs documented, `MaterializeResult`/`AssetSpec`/`AssetDep` stabilized |
| **1.7** | "Love Plus One" | ~April 2024 | Asset Checks GA, `@multi_asset_check`, freshness checks, column schema change checks, Asset Catalog UI |
| **1.8** | "Call Me Maybe" | August 2024 | Dagster Pipes GA (subprocess, K8s, Databricks, Lambda), `AssetSpec` directly in `Definitions`, `SourceAsset` deprecated, Auto-Materialize Policies deprecated |
| **1.9** | "Spooky" | November 2024 | Declarative Automation GA (`AutomationCondition`), BI integrations (Tableau, Power BI, Looker, Sigma), `load_definitions_from_module`, `map_asset_specs` |
| **1.10** | "Mambo No. 5" | February 2025 | Concurrency pools (unified run/op concurrency), Components preview, `dg` CLI preview, FreshnessPolicy preview |
| **1.11** | "Build Me Up Buttercup" | June 2025 | Components + `dg` CLI stable (1.11.10), `create-dagster` CLI, new project structure with `defs/` folder, auto-discovery via `load_from_defs_folder`, docs rewrite on Docusaurus v3, partial retries, hooks in assets |
| **1.12** | "Monster Mash" | October 2025 | FreshnessPolicy GA, Components RC, partitioned asset checks, configurable backfills, Python 3.14 support, `Definitions.map_asset_specs` |

Latest patch: **1.12.17** (February 27, 2026).

### Key API Migration Paths

| Deprecated API | Replacement | Deprecated In | Removal Target |
|---------------|-------------|---------------|----------------|
| `SourceAsset` | `AssetSpec` | 1.8 | 2.0 |
| `AutoMaterializePolicy` | `AutomationCondition` | 1.8 | 2.0 |
| `AutoMaterializeRule` | `AutomationCondition` composables | 1.8 | 2.0 |
| `@multi_asset_sensor` | `AutomationCondition` | ~1.9 | 2.0 |
| `dagster project scaffold` | `create-dagster project` | 1.11 | TBD |
| `external_assets_from_specs()` | `AssetSpec` directly in `Definitions` | 1.8 | 2.0 |

### Documentation Infrastructure Changes

The docs themselves underwent a major rebuild between 1.6 and current:
- **Migrated to Docusaurus v3** from a previous custom system
- **Dual documentation system**: Docusaurus for guides/tutorials, Sphinx for API reference
- **Legacy docs** preserved at `legacy-docs.dagster.io` (covering 1.9.9 and earlier)
- **AI-powered "Ask AI" assistant** backed by docs, GitHub issues, and discussions (answers 16,000+ community questions per month)
- **Public announcement**: GitHub Discussion #27332 for the new docs site going live
- **Conference talk**: "Write Less More: How Dagster Rebuilt Our Docs from the Ground Up" at Data Council 2025

---

## Appendix: Navigation Structure Comparison

### 1.6 Top-Level Navigation
```
Getting Started
  ├── What's Dagster?
  ├── Hello Dagster
  ├── Installation
  ├── Create New Project
  └── Getting Help
Tutorial
  ├── Part 1: Intro to Assets
  ├── Part 2: Setup
  ├── Part 3: First Asset
  ├── Part 4: Asset Graph
  ├── Part 5: Scheduling
  ├── Part 6: I/O Managers
  ├── Part 7: Resources
  └── Part 8: Next Steps
Concepts
  ├── Assets (9 sub-pages: SDAs, graph-backed, multi-assets, asset jobs,
  │          observations, selection syntax, auto-materialize, checks, external)
  ├── Schedules & Sensors
  ├── Partitions & Backfills
  ├── Resources & Configuration
  ├── Code Locations
  ├── Dagster UI
  ├── Logging
  ├── Testing
  └── Advanced  ← Ops, Graphs, Jobs, I/O Management, Dagster Types, GraphQL
                   (NOTE: deliberately placed under "Advanced" subsection)
Guides
  ├── Best Practices
  │   ├── Project Structure (with full recommended file tree)
  │   ├── Automating Pipelines
  │   ├── Building ML Pipelines
  │   ├── Managing ML Models
  │   └── Exploring a Dagster Project (fully-featured example)
  ├── How Assets Relate to Ops and Graphs
  └── (Various how-to guides)
Integrations (25+ tools)
Deployment (OSS + Cloud)
API Reference (50+ libraries)
About (Community, Releases, Changelog)
```

**Key 1.6 structural signal**: Ops, Graphs, and Jobs were deliberately placed under a "Concepts → Advanced" subsection. This was a strong editorial choice — while they were fully documented, their placement signaled to new users that these were not the primary path.

### Current Top-Level Navigation
```
Getting Started
  ├── Installation
  ├── Quickstart
  ├── Create New Project
  └── Concepts Overview
Dagster Basics Tutorial
  ├── Projects
  ├── Assets
  ├── Resources
  ├── Asset Dependencies
  ├── Asset Checks
  ├── Automation (Schedules)
  └── Components
ETL Pipeline Tutorial
  ├── Extract (Sling)
  ├── Transform (dbt)
  ├── Data Quality
  ├── Automate
  └── Visualize (Evidence)
Concepts
  ├── Assets
  ├── Automation
  └── (other concept pages)
Guides
  ├── Build
  │   ├── Assets (defining, factories, external)
  │   ├── Components (building, creating, registering)
  │   ├── Projects (creating, structure, organizing)
  │   ├── Ops & Jobs
  │   └── ML Pipelines
  ├── Automate
  │   ├── Declarative Automation
  │   ├── Schedules
  │   ├── Sensors
  │   └── Run-status Sensors
  ├── Deploy
  ├── Observe (alerts, catalog, freshness)
  ├── Operate (webserver, running locally)
  ├── Test (asset checks, unit testing)
  ├── Migrate (Airflow-to-Dagster)
  └── Best Practices
Integrations
Deployment
Dagster+
API Reference
  ├── dg CLI Reference
  ├── create-dagster CLI Reference
  └── Python API
About (Changelog, Releases)
```

**Notable structural change**: In 1.6, "Ops, Jobs & Graphs" was a first-class Concepts section. In the current docs, it is buried under Guides → Build → Ops & Jobs — several layers deep, signaling its demotion from a core concept to an advanced/legacy pattern.

---

*This analysis was prepared by comparing the Dagster 1.6 release documentation (available at release-1-6-0.dagster.dagster-docs.io and in the GitHub repo at the 1.6.0 tag) with the current documentation (docs.dagster.io), examining page content, structure, CLI references, abstraction layers, and editorial tone across both versions.*
