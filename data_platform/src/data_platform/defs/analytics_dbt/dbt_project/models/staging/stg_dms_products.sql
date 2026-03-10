-- Staging model for MariaDB products via AWS DMS CDC
select
    id as product_id,
    product_name,
    category,
    price,
    cost,
    created_at,
    updated_at
from {{ source('dms_cdc', 'products') }}
