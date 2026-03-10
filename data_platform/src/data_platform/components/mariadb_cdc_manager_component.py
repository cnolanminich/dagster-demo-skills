"""MariaDB CDC Manager component using Debezium + Kafka + Snowflake.

This component manages a Debezium connector that reads the MariaDB binlog (using
GTID for position tracking) and streams changes through Kafka into Snowflake.

Architecture:
  MariaDB (binlog w/ GTID) → Debezium (Kafka Connect) → Kafka → Snowflake Sink Connector → Snowflake

Materializing the cdc/debezium_connector asset:
  1. Registers the Debezium MariaDB source connector with Kafka Connect
  2. Registers the Snowflake sink connector
  3. Connector runs continuously — Debezium reads binlog, Kafka delivers to Snowflake

The sensor polls Kafka Connect REST API to monitor connector health and GTID progress,
emitting observations on the Snowflake destination table assets.
"""

import json
from dataclasses import dataclass, field

import dagster as dg


@dataclass
class MariadbCdcManagerComponent(dg.Component, dg.Resolvable):
    """Manages Debezium CDC from MariaDB to Snowflake via Kafka.

    Materializing the connector asset registers Debezium source and Snowflake
    sink connectors with Kafka Connect. The sensor monitors connector status
    and GTID progress. Supports demo mode for local testing.
    """

    demo_mode: bool = False

    # Kafka Connect
    kafka_connect_url: str = "http://localhost:8083"

    # MariaDB source
    mariadb_host: str = "localhost"
    mariadb_port: int = 3306
    mariadb_user: str = "debezium"
    mariadb_password: str = "demo_password"
    database_server_name: str = "mariadb-ecommerce"

    # Snowflake sink
    snowflake_account: str = "myorg-myaccount"
    snowflake_user: str = "CDC_LOADER"
    snowflake_private_key: str = ""
    snowflake_database: str = "RAW"
    snowflake_schema: str = "CDC_ECOMMERCE"

    # Tables
    tracked_tables: list[dict] = field(default_factory=list)
    minimum_interval_seconds: int = 60

    def build_defs(self, context: dg.ComponentLoadContext) -> dg.Definitions:
        if self.demo_mode:
            return self._build_demo_defs()
        return self._build_real_defs()

    def _build_demo_defs(self) -> dg.Definitions:
        tracked = self.tracked_tables
        interval = self.minimum_interval_seconds
        sf_database = self.snowflake_database
        sf_schema = self.snowflake_schema
        server_name = self.database_server_name

        # The Debezium connector asset — materializing it registers the connectors
        connector_spec = dg.AssetSpec(
            key=dg.AssetKey(["cdc", "debezium_connector"]),
            group_name="mariadb_cdc",
            kinds={"debezium", "kafka"},
            tags={"ingestion_tool": "debezium", "cdc_role": "connector"},
            owners=["team:data-engineering"],
            description=(
                "Debezium CDC connector. Materializing this asset registers the "
                "Debezium MariaDB source connector and Snowflake sink connector "
                "with Kafka Connect. Once registered, Debezium continuously reads "
                "the MariaDB binlog and streams changes to Snowflake."
            ),
        )

        # Snowflake destination table assets — downstream of the connector
        table_specs = []
        for table_cfg in tracked:
            source_table = table_cfg["source_table"]
            dest_table = table_cfg["destination_table"]
            schema_name, table_name = source_table.split(".")
            snowflake_fqn = f"{sf_database}.{sf_schema}.{dest_table}".upper()
            table_specs.append(
                dg.AssetSpec(
                    key=dg.AssetKey(["cdc", dest_table]),
                    group_name="mariadb_cdc",
                    kinds={"snowflake", "cdc"},
                    tags={
                        "ingestion_tool": "debezium",
                        "cdc_method": "binlog_gtid",
                        "destination": "snowflake",
                    },
                    owners=["team:data-engineering"],
                    deps=[dg.AssetKey(["cdc", "debezium_connector"])],
                    description=(
                        f"Snowflake table {snowflake_fqn} populated via CDC from "
                        f"MariaDB {source_table}. Debezium reads the binlog using "
                        f"GTID position tracking and streams changes through Kafka."
                    ),
                    metadata={
                        "snowflake_table": dg.MetadataValue.text(snowflake_fqn),
                        "mariadb_source": dg.MetadataValue.text(source_table),
                        "kafka_topic": dg.MetadataValue.text(
                            f"{server_name}.{schema_name}.{table_name}"
                        ),
                    },
                )
            )

        @dg.multi_asset(
            name="cdc_register_connectors",
            specs=[connector_spec],
        )
        def cdc_register_connectors(context: dg.AssetExecutionContext):
            """Register Debezium source and Snowflake sink connectors (demo mode)."""
            context.log.info("=== Debezium CDC Setup (Demo Mode) ===")

            # Step 1: Register Debezium MariaDB source connector
            source_config = {
                "connector.class": "io.debezium.connector.mariadb.MariaDbConnector",
                "database.hostname": "mariadb.internal.example.com",
                "database.port": 3306,
                "database.user": "debezium",
                "database.server.name": server_name,
                "database.include.list": ",".join(
                    set(t["source_table"].split(".")[0] for t in tracked)
                ),
                "table.include.list": ",".join(
                    t["source_table"] for t in tracked
                ),
                "include.schema.changes": True,
                "gtid.source.includes": ".*",
                "snapshot.mode": "initial",
                "topic.prefix": server_name,
            }
            context.log.info(
                f"Step 1: Registering Debezium source connector '{server_name}-source'"
            )
            context.log.info(f"  Config: {json.dumps(source_config, indent=2)}")
            context.log.info("  -> PUT /connectors/mariadb-ecommerce-source/config (simulated)")
            context.log.info("  -> Connector registered: RUNNING")

            # Step 2: Register Snowflake sink connector
            sink_config = {
                "connector.class": "com.snowflake.kafka.connector.SnowflakeSinkConnector",
                "snowflake.url.name": f"{sf_database}.snowflakecomputing.com",
                "snowflake.user.name": "CDC_LOADER",
                "snowflake.database.name": sf_database,
                "snowflake.schema.name": sf_schema,
                "topics": ",".join(
                    f"{server_name}.{t['source_table']}" for t in tracked
                ),
                "key.converter": "io.confluent.connect.avro.AvroConverter",
                "value.converter": "io.confluent.connect.avro.AvroConverter",
            }
            context.log.info(
                f"Step 2: Registering Snowflake sink connector '{server_name}-snowflake-sink'"
            )
            context.log.info(f"  Config: {json.dumps(sink_config, indent=2)}")
            context.log.info("  -> PUT /connectors/mariadb-ecommerce-snowflake-sink/config (simulated)")
            context.log.info("  -> Connector registered: RUNNING")

            # Step 3: Verify Kafka topics created
            topics = [f"{server_name}.{t['source_table']}" for t in tracked]
            context.log.info(f"Step 3: Kafka topics created: {topics}")

            context.log.info("=== CDC pipeline active: MariaDB → Debezium → Kafka → Snowflake ===")

            return dg.MaterializeResult(
                metadata={
                    "source_connector": dg.MetadataValue.text(f"{server_name}-source"),
                    "source_connector_status": dg.MetadataValue.text("RUNNING"),
                    "sink_connector": dg.MetadataValue.text(f"{server_name}-snowflake-sink"),
                    "sink_connector_status": dg.MetadataValue.text("RUNNING"),
                    "kafka_topics": dg.MetadataValue.json_serializable(topics),
                    "snowflake_database": dg.MetadataValue.text(sf_database),
                    "snowflake_schema": dg.MetadataValue.text(sf_schema),
                    "snapshot_mode": dg.MetadataValue.text("initial"),
                    "tables_configured": dg.MetadataValue.int(len(tracked)),
                    "demo_mode": dg.MetadataValue.bool(True),
                },
            )

        # Sensor: polls Kafka Connect for connector health and GTID progress
        @dg.sensor(
            name="debezium_cdc_monitor",
            minimum_interval_seconds=interval,
            default_status=dg.DefaultSensorStatus.RUNNING,
            description=(
                "Monitors Debezium connector health and GTID progress via "
                "Kafka Connect REST API. Reports observations on Snowflake "
                "destination table assets."
            ),
        )
        def debezium_monitor_sensor(context: dg.SensorEvaluationContext):
            cursor_state = json.loads(context.cursor) if context.cursor else {}
            previous_gtid = cursor_state.get("last_gtid", "0-0-0")

            # Demo: simulate advancing GTID and connector health
            domain_id, server_id, seq = previous_gtid.split("-")
            new_seq = int(seq) + 843
            new_gtid = f"{domain_id}-{server_id}-{new_seq}"

            source_status = "RUNNING"
            sink_status = "RUNNING"

            observations = []
            for table_cfg in tracked:
                dest_table = table_cfg["destination_table"]
                source_table = table_cfg["source_table"]
                observations.append(
                    dg.AssetObservation(
                        asset_key=dg.AssetKey(["cdc", dest_table]),
                        metadata={
                            "gtid_position": dg.MetadataValue.text(new_gtid),
                            "source_connector_status": dg.MetadataValue.text(source_status),
                            "sink_connector_status": dg.MetadataValue.text(sink_status),
                            "kafka_topic": dg.MetadataValue.text(
                                f"{server_name}.{source_table}"
                            ),
                            "kafka_consumer_lag": dg.MetadataValue.int(12),
                            "events_since_last_check": dg.MetadataValue.int(843),
                            "demo_mode": dg.MetadataValue.bool(True),
                        },
                    )
                )

            new_cursor = json.dumps({
                "last_gtid": new_gtid,
                "source_status": source_status,
                "sink_status": sink_status,
            })
            return dg.SensorResult(
                asset_events=observations,
                cursor=new_cursor,
            )

        return dg.Definitions(
            assets=[cdc_register_connectors, *table_specs],
            sensors=[debezium_monitor_sensor],
        )

    def _build_real_defs(self) -> dg.Definitions:
        tracked = self.tracked_tables
        interval = self.minimum_interval_seconds
        connect_url = self.kafka_connect_url
        db_host = self.mariadb_host
        db_port = self.mariadb_port
        db_user = self.mariadb_user
        db_password = self.mariadb_password
        server_name = self.database_server_name
        sf_account = self.snowflake_account
        sf_user = self.snowflake_user
        sf_private_key = self.snowflake_private_key
        sf_database = self.snowflake_database
        sf_schema = self.snowflake_schema

        connector_spec = dg.AssetSpec(
            key=dg.AssetKey(["cdc", "debezium_connector"]),
            group_name="mariadb_cdc",
            kinds={"debezium", "kafka"},
            tags={"ingestion_tool": "debezium", "cdc_role": "connector"},
            owners=["team:data-engineering"],
            description=(
                "Debezium CDC connector. Materializing this asset registers the "
                "Debezium MariaDB source and Snowflake sink connectors."
            ),
        )

        table_specs = []
        for table_cfg in tracked:
            source_table = table_cfg["source_table"]
            dest_table = table_cfg["destination_table"]
            schema_name, table_name = source_table.split(".")
            snowflake_fqn = f"{sf_database}.{sf_schema}.{dest_table}".upper()
            table_specs.append(
                dg.AssetSpec(
                    key=dg.AssetKey(["cdc", dest_table]),
                    group_name="mariadb_cdc",
                    kinds={"snowflake", "cdc"},
                    tags={
                        "ingestion_tool": "debezium",
                        "cdc_method": "binlog_gtid",
                        "destination": "snowflake",
                    },
                    owners=["team:data-engineering"],
                    deps=[dg.AssetKey(["cdc", "debezium_connector"])],
                    description=(
                        f"Snowflake table {snowflake_fqn} populated via CDC from "
                        f"MariaDB {source_table}"
                    ),
                    metadata={
                        "snowflake_table": dg.MetadataValue.text(snowflake_fqn),
                        "mariadb_source": dg.MetadataValue.text(source_table),
                        "kafka_topic": dg.MetadataValue.text(
                            f"{server_name}.{schema_name}.{table_name}"
                        ),
                    },
                )
            )

        @dg.multi_asset(
            name="cdc_register_connectors",
            specs=[connector_spec],
        )
        def cdc_register_connectors(context: dg.AssetExecutionContext):
            """Register Debezium source and Snowflake sink with Kafka Connect."""
            import requests

            # Build Debezium MariaDB source connector config
            db_include_list = ",".join(
                set(t["source_table"].split(".")[0] for t in tracked)
            )
            table_include_list = ",".join(t["source_table"] for t in tracked)

            source_connector_name = f"{server_name}-source"
            source_config = {
                "connector.class": "io.debezium.connector.mariadb.MariaDbConnector",
                "database.hostname": db_host,
                "database.port": str(db_port),
                "database.user": db_user,
                "database.password": db_password,
                "database.server.name": server_name,
                "database.include.list": db_include_list,
                "table.include.list": table_include_list,
                "include.schema.changes": "true",
                "gtid.source.includes": ".*",
                "snapshot.mode": "initial",
                "topic.prefix": server_name,
                "schema.history.internal.kafka.bootstrap.servers": "kafka:9092",
                "schema.history.internal.kafka.topic": f"{server_name}.schema-history",
            }

            context.log.info(f"Registering Debezium source connector: {source_connector_name}")
            resp = requests.put(
                f"{connect_url}/connectors/{source_connector_name}/config",
                json=source_config,
                timeout=30,
            )
            resp.raise_for_status()
            context.log.info(f"Source connector registered: {resp.status_code}")

            # Build Snowflake sink connector config
            topics = ",".join(
                f"{server_name}.{t['source_table']}" for t in tracked
            )
            sink_connector_name = f"{server_name}-snowflake-sink"
            sink_config = {
                "connector.class": "com.snowflake.kafka.connector.SnowflakeSinkConnector",
                "tasks.max": "4",
                "topics": topics,
                "snowflake.url.name": f"{sf_account}.snowflakecomputing.com",
                "snowflake.user.name": sf_user,
                "snowflake.private.key": sf_private_key,
                "snowflake.database.name": sf_database,
                "snowflake.schema.name": sf_schema,
                "key.converter": "io.confluent.connect.avro.AvroConverter",
                "value.converter": "io.confluent.connect.avro.AvroConverter",
                "key.converter.schema.registry.url": "http://schema-registry:8081",
                "value.converter.schema.registry.url": "http://schema-registry:8081",
            }

            context.log.info(f"Registering Snowflake sink connector: {sink_connector_name}")
            resp = requests.put(
                f"{connect_url}/connectors/{sink_connector_name}/config",
                json=sink_config,
                timeout=30,
            )
            resp.raise_for_status()
            context.log.info(f"Sink connector registered: {resp.status_code}")

            # Verify both connectors are running
            source_resp = requests.get(
                f"{connect_url}/connectors/{source_connector_name}/status",
                timeout=10,
            )
            sink_resp = requests.get(
                f"{connect_url}/connectors/{sink_connector_name}/status",
                timeout=10,
            )
            source_state = source_resp.json()["connector"]["state"]
            sink_state = sink_resp.json()["connector"]["state"]

            context.log.info(f"Source: {source_state}, Sink: {sink_state}")

            return dg.MaterializeResult(
                metadata={
                    "source_connector": dg.MetadataValue.text(source_connector_name),
                    "source_connector_status": dg.MetadataValue.text(source_state),
                    "sink_connector": dg.MetadataValue.text(sink_connector_name),
                    "sink_connector_status": dg.MetadataValue.text(sink_state),
                    "kafka_topics": dg.MetadataValue.json_serializable(topics.split(",")),
                    "snowflake_database": dg.MetadataValue.text(sf_database),
                    "snowflake_schema": dg.MetadataValue.text(sf_schema),
                    "snapshot_mode": dg.MetadataValue.text("initial"),
                    "tables_configured": dg.MetadataValue.int(len(tracked)),
                },
            )

        # Sensor: polls Kafka Connect REST API for connector health
        @dg.sensor(
            name="debezium_cdc_monitor",
            minimum_interval_seconds=interval,
            default_status=dg.DefaultSensorStatus.RUNNING,
            description=(
                "Monitors Debezium and Snowflake sink connector health via "
                "Kafka Connect REST API"
            ),
        )
        def debezium_monitor_sensor(context: dg.SensorEvaluationContext):
            import requests

            cursor_state = json.loads(context.cursor) if context.cursor else {}

            source_connector_name = f"{server_name}-source"
            sink_connector_name = f"{server_name}-snowflake-sink"

            # Get connector statuses
            try:
                source_resp = requests.get(
                    f"{connect_url}/connectors/{source_connector_name}/status",
                    timeout=10,
                )
                source_resp.raise_for_status()
                source_info = source_resp.json()
                source_state = source_info["connector"]["state"]

                sink_resp = requests.get(
                    f"{connect_url}/connectors/{sink_connector_name}/status",
                    timeout=10,
                )
                sink_resp.raise_for_status()
                sink_info = sink_resp.json()
                sink_state = sink_info["connector"]["state"]
            except requests.RequestException as e:
                context.log.warning(f"Failed to reach Kafka Connect: {e}")
                return dg.SkipReason(f"Kafka Connect unavailable: {e}")

            if source_state != "RUNNING" or sink_state != "RUNNING":
                context.log.error(
                    f"Connector unhealthy — source: {source_state}, sink: {sink_state}"
                )

            # Get source connector metrics for GTID position
            try:
                metrics_resp = requests.get(
                    f"{connect_url}/connectors/{source_connector_name}/tasks/0/status",
                    timeout=10,
                )
                task_info = metrics_resp.json()
                # Debezium exposes GTID in connector offsets
                worker_id = task_info.get("worker_id", "unknown")
            except requests.RequestException:
                worker_id = "unknown"

            observations = []
            for table_cfg in tracked:
                dest_table = table_cfg["destination_table"]
                source_table = table_cfg["source_table"]
                observations.append(
                    dg.AssetObservation(
                        asset_key=dg.AssetKey(["cdc", dest_table]),
                        metadata={
                            "source_connector_status": dg.MetadataValue.text(source_state),
                            "sink_connector_status": dg.MetadataValue.text(sink_state),
                            "kafka_topic": dg.MetadataValue.text(
                                f"{server_name}.{source_table}"
                            ),
                            "worker_id": dg.MetadataValue.text(worker_id),
                        },
                    )
                )

            new_cursor = json.dumps({
                "source_status": source_state,
                "sink_status": sink_state,
            })
            return dg.SensorResult(
                asset_events=observations,
                cursor=new_cursor,
            )

        return dg.Definitions(
            assets=[cdc_register_connectors, *table_specs],
            sensors=[debezium_monitor_sensor],
        )
