-- Staging model for MariaDB orders via CDC
select
    id as order_id,
    customer_id,
    order_date,
    total_amount,
    status as order_status,
    updated_at
from {{ source('cdc_mariadb', 'orders') }}
