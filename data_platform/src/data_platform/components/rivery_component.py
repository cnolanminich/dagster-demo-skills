"""Rivery ingestion component with sync-and-poll support.

Triggers Rivery river runs and polls for completion before reporting success.
In real mode, calls the Rivery REST API to trigger a run and polls the run
status endpoint until the river finishes or fails.
"""

import random
from dataclasses import dataclass, field

import dagster as dg


@dataclass
class RiveryComponent(dg.Component, dg.Resolvable):
    """Loads data from source systems via Rivery rivers (ELT pipelines).

    Rivery is a SaaS ELT platform that connects to various data sources and
    loads data into cloud warehouses. This component triggers river runs and
    polls for completion (sync-and-poll), so materializations only succeed
    when the river finishes successfully.
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
            run_id = f"demo-run-{random.randint(10000, 99999)}"
            rows_synced = random.randint(5000, 50000)
            duration_seconds = random.randint(12, 90)

            context.log.info(f"[DEMO] Triggering Rivery river '{river_name}' sync to {destination_table}")
            context.log.info(f"[DEMO] Run started: {run_id}")
            context.log.info(f"[DEMO] Polling for completion...")
            context.log.info(f"[DEMO] River '{river_name}' run {run_id}: running ({duration_seconds // 3}s elapsed)")
            context.log.info(f"[DEMO] River '{river_name}' run {run_id}: running ({duration_seconds * 2 // 3}s elapsed)")
            context.log.info(f"[DEMO] River '{river_name}' run {run_id}: done ({duration_seconds}s elapsed)")
            context.log.info(f"[DEMO] Completed: {rows_synced} rows in {duration_seconds}s")

            return dg.MaterializeResult(
                metadata={
                    "run_id": dg.MetadataValue.text(run_id),
                    "river_name": dg.MetadataValue.text(river_name),
                    "status": dg.MetadataValue.text("done"),
                    "rows_synced": dg.MetadataValue.int(rows_synced),
                    "duration_seconds": dg.MetadataValue.int(duration_seconds),
                    "destination": dg.MetadataValue.text(destination_table),
                    "demo_mode": dg.MetadataValue.bool(True),
                }
            )

        return _rivery_asset

    @staticmethod
    def _make_real_river_asset(river_name: str, river_id: str, destination_table: str,
                               source_type: str, api_token: str, account_id: str,
                               poll_interval_seconds: int = 15, poll_timeout_seconds: int = 3600):
        asset_key = dg.AssetKey(["rivery", destination_table])
        base_url = f"https://api.rivery.io/v1/accounts/{account_id}"

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
            import time

            import requests

            headers = {"Authorization": f"Bearer {api_token}"}

            # Step 1: Trigger the river run
            context.log.info(f"Triggering Rivery river '{river_name}' (ID: {river_id})")
            resp = requests.post(
                f"{base_url}/rivers/{river_id}/run",
                headers=headers,
                timeout=30,
            )
            resp.raise_for_status()
            run_id = resp.json().get("run_id", "unknown")
            context.log.info(f"Rivery run started: {run_id}")

            # Step 2: Poll for completion
            start_time = time.time()
            status = "running"
            while status in ("running", "pending"):
                elapsed = time.time() - start_time
                if elapsed > poll_timeout_seconds:
                    raise TimeoutError(
                        f"Rivery river '{river_name}' run {run_id} timed out "
                        f"after {poll_timeout_seconds}s"
                    )

                time.sleep(poll_interval_seconds)

                poll_resp = requests.get(
                    f"{base_url}/rivers/{river_id}/runs/{run_id}",
                    headers=headers,
                    timeout=30,
                )
                poll_resp.raise_for_status()
                run_data = poll_resp.json()
                status = run_data.get("status", "unknown")
                context.log.info(
                    f"River '{river_name}' run {run_id}: {status} "
                    f"({int(elapsed)}s elapsed)"
                )

            if status == "error":
                error_msg = run_data.get("error_message", "Unknown error")
                raise RuntimeError(
                    f"Rivery river '{river_name}' run {run_id} failed: {error_msg}"
                )

            rows_synced = run_data.get("rows_synced", 0)
            duration_seconds = int(time.time() - start_time)
            context.log.info(
                f"River '{river_name}' completed: {rows_synced} rows in {duration_seconds}s"
            )

            return dg.MaterializeResult(
                metadata={
                    "run_id": dg.MetadataValue.text(run_id),
                    "river_name": dg.MetadataValue.text(river_name),
                    "status": dg.MetadataValue.text(status),
                    "rows_synced": dg.MetadataValue.int(rows_synced),
                    "duration_seconds": dg.MetadataValue.int(duration_seconds),
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
