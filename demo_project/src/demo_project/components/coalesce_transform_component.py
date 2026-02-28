"""Custom Coalesce transformation component.

Triggers Coalesce jobs to transform data in the warehouse.
Supports demo mode for local execution without Coalesce API access.
"""

from typing import Optional

import dagster as dg


class CoalesceNode(dg.Model):
    """Configuration for a single Coalesce transformation node/model."""

    name: str
    description: Optional[str] = None
    upstream_keys: list[list[str]] = []


class CoalesceTransformComponent(dg.Component, dg.Model, dg.Resolvable):
    """Coalesce data transformation component with demo mode support.

    Triggers Coalesce environment runs to execute SQL-based transformations.
    Coalesce nodes consume raw data from upstream ingestion (dlt, Fivetran)
    and produce cleaned, modeled datasets.

    When demo_mode is true, simulates Coalesce job runs locally.
    When demo_mode is false, calls the Coalesce API to trigger real jobs.
    """

    demo_mode: bool = False
    environment_id: str = ""
    api_token: str = ""
    base_url: str = "https://app.coalescesoftware.io/api/v1"
    nodes: list[CoalesceNode] = []

    def _make_asset(self, node: CoalesceNode) -> dg.AssetsDefinition:
        """Create a single Coalesce node asset."""
        asset_key = dg.AssetKey(["coalesce", node.name])
        node_desc = node.description or f"Coalesce transformation: {node.name}"
        upstream_deps = [dg.AssetKey(k) for k in node.upstream_keys]

        # Capture config in closure
        node_name = node.name
        demo_mode = self.demo_mode
        environment_id = self.environment_id
        api_token = self.api_token
        base_url = self.base_url

        @dg.asset(
            key=asset_key,
            kinds={"coalesce", "sql"},
            description=node_desc,
            deps=upstream_deps,
            tags={
                "domain": "transformation",
                "schedule": "daily",
                "source": "coalesce",
            },
            group_name="coalesce_transform",
            owners=["analytics-engineering@company.com"],
        )
        def coalesce_node_asset(context: dg.AssetExecutionContext):
            if demo_mode:
                context.log.info(
                    f"Demo mode: Simulating Coalesce transformation for {node_name}"
                )
                row_counts = {
                    "customer_360": 24500,
                    "transaction_summary": 78000,
                    "product_performance": 3200,
                }
                return dg.MaterializeResult(
                    metadata={
                        "rows_transformed": dg.MetadataValue.int(
                            row_counts.get(node_name, 5000)
                        ),
                        "coalesce_node": dg.MetadataValue.text(node_name),
                        "environment_id": dg.MetadataValue.text(
                            environment_id or "demo_env"
                        ),
                        "mode": dg.MetadataValue.text("demo"),
                    }
                )
            else:
                import requests

                context.log.info(
                    f"Triggering Coalesce run for node '{node_name}' "
                    f"in environment '{environment_id}'"
                )
                response = requests.post(
                    f"{base_url}/environments/{environment_id}/runs",
                    headers={
                        "Authorization": f"Bearer {api_token}",
                        "Content-Type": "application/json",
                    },
                    json={"nodes": [node_name]},
                    timeout=300,
                )
                response.raise_for_status()
                run_data = response.json()
                return dg.MaterializeResult(
                    metadata={
                        "run_id": dg.MetadataValue.text(
                            str(run_data.get("id", "unknown"))
                        ),
                        "status": dg.MetadataValue.text(
                            run_data.get("status", "triggered")
                        ),
                        "coalesce_node": dg.MetadataValue.text(node_name),
                    }
                )

        return coalesce_node_asset

    def build_defs(self, context: dg.ComponentLoadContext) -> dg.Definitions:
        assets = [self._make_asset(node) for node in self.nodes]
        return dg.Definitions(assets=assets)
