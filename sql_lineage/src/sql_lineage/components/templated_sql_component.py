"""A Dagster component that turns a directory of templated SQL files into assets.

Each ``.sql`` file in ``sql_dir`` becomes one asset. The file is first rendered
as a Jinja2 template (using ``template_vars``), then parsed to discover its
upstream table dependencies (see :mod:`.sql_lineage`). Those dependencies are
wired into the asset graph automatically:

* a referenced table that matches another ``.sql`` model becomes an
  **internal dependency** on that model's asset, and
* a referenced table that is *not* produced by any model becomes an external
  **source asset**, so the lineage graph is fully connected.

CTEs and nested subqueries are resolved correctly: CTE names and derived-table
aliases never show up as dependencies, while the real tables buried inside them
always do.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any, Optional

import dagster as dg
import jinja2

from sql_lineage.components.sql_lineage import extract_upstream_tables


def _asset_key_for_table(table: str) -> dg.AssetKey:
    """Map a dotted SQL table name (``raw.customers``) to an AssetKey."""
    return dg.AssetKey(table.split("."))


class SqlModel:
    """A single rendered SQL model: its name, SQL text, and upstream tables."""

    def __init__(self, name: str, sql: str, dialect: str):
        self.name = name
        self.sql = sql
        self.upstream_tables = extract_upstream_tables(sql, dialect=dialect)


class TemplatedSqlComponent(dg.Component, dg.Model, dg.Resolvable):
    """Build assets from a directory of templated SQL files.

    Upstream dependencies are inferred by parsing each query's AST, so CTEs and
    nested subqueries resolve to the correct physical source tables.
    """

    # Directory (relative to this component's defs.yaml) holding the .sql files.
    sql_dir: str

    # sqlglot dialect used both to parse dependencies and to execute the SQL.
    dialect: str = "duckdb"

    # Optional asset group for every model produced by this component.
    group_name: Optional[str] = None

    # Variables injected into each .sql file's Jinja2 template before parsing.
    template_vars: Mapping[str, Any] = {}

    # When True, run against an in-memory DuckDB with mock source tables so the
    # demo materializes end-to-end without any external database.
    demo_mode: bool = False

    # DuckDB database path used outside of demo mode. None => in-memory.
    database_path: Optional[str] = None

    def _load_models(self, context: dg.ComponentLoadContext) -> list[SqlModel]:
        sql_dir = Path(self.sql_dir)
        if not sql_dir.is_absolute():
            sql_dir = context.path / sql_dir

        env = jinja2.Environment(undefined=jinja2.StrictUndefined)
        models: list[SqlModel] = []
        for sql_file in sorted(sql_dir.glob("*.sql")):
            rendered = env.from_string(sql_file.read_text()).render(
                **self.template_vars
            )
            models.append(SqlModel(sql_file.stem, rendered, self.dialect))
        return models

    def build_defs(self, context: dg.ComponentLoadContext) -> dg.Definitions:
        models = self._load_models(context)
        model_names = {model.name for model in models}

        # Topologically order models so downstream SQL executes after the
        # upstream tables it reads have been created (matters for demo runs).
        internal_deps = {
            model.name: {
                t.split(".")[-1]
                for t in model.upstream_tables
                if t.split(".")[-1] in model_names
            }
            for model in models
        }
        ordered_names: list[str] = []
        visited: set[str] = set()

        def _visit(name: str) -> None:
            if name in visited:
                return
            visited.add(name)
            for dep in sorted(internal_deps[name]):
                _visit(dep)
            ordered_names.append(name)

        for name in sorted(model_names):
            _visit(name)

        # Build one AssetSpec per model and collect any external source tables.
        model_specs: list[dg.AssetSpec] = []
        external_sources: dict[str, dg.AssetKey] = {}
        sql_by_key: dict[dg.AssetKey, str] = {}
        upstream_by_key: dict[dg.AssetKey, list[str]] = {}

        for model in models:
            deps: list[dg.AssetKey] = []
            for table in model.upstream_tables:
                # Match on the final name segment (db-qualified or not).
                table_name = table.split(".")[-1]
                if table_name in model_names:
                    deps.append(dg.AssetKey([table_name]))
                else:
                    key = _asset_key_for_table(table)
                    external_sources[table] = key
                    deps.append(key)

            key = dg.AssetKey([model.name])
            sql_by_key[key] = model.sql
            upstream_by_key[key] = model.upstream_tables
            model_specs.append(
                dg.AssetSpec(
                    key=key,
                    deps=deps,
                    group_name=self.group_name,
                    kinds={self.dialect, "sql"},
                    skippable=True,
                    description=f"SQL model `{model.name}`",
                    metadata={
                        "sql": dg.MetadataValue.md(f"```sql\n{model.sql}\n```"),
                        "upstream_tables": dg.MetadataValue.json(
                            model.upstream_tables
                        ),
                        "dagster/relation_identifier": model.name,
                    },
                )
            )

        # External tables become unmaterialized source assets so the lineage
        # graph is connected end-to-end.
        source_specs = [
            dg.AssetSpec(
                key=key,
                group_name="sources",
                kinds={self.dialect},
                description=f"External source table `{table}`",
            )
            for table, key in sorted(external_sources.items())
        ]

        demo_mode = self.demo_mode
        database_path = self.database_path
        dialect = self.dialect

        @dg.multi_asset(specs=model_specs, can_subset=True)
        def _sql_models(context):
            import duckdb

            con = duckdb.connect(database_path or ":memory:")
            try:
                if demo_mode:
                    # Seed mock source tables so the SQL actually runs locally.
                    # Each source gets the same superset of columns, so any
                    # staging model can select whatever columns it needs.
                    seed_rows = (
                        "SELECT * FROM (VALUES "
                        "(1, 1, 101, DATE '2024-01-01', 'Ada Lovelace', 50.0), "
                        "(2, 2, 102, DATE '2024-01-05', 'Linus Torvalds', 75.0), "
                        "(3, 1, 103, DATE '2024-02-01', 'Ada Lovelace', 120.0)"
                        ") AS t(id, customer_id, order_id, order_date, name, amount)"
                    )
                    for spec in source_specs:
                        parts = spec.key.path
                        if len(parts) > 1:
                            schema = ".".join(parts[:-1])
                            con.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
                        table = ".".join(parts)
                        con.execute(
                            f"CREATE OR REPLACE TABLE {table} AS {seed_rows}"
                        )

                selected = context.selected_asset_keys
                ordered_keys = [
                    dg.AssetKey([name])
                    for name in ordered_names
                    if dg.AssetKey([name]) in selected
                ]
                for key in ordered_keys:
                    model_name = key.path[-1]
                    sql = sql_by_key[key]
                    context.log.info(
                        f"Materializing `{model_name}` "
                        f"(dialect={dialect}, demo_mode={demo_mode}); "
                        f"upstream tables: {upstream_by_key[key]}"
                    )
                    # Outside demo mode the source tables are expected to
                    # already exist in the configured DuckDB database.
                    con.execute(
                        f'CREATE OR REPLACE TABLE "{model_name}" AS {sql}'
                    )
                    n_rows = con.execute(
                        f'SELECT count(*) FROM "{model_name}"'
                    ).fetchone()[0]

                    yield dg.MaterializeResult(
                        asset_key=key,
                        metadata={"dagster/row_count": dg.MetadataValue.int(n_rows)},
                    )
            finally:
                con.close()

        return dg.Definitions(assets=[_sql_models, *source_specs])
