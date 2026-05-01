"""
Connection Pool — asyncpg pool management for direct PostgreSQL access.

Provides the shared connection pool used by all repository modules.
"""
import logging
import os
from contextlib import asynccontextmanager

logger = logging.getLogger("meridian.db.pool")

_asyncpg = None


def _get_asyncpg():
    global _asyncpg
    if _asyncpg is None:
        try:
            import asyncpg as _mod
            _asyncpg = _mod
        except ImportError:
            raise ImportError(
                "asyncpg required for Supabase direct connection. "
                "Install with: pip install asyncpg"
            )
    return _asyncpg


class SupabaseConfig:
    """Supabase connection settings."""

    def __init__(
        self,
        database_url: str | None = None,
        supabase_url: str | None = None,
        supabase_key: str | None = None,
        supabase_service_key: str | None = None,
        pool_min: int = 2,
        pool_max: int = 10,
    ):
        self.database_url = database_url or os.getenv("DATABASE_URL", "")
        self.supabase_url = supabase_url or os.getenv("SUPABASE_URL", "")
        self.supabase_key = supabase_key or os.getenv("SUPABASE_ANON_KEY", "")
        self.supabase_service_key = (
            supabase_service_key or os.getenv("SUPABASE_SERVICE_KEY", "")
        )
        self.pool_min = pool_min
        self.pool_max = pool_max

    @property
    def direct_url(self) -> str:
        """PostgreSQL direct URL for asyncpg (bypasses PgBouncer)."""
        url = os.getenv("DATABASE_DIRECT_URL", self.database_url)
        return url


class ConnectionPool:
    """Manages the asyncpg connection pool."""

    def __init__(self, config: SupabaseConfig | None = None):
        self.config = config or SupabaseConfig()
        self._pool = None

    async def connect(self):
        """Initialize connection pool."""
        asyncpg = _get_asyncpg()

        if not self.config.database_url:
            raise ValueError(
                "DATABASE_URL not set. Add to .env:\n"
                "DATABASE_URL=postgresql://postgres:<password>@db.<ref>.supabase.co:5432/postgres"
            )

        self._pool = await asyncpg.create_pool(
            self.config.direct_url or self.config.database_url,
            min_size=self.config.pool_min,
            max_size=self.config.pool_max,
            command_timeout=60,
            ssl="prefer",
        )
        logger.info(
            f"Connected to Supabase PostgreSQL "
            f"(pool: {self.config.pool_min}-{self.config.pool_max})"
        )

    async def close(self):
        """Close connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("Database connection pool closed")

    @asynccontextmanager
    async def acquire(self):
        """Acquire a connection from the pool."""
        if not self._pool:
            await self.connect()
        async with self._pool.acquire() as conn:
            yield conn

    async def execute(self, query: str, *args) -> str:
        async with self.acquire() as conn:
            return await conn.execute(query, *args)

    async def fetch(self, query: str, *args) -> list:
        async with self.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args):
        async with self.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetchval(self, query: str, *args):
        async with self.acquire() as conn:
            return await conn.fetchval(query, *args)

    async def health_check(self) -> dict:
        """Verify database connectivity and basic stats."""
        try:
            version = await self.fetchval("SELECT version()")
            now = await self.fetchval("SELECT NOW()")
            table_count = await self.fetchval(
                """
                SELECT COUNT(*) FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_type = 'BASE TABLE'
                """
            )
            return {
                "status": "healthy",
                "postgres_version": version.split(",")[0] if version else None,
                "server_time": str(now),
                "public_tables": table_count,
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
            }
