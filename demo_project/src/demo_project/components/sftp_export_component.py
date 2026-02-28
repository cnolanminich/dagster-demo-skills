"""Custom SFTP export component.

Exports transformed data to remote SFTP servers as CSV/Parquet files.
Supports demo mode for local execution without SFTP connectivity.
"""

from typing import Optional

import dagster as dg


class SftpExportFile(dg.Model):
    """Configuration for a single SFTP export file."""

    name: str
    format: str = "csv"
    remote_path: str = "/exports"
    description: Optional[str] = None
    upstream_keys: list[list[str]] = []


class SftpExportComponent(dg.Component, dg.Model, dg.Resolvable):
    """SFTP file export component with demo mode support.

    Exports processed data as files to remote SFTP servers for
    downstream consumption by external systems and partners.

    When demo_mode is true, simulates file export locally.
    When demo_mode is false, connects to the SFTP server and uploads files.
    """

    demo_mode: bool = False
    sftp_host: str = ""
    sftp_port: int = 22
    sftp_username: str = ""
    sftp_password: str = ""
    sftp_key_path: str = ""
    exports: list[SftpExportFile] = []

    def _make_asset(self, export: SftpExportFile) -> dg.AssetsDefinition:
        """Create a single SFTP export asset."""
        asset_key = dg.AssetKey(["sftp_export", export.name])
        export_desc = export.description or f"SFTP export: {export.name}.{export.format}"
        upstream_deps = [dg.AssetKey(k) for k in export.upstream_keys]

        # Capture config in closure
        export_name = export.name
        file_format = export.format
        remote_path = export.remote_path
        demo_mode = self.demo_mode
        sftp_host = self.sftp_host
        sftp_port = self.sftp_port
        sftp_username = self.sftp_username
        sftp_key_path = self.sftp_key_path

        @dg.asset(
            key=asset_key,
            kinds={"sftp", "python"},
            description=export_desc,
            deps=upstream_deps,
            tags={
                "domain": "export",
                "schedule": "daily",
                "source": "sftp",
            },
            group_name="sftp_export",
            owners=["data-engineering@company.com"],
        )
        def sftp_export_asset(context: dg.AssetExecutionContext):
            filename = f"{export_name}.{file_format}"
            full_remote_path = f"{remote_path}/{filename}"

            if demo_mode:
                context.log.info(
                    f"Demo mode: Simulating SFTP upload of {filename} "
                    f"to {full_remote_path}"
                )
                file_sizes = {
                    "customer_360_export": 2_400_000,
                    "transaction_summary_export": 8_900_000,
                    "product_performance_export": 450_000,
                }
                return dg.MaterializeResult(
                    metadata={
                        "file_name": dg.MetadataValue.text(filename),
                        "remote_path": dg.MetadataValue.text(full_remote_path),
                        "file_size_bytes": dg.MetadataValue.int(
                            file_sizes.get(export_name, 100_000)
                        ),
                        "format": dg.MetadataValue.text(file_format),
                        "mode": dg.MetadataValue.text("demo"),
                    }
                )
            else:
                import paramiko

                context.log.info(
                    f"Uploading {filename} to {sftp_host}:{full_remote_path}"
                )
                transport = paramiko.Transport((sftp_host, sftp_port))
                if sftp_key_path:
                    key = paramiko.RSAKey.from_private_key_file(sftp_key_path)
                    transport.connect(username=sftp_username, pkey=key)
                else:
                    transport.connect(
                        username=sftp_username,
                        password=context.op_execution_context.op_config.get(
                            "sftp_password", ""
                        ),
                    )
                sftp = paramiko.SFTPClient.from_transport(transport)
                try:
                    # In production, generate the file from upstream data
                    # and upload via sftp.put(local_path, full_remote_path)
                    raise NotImplementedError(
                        f"Production SFTP export for '{export_name}' must be "
                        f"configured. Set demo_mode: true for local testing."
                    )
                finally:
                    sftp.close()
                    transport.close()

        return sftp_export_asset

    def build_defs(self, context: dg.ComponentLoadContext) -> dg.Definitions:
        assets = [self._make_asset(export) for export in self.exports]
        return dg.Definitions(assets=assets)
