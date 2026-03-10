"""Sigma Computing BI workspace component with demo mode support."""

from dataclasses import dataclass, field

import dagster as dg


@dataclass
class SigmaWorkspaceComponent(dg.Component, dg.Resolvable):
    """Models Sigma Computing workbooks and datasets as Dagster assets.

    Sigma is a cloud-native BI platform that connects directly to cloud
    data warehouses. This component represents Sigma workbooks and their
    underlying datasets as observable assets in the Dagster asset graph.
    """

    demo_mode: bool = False
    client_id: str = "demo_client_id"
    client_secret: str = "demo_client_secret"
    base_url: str = "https://api.sigmacomputing.com"
    workbooks: list[dict] = field(default_factory=list)

    def build_defs(self, context: dg.ComponentLoadContext) -> dg.Definitions:
        if self.demo_mode:
            return self._build_demo_defs()
        return self._build_real_defs()

    @staticmethod
    def _make_demo_asset(wb_name: str, upstream_keys: list):
        @dg.multi_asset(
            specs=[
                dg.AssetSpec(
                    key=dg.AssetKey(["sigma", wb_name]),
                    group_name="sigma_bi",
                    kinds={"sigma"},
                    tags={"bi_tool": "sigma", "schedule": "daily"},
                    owners=["team:analytics"],
                    deps=upstream_keys,
                    description=f"Sigma workbook: {wb_name}",
                )
            ],
            name=f"sigma_{wb_name}",
            can_subset=False,
        )
        def _sigma_asset(context: dg.AssetExecutionContext):
            context.log.info(f"[DEMO] Refreshing Sigma workbook '{wb_name}'")
            return dg.MaterializeResult(
                metadata={
                    "workbook": dg.MetadataValue.text(wb_name),
                    "demo_mode": dg.MetadataValue.bool(True),
                    "status": dg.MetadataValue.text("refreshed"),
                }
            )

        return _sigma_asset

    @staticmethod
    def _make_real_asset(wb_name: str, wb_id: str, upstream_keys: list,
                         client_id: str, client_secret: str, base_url: str):
        @dg.multi_asset(
            specs=[
                dg.AssetSpec(
                    key=dg.AssetKey(["sigma", wb_name]),
                    group_name="sigma_bi",
                    kinds={"sigma"},
                    tags={"bi_tool": "sigma", "schedule": "daily"},
                    owners=["team:analytics"],
                    deps=upstream_keys,
                    description=f"Sigma workbook: {wb_name}",
                )
            ],
            name=f"sigma_{wb_name}",
            can_subset=False,
        )
        def _sigma_asset(context: dg.AssetExecutionContext):
            import requests

            auth_resp = requests.post(
                f"{base_url}/v2/auth/token",
                json={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
                timeout=30,
            )
            auth_resp.raise_for_status()
            token = auth_resp.json()["access_token"]

            context.log.info(f"Materializing Sigma workbook '{wb_name}' (ID: {wb_id})")
            resp = requests.post(
                f"{base_url}/v2/workbooks/{wb_id}/materialization",
                headers={"Authorization": f"Bearer {token}"},
                timeout=300,
            )
            resp.raise_for_status()
            return dg.MaterializeResult(
                metadata={
                    "workbook": dg.MetadataValue.text(wb_name),
                    "workbook_id": dg.MetadataValue.text(wb_id),
                }
            )

        return _sigma_asset

    def _build_demo_defs(self) -> dg.Definitions:
        assets = []
        for wb in self.workbooks:
            wb_name = wb["name"]
            upstream_keys = [dg.AssetKey(k.split("/")) for k in wb.get("upstream_assets", [])]
            assets.append(self._make_demo_asset(wb_name, upstream_keys))
        return dg.Definitions(assets=assets)

    def _build_real_defs(self) -> dg.Definitions:
        assets = []
        for wb in self.workbooks:
            wb_name = wb["name"]
            wb_id = wb["workbook_id"]
            upstream_keys = [dg.AssetKey(k.split("/")) for k in wb.get("upstream_assets", [])]
            assets.append(self._make_real_asset(
                wb_name, wb_id, upstream_keys,
                self.client_id, self.client_secret, self.base_url,
            ))
        return dg.Definitions(assets=assets)
