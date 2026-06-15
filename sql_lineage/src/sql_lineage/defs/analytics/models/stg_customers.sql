-- Staging model for customers.
-- Upstream resolves to the templated external source `{{ source_schema }}.customers`.
-- The deduplication CTE here is query-local and must NOT appear as a dependency.
with deduplicated as (
    select distinct
        id as customer_id,
        name
    from {{ source_schema }}.customers
)

select
    customer_id,
    name
from deduplicated
