"""Tests for the SQL upstream-dependency parser.

These focus on the tricky cases the component is meant to handle: CTEs and
nested subqueries must never leak into the dependency set, while the real
physical tables buried inside them must always be discovered.
"""

from sql_lineage.components.sql_lineage import extract_upstream_tables


def test_simple_from():
    assert extract_upstream_tables("select * from raw.customers") == ["raw.customers"]


def test_join_dedupes_and_sorts():
    sql = """
        select *
        from orders o
        join customers c on o.customer_id = c.id
        join orders o2 on o.parent_id = o2.id
    """
    # `orders` referenced twice -> reported once; results are sorted.
    assert extract_upstream_tables(sql) == ["customers", "orders"]


def test_cte_name_is_not_a_dependency():
    sql = """
        with deduped as (
            select distinct id, name from raw.customers
        )
        select * from deduped
    """
    # `deduped` is a CTE, not an upstream table.
    assert extract_upstream_tables(sql) == ["raw.customers"]


def test_multiple_ctes_referencing_each_other():
    sql = """
        with a as (select * from src_a),
             b as (select * from a join src_b using (id))
        select * from b
    """
    # a and b are CTEs; only the real tables remain.
    assert extract_upstream_tables(sql) == ["src_a", "src_b"]


def test_nested_subquery_with_its_own_cte():
    sql = """
        select c.id, recent.last_seen
        from dim_customers c
        left join (
            with ranked as (
                select customer_id, event_date,
                       row_number() over (
                           partition by customer_id order by event_date desc
                       ) as rn
                from fct_events
            )
            select customer_id, event_date as last_seen
            from ranked where rn = 1
        ) as recent on c.id = recent.customer_id
    """
    # `ranked` (CTE) and `recent` (subquery alias) are not dependencies;
    # the table two levels deep (`fct_events`) is.
    assert extract_upstream_tables(sql) == ["dim_customers", "fct_events"]
