# Dagster Documentation Analysis: 1.6 Release vs. Current (1.11+)

*Analysis Date: March 2, 2026*

---

## Executive Summary

Between Dagster 1.6 and the current release (1.11+), the documentation has undergone a **fundamental transformation** — not just a cosmetic refresh, but a philosophical and structural overhaul that reflects Dagster's evolution from a flexible orchestration framework into a highly opinionated data platform with prescribed workflows, new abstractions (Components, `dg` CLI), and a dramatically narrower "happy path" for new users.

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

- **Ops and Graphs**: In 1.6, ops were called "the core unit of computation in Dagster" (with the caveat that they were an "advanced topic"). In the current docs, ops and graphs are almost entirely absent from onboarding materials. They exist only in deep reference pages.

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

- **Declarative Automation** is clearly favored over other automation methods. The `@multi_asset_sensor` is deprecated. While schedules and sensors are still documented, the framing suggests Declarative Automation is the forward-looking choice: *"Declarative automation is now marked stable! Dagster now offers a mature, first-class way to automatically materialize assets."*

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
