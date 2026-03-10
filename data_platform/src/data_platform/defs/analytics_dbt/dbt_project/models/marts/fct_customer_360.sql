-- Customer 360 view combining CRM, payments, orders, marketing, and DMS CDC customer data
select
    a.account_id,
    a.account_name,
    a.industry,
    a.annual_revenue,
    cust.email as customer_email,
    cust.first_name,
    cust.last_name,
    count(distinct o.opportunity_id) as total_opportunities,
    sum(case when o.is_won then o.amount else 0 end) as won_revenue,
    count(distinct ord.order_id) as total_orders,
    sum(ord.total_amount) as total_order_value,
    count(distinct oi.order_item_id) as total_line_items,
    sum(oi.line_total) as total_line_item_value,
    count(distinct c.campaign_id) as campaigns_touched
from {{ ref('stg_sf_accounts') }} a
left join {{ ref('stg_sf_opportunities') }} o on a.account_id = o.account_id
left join {{ ref('stg_cdc_orders') }} ord on a.account_id = ord.customer_id
left join {{ ref('stg_dms_customers') }} cust on ord.customer_id = cust.customer_id
left join {{ ref('stg_dms_order_items') }} oi on ord.order_id = oi.order_id
left join {{ ref('stg_hubspot_campaigns') }} c on 1=1
group by a.account_id, a.account_name, a.industry, a.annual_revenue,
         cust.email, cust.first_name, cust.last_name
