"""
Worker: Square initial backfill.

Triggered once when a merchant first connects their Square account.
Pulls 18 months of historical data in monthly chunks:
  Locations → Catalog → Team Members → Orders → Inventory

In production this runs as a background task (Celery / Cloud Run Job / etc).
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone

from ..services.square.client import SquareClient
from ..services.square.rate_limiter import SquareRateLimiter
from ..services.square.sync_engine import SyncResult, run_initial_backfill

logger = logging.getLogger("meridian.workers.backfill")


async def backfill_worker(
    access_token: str,
    org_id: str,
    pos_connection_id: str | None = None,
    environment: str = "sandbox",
) -> SyncResult:
    """
    Execute a full 18-month backfill for one POS connection.

    Args:
        access_token: Decrypted Square access token.
        org_id: Meridian organization UUID.
        pos_connection_id: pos_connections.id (for tagging transactions).
        environment: "sandbox" or "production".

    Returns:
        SyncResult with counts and any errors.
    """
    logger.info("Starting backfill for org=%s env=%s", org_id, environment)
    started_at = datetime.now(timezone.utc)

    # -- Update connection status: 'syncing' --
    # await db.update("pos_connections", pos_connection_id, status="syncing",
    #                 historical_import_started_at=started_at)

    rate_limiter = SquareRateLimiter()
    async with SquareClient(access_token, environment, rate_limiter) as client:
        result = await run_initial_backfill(client, org_id, pos_connection_id)

    elapsed = (datetime.now(timezone.utc) - started_at).total_seconds()
    logger.info(
        "Backfill finished in %.1fs — %s | errors: %d",
        elapsed, result.summary, len(result.errors),
    )

    # -- Update connection status: 'connected' + mark complete --
    # await db.update("pos_connections", pos_connection_id,
    #     status="connected",
    #     historical_import_complete=True,
    #     historical_import_completed_at=datetime.now(timezone.utc),
    #     last_sync_at=datetime.now(timezone.utc),
    #     last_sync_status=result.summary,
    # )

    if result.errors:
        logger.warning("Backfill had %d errors: %s", len(result.errors), result.errors)
        # In production: push to dead letter queue / alert Slack

    return result


# ---------------------------------------------------------------------------
# Standalone execution (for testing / manual runs)
# ---------------------------------------------------------------------------
async def _main() -> None:
    from dotenv import load_dotenv
    load_dotenv("/work/meridian/.env")

    result = await backfill_worker(
        access_token=os.getenv("SQUARE_ACCESS_TOKEN", ""),
        org_id="test-org-001",
        environment=os.getenv("SQUARE_ENVIRONMENT", "sandbox"),
    )
    print(f"\n{'='*60}")
    print(f"BACKFILL RESULT: {result.summary}")
    if result.errors:
        print(f"ERRORS ({len(result.errors)}):")
        for e in result.errors:
            print(f"  • {e}")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(_main())
