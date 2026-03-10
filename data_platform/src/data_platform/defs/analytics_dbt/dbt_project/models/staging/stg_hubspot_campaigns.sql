-- Staging model for HubSpot campaigns via Rivery
select
    id as campaign_id,
    name as campaign_name,
    type as campaign_type,
    status,
    budget,
    start_date,
    end_date
from {{ source('rivery_hubspot', 'marketing_campaigns') }}
