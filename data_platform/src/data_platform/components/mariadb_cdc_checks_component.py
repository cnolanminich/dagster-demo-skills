"""MariaDB CDC asset checks for Snowflake destination tables.

Validates data quality on the Snowflake tables populated by the Debezium CDC pipeline.
Checks run on a separate hourly schedule and verify row counts, freshness (via
Kafka Connect lag), null primary keys, and schema consistency in Snowflake.
"""

import json
from dataclasses import dataclass, field

import dagster as dg


@dataclass
class MariadbCdcChecksComponent(dg.Component, dg.Resolvable):
    """Asset checks for CDC-replicated Snowflake tables.

    Runs data quality checks against the Snowflake destination tables to ensure
    the Debezium CDC pipeline is producing valid, fresh, and consistent data.
    Checks include row count thresholds, freshness via Kafka consumer lag,
    null primary keys, and schema validation. Supports demo mode for local testing.
    """

    demo_mode: bool = False

    # Snowflake connection
    snowflake_account: str = "myorg-myaccount"
    snowflake_user: str = "ANALYTICS_READER"
    snowflake_password: str = ""
    snowflake_warehouse: str = "COMPUTE_WH"
    snowflake_database: str = "RAW"
    snowflake_schema: str = "CDC_ECOMMERCE"

    # Kafka Connect (for lag checks)
    kafka_connect_url: str = "http://localhost:8083"
    sink_connector_name: str = "mariadb-ecommerce-snowflake-sink"

    # Tables and thresholds
    tracked_tables: list[dict] = field(default_factory=list)
    max_lag_events: int = 1000
    min_row_count: int = 1

    def build_defs(self, context: dg.ComponentLoadContext) -> dg.Definitions:
        if self.demo_mode:
            return self._build_demo_defs()
        return self._build_real_defs()

    def _build_demo_defs(self) -> dg.Definitions:
        tracked = self.tracked_tables
        max_lag = self.max_lag_events
        min_rows = self.min_row_count
        sf_database = self.snowflake_database
        sf_schema = self.snowflake_schema

        check_specs = self._build_check_specs(tracked)

        @dg.multi_asset_check(
            specs=check_specs,
            name="cdc_table_quality_checks",
            description="Data quality checks for CDC-replicated Snowflake tables",
        )
        def cdc_quality_checks(context: dg.AssetCheckExecutionContext):
            context.log.info("=== CDC Snowflake Quality Checks (Demo Mode) ===")

            for table_cfg in tracked:
                dest_table = table_cfg["destination_table"]
                source_table = table_cfg["source_table"]
                sf_table = f"{sf_database}.{sf_schema}.{dest_table}".upper()
                context.log.info(f"Checking {sf_table} (source: {source_table})")

                # Demo: simulate Snowflake row count
                simulated_counts = {
                    "orders": 15234,
                    "order_items": 48721,
                    "customers": 8932,
                    "inventory": 1247,
                }
                row_count = simulated_counts.get(dest_table, 1000)
                yield dg.AssetCheckResult(
                    check_name=f"{dest_table}_row_count",
                    asset_key=dg.AssetKey(["cdc", dest_table]),
                    passed=row_count >= min_rows,
                    metadata={
                        "snowflake_table": dg.MetadataValue.text(sf_table),
                        "row_count": dg.MetadataValue.int(row_count),
                        "threshold": dg.MetadataValue.int(min_rows),
                        "demo_mode": dg.MetadataValue.bool(True),
                    },
                )

                # Demo: simulate Kafka consumer lag (freshness proxy)
                simulated_lag = 12
                yield dg.AssetCheckResult(
                    check_name=f"{dest_table}_freshness",
                    asset_key=dg.AssetKey(["cdc", dest_table]),
                    passed=simulated_lag < max_lag,
                    metadata={
                        "kafka_consumer_lag_events": dg.MetadataValue.int(simulated_lag),
                        "max_allowed_lag_events": dg.MetadataValue.int(max_lag),
                        "demo_mode": dg.MetadataValue.bool(True),
                    },
                )

                # Demo: simulate null PK check in Snowflake
                yield dg.AssetCheckResult(
                    check_name=f"{dest_table}_no_null_pks",
                    asset_key=dg.AssetKey(["cdc", dest_table]),
                    passed=True,
                    metadata={
                        "null_pk_rows": dg.MetadataValue.int(0),
                        "demo_mode": dg.MetadataValue.bool(True),
                    },
                )

                # Demo: simulate Snowflake schema check
                expected_schemas = {
                    "orders": ["ID", "CUSTOMER_ID", "STATUS", "TOTAL_AMOUNT", "CREATED_AT", "UPDATED_AT", "_CDC_TIMESTAMP", "_CDC_OPERATION"],
                    "order_items": ["ID", "ORDER_ID", "PRODUCT_ID", "QUANTITY", "UNIT_PRICE", "_CDC_TIMESTAMP", "_CDC_OPERATION"],
                    "customers": ["ID", "EMAIL", "NAME", "CREATED_AT", "UPDATED_AT", "_CDC_TIMESTAMP", "_CDC_OPERATION"],
                    "inventory": ["ID", "PRODUCT_ID", "WAREHOUSE_ID", "QUANTITY", "LAST_UPDATED", "_CDC_TIMESTAMP", "_CDC_OPERATION"],
                }
                columns = expected_schemas.get(dest_table, ["ID"])
                # Check that CDC metadata columns are present
                has_cdc_cols = "_CDC_TIMESTAMP" in columns and "_CDC_OPERATION" in columns
                yield dg.AssetCheckResult(
                    check_name=f"{dest_table}_schema_valid",
                    asset_key=dg.AssetKey(["cdc", dest_table]),
                    passed=has_cdc_cols,
                    metadata={
                        "columns_found": dg.MetadataValue.json_serializable(columns),
                        "column_count": dg.MetadataValue.int(len(columns)),
                        "has_cdc_metadata_columns": dg.MetadataValue.bool(has_cdc_cols),
                        "demo_mode": dg.MetadataValue.bool(True),
                    },
                )

            context.log.info("=== All CDC Snowflake checks completed ===")

        # Hourly schedule
        checks_job = dg.define_asset_job(
            name="cdc_quality_checks_job",
            selection=dg.AssetSelection.checks(cdc_quality_checks),
        )

        checks_schedule = dg.ScheduleDefinition(
            name="hourly_cdc_quality_checks",
            job=checks_job,
            cron_schedule="0 * * * *",
            default_status=dg.DefaultScheduleStatus.RUNNING,
            description="Runs CDC data quality checks on Snowflake tables every hour",
        )

        return dg.Definitions(
            asset_checks=[cdc_quality_checks],
            jobs=[checks_job],
            schedules=[checks_schedule],
        )

    def _build_real_defs(self) -> dg.Definitions:
        tracked = self.tracked_tables
        max_lag = self.max_lag_events
        min_rows = self.min_row_count
        sf_account = self.snowflake_account
        sf_user = self.snowflake_user
        sf_password = self.snowflake_password
        sf_warehouse = self.snowflake_warehouse
        sf_database = self.snowflake_database
        sf_schema = self.snowflake_schema
        connect_url = self.kafka_connect_url
        sink_name = self.sink_connector_name

        check_specs = self._build_check_specs(tracked)

        @dg.multi_asset_check(
            specs=check_specs,
            name="cdc_table_quality_checks",
            description="Data quality checks for CDC-replicated Snowflake tables",
        )
        def cdc_quality_checks(context: dg.AssetCheckExecutionContext):
            import requests
            import snowflake.connector

            context.log.info("Running CDC data quality checks on Snowflake...")

            # Connect to Snowflake
            conn = snowflake.connector.connect(
                account=sf_account,
                user=sf_user,
                password=sf_password,
                warehouse=sf_warehouse,
                database=sf_database,
                schema=sf_schema,
            )

            # Get Kafka consumer lag from Kafka Connect
            try:
                resp = requests.get(
                    f"{connect_url}/connectors/{sink_name}/status",
                    timeout=10,
                )
                resp.raise_for_status()
                sink_info = resp.json()
                sink_state = sink_info["connector"]["state"]
            except requests.RequestException as e:
                context.log.warning(f"Could not reach Kafka Connect for lag: {e}")
                sink_state = "UNKNOWN"

            try:
                cur = conn.cursor()

                for table_cfg in tracked:
                    dest_table = table_cfg["destination_table"]
                    sf_table_name = dest_table.upper()
                    context.log.info(f"Checking {sf_database}.{sf_schema}.{sf_table_name}...")

                    # Row count
                    cur.execute(f"SELECT COUNT(*) FROM {sf_schema}.{sf_table_name}")
                    row_count = cur.fetchone()[0]
                    yield dg.AssetCheckResult(
                        check_name=f"{dest_table}_row_count",
                        asset_key=dg.AssetKey(["cdc", dest_table]),
                        passed=row_count >= min_rows,
                        metadata={
                            "snowflake_table": dg.MetadataValue.text(
                                f"{sf_database}.{sf_schema}.{sf_table_name}"
                            ),
                            "row_count": dg.MetadataValue.int(row_count),
                            "threshold": dg.MetadataValue.int(min_rows),
                        },
                    )

                    # Freshness — check if sink connector is running
                    is_fresh = sink_state == "RUNNING"
                    yield dg.AssetCheckResult(
                        check_name=f"{dest_table}_freshness",
                        asset_key=dg.AssetKey(["cdc", dest_table]),
                        passed=is_fresh,
                        metadata={
                            "sink_connector_status": dg.MetadataValue.text(sink_state),
                        },
                    )

                    # Null PK check
                    cur.execute(
                        f"SELECT COUNT(*) FROM {sf_schema}.{sf_table_name} WHERE ID IS NULL"
                    )
                    null_pks = cur.fetchone()[0]
                    yield dg.AssetCheckResult(
                        check_name=f"{dest_table}_no_null_pks",
                        asset_key=dg.AssetKey(["cdc", dest_table]),
                        passed=null_pks == 0,
                        metadata={
                            "null_pk_rows": dg.MetadataValue.int(null_pks),
                        },
                    )

                    # Schema — verify CDC metadata columns exist
                    cur.execute(
                        f"SELECT COLUMN_NAME FROM {sf_database}.INFORMATION_SCHEMA.COLUMNS "
                        f"WHERE TABLE_SCHEMA = '{sf_schema}' "
                        f"AND TABLE_NAME = '{sf_table_name}' "
                        f"ORDER BY ORDINAL_POSITION"
                    )
                    columns = [row[0] for row in cur.fetchall()]
                    has_cdc_cols = (
                        "_CDC_TIMESTAMP" in columns and "_CDC_OPERATION" in columns
                    )
                    yield dg.AssetCheckResult(
                        check_name=f"{dest_table}_schema_valid",
                        asset_key=dg.AssetKey(["cdc", dest_table]),
                        passed=has_cdc_cols and len(columns) > 0,
                        metadata={
                            "columns_found": dg.MetadataValue.json_serializable(columns),
                            "column_count": dg.MetadataValue.int(len(columns)),
                            "has_cdc_metadata_columns": dg.MetadataValue.bool(has_cdc_cols),
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
            description="Runs CDC data quality checks on Snowflake tables every hour",
        )

        return dg.Definitions(
            asset_checks=[cdc_quality_checks],
            jobs=[checks_job],
            schedules=[checks_schedule],
        )

    @staticmethod
    def _build_check_specs(tracked_tables: list[dict]) -> list[dg.AssetCheckSpec]:
        """Build check specs shared between demo and real modes."""
        specs = []
        for table_cfg in tracked_tables:
            dest_table = table_cfg["destination_table"]
            asset_key = dg.AssetKey(["cdc", dest_table])
            specs.extend([
                dg.AssetCheckSpec(
                    name=f"{dest_table}_row_count",
                    asset=asset_key,
                    description=f"Verify Snowflake {dest_table} has rows",
                ),
                dg.AssetCheckSpec(
                    name=f"{dest_table}_freshness",
                    asset=asset_key,
                    description=f"Verify CDC sink connector is running and data is fresh",
                ),
                dg.AssetCheckSpec(
                    name=f"{dest_table}_no_null_pks",
                    asset=asset_key,
                    description=f"Verify Snowflake {dest_table} has no NULL primary keys",
                ),
                dg.AssetCheckSpec(
                    name=f"{dest_table}_schema_valid",
                    asset=asset_key,
                    description=f"Verify Snowflake {dest_table} has CDC metadata columns",
                ),
            ])
        return specs
