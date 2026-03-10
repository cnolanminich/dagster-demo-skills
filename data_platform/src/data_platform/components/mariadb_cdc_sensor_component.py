"""MariaDB CDC GTID sensor component for observing change data capture processes.

This component creates a sensor that monitors a running CDC process that uses
MariaDB GTID-based replication. Instead of running CDC itself, it observes the
CDC process and reports asset observations with metadata about replication position,
tables affected, and lag.
"""

import json
from dataclasses import dataclass, field

import dagster as dg


@dataclass
class MariadbCdcSensorComponent(dg.Component, dg.Resolvable):
    """Sensor that observes a running MariaDB CDC process using GTID tracking.

    Monitors GTID positions and reports asset observations for tables being
    replicated via change data capture. Supports demo mode for local testing.
    """

    demo_mode: bool = False
    mariadb_host: str = "localhost"
    mariadb_port: int = 3306
    mariadb_user: str = "cdc_reader"
    mariadb_password: str = "demo_password"
    cdc_state_table: str = "cdc_metadata.replication_state"
    tracked_tables: list[dict] = field(default_factory=list)
    minimum_interval_seconds: int = 60

    def build_defs(self, context: dg.ComponentLoadContext) -> dg.Definitions:
        if self.demo_mode:
            return self._build_demo_defs()
        return self._build_real_defs()

    def _build_demo_defs(self) -> dg.Definitions:
        tracked = self.tracked_tables
        interval = self.minimum_interval_seconds

        # Define asset specs for each tracked CDC table
        asset_specs = []
        for table_cfg in tracked:
            source_table = table_cfg["source_table"]
            dest_table = table_cfg["destination_table"]
            asset_specs.append(
                dg.AssetSpec(
                    key=dg.AssetKey(["cdc", dest_table]),
                    group_name="mariadb_cdc",
                    kinds={"mariadb", "cdc"},
                    tags={"ingestion_tool": "cdc", "cdc_method": "gtid", "schedule": "sensor"},
                    owners=["team:data-engineering"],
                    description=f"CDC replica of MariaDB table {source_table} via GTID replication",
                )
            )

        @dg.sensor(
            name="mariadb_cdc_gtid_sensor",
            minimum_interval_seconds=interval,
            default_status=dg.DefaultSensorStatus.RUNNING,
            description="Observes MariaDB CDC GTID replication and reports asset observations",
        )
        def cdc_sensor(context: dg.SensorEvaluationContext):
            cursor_state = json.loads(context.cursor) if context.cursor else {}
            previous_gtid = cursor_state.get("last_gtid", "0-0-0")

            # Demo: simulate advancing GTID position
            domain_id, server_id, seq = previous_gtid.split("-")
            new_seq = int(seq) + 157
            new_gtid = f"{domain_id}-{server_id}-{new_seq}"

            observations = []
            for table_cfg in tracked:
                dest_table = table_cfg["destination_table"]
                observations.append(
                    dg.AssetObservation(
                        asset_key=dg.AssetKey(["cdc", dest_table]),
                        metadata={
                            "gtid_position": dg.MetadataValue.text(new_gtid),
                            "rows_replicated": dg.MetadataValue.int(157),
                            "replication_lag_seconds": dg.MetadataValue.float(2.3),
                            "demo_mode": dg.MetadataValue.bool(True),
                        },
                    )
                )

            new_cursor = json.dumps({"last_gtid": new_gtid})
            return dg.SensorResult(
                asset_events=observations,
                cursor=new_cursor,
            )

        return dg.Definitions(
            assets=[*asset_specs],
            sensors=[cdc_sensor],
        )

    def _build_real_defs(self) -> dg.Definitions:
        tracked = self.tracked_tables
        interval = self.minimum_interval_seconds
        host = self.mariadb_host
        port = self.mariadb_port
        user = self.mariadb_user
        password = self.mariadb_password
        state_table = self.cdc_state_table

        asset_specs = []
        for table_cfg in tracked:
            source_table = table_cfg["source_table"]
            dest_table = table_cfg["destination_table"]
            asset_specs.append(
                dg.AssetSpec(
                    key=dg.AssetKey(["cdc", dest_table]),
                    group_name="mariadb_cdc",
                    kinds={"mariadb", "cdc"},
                    tags={"ingestion_tool": "cdc", "cdc_method": "gtid", "schedule": "sensor"},
                    owners=["team:data-engineering"],
                    description=f"CDC replica of MariaDB table {source_table} via GTID replication",
                )
            )

        @dg.sensor(
            name="mariadb_cdc_gtid_sensor",
            minimum_interval_seconds=interval,
            default_status=dg.DefaultSensorStatus.RUNNING,
            description="Observes MariaDB CDC GTID replication and reports asset observations",
        )
        def cdc_sensor(context: dg.SensorEvaluationContext):
            import pymysql

            cursor_state = json.loads(context.cursor) if context.cursor else {}
            previous_gtid = cursor_state.get("last_gtid", "")

            conn = pymysql.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                cursorclass=pymysql.cursors.DictCursor,
            )
            try:
                with conn.cursor() as cur:
                    # Query current GTID position from MariaDB
                    cur.execute("SELECT @@gtid_current_pos AS gtid_pos")
                    current_gtid = cur.fetchone()["gtid_pos"]

                    if current_gtid == previous_gtid:
                        return dg.SkipReason("No new GTID changes detected")

                    # Query CDC state table for per-table replication status
                    state_db, state_tbl = state_table.split(".")
                    cur.execute(f"SELECT * FROM `{state_db}`.`{state_tbl}`")
                    states = {row["table_name"]: row for row in cur.fetchall()}

                    # Check replication lag
                    cur.execute("SHOW SLAVE STATUS")
                    slave_status = cur.fetchone()
                    lag = float(slave_status.get("Seconds_Behind_Master", 0)) if slave_status else 0.0

                observations = []
                for table_cfg in tracked:
                    source_table = table_cfg["source_table"]
                    dest_table = table_cfg["destination_table"]
                    state = states.get(source_table, {})
                    rows_replicated = state.get("rows_applied", 0)

                    observations.append(
                        dg.AssetObservation(
                            asset_key=dg.AssetKey(["cdc", dest_table]),
                            metadata={
                                "gtid_position": dg.MetadataValue.text(current_gtid),
                                "rows_replicated": dg.MetadataValue.int(rows_replicated),
                                "replication_lag_seconds": dg.MetadataValue.float(lag),
                                "source_table": dg.MetadataValue.text(source_table),
                            },
                        )
                    )

                new_cursor = json.dumps({"last_gtid": current_gtid})
                return dg.SensorResult(
                    asset_events=observations,
                    cursor=new_cursor,
                )
            finally:
                conn.close()

        return dg.Definitions(
            assets=[*asset_specs],
            sensors=[cdc_sensor],
        )
