"""AWS DMS Replication component for MariaDB → Snowflake CDC.

This component manages AWS Database Migration Service (DMS) replication tasks
that read MariaDB binlogs (CDC) and write changes to Snowflake.

Architecture:
  MariaDB (binlog CDC) → AWS DMS Replication Task → Snowflake

Materializing the dms_replication_tasks asset:
  1. Starts/resumes DMS replication tasks for each tracked table
  2. DMS reads MariaDB binlog and applies changes to Snowflake target

The sensor polls the DMS API to monitor replication task status, table statistics
(inserts/updates/deletes), and CDC latency.
"""

import json
import random
import time
from typing import Optional

import dagster as dg
from pydantic import BaseModel


class ReplicationTask(BaseModel):
    """Configuration for a single DMS replication task."""

    task_id: str
    source_schema: str
    source_table: str
    target_schema: str
    target_table: str
    cdc_start_position: Optional[str] = None


class AwsDmsReplicationComponent(dg.Component, dg.Model, dg.Resolvable):
    """Manages AWS DMS CDC replication from MariaDB to Snowflake.

    Materializing the replication tasks asset starts or resumes DMS tasks.
    The sensor monitors task status, table statistics, and CDC latency.
    Supports demo mode for local testing without AWS credentials.
    """

    demo_mode: bool = False

    # AWS configuration
    aws_region: str = "us-east-1"
    replication_instance_arn: str = ""
    source_endpoint_arn: str = ""
    target_endpoint_arn: str = ""

    # Replication tasks
    replication_tasks: list[ReplicationTask] = []
    minimum_interval_seconds: int = 60

    def build_defs(self, context: dg.ComponentLoadContext) -> dg.Definitions:
        if self.demo_mode:
            return self._build_demo_defs()
        return self._build_real_defs()

    def _build_demo_defs(self) -> dg.Definitions:
        tasks = self.replication_tasks
        region = self.aws_region
        instance_arn = self.replication_instance_arn

        # The DMS replication tasks asset — materializing starts/resumes tasks
        replication_spec = dg.AssetSpec(
            key=dg.AssetKey(["dms_cdc", "replication_tasks"]),
            group_name="aws_dms_cdc",
            kinds={"aws_dms", "mariadb"},
            tags={
                "cdc_method": "aws_dms",
                "source": "mariadb",
                "destination": "snowflake",
            },
            owners=["team:data-engineering"],
            description=(
                "AWS DMS replication tasks. Materializing this asset starts or "
                "resumes DMS CDC replication from MariaDB to Snowflake. DMS reads "
                "the MariaDB binlog and applies inserts, updates, and deletes to "
                "the Snowflake target tables."
            ),
        )

        # Snowflake destination table assets — downstream of the replication tasks
        table_specs = []
        for task in tasks:
            snowflake_fqn = f"{task.target_schema}.{task.target_table}".upper()
            table_specs.append(
                dg.AssetSpec(
                    key=dg.AssetKey(["dms_cdc", task.target_table]),
                    group_name="aws_dms_cdc",
                    kinds={"snowflake", "cdc"},
                    tags={
                        "cdc_method": "aws_dms",
                        "source": "mariadb",
                        "destination": "snowflake",
                    },
                    owners=["team:data-engineering"],
                    deps=[dg.AssetKey(["dms_cdc", "replication_tasks"])],
                    description=(
                        f"Snowflake table {snowflake_fqn} populated via AWS DMS "
                        f"CDC from MariaDB {task.source_schema}.{task.source_table}."
                    ),
                    metadata={
                        "snowflake_table": dg.MetadataValue.text(snowflake_fqn),
                        "mariadb_source": dg.MetadataValue.text(
                            f"{task.source_schema}.{task.source_table}"
                        ),
                        "dms_task_id": dg.MetadataValue.text(task.task_id),
                    },
                )
            )

        @dg.multi_asset(
            name="dms_start_replication",
            specs=[replication_spec],
        )
        def dms_start_replication(context: dg.AssetExecutionContext):
            """Start or resume DMS replication tasks (demo mode)."""
            context.log.info("=== AWS DMS CDC Replication Setup (Demo Mode) ===")
            context.log.info(f"Region: {region}")
            context.log.info(f"Replication Instance: {instance_arn}")

            started_tasks = []
            for task in tasks:
                context.log.info(
                    f"Starting task '{task.task_id}': "
                    f"{task.source_schema}.{task.source_table} → "
                    f"{task.target_schema}.{task.target_table}"
                )
                if task.cdc_start_position:
                    context.log.info(
                        f"  CDC start position: {task.cdc_start_position}"
                    )
                context.log.info(
                    f"  -> start_replication_task(TaskArn=...{task.task_id}) (simulated)"
                )
                context.log.info("  -> Task status: running")
                started_tasks.append(task.task_id)

            context.log.info(
                f"=== {len(started_tasks)} DMS tasks running: "
                "MariaDB → Snowflake CDC active ==="
            )

            return dg.MaterializeResult(
                metadata={
                    "replication_instance": dg.MetadataValue.text(instance_arn),
                    "aws_region": dg.MetadataValue.text(region),
                    "tasks_started": dg.MetadataValue.int(len(started_tasks)),
                    "task_ids": dg.MetadataValue.json_serializable(started_tasks),
                    "replication_type": dg.MetadataValue.text("cdc"),
                    "demo_mode": dg.MetadataValue.bool(True),
                },
            )

        # Sensor: polls DMS API for task status and table statistics
        interval = self.minimum_interval_seconds

        @dg.sensor(
            name="dms_cdc_monitor",
            minimum_interval_seconds=interval,
            default_status=dg.DefaultSensorStatus.RUNNING,
            description=(
                "Monitors AWS DMS replication task status, table statistics "
                "(inserts/updates/deletes), and CDC latency via the DMS API."
            ),
        )
        def dms_monitor_sensor(context: dg.SensorEvaluationContext):
            cursor_state = json.loads(context.cursor) if context.cursor else {}
            prev_totals = cursor_state.get("totals", {})
            check_count = cursor_state.get("check_count", 0)

            observations = []
            new_totals = {}

            for task in tasks:
                dest_table = task.target_table
                prev = prev_totals.get(dest_table, {})

                # Simulate accumulating DMS table statistics
                inserts = prev.get("inserts", 0) + random.randint(50, 500)
                updates = prev.get("updates", 0) + random.randint(10, 100)
                deletes = prev.get("deletes", 0) + random.randint(0, 20)
                cdc_latency_seconds = random.randint(1, 8)

                new_totals[dest_table] = {
                    "inserts": inserts,
                    "updates": updates,
                    "deletes": deletes,
                }

                observations.append(
                    dg.AssetObservation(
                        asset_key=dg.AssetKey(["dms_cdc", dest_table]),
                        metadata={
                            "task_status": dg.MetadataValue.text("running"),
                            "task_id": dg.MetadataValue.text(task.task_id),
                            "total_inserts": dg.MetadataValue.int(inserts),
                            "total_updates": dg.MetadataValue.int(updates),
                            "total_deletes": dg.MetadataValue.int(deletes),
                            "cdc_latency_seconds": dg.MetadataValue.int(
                                cdc_latency_seconds
                            ),
                            "demo_mode": dg.MetadataValue.bool(True),
                        },
                    )
                )

            new_cursor = json.dumps({
                "totals": new_totals,
                "check_count": check_count + 1,
                "last_check_epoch": int(time.time()),
            })
            return dg.SensorResult(
                asset_events=observations,
                cursor=new_cursor,
            )

        return dg.Definitions(
            assets=[dms_start_replication, *table_specs],
            sensors=[dms_monitor_sensor],
        )

    def _build_real_defs(self) -> dg.Definitions:
        tasks = self.replication_tasks
        region = self.aws_region
        instance_arn = self.replication_instance_arn
        source_arn = self.source_endpoint_arn
        target_arn = self.target_endpoint_arn

        replication_spec = dg.AssetSpec(
            key=dg.AssetKey(["dms_cdc", "replication_tasks"]),
            group_name="aws_dms_cdc",
            kinds={"aws_dms", "mariadb"},
            tags={
                "cdc_method": "aws_dms",
                "source": "mariadb",
                "destination": "snowflake",
            },
            owners=["team:data-engineering"],
            description=(
                "AWS DMS replication tasks. Starts or resumes CDC replication "
                "from MariaDB to Snowflake."
            ),
        )

        table_specs = []
        for task in tasks:
            snowflake_fqn = f"{task.target_schema}.{task.target_table}".upper()
            table_specs.append(
                dg.AssetSpec(
                    key=dg.AssetKey(["dms_cdc", task.target_table]),
                    group_name="aws_dms_cdc",
                    kinds={"snowflake", "cdc"},
                    tags={
                        "cdc_method": "aws_dms",
                        "source": "mariadb",
                        "destination": "snowflake",
                    },
                    owners=["team:data-engineering"],
                    deps=[dg.AssetKey(["dms_cdc", "replication_tasks"])],
                    description=(
                        f"Snowflake table {snowflake_fqn} populated via AWS DMS "
                        f"CDC from MariaDB {task.source_schema}.{task.source_table}."
                    ),
                    metadata={
                        "snowflake_table": dg.MetadataValue.text(snowflake_fqn),
                        "mariadb_source": dg.MetadataValue.text(
                            f"{task.source_schema}.{task.source_table}"
                        ),
                        "dms_task_id": dg.MetadataValue.text(task.task_id),
                    },
                )
            )

        @dg.multi_asset(
            name="dms_start_replication",
            specs=[replication_spec],
        )
        def dms_start_replication(context: dg.AssetExecutionContext):
            """Start or resume DMS replication tasks via boto3."""
            import boto3

            client = boto3.client("dms", region_name=region)

            started_tasks = []
            for task in tasks:
                # Describe the task to check current status
                task_arn = f"arn:aws:dms:{region}:*:task:{task.task_id}"

                try:
                    desc = client.describe_replication_tasks(
                        Filters=[{"Name": "replication-task-id", "Values": [task.task_id]}]
                    )
                    existing = desc["ReplicationTasks"]

                    if existing:
                        task_arn = existing[0]["ReplicationTaskArn"]
                        status = existing[0]["Status"]
                        context.log.info(
                            f"Task '{task.task_id}' exists with status: {status}"
                        )

                        if status == "stopped":
                            start_type = "resume-processing"
                            if task.cdc_start_position:
                                client.start_replication_task(
                                    ReplicationTaskArn=task_arn,
                                    StartReplicationTaskType="start-replication",
                                    CdcStartPosition=task.cdc_start_position,
                                )
                            else:
                                client.start_replication_task(
                                    ReplicationTaskArn=task_arn,
                                    StartReplicationTaskType=start_type,
                                )
                            context.log.info(f"Resumed task '{task.task_id}'")
                        elif status == "running":
                            context.log.info(f"Task '{task.task_id}' already running")
                        else:
                            context.log.warning(
                                f"Task '{task.task_id}' in state '{status}', skipping"
                            )
                    else:
                        # Create the replication task
                        table_mapping = json.dumps({
                            "rules": [
                                {
                                    "rule-type": "selection",
                                    "rule-id": "1",
                                    "rule-name": f"include-{task.source_table}",
                                    "rule-action": "include",
                                    "object-locator": {
                                        "schema-name": task.source_schema,
                                        "table-name": task.source_table,
                                    },
                                },
                                {
                                    "rule-type": "transformation",
                                    "rule-id": "2",
                                    "rule-name": f"rename-schema-{task.target_schema}",
                                    "rule-action": "rename",
                                    "rule-target": "schema",
                                    "object-locator": {
                                        "schema-name": task.source_schema,
                                    },
                                    "value": task.target_schema,
                                },
                            ]
                        })

                        response = client.create_replication_task(
                            ReplicationTaskIdentifier=task.task_id,
                            SourceEndpointArn=source_arn,
                            TargetEndpointArn=target_arn,
                            ReplicationInstanceArn=instance_arn,
                            MigrationType="cdc",
                            TableMappings=table_mapping,
                            ReplicationTaskSettings=json.dumps({
                                "TargetMetadata": {
                                    "TargetSchema": task.target_schema,
                                    "SupportLobs": True,
                                },
                                "Logging": {"EnableLogging": True},
                            }),
                        )
                        task_arn = response["ReplicationTask"]["ReplicationTaskArn"]
                        context.log.info(f"Created task '{task.task_id}': {task_arn}")

                        # Start the newly created task
                        client.start_replication_task(
                            ReplicationTaskArn=task_arn,
                            StartReplicationTaskType="start-replication",
                        )
                        context.log.info(f"Started task '{task.task_id}'")

                    started_tasks.append(task.task_id)

                except Exception as e:
                    context.log.error(f"Failed to manage task '{task.task_id}': {e}")
                    raise

            return dg.MaterializeResult(
                metadata={
                    "replication_instance": dg.MetadataValue.text(instance_arn),
                    "aws_region": dg.MetadataValue.text(region),
                    "tasks_started": dg.MetadataValue.int(len(started_tasks)),
                    "task_ids": dg.MetadataValue.json_serializable(started_tasks),
                    "replication_type": dg.MetadataValue.text("cdc"),
                },
            )

        # Sensor: polls DMS API for task status and table statistics
        interval = self.minimum_interval_seconds

        @dg.sensor(
            name="dms_cdc_monitor",
            minimum_interval_seconds=interval,
            default_status=dg.DefaultSensorStatus.RUNNING,
            description=(
                "Monitors AWS DMS replication task status, table statistics, "
                "and CDC latency via the DMS API."
            ),
        )
        def dms_monitor_sensor(context: dg.SensorEvaluationContext):
            import boto3

            client = boto3.client("dms", region_name=region)
            cursor_state = json.loads(context.cursor) if context.cursor else {}

            observations = []
            new_totals = {}

            for task in tasks:
                dest_table = task.target_table

                try:
                    # Get task status
                    desc = client.describe_replication_tasks(
                        Filters=[
                            {"Name": "replication-task-id", "Values": [task.task_id]}
                        ]
                    )
                    if not desc["ReplicationTasks"]:
                        context.log.warning(f"Task '{task.task_id}' not found")
                        continue

                    task_info = desc["ReplicationTasks"][0]
                    task_arn = task_info["ReplicationTaskArn"]
                    task_status = task_info["Status"]
                    cdc_latency = task_info.get(
                        "ReplicationTaskStats", {}
                    ).get("CDCLatencySource", 0)

                    # Get table statistics
                    stats_resp = client.describe_table_statistics(
                        ReplicationTaskArn=task_arn,
                        Filters=[
                            {
                                "Name": "table-name",
                                "Values": [task.source_table],
                            }
                        ],
                    )

                    inserts = 0
                    updates = 0
                    deletes = 0
                    if stats_resp["TableStatistics"]:
                        tbl_stats = stats_resp["TableStatistics"][0]
                        inserts = tbl_stats.get("Inserts", 0)
                        updates = tbl_stats.get("Updates", 0)
                        deletes = tbl_stats.get("Deletes", 0)

                    new_totals[dest_table] = {
                        "inserts": inserts,
                        "updates": updates,
                        "deletes": deletes,
                    }

                    observations.append(
                        dg.AssetObservation(
                            asset_key=dg.AssetKey(["dms_cdc", dest_table]),
                            metadata={
                                "task_status": dg.MetadataValue.text(task_status),
                                "task_id": dg.MetadataValue.text(task.task_id),
                                "total_inserts": dg.MetadataValue.int(inserts),
                                "total_updates": dg.MetadataValue.int(updates),
                                "total_deletes": dg.MetadataValue.int(deletes),
                                "cdc_latency_seconds": dg.MetadataValue.int(
                                    int(cdc_latency)
                                ),
                            },
                        )
                    )

                except Exception as e:
                    context.log.warning(
                        f"Failed to get status for task '{task.task_id}': {e}"
                    )
                    observations.append(
                        dg.AssetObservation(
                            asset_key=dg.AssetKey(["dms_cdc", dest_table]),
                            metadata={
                                "task_status": dg.MetadataValue.text("error"),
                                "task_id": dg.MetadataValue.text(task.task_id),
                                "error": dg.MetadataValue.text(str(e)),
                            },
                        )
                    )

            new_cursor = json.dumps({
                "totals": new_totals,
                "check_count": cursor_state.get("check_count", 0) + 1,
                "last_check_epoch": int(time.time()),
            })
            return dg.SensorResult(
                asset_events=observations,
                cursor=new_cursor,
            )

        return dg.Definitions(
            assets=[dms_start_replication, *table_specs],
            sensors=[dms_monitor_sensor],
        )
