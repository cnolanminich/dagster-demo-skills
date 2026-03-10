-- Revenue fact table combining Salesforce opportunities and Stripe payments
select
    o.opportunity_id,
    o.account_id,
    a.account_name,
    a.industry,
    o.opportunity_name,
    o.amount as opportunity_amount,
    o.stage_name,
    o.is_won,
    p.payment_id,
    p.amount as payment_amount,
    p.currency,
    p.payment_date
from {{ ref('stg_sf_opportunities') }} o
left join {{ ref('stg_sf_accounts') }} a on o.account_id = a.account_id
left join {{ ref('stg_stripe_payments') }} p on o.opportunity_id = p.payment_id
