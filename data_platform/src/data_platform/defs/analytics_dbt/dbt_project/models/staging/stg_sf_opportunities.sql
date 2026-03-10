-- Staging model for Salesforce opportunities via Fivetran
select
    id as opportunity_id,
    account_id,
    name as opportunity_name,
    stage_name,
    amount,
    close_date,
    is_won
from {{ source('fivetran_salesforce', 'opportunities') }}
