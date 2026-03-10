-- Staging model for MariaDB order items via AWS DMS CDC
select
    id as order_item_id,
    order_id,
    product_id,
    quantity,
    unit_price,
    quantity * unit_price as line_total,
    created_at
from {{ source('dms_cdc', 'order_items') }}
