-- Marketing attribution combining HubSpot campaigns with Salesforce pipeline
select
    c.campaign_id,
    c.campaign_name,
    c.campaign_type,
    c.budget,
    count(distinct o.opportunity_id) as attributed_opportunities,
    sum(o.amount) as attributed_pipeline,
    sum(case when o.is_won then o.amount else 0 end) as attributed_revenue
from {{ ref('stg_hubspot_campaigns') }} c
left join {{ ref('stg_sf_opportunities') }} o on 1=1
group by c.campaign_id, c.campaign_name, c.campaign_type, c.budget
