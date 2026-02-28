"""Custom Fivetran component with demo mode support.

Subclasses FivetranAccountComponent to add demo_mode functionality,
allowing local demonstration without Fivetran API credentials.
"""

import dagster as dg
from dagster_fivetran import FivetranAccountComponent


class CustomFivetranComponent(FivetranAccountComponent):
    """Fivetran connector sync component with demo mode.

    When demo_mode is true, returns mocked assets representing
    Fivetran-synced tables without calling the Fivetran API.
    When demo_mode is false, uses real Fivetran API credentials.
    """

    demo_mode: bool = False

    def build_defs(self, context: dg.ComponentLoadContext) -> dg.Definitions:
        if self.demo_mode:
            return self._build_demo_defs(context)
        return super().build_defs(context)

    def _build_demo_defs(self, context: dg.ComponentLoadContext) -> dg.Definitions:
        """Build demo mode definitions with mocked Fivetran sync assets."""

        @dg.asset(
            key=dg.AssetKey(["fivetran_raw", "accounts"]),
            kinds={"fivetran"},
            description="Fivetran sync: CRM accounts from Salesforce",
            tags={"domain": "sales", "schedule": "hourly", "source": "fivetran"},
            group_name="fivetran_ingestion",
            owners=["data-engineering@company.com"],
        )
        def fivetran_accounts(context: dg.AssetExecutionContext):
            context.log.info("Demo mode: Simulating Fivetran sync for accounts")
            return dg.MaterializeResult(
                metadata={
                    "records_synced": dg.MetadataValue.int(15200),
                    "sync_duration_seconds": dg.MetadataValue.float(45.3),
                    "connector": dg.MetadataValue.text("salesforce_crm"),
                    "mode": dg.MetadataValue.text("demo"),
                }
            )

        @dg.asset(
            key=dg.AssetKey(["fivetran_raw", "transactions"]),
            kinds={"fivetran"},
            description="Fivetran sync: Financial transactions from Stripe",
            tags={"domain": "finance", "schedule": "hourly", "source": "fivetran"},
            group_name="fivetran_ingestion",
            owners=["data-engineering@company.com"],
        )
        def fivetran_transactions(context: dg.AssetExecutionContext):
            context.log.info("Demo mode: Simulating Fivetran sync for transactions")
            return dg.MaterializeResult(
                metadata={
                    "records_synced": dg.MetadataValue.int(89400),
                    "sync_duration_seconds": dg.MetadataValue.float(112.7),
                    "connector": dg.MetadataValue.text("stripe_payments"),
                    "mode": dg.MetadataValue.text("demo"),
                }
            )

        @dg.asset(
            key=dg.AssetKey(["fivetran_raw", "products"]),
            kinds={"fivetran"},
            description="Fivetran sync: Product catalog from inventory system",
            tags={"domain": "operations", "schedule": "daily", "source": "fivetran"},
            group_name="fivetran_ingestion",
            owners=["data-engineering@company.com"],
        )
        def fivetran_products(context: dg.AssetExecutionContext):
            context.log.info("Demo mode: Simulating Fivetran sync for products")
            return dg.MaterializeResult(
                metadata={
                    "records_synced": dg.MetadataValue.int(3420),
                    "sync_duration_seconds": dg.MetadataValue.float(18.1),
                    "connector": dg.MetadataValue.text("inventory_db"),
                    "mode": dg.MetadataValue.text("demo"),
                }
            )

        return dg.Definitions(
            assets=[fivetran_accounts, fivetran_transactions, fivetran_products]
        )
