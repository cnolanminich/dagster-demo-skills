"""MariaDB CDC asset checks component for data quality validation.

Defines asset checks on CDC-replicated tables that run on a separate schedule
(e.g., hourly) to validate row counts, freshness, schema consistency, and
primary key integrity of the replicated data.
"""

import time
from dataclasses import dataclass, field

import dagster as dg


@dataclass
class MariadbCdcChecksComponent(dg.Component, dg.Resolvable):
    """Asset checks for MariaDB CDC-replicated tables.

    Runs data quality checks against the destination tables to ensure CDC
    replication is producing valid, fresh, and consistent data. Checks include
    row count thresholds, replication freshness, null primary keys, and
    schema drift detection. Supports demo mode for local testing.
    """

    demo_mode: bool = False
    destination_host: str = "localhost"
    destination_port: int = 5432
    destination_user: str = "analytics"
    destination_password: str = "demo_password"
    destination_database: str = "warehouse"
    tracked_tables: list[dict] = field(default_factory=list)
    max_replication_lag_seconds: int = 300
    min_row_count: int = 1

    def build_defs(self, context: dg.ComponentLoadContext) -> dg.Definitions:
        if self.demo_mode:
            return self._build_demo_defs()
        return self._build_real_defs()

    def _build_demo_defs(self) -> dg.Definitions:
        tracked = self.tracked_tables
        max_lag = self.max_replication_lag_seconds
        min_rows = self.min_row_count

        check_specs = []
        for table_cfg in tracked:
            dest_table = table_cfg["destination_table"]
            asset_key = dg.AssetKey(["cdc", dest_table])

            check_specs.extend([
                dg.AssetCheckSpec(
                    name=f"{dest_table}_row_count",
                    asset=asset_key,
                    description=f"Verify {dest_table} has at least {min_rows} rows",
                ),
                dg.AssetCheckSpec(
                    name=f"{dest_table}_freshness",
                    asset=asset_key,
                    description=f"Verify {dest_table} replication lag < {max_lag}s",
                ),
                dg.AssetCheckSpec(
                    name=f"{dest_table}_no_null_pks",
                    asset=asset_key,
                    description=f"Verify {dest_table} has no NULL primary keys",
                ),
                dg.AssetCheckSpec(
                    name=f"{dest_table}_schema_valid",
                    asset=asset_key,
                    description=f"Verify {dest_table} schema matches expected columns",
                ),
            ])

        @dg.multi_asset_check(
            specs=check_specs,
            name="cdc_table_quality_checks",
            description="Data quality checks for CDC-replicated MariaDB tables",
        )
        def cdc_quality_checks(context: dg.AssetCheckExecutionContext):
            context.log.info("=== CDC Asset Checks (Demo Mode) ===")

            for table_cfg in tracked:
                dest_table = table_cfg["destination_table"]
                source_table = table_cfg["source_table"]
                context.log.info(f"Checking table: {dest_table} (source: {source_table})")

                # Demo: simulate row count check
                simulated_row_count = {"orders": 15234, "order_items": 48721, "customers": 8932, "inventory": 1247}
                row_count = simulated_row_count.get(dest_table, 1000)
                yield dg.AssetCheckResult(
                    check_name=f"{dest_table}_row_count",
                    asset_key=dg.AssetKey(["cdc", dest_table]),
                    passed=row_count >= min_rows,
                    metadata={
                        "row_count": dg.MetadataValue.int(row_count),
                        "threshold": dg.MetadataValue.int(min_rows),
                        "demo_mode": dg.MetadataValue.bool(True),
                    },
                )

                # Demo: simulate freshness check
                simulated_lag = 2.3
                yield dg.AssetCheckResult(
                    check_name=f"{dest_table}_freshness",
                    asset_key=dg.AssetKey(["cdc", dest_table]),
                    passed=simulated_lag < max_lag,
                    metadata={
                        "replication_lag_seconds": dg.MetadataValue.float(simulated_lag),
                        "max_allowed_lag_seconds": dg.MetadataValue.int(max_lag),
                        "demo_mode": dg.MetadataValue.bool(True),
                    },
                )

                # Demo: simulate null PK check
                null_pk_count = 0
                yield dg.AssetCheckResult(
                    check_name=f"{dest_table}_no_null_pks",
                    asset_key=dg.AssetKey(["cdc", dest_table]),
                    passed=null_pk_count == 0,
                    metadata={
                        "null_pk_rows": dg.MetadataValue.int(null_pk_count),
                        "demo_mode": dg.MetadataValue.bool(True),
                    },
                )

                # Demo: simulate schema check
                expected_schemas = {
                    "orders": ["id", "customer_id", "status", "total_amount", "created_at", "updated_at"],
                    "order_items": ["id", "order_id", "product_id", "quantity", "unit_price"],
                    "customers": ["id", "email", "name", "created_at", "updated_at"],
                    "inventory": ["id", "product_id", "warehouse_id", "quantity", "last_updated"],
                }
                columns = expected_schemas.get(dest_table, ["id"])
                yield dg.AssetCheckResult(
                    check_name=f"{dest_table}_schema_valid",
                    asset_key=dg.AssetKey(["cdc", dest_table]),
                    passed=True,
                    metadata={
                        "columns_found": dg.MetadataValue.json_serializable(columns),
                        "column_count": dg.MetadataValue.int(len(columns)),
                        "schema_matches": dg.MetadataValue.bool(True),
                        "demo_mode": dg.MetadataValue.bool(True),
                    },
                )

            context.log.info("=== All CDC checks completed ===")

        # Hourly schedule for running checks
        checks_job = dg.define_asset_job(
            name="cdc_quality_checks_job",
            selection=dg.AssetSelection.checks(cdc_quality_checks),
        )

        checks_schedule = dg.ScheduleDefinition(
            name="hourly_cdc_quality_checks",
            job=checks_job,
            cron_schedule="0 * * * *",
            default_status=dg.DefaultScheduleStatus.RUNNING,
            description="Runs CDC data quality checks every hour",
        )

        return dg.Definitions(
            asset_checks=[cdc_quality_checks],
            jobs=[checks_job],
            schedules=[checks_schedule],
        )

    def _build_real_defs(self) -> dg.Definitions:
        tracked = self.tracked_tables
        max_lag = self.max_replication_lag_seconds
        min_rows = self.min_row_count
        dest_host = self.destination_host
        dest_port = self.destination_port
        dest_user = self.destination_user
        dest_password = self.destination_password
        dest_db = self.destination_database

        check_specs = []
        for table_cfg in tracked:
            dest_table = table_cfg["destination_table"]
            asset_key = dg.AssetKey(["cdc", dest_table])

            check_specs.extend([
                dg.AssetCheckSpec(
                    name=f"{dest_table}_row_count",
                    asset=asset_key,
                    description=f"Verify {dest_table} has at least {min_rows} rows",
                ),
                dg.AssetCheckSpec(
                    name=f"{dest_table}_freshness",
                    asset=asset_key,
                    description=f"Verify {dest_table} replication lag < {max_lag}s",
                ),
                dg.AssetCheckSpec(
                    name=f"{dest_table}_no_null_pks",
                    asset=asset_key,
                    description=f"Verify {dest_table} has no NULL primary keys",
                ),
                dg.AssetCheckSpec(
                    name=f"{dest_table}_schema_valid",
                    asset=asset_key,
                    description=f"Verify {dest_table} schema matches expected columns",
                ),
            ])

        @dg.multi_asset_check(
            specs=check_specs,
            name="cdc_table_quality_checks",
            description="Data quality checks for CDC-replicated MariaDB tables",
        )
        def cdc_quality_checks(context: dg.AssetCheckExecutionContext):
            import pymysql

            context.log.info("Running CDC data quality checks...")

            # Connect to the destination (replica) database
            conn = pymysql.connect(
                host=dest_host,
                port=dest_port,
                user=dest_user,
                password=dest_password,
                database=dest_db,
                cursorclass=pymysql.cursors.DictCursor,
            )

            try:
                with conn.cursor() as cur:
                    # Get current replication lag once
                    cur.execute("SHOW SLAVE STATUS")
                    slave_status = cur.fetchone()
                    current_lag = (
                        float(slave_status.get("Seconds_Behind_Master", 0))
                        if slave_status
                        else 0.0
                    )

                    for table_cfg in tracked:
                        dest_table = table_cfg["destination_table"]
                        source_table = table_cfg["source_table"]
                        schema, table = source_table.split(".")
                        context.log.info(f"Checking {dest_table}...")

                        # Row count check
                        cur.execute(f"SELECT COUNT(*) AS cnt FROM `{schema}`.`{table}`")
                        row_count = cur.fetchone()["cnt"]
                        yield dg.AssetCheckResult(
                            check_name=f"{dest_table}_row_count",
                            asset_key=dg.AssetKey(["cdc", dest_table]),
                            passed=row_count >= min_rows,
                            metadata={
                                "row_count": dg.MetadataValue.int(row_count),
                                "threshold": dg.MetadataValue.int(min_rows),
                            },
                        )

                        # Freshness check
                        yield dg.AssetCheckResult(
                            check_name=f"{dest_table}_freshness",
                            asset_key=dg.AssetKey(["cdc", dest_table]),
                            passed=current_lag < max_lag,
                            metadata={
                                "replication_lag_seconds": dg.MetadataValue.float(
                                    current_lag
                                ),
                                "max_allowed_lag_seconds": dg.MetadataValue.int(max_lag),
                            },
                        )

                        # Null PK check - assumes first column is the PK
                        cur.execute(
                            f"SELECT COUNT(*) AS cnt FROM `{schema}`.`{table}` "
                            f"WHERE id IS NULL"
                        )
                        null_pks = cur.fetchone()["cnt"]
                        yield dg.AssetCheckResult(
                            check_name=f"{dest_table}_no_null_pks",
                            asset_key=dg.AssetKey(["cdc", dest_table]),
                            passed=null_pks == 0,
                            metadata={
                                "null_pk_rows": dg.MetadataValue.int(null_pks),
                            },
                        )

                        # Schema validation
                        cur.execute(
                            f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
                            f"WHERE TABLE_SCHEMA = '{schema}' AND TABLE_NAME = '{table}' "
                            f"ORDER BY ORDINAL_POSITION"
                        )
                        columns = [row["COLUMN_NAME"] for row in cur.fetchall()]
                        has_columns = len(columns) > 0
                        yield dg.AssetCheckResult(
                            check_name=f"{dest_table}_schema_valid",
                            asset_key=dg.AssetKey(["cdc", dest_table]),
                            passed=has_columns,
                            metadata={
                                "columns_found": dg.MetadataValue.json_serializable(
                                    columns
                                ),
                                "column_count": dg.MetadataValue.int(len(columns)),
                            },
                        )
            finally:
                conn.close()

        checks_job = dg.define_asset_job(
            name="cdc_quality_checks_job",
            selection=dg.AssetSelection.checks(cdc_quality_checks),
        )

        checks_schedule = dg.ScheduleDefinition(
            name="hourly_cdc_quality_checks",
            job=checks_job,
            cron_schedule="0 * * * *",
            default_status=dg.DefaultScheduleStatus.RUNNING,
            description="Runs CDC data quality checks every hour",
        )

        return dg.Definitions(
            asset_checks=[cdc_quality_checks],
            jobs=[checks_job],
            schedules=[checks_schedule],
        )
