"""Scheduled job component for flexible asset scheduling.

Allows creating schedules using asset selection syntax
instead of hardcoded asset keys, making schedules maintainable and scalable.
"""

import dagster as dg


class ScheduledJobComponent(dg.Component, dg.Model, dg.Resolvable):
    """Component for scheduling assets using flexible selection syntax.

    Adds a Dagster schedule for a given asset selection string and cron schedule.

    Asset selection examples:
    - "tag:schedule=daily" - All assets tagged with schedule=daily
    - "group:fivetran_ingestion" - All assets in the fivetran_ingestion group
    - "kind:dlt" - All dlt assets
    - "owner:data-engineering@company.com" - All assets owned by data-engineering
    """

    job_name: str
    cron_schedule: str
    asset_selection: str

    def build_defs(self, context: dg.ComponentLoadContext) -> dg.Definitions:
        """Build a scheduled job with flexible asset selection."""
        job = dg.define_asset_job(
            name=self.job_name,
            selection=self.asset_selection,
        )

        schedule = dg.ScheduleDefinition(
            job=job,
            cron_schedule=self.cron_schedule,
        )

        return dg.Definitions(
            schedules=[schedule],
            jobs=[job],
        )
