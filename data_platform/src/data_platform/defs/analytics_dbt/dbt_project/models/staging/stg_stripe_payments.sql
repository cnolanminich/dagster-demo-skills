-- Staging model for Stripe payments via Fivetran
select
    id as payment_id,
    customer_id,
    amount,
    currency,
    status,
    created as payment_date
from {{ source('fivetran_stripe', 'payments') }}
