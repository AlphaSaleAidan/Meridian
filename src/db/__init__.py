"""
Database module — Singleton SupabaseREST client for the application.

Usage:
    from src.db import init_db, close_db, get_db

    # At startup
    await init_db()

    # In request handlers (via FastAPI Depends)
    db = get_db()

    # At shutdown
    await close_db()
"""
import os
import logging
from .supabase_rest import SupabaseREST

logger = logging.getLogger("meridian.db")

_db_instance: SupabaseREST | None = None


async def init_db() -> SupabaseREST | None:
    """Initialize the global DB client from environment variables."""
    global _db_instance

    url = os.environ.get("SUPABASE_URL", "")
    # Accept both naming conventions
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "") or os.environ.get("SUPABASE_SERVICE_KEY", "")

    if not url or not key:
        logger.warning("SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set — DB unavailable")
        return None

    _db_instance = SupabaseREST(url=url, service_key=key)
    health = await _db_instance.health_check()
    logger.info(f"Database initialized: {health}")
    return _db_instance


async def close_db():
    """Close the global DB client."""
    global _db_instance
    if _db_instance:
        await _db_instance.close()
        _db_instance = None
        logger.info("Database connection closed")


def get_db() -> SupabaseREST:
    """Get the global DB client. Raises if not initialized."""
    if _db_instance is None:
        raise RuntimeError("Database not initialized — call init_db() first")
    return _db_instance
