"""
Base POS Connector — Abstract interface for all POS system integrations.

Every POS connector (REST, SOAP, CSV) implements this interface. The
framework is config-driven: most systems use GenericRESTConnector with
a system-specific config dict. Only systems with unusual APIs (SOAP,
GraphQL, custom auth) need a dedicated subclass.
"""
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger("meridian.pos_connectors")


@dataclass
class POSConnectionConfig:
    system_key: str
    system_name: str
    tier: int
    auth_method: str
    base_url: str = ""
    credentials: dict = field(default_factory=dict)
    merchant_id: str = ""
    org_id: str = ""
    sync_frequency_minutes: int = 60
    category: str = "restaurant"
    supports_order_creation: bool = False
    order_creation_endpoint: str = ""
    api_docs_url: str = ""


@dataclass
class SyncResult:
    transactions: list[dict] = field(default_factory=list)
    catalog_items: list[dict] = field(default_factory=list)
    employees: list[dict] = field(default_factory=list)
    customers: list[dict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    records_fetched: int = 0
    sync_duration_seconds: float = 0.0


@dataclass
class OrderResult:
    success: bool = False
    order_id: str = ""
    pos_system: str = ""
    fallback_used: bool = False
    fallback_reason: str = ""
    raw_response: dict = field(default_factory=dict)


class BasePOSConnector(ABC):

    def __init__(self, config: POSConnectionConfig):
        self.config = config
        self._logger = logging.getLogger(f"meridian.pos.{config.system_key}")

    @abstractmethod
    async def test_connection(self) -> dict[str, Any]:
        """Validate credentials without saving. Returns {success, message}."""
        ...

    @abstractmethod
    async def fetch_transactions(
        self, start_date: datetime, end_date: datetime
    ) -> list[dict]:
        """Fetch transactions in the date range."""
        ...

    async def fetch_catalog(self) -> list[dict]:
        """Fetch menu/product catalog. Override if supported."""
        return []

    async def fetch_employees(self) -> list[dict]:
        """Fetch employee list. Override if supported."""
        return []

    async def fetch_customers(self) -> list[dict]:
        """Fetch customer records. Override if supported."""
        return []

    async def create_order(self, order_data: dict) -> OrderResult:
        """Create an order in the POS. Override if supported."""
        return OrderResult(
            success=False,
            pos_system=self.config.system_key,
            fallback_used=True,
            fallback_reason=f"{self.config.system_name} does not support API order creation",
        )

    async def run_sync(
        self, since: datetime | None = None
    ) -> SyncResult:
        """Run a full or incremental sync."""
        import time
        start = time.time()
        result = SyncResult()

        end = datetime.utcnow()
        begin = since or datetime(end.year, end.month, 1)

        try:
            result.transactions = await self.fetch_transactions(begin, end)
            result.records_fetched += len(result.transactions)
        except Exception as e:
            self._logger.error(f"Transaction fetch failed: {e}")
            result.errors.append(f"transactions: {e}")

        try:
            result.catalog_items = await self.fetch_catalog()
            result.records_fetched += len(result.catalog_items)
        except Exception as e:
            self._logger.error(f"Catalog fetch failed: {e}")
            result.errors.append(f"catalog: {e}")

        try:
            result.employees = await self.fetch_employees()
            result.records_fetched += len(result.employees)
        except Exception as e:
            self._logger.error(f"Employee fetch failed: {e}")
            result.errors.append(f"employees: {e}")

        result.sync_duration_seconds = time.time() - start
        self._logger.info(
            f"Sync complete: {result.records_fetched} records, "
            f"{len(result.errors)} errors, {result.sync_duration_seconds:.1f}s"
        )
        return result
