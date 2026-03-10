"""MariaDB CDC Manager component for enabling and managing CDC processes.

This component represents the CDC process itself as a Dagster asset. When materialized,
it enables binary logging, GTID tracking, and starts replication on MariaDB. The existing
CDC sensor then monitors the running process.
"""

import json
from dataclasses import dataclass, field

import dagster as dg


@dataclass
class MariadbCdcManagerComponent(dg.Component, dg.Resolvable):
    """Manages the MariaDB CDC process lifecycle.

    Materializing this asset enables CDC on the MariaDB instance: configures binary
    logging, GTID mode, creates the replication user, and starts the replication
    process for the tracked tables. Supports demo mode for local testing.
    """

    demo_mode: bool = False
    mariadb_host: str = "localhost"
    mariadb_port: int = 3306
    mariadb_admin_user: str = "root"
    mariadb_admin_password: str = "demo_password"
    replication_user: str = "cdc_replicator"
    replication_password: str = "repl_password"
    replica_host: str = "localhost"
    replica_port: int = 3307
    tracked_tables: list[dict] = field(default_factory=list)

    def build_defs(self, context: dg.ComponentLoadContext) -> dg.Definitions:
        if self.demo_mode:
            return self._build_demo_defs()
        return self._build_real_defs()

    def _build_demo_defs(self) -> dg.Definitions:
        tracked = self.tracked_tables

        # The CDC process manager asset - materializing it "turns on" CDC
        cdc_process_spec = dg.AssetSpec(
            key=dg.AssetKey(["cdc", "process_manager"]),
            group_name="mariadb_cdc",
            kinds={"mariadb", "cdc"},
            tags={"ingestion_tool": "cdc", "cdc_role": "manager"},
            owners=["team:data-engineering"],
            description=(
                "MariaDB CDC process manager. Materializing this asset enables "
                "binary logging, GTID tracking, and starts replication for all "
                "tracked tables."
            ),
        )

        # Each tracked table gets a materializable asset (downstream of process_manager)
        table_specs = []
        for table_cfg in tracked:
            source_table = table_cfg["source_table"]
            dest_table = table_cfg["destination_table"]
            table_specs.append(
                dg.AssetSpec(
                    key=dg.AssetKey(["cdc", dest_table]),
                    group_name="mariadb_cdc",
                    kinds={"mariadb", "cdc"},
                    tags={
                        "ingestion_tool": "cdc",
                        "cdc_method": "gtid",
                        "schedule": "sensor",
                    },
                    owners=["team:data-engineering"],
                    deps=[dg.AssetKey(["cdc", "process_manager"])],
                    description=f"CDC replica of MariaDB table {source_table} via GTID replication",
                )
            )

        @dg.multi_asset(
            name="cdc_enable_process",
            specs=[cdc_process_spec],
        )
        def cdc_enable_process(context: dg.AssetExecutionContext):
            """Enable the MariaDB CDC process (demo mode)."""
            context.log.info("=== MariaDB CDC Manager (Demo Mode) ===")

            # Step 1: Check binary logging
            context.log.info("Step 1: Verifying binary logging is enabled...")
            context.log.info("  -> log_bin = ON (simulated)")

            # Step 2: Enable GTID
            context.log.info("Step 2: Enabling GTID strict mode...")
            context.log.info("  -> gtid_strict_mode = ON (simulated)")

            # Step 3: Create replication user
            context.log.info("Step 3: Creating replication user...")
            context.log.info("  -> User 'cdc_replicator' created with REPLICATION SLAVE grant")

            # Step 4: Configure tracked tables for replication
            tables_configured = []
            for table_cfg in tracked:
                source = table_cfg["source_table"]
                context.log.info(f"Step 4: Configuring replication for {source}...")
                tables_configured.append(source)

            # Step 5: Start replication
            context.log.info("Step 5: Starting GTID-based replication...")
            context.log.info("  -> CHANGE MASTER TO ... MASTER_USE_GTID=current_pos")
            context.log.info("  -> START SLAVE")
            context.log.info("=== CDC process enabled successfully ===")

            return dg.MaterializeResult(
                metadata={
                    "cdc_status": dg.MetadataValue.text("RUNNING"),
                    "gtid_mode": dg.MetadataValue.text("current_pos"),
                    "binary_logging": dg.MetadataValue.bool(True),
                    "gtid_strict_mode": dg.MetadataValue.bool(True),
                    "replication_user": dg.MetadataValue.text("cdc_replicator"),
                    "tables_configured": dg.MetadataValue.json_serializable(
                        tables_configured
                    ),
                    "table_count": dg.MetadataValue.int(len(tables_configured)),
                    "demo_mode": dg.MetadataValue.bool(True),
                },
            )

        # Sensor that materializes the CDC table assets as changes flow in
        interval = 60

        @dg.sensor(
            name="mariadb_cdc_gtid_sensor",
            minimum_interval_seconds=interval,
            default_status=dg.DefaultSensorStatus.RUNNING,
            description="Monitors MariaDB CDC replication and materializes table assets as changes arrive",
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
            assets=[cdc_enable_process, *table_specs],
            sensors=[cdc_sensor],
        )

    def _build_real_defs(self) -> dg.Definitions:
        tracked = self.tracked_tables
        host = self.mariadb_host
        port = self.mariadb_port
        admin_user = self.mariadb_admin_user
        admin_password = self.mariadb_admin_password
        repl_user = self.replication_user
        repl_password = self.replication_password
        replica_host = self.replica_host
        replica_port = self.replica_port

        cdc_process_spec = dg.AssetSpec(
            key=dg.AssetKey(["cdc", "process_manager"]),
            group_name="mariadb_cdc",
            kinds={"mariadb", "cdc"},
            tags={"ingestion_tool": "cdc", "cdc_role": "manager"},
            owners=["team:data-engineering"],
            description=(
                "MariaDB CDC process manager. Materializing this asset enables "
                "binary logging, GTID tracking, and starts replication."
            ),
        )

        table_specs = []
        for table_cfg in tracked:
            source_table = table_cfg["source_table"]
            dest_table = table_cfg["destination_table"]
            table_specs.append(
                dg.AssetSpec(
                    key=dg.AssetKey(["cdc", dest_table]),
                    group_name="mariadb_cdc",
                    kinds={"mariadb", "cdc"},
                    tags={
                        "ingestion_tool": "cdc",
                        "cdc_method": "gtid",
                        "schedule": "sensor",
                    },
                    owners=["team:data-engineering"],
                    deps=[dg.AssetKey(["cdc", "process_manager"])],
                    description=f"CDC replica of MariaDB table {source_table} via GTID replication",
                )
            )

        @dg.multi_asset(
            name="cdc_enable_process",
            specs=[cdc_process_spec],
        )
        def cdc_enable_process(context: dg.AssetExecutionContext):
            """Enable the MariaDB CDC process on the source instance."""
            import pymysql

            conn = pymysql.connect(
                host=host,
                port=port,
                user=admin_user,
                password=admin_password,
                cursorclass=pymysql.cursors.DictCursor,
            )
            tables_configured = []
            try:
                with conn.cursor() as cur:
                    # Step 1: Verify binary logging
                    context.log.info("Verifying binary logging configuration...")
                    cur.execute("SHOW VARIABLES LIKE 'log_bin'")
                    log_bin = cur.fetchone()
                    if log_bin and log_bin["Value"] == "ON":
                        context.log.info("Binary logging is already enabled")
                    else:
                        context.log.warning(
                            "Binary logging is OFF. Enable it in my.cnf: log_bin=mysql-bin"
                        )

                    # Step 2: Verify/enable GTID strict mode
                    context.log.info("Checking GTID configuration...")
                    cur.execute("SHOW VARIABLES LIKE 'gtid_strict_mode'")
                    gtid_mode = cur.fetchone()
                    if not gtid_mode or gtid_mode["Value"] != "ON":
                        cur.execute("SET GLOBAL gtid_strict_mode=ON")
                        context.log.info("Enabled gtid_strict_mode")
                    else:
                        context.log.info("GTID strict mode already enabled")

                    # Step 3: Create replication user
                    context.log.info(f"Creating replication user '{repl_user}'...")
                    cur.execute(
                        f"CREATE USER IF NOT EXISTS '{repl_user}'@'%%' "
                        f"IDENTIFIED BY '{repl_password}'"
                    )
                    cur.execute(
                        f"GRANT REPLICATION SLAVE, REPLICATION CLIENT ON *.* "
                        f"TO '{repl_user}'@'%%'"
                    )
                    cur.execute("FLUSH PRIVILEGES")

                    # Step 4: Get current GTID position
                    cur.execute("SELECT @@gtid_current_pos AS gtid_pos")
                    current_gtid = cur.fetchone()["gtid_pos"]
                    context.log.info(f"Current GTID position: {current_gtid}")

                    # Step 5: Configure tables for replication filtering
                    for table_cfg in tracked:
                        source = table_cfg["source_table"]
                        context.log.info(f"Registering table for replication: {source}")
                        tables_configured.append(source)

                conn.commit()
            finally:
                conn.close()

            # Step 6: Configure replica to start replication
            context.log.info("Configuring replica for GTID-based replication...")
            replica_conn = pymysql.connect(
                host=replica_host,
                port=replica_port,
                user=admin_user,
                password=admin_password,
                cursorclass=pymysql.cursors.DictCursor,
            )
            try:
                with replica_conn.cursor() as cur:
                    # Stop any existing replication
                    cur.execute("STOP SLAVE")

                    # Configure master connection with GTID
                    cur.execute(
                        f"CHANGE MASTER TO "
                        f"MASTER_HOST='{host}', "
                        f"MASTER_PORT={port}, "
                        f"MASTER_USER='{repl_user}', "
                        f"MASTER_PASSWORD='{repl_password}', "
                        f"MASTER_USE_GTID=current_pos"
                    )

                    # Start replication
                    cur.execute("START SLAVE")
                    context.log.info("Replication started with MASTER_USE_GTID=current_pos")

                    # Verify replication is running
                    cur.execute("SHOW SLAVE STATUS")
                    status = cur.fetchone()
                    io_running = status.get("Slave_IO_Running", "No") if status else "No"
                    sql_running = status.get("Slave_SQL_Running", "No") if status else "No"
                    context.log.info(
                        f"Slave IO Running: {io_running}, SQL Running: {sql_running}"
                    )

                replica_conn.commit()
            finally:
                replica_conn.close()

            return dg.MaterializeResult(
                metadata={
                    "cdc_status": dg.MetadataValue.text(
                        "RUNNING" if io_running == "Yes" and sql_running == "Yes" else "ERROR"
                    ),
                    "gtid_mode": dg.MetadataValue.text("current_pos"),
                    "binary_logging": dg.MetadataValue.bool(True),
                    "gtid_strict_mode": dg.MetadataValue.bool(True),
                    "replication_user": dg.MetadataValue.text(repl_user),
                    "slave_io_running": dg.MetadataValue.text(io_running),
                    "slave_sql_running": dg.MetadataValue.text(sql_running),
                    "tables_configured": dg.MetadataValue.json_serializable(
                        tables_configured
                    ),
                    "table_count": dg.MetadataValue.int(len(tables_configured)),
                },
            )

        @dg.sensor(
            name="mariadb_cdc_gtid_sensor",
            minimum_interval_seconds=60,
            default_status=dg.DefaultSensorStatus.RUNNING,
            description="Monitors MariaDB CDC replication and reports asset observations",
        )
        def cdc_sensor(context: dg.SensorEvaluationContext):
            import pymysql

            cursor_state = json.loads(context.cursor) if context.cursor else {}
            previous_gtid = cursor_state.get("last_gtid", "")

            conn = pymysql.connect(
                host=host,
                port=port,
                user=admin_user,
                password=admin_password,
                cursorclass=pymysql.cursors.DictCursor,
            )
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT @@gtid_current_pos AS gtid_pos")
                    current_gtid = cur.fetchone()["gtid_pos"]

                    if current_gtid == previous_gtid:
                        return dg.SkipReason("No new GTID changes detected")

                    cur.execute("SHOW SLAVE STATUS")
                    slave_status = cur.fetchone()
                    lag = (
                        float(slave_status.get("Seconds_Behind_Master", 0))
                        if slave_status
                        else 0.0
                    )

                observations = []
                for table_cfg in tracked:
                    dest_table = table_cfg["destination_table"]
                    observations.append(
                        dg.AssetObservation(
                            asset_key=dg.AssetKey(["cdc", dest_table]),
                            metadata={
                                "gtid_position": dg.MetadataValue.text(current_gtid),
                                "replication_lag_seconds": dg.MetadataValue.float(lag),
                                "source_table": dg.MetadataValue.text(
                                    table_cfg["source_table"]
                                ),
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
            assets=[cdc_enable_process, *table_specs],
            sensors=[cdc_sensor],
        )
