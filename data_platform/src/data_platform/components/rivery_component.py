"""Rivery ingestion component with demo mode support."""

from dataclasses import dataclass, field

import dagster as dg


@dataclass
class RiveryComponent(dg.Component, dg.Resolvable):
    """Loads data from source systems via Rivery rivers (ELT pipelines).

    Rivery is a SaaS ELT platform that connects to various data sources and
    loads data into cloud warehouses. This component models Rivery rivers
    as Dagster assets, allowing you to orchestrate and monitor ingestion.
    """

    demo_mode: bool = False
    api_token: str = "demo_token"
    account_id: str = "demo_account"
    rivers: list[dict] = field(default_factory=list)

    def build_defs(self, context: dg.ComponentLoadContext) -> dg.Definitions:
        if self.demo_mode:
            return self._build_demo_defs()
        return self._build_real_defs()

    @staticmethod
    def _make_demo_river_asset(river_name: str, destination_table: str, source_type: str):
        asset_key = dg.AssetKey(["rivery", destination_table])

        @dg.multi_asset(
            specs=[
                dg.AssetSpec(
                    key=asset_key,
                    group_name="rivery_ingestion",
                    kinds={"rivery", source_type},
                    tags={"ingestion_tool": "rivery", "schedule": "hourly"},
                    owners=["team:data-engineering"],
                    description=f"Rivery river '{river_name}' loading {source_type} data into {destination_table}",
                )
            ],
            name=f"rivery_{destination_table}",
            can_subset=False,
        )
        def _rivery_asset(context: dg.AssetExecutionContext):
            context.log.info(f"[DEMO] Simulating Rivery river '{river_name}' sync to {destination_table}")
            rows_synced = 15000
            context.log.info(f"[DEMO] Synced {rows_synced} rows")
            return dg.MaterializeResult(
                metadata={
                    "rows_synced": dg.MetadataValue.int(rows_synced),
                    "river_name": dg.MetadataValue.text(river_name),
                    "destination": dg.MetadataValue.text(destination_table),
                    "demo_mode": dg.MetadataValue.bool(True),
                }
            )

        return _rivery_asset

    @staticmethod
    def _make_real_river_asset(river_name: str, river_id: str, destination_table: str,
                               source_type: str, api_token: str, account_id: str):
        asset_key = dg.AssetKey(["rivery", destination_table])

        @dg.multi_asset(
            specs=[
                dg.AssetSpec(
                    key=asset_key,
                    group_name="rivery_ingestion",
                    kinds={"rivery", source_type},
                    tags={"ingestion_tool": "rivery", "schedule": "hourly"},
                    owners=["team:data-engineering"],
                    description=f"Rivery river '{river_name}' loading {source_type} data into {destination_table}",
                )
            ],
            name=f"rivery_{destination_table}",
            can_subset=False,
        )
        def _rivery_asset(context: dg.AssetExecutionContext):
            import requests

            context.log.info(f"Triggering Rivery river '{river_name}' (ID: {river_id})")
            resp = requests.post(
                f"https://api.rivery.io/v1/accounts/{account_id}/rivers/{river_id}/run",
                headers={"Authorization": f"Bearer {api_token}"},
                timeout=300,
            )
            resp.raise_for_status()
            run_id = resp.json().get("run_id", "unknown")
            context.log.info(f"Rivery run started: {run_id}")
            return dg.MaterializeResult(
                metadata={
                    "run_id": dg.MetadataValue.text(run_id),
                    "river_name": dg.MetadataValue.text(river_name),
                }
            )

        return _rivery_asset

    def _build_demo_defs(self) -> dg.Definitions:
        assets = []
        for river in self.rivers:
            assets.append(self._make_demo_river_asset(
                river["name"], river["destination_table"],
                river.get("source_type", "api"),
            ))
        return dg.Definitions(assets=assets)

    def _build_real_defs(self) -> dg.Definitions:
        assets = []
        for river in self.rivers:
            assets.append(self._make_real_river_asset(
                river["name"], river["river_id"], river["destination_table"],
                river.get("source_type", "api"), self.api_token, self.account_id,
            ))
        return dg.Definitions(assets=assets)
