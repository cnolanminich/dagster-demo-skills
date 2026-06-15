-- =====================================================================
-- SHOWCASE: CTEs + nested subqueries.
--
-- The dependency parser must resolve the upstream tables of this model to
-- EXACTLY three internal models:
--     stg_customers, stg_orders, stg_payments
--
-- It must NOT report any of the following as dependencies:
--   * CTE names:        paid_orders, order_totals, ranked_orders
--   * subquery alias:   recent_orders
-- ...even though `stg_orders` is referenced both inside a CTE and two levels
-- deep inside a subquery that defines its own CTE.
-- =====================================================================

with paid_orders as (
    -- Join two staging models inside a CTE.
    select
        o.order_id,
        o.customer_id,
        o.order_date,
        p.amount
    from stg_orders as o
    join stg_payments as p
        on o.order_id = p.order_id
),

order_totals as (
    -- References the CTE above (paid_orders), not a physical table.
    select
        customer_id,
        count(*) as n_orders,
        sum(amount) as total_amount
    from paid_orders
    group by customer_id
)

select
    c.customer_id,
    c.name,
    coalesce(ot.n_orders, 0) as n_orders,
    coalesce(ot.total_amount, 0) as total_amount,
    recent_orders.last_order_date
from stg_customers as c
left join order_totals as ot
    on c.customer_id = ot.customer_id
left join (
    -- Nested subquery that defines its OWN CTE referencing a real table
    -- two levels deep. The subquery alias (recent_orders) is not a table.
    with ranked_orders as (
        select
            customer_id,
            order_date,
            row_number() over (
                partition by customer_id
                order by order_date desc
            ) as rn
        from stg_orders
    )
    select
        customer_id,
        order_date as last_order_date
    from ranked_orders
    where rn = 1
) as recent_orders
    on c.customer_id = recent_orders.customer_id
