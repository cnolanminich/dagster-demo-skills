-- Staging model for MariaDB customers via AWS DMS CDC
select
    id as customer_id,
    email,
    first_name,
    last_name,
    created_at,
    updated_at
from {{ source('dms_cdc', 'customers') }}
