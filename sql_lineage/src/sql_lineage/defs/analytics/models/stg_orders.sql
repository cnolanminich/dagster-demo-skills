-- Staging model for orders.
-- Upstream resolves to the external source `{{ source_schema }}.orders`.
select
    order_id,
    customer_id,
    order_date
from {{ source_schema }}.orders
