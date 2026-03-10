"""Custom Fivetran component with demo mode support."""

from dataclasses import dataclass, field

import dagster as dg


@dataclass
class CustomFivetranComponent(dg.Component, dg.Resolvable):
    """Fivetran connector component with demo mode for local development.

    In real mode, connects to Fivetran API to sync connectors.
    In demo mode, generates mock assets representing Fivetran connector outputs.
    """

    demo_mode: bool = False
    api_key: str = "demo_api_key"
    api_secret: str = "demo_api_secret"
    connectors: list[dict] = field(default_factory=list)

    def build_defs(self, context: dg.ComponentLoadContext) -> dg.Definitions:
        if self.demo_mode:
            return self._build_demo_defs()
        return self._build_real_defs()

    @staticmethod
    def _make_demo_asset(connector_name: str, table: str):
        asset_key = dg.AssetKey(["fivetran", connector_name, table])

        @dg.multi_asset(
            specs=[
                dg.AssetSpec(
                    key=asset_key,
                    group_name="fivetran_ingestion",
                    kinds={"fivetran"},
                    tags={"ingestion_tool": "fivetran", "schedule": "hourly"},
                    owners=["team:data-engineering"],
                    description=f"Fivetran connector '{connector_name}' table: {table}",
                )
            ],
            name=f"fivetran_{connector_name}_{table}",
            can_subset=False,
        )
        def _fivetran_asset(context: dg.AssetExecutionContext):
            context.log.info(f"[DEMO] Simulating Fivetran sync: {connector_name}/{table}")
            rows_synced = 25000
            return dg.MaterializeResult(
                metadata={
                    "rows_synced": dg.MetadataValue.int(rows_synced),
                    "connector": dg.MetadataValue.text(connector_name),
                    "table": dg.MetadataValue.text(table),
                    "demo_mode": dg.MetadataValue.bool(True),
                }
            )

        return _fivetran_asset

    @staticmethod
    def _make_real_asset(connector_name: str, connector_id: str, table: str,
                         api_key: str, api_secret: str):
        asset_key = dg.AssetKey(["fivetran", connector_name, table])

        @dg.multi_asset(
            specs=[
                dg.AssetSpec(
                    key=asset_key,
                    group_name="fivetran_ingestion",
                    kinds={"fivetran"},
                    tags={"ingestion_tool": "fivetran", "schedule": "hourly"},
                    owners=["team:data-engineering"],
                    description=f"Fivetran connector '{connector_name}' table: {table}",
                )
            ],
            name=f"fivetran_{connector_name}_{table}",
            can_subset=False,
        )
        def _fivetran_asset(context: dg.AssetExecutionContext):
            import requests

            context.log.info(f"Triggering Fivetran sync for connector '{connector_name}'")
            resp = requests.post(
                f"https://api.fivetran.com/v1/connectors/{connector_id}/force",
                auth=(api_key, api_secret),
                timeout=300,
            )
            resp.raise_for_status()
            return dg.MaterializeResult(
                metadata={
                    "connector": dg.MetadataValue.text(connector_name),
                    "connector_id": dg.MetadataValue.text(connector_id),
                }
            )

        return _fivetran_asset

    def _build_demo_defs(self) -> dg.Definitions:
        assets = []
        for connector in self.connectors:
            connector_name = connector["name"]
            for table in connector.get("tables", []):
                assets.append(self._make_demo_asset(connector_name, table))
        return dg.Definitions(assets=assets)

    def _build_real_defs(self) -> dg.Definitions:
        assets = []
        for connector in self.connectors:
            connector_name = connector["name"]
            connector_id = connector["connector_id"]
            for table in connector.get("tables", []):
                assets.append(self._make_real_asset(
                    connector_name, connector_id, table,
                    self.api_key, self.api_secret,
                ))
        return dg.Definitions(assets=assets)
