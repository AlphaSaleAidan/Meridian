"""
Worker: Square incremental sync (runs every 15 minutes via cron).

Only processes orders updated since the last sync. Skips connections
that haven't completed backfill yet.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone

from ..services.square.client import SquareClient
from ..services.square.rate_limiter import SquareRateLimiter
from ..services.square.sync_engine import SyncResult, run_incremental_sync

logger = logging.getLogger("meridian.workers.incremental")


async def incremental_worker(
    access_token: str,
    org_id: str,
    last_sync_at: datetime | None = None,
    pos_connection_id: str | None = None,
    environment: str = "sandbox",
) -> SyncResult:
    """
    Run an incremental sync for one connection.

    In production this is called for every active pos_connection
    whose historical_import_complete = True.
    """
    since = last_sync_at or (datetime.now(timezone.utc) - timedelta(hours=1))
    logger.info("Incremental sync for org=%s since=%s", org_id, since.isoformat())

    rate_limiter = SquareRateLimiter()
    async with SquareClient(access_token, environment, rate_limiter) as client:
        result = await run_incremental_sync(
            client=client,
            org_id=org_id,
            last_sync_at=since,
            pos_connection_id=pos_connection_id,
        )

    logger.info("Incremental sync done: %s", result.summary)

    # -- Update last_sync_at --
    # await db.update("pos_connections", pos_connection_id,
    #     last_sync_at=datetime.now(timezone.utc),
    #     last_sync_status=result.summary,
    # )

    return result


async def run_all_incremental_syncs() -> list[SyncResult]:
    """
    Cron entry point — iterate all active connections and sync each.

    In production:
        connections = await db.query('''
            SELECT * FROM pos_connections
            WHERE provider = 'square'
              AND status IN ('connected', 'syncing')
              AND historical_import_complete = TRUE
        ''')
    """
    # Placeholder: in production, loop over all connections
    logger.info("Incremental cron tick — scanning active Square connections")
    results: list[SyncResult] = []

    # Example single-connection run for sandbox testing:
    access_token = os.getenv("SQUARE_ACCESS_TOKEN", "")
    if access_token:
        result = await incremental_worker(
            access_token=access_token,
            org_id="test-org-001",
            environment=os.getenv("SQUARE_ENVIRONMENT", "sandbox"),
        )
        results.append(result)

    return results


# ---------------------------------------------------------------------------
# Standalone
# ---------------------------------------------------------------------------
async def _main() -> None:
    from dotenv import load_dotenv
    load_dotenv("/work/meridian/.env")

    results = await run_all_incremental_syncs()
    for i, r in enumerate(results):
        print(f"Connection {i+1}: {r.summary}")


if __name__ == "__main__":
    asyncio.run(_main())
