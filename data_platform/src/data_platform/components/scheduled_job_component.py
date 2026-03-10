"""Scheduled job component for flexible asset scheduling."""

from dataclasses import dataclass

import dagster as dg


@dataclass
class ScheduledJobComponent(dg.Component, dg.Resolvable):
    """Component for scheduling assets using flexible selection syntax.

    Adds a Dagster schedule for a given asset selection string and cron schedule.
    """

    job_name: str = ""
    cron_schedule: str = "0 6 * * *"
    asset_selection: str = "*"

    def build_defs(self, context: dg.ComponentLoadContext) -> dg.Definitions:
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
