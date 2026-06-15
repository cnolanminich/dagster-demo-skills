-- Staging model for payments.
-- Upstream resolves to the external source `{{ source_schema }}.payments`.
select
    order_id,
    amount
from {{ source_schema }}.payments
