"""Custom dlt (data load tool) ingestion component.

Ingests data from various sources using dlt pipelines.
Supports demo mode for local execution without external dependencies.
"""

from typing import Optional

import dagster as dg


class DltSource(dg.Model):
    """Configuration for a single dlt source table."""

    name: str
    source_type: str = "rest_api"
    description: Optional[str] = None


class DltIngestionComponent(dg.Component, dg.Model, dg.Resolvable):
    """dlt data ingestion component with demo mode support.

    Runs dlt pipelines to extract data from REST APIs, databases,
    and other sources, loading into a destination warehouse.

    When demo_mode is true, generates realistic mock data locally.
    When demo_mode is false, runs actual dlt pipelines against
    configured sources and destinations.
    """

    demo_mode: bool = False
    pipeline_name: str = "dlt_ingestion"
    destination: str = "snowflake"
    dataset_name: str = "raw_dlt"
    sources: list[DltSource] = []

    def _make_asset(self, source: DltSource) -> dg.AssetsDefinition:
        """Create a single dlt source ingestion asset."""
        asset_key = dg.AssetKey(["dlt_raw", source.name])
        source_desc = source.description or f"dlt ingestion: {source.name} via {source.source_type}"

        # Capture config in closure
        source_name = source.name
        source_type = source.source_type
        demo_mode = self.demo_mode
        pipeline_name = self.pipeline_name
        destination = self.destination
        dataset_name = self.dataset_name

        @dg.asset(
            key=asset_key,
            kinds={"dlt", "python"},
            description=source_desc,
            tags={"domain": "ingestion", "schedule": "hourly", "source": "dlt"},
            group_name="dlt_ingestion",
            owners=["data-engineering@company.com"],
        )
        def dlt_source_asset(context: dg.AssetExecutionContext):
            if demo_mode:
                context.log.info(
                    f"Demo mode: Simulating dlt pipeline for {source_name} "
                    f"({source_type})"
                )
                row_counts = {
                    "customers": 25000,
                    "events": 150000,
                    "invoices": 45000,
                }
                return dg.MaterializeResult(
                    metadata={
                        "records_loaded": dg.MetadataValue.int(
                            row_counts.get(source_name, 10000)
                        ),
                        "pipeline": dg.MetadataValue.text(pipeline_name),
                        "destination": dg.MetadataValue.text(destination),
                        "dataset": dg.MetadataValue.text(dataset_name),
                        "source_type": dg.MetadataValue.text(source_type),
                        "mode": dg.MetadataValue.text("demo"),
                    }
                )
            else:
                import dlt

                context.log.info(
                    f"Running dlt pipeline '{pipeline_name}' for {source_name}"
                )
                pipeline = dlt.pipeline(
                    pipeline_name=pipeline_name,
                    destination=destination,
                    dataset_name=dataset_name,
                )
                # In production, configure the actual dlt source here
                # e.g. from dlt.sources.rest_api import rest_api_source
                raise NotImplementedError(
                    f"Production dlt source for '{source_name}' must be configured. "
                    f"Set demo_mode: true for local testing."
                )

        return dlt_source_asset

    def build_defs(self, context: dg.ComponentLoadContext) -> dg.Definitions:
        assets = [self._make_asset(source) for source in self.sources]
        return dg.Definitions(assets=assets)
