-- Product performance combining DMS CDC products/order_items with Stripe payments
select
    p.product_id,
    p.product_name,
    p.category,
    p.price as list_price,
    p.cost,
    p.price - p.cost as margin,
    count(distinct oi.order_id) as orders_containing_product,
    sum(oi.quantity) as total_units_sold,
    sum(oi.line_total) as total_revenue,
    sum(oi.quantity * p.cost) as total_cost,
    sum(oi.line_total) - sum(oi.quantity * p.cost) as total_profit,
    count(distinct pay.payment_id) as associated_payments,
    sum(pay.payment_amount) as collected_revenue
from {{ ref('stg_dms_products') }} p
left join {{ ref('stg_dms_order_items') }} oi on p.product_id = oi.product_id
left join {{ ref('stg_cdc_orders') }} ord on oi.order_id = ord.order_id
left join {{ ref('stg_stripe_payments') }} pay on ord.order_id = pay.payment_id
group by p.product_id, p.product_name, p.category, p.price, p.cost
