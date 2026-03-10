-- Staging model for Salesforce accounts via Fivetran
select
    id as account_id,
    name as account_name,
    industry,
    annual_revenue,
    created_date,
    last_modified_date
from {{ source('fivetran_salesforce', 'accounts') }}
