"""SQL lineage parsing utilities.

The core capability of :class:`TemplatedSqlComponent` is figuring out which
*physical* tables a SQL query reads from. This is harder than a naive
``FROM``/``JOIN`` regex because real-world SQL nests table references inside:

* **CTEs** (``WITH foo AS (...)``) — ``foo`` looks like a table when it is later
  selected from, but it is a query-local name, not an upstream dependency.
* **Nested subqueries** (derived tables in ``FROM (SELECT ...)``) — the subquery
  itself is anonymous, but the *real* tables inside it are genuine dependencies.

We parse the query into an AST with ``sqlglot`` and walk it, which makes both
cases fall out naturally:

* Every CTE name is collected first and then excluded from the set of upstream
  tables, no matter how deeply it is referenced.
* Derived tables are :class:`sqlglot.exp.Subquery` nodes, not
  :class:`sqlglot.exp.Table` nodes, so iterating over ``Table`` nodes only ever
  yields the real underlying tables — even when they are arbitrarily nested.
"""

from __future__ import annotations

import sqlglot
from sqlglot import exp


def extract_upstream_tables(sql: str, dialect: str = "duckdb") -> list[str]:
    """Return the sorted set of physical tables a SQL statement depends on.

    CTE names and derived-subquery aliases are *not* returned, even when nested
    arbitrarily deep. Real tables referenced inside CTEs or subqueries *are*
    returned, normalized to a dotted ``catalog.db.table`` string.

    Args:
        sql: The (already-rendered) SQL statement.
        dialect: The sqlglot dialect used to parse the statement.
    """
    expression = sqlglot.parse_one(sql, dialect=dialect)

    # 1. Collect every name introduced by a CTE anywhere in the tree. A nested
    #    query can define its own CTEs, so we gather them globally and treat any
    #    table reference matching one of these names as query-local.
    cte_names: set[str] = {
        cte.alias_or_name for cte in expression.find_all(exp.CTE)
    }

    upstream: set[str] = set()
    for table in expression.find_all(exp.Table):
        # A reference to a CTE is represented as a Table node whose name matches
        # the CTE alias — skip it, it is not an upstream dependency.
        if table.name in cte_names:
            continue

        # Reassemble the fully-qualified name from whatever parts are present
        # (catalog.db.table), so `raw.customers` and `customers` stay distinct.
        parts = [part for part in (table.catalog, table.db, table.name) if part]
        upstream.add(".".join(parts))

    return sorted(upstream)
