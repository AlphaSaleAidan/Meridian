"""
Supabase Database Client — Production database operations for Meridian.

Thin facade over ConnectionPool + repository modules.
All public method signatures are preserved for backward compatibility.

Connection modes:
  • DIRECT (asyncpg) — Used by sync engine, workers, AI engine
  • REST (supabase-py) — Used by API routes (respects RLS)
"""
import logging

from .pool import SupabaseConfig, ConnectionPool
from .repos.sync_repo import SyncRepo
from .repos.query_repo import QueryRepo
from .repos.persist_repo import PersistRepo

logger = logging.getLogger("meridian.db.supabase")


class SupabaseDB:
    """
    Production database client for Meridian.

    Composes ConnectionPool with SyncRepo, QueryRepo, and PersistRepo.
    All method signatures are backward-compatible.

    Usage:
        db = SupabaseDB(config)
        await db.connect()

        # Bulk operations (sync engine)
        await db.upsert_locations(org_id, locations)
        await db.upsert_products(org_id, products)
        await db.upsert_transactions(org_id, transactions, items)

        # Analytics queries (AI engine)
        revenue = await db.get_daily_revenue(org_id, 30)
        products = await db.get_product_performance(org_id, 30)

        await db.close()
    """

    def __init__(self, config: SupabaseConfig | None = None):
        self.config = config or SupabaseConfig()
        self._pool = ConnectionPool(self.config)
        self._sync = SyncRepo(self._pool)
        self._query = QueryRepo(self._pool)
        self._persist = PersistRepo(self._pool)

    # ─── Pool Delegation ─────────────────────────────────────

    async def connect(self):
        await self._pool.connect()

    async def close(self):
        await self._pool.close()

    @property
    def acquire(self):
        return self._pool.acquire

    async def execute(self, query: str, *args) -> str:
        return await self._pool.execute(query, *args)

    async def fetch(self, query: str, *args) -> list:
        return await self._pool.fetch(query, *args)

    async def fetchrow(self, query: str, *args):
        return await self._pool.fetchrow(query, *args)

    async def fetchval(self, query: str, *args):
        return await self._pool.fetchval(query, *args)

    async def health_check(self) -> dict:
        return await self._pool.health_check()

    # ─── Sync Repo Delegation ────────────────────────────────

    async def upsert_locations(self, org_id: str, locations: list[dict]) -> int:
        return await self._sync.upsert_locations(org_id, locations)

    async def upsert_categories(self, org_id: str, categories: list[dict]) -> int:
        return await self._sync.upsert_categories(org_id, categories)

    async def upsert_products(self, org_id: str, products: list[dict]) -> int:
        return await self._sync.upsert_products(org_id, products)

    async def upsert_transactions_batch(
        self, org_id: str, transactions: list[dict], items: list[dict]
    ) -> tuple[int, int]:
        return await self._sync.upsert_transactions_batch(org_id, transactions, items)

    async def upsert_inventory_snapshots(
        self, org_id: str, snapshots: list[dict]
    ) -> int:
        return await self._sync.upsert_inventory_snapshots(org_id, snapshots)

    async def upsert_pos_connection(self, connection: dict) -> str:
        return await self._sync.upsert_pos_connection(connection)

    async def update_connection_sync_status(
        self,
        connection_id: str,
        status: str,
        last_sync_status: str | None = None,
        historical_complete: bool | None = None,
    ):
        return await self._sync.update_connection_sync_status(
            connection_id, status, last_sync_status, historical_complete
        )

    async def get_active_connections(self) -> list:
        return await self._sync.get_active_connections()

    async def get_connections_needing_refresh(self) -> list:
        return await self._sync.get_connections_needing_refresh()

    # ─── Query Repo Delegation ───────────────────────────────

    async def get_daily_revenue(self, org_id: str, days: int = 30) -> list:
        return await self._query.get_daily_revenue(org_id, days)

    async def get_hourly_revenue(self, org_id: str, days: int = 30) -> list:
        return await self._query.get_hourly_revenue(org_id, days)

    async def get_product_performance(self, org_id: str, days: int = 30) -> list:
        return await self._query.get_product_performance(org_id, days)

    async def get_transaction_details(self, org_id: str, days: int = 30) -> list:
        return await self._query.get_transaction_details(org_id, days)

    async def get_inventory_current(self, org_id: str) -> list:
        return await self._query.get_inventory_current(org_id)

    async def get_dashboard_summary(
        self, org_id: str, start_date: str | None = None, end_date: str | None = None
    ):
        return await self._query.get_dashboard_summary(org_id, start_date, end_date)

    # ─── Persist Repo Delegation ─────────────────────────────

    async def save_insight(self, insight: dict) -> str:
        return await self._persist.save_insight(insight)

    async def save_money_left_score(self, score: dict) -> str:
        return await self._persist.save_money_left_score(score)

    async def save_forecasts(self, forecasts: list[dict]) -> int:
        return await self._persist.save_forecasts(forecasts)

    async def save_weekly_report(self, report: dict) -> str:
        return await self._persist.save_weekly_report(report)

    async def run_migrations(self, migrations_dir: str) -> list[str]:
        return await self._persist.run_migrations(migrations_dir)
