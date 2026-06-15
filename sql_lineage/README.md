# sql_lineage

A Dagster project demonstrating a **templated SQL component** that parses SQL to
automatically discover upstream dependencies — and resolves them correctly even
through CTEs and deeply nested subqueries.

## The component

`TemplatedSqlComponent`
(`src/sql_lineage/components/templated_sql_component.py`) turns a directory of
`.sql` files into Dagster assets:

1. Each `.sql` file is rendered as a **Jinja2 template** using the configured
   `template_vars`.
2. The rendered SQL is parsed into an AST with [`sqlglot`](https://github.com/tobymao/sqlglot)
   to extract the **physical tables** it reads from
   (`src/sql_lineage/components/sql_lineage.py`).
3. Each file becomes one asset. A referenced table that matches another model
   becomes an **internal dependency**; any other referenced table becomes an
   external **source asset**, so the lineage graph is fully connected.

### Why AST parsing (not regex)

Naive `FROM`/`JOIN` scanning breaks on real SQL. The parser walks the AST so:

- **CTE names** (`WITH foo AS (...)`) are collected and excluded — they are
  query-local, not upstream tables, no matter how often they are referenced.
- **Nested subqueries** (derived tables) are `Subquery` nodes, not `Table`
  nodes, so iterating over real `Table` nodes always finds the genuine
  underlying tables — even nested several levels deep, even when the subquery
  defines its own CTEs.

## The example

`src/sql_lineage/defs/analytics/models/` contains four templated models:

| Model | Upstream resolved by the parser |
|-------|---------------------------------|
| `stg_customers` | `raw.customers` |
| `stg_orders` | `raw.orders` |
| `stg_payments` | `raw.payments` |
| `customer_order_summary` | `stg_customers`, `stg_orders`, `stg_payments` |

`customer_order_summary.sql` is the showcase. It uses three CTEs
(`paid_orders`, `order_totals`, `ranked_orders`) and a nested subquery aliased
`recent_orders` that defines its *own* CTE referencing `stg_orders` two levels
deep. Despite all that, the parser resolves its dependencies to **exactly** the
three staging models — none of the CTE names or the subquery alias leak in.

## Try it

```bash
cd sql_lineage

# Show the inferred lineage graph
uv run dg list defs

# Validate everything loads
uv run dg check defs

# Materialize end-to-end (demo_mode seeds mock source tables in DuckDB)
uv run dg launch --assets '*'

# Run the parser unit tests
uv run python -m pytest tests/

# Explore in the UI
uv run dg dev
```

## Configuration

See `src/sql_lineage/defs/analytics/defs.yaml`:

```yaml
type: sql_lineage.components.templated_sql_component.TemplatedSqlComponent
attributes:
  sql_dir: models          # directory of .sql files, relative to defs.yaml
  dialect: duckdb          # sqlglot dialect for parsing + execution
  group_name: analytics
  template_vars:
    source_schema: raw     # injected into every {{ ... }} in the SQL
  demo_mode: true          # seed mock sources + run against in-memory DuckDB
  # database_path: /path/to/warehouse.duckdb   # used when demo_mode: false
```

For a real deployment, set `demo_mode: false` and point `database_path` at a
DuckDB database whose source tables already exist.
