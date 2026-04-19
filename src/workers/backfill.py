"""
Backfill Worker — Runs initial data import for a new connection.

This is triggered after a merchant completes the OAuth flow.
Runs as a background task — can take 1-30 minutes depending on
transaction volume (18 months of history).
"""
import asyncio
import json
import logging
from datetime import datetime, timezone

from ..square.client import SquareClient
from ..square.sync_engine import SyncEngine, SyncResult
from ..db.client import InMemoryDB

logger = logging.getLogger("meridian.workers.backfill")


async def run_backfill(
    access_token: str,
    org_id: str,
    connection_id: str,
    db: InMemoryDB | None = None,
) -> SyncResult:
    """
    Execute full initial backfill for a merchant.
    
    Args:
        access_token: Square OAuth access token
        org_id: Meridian organization UUID
        connection_id: POS connection UUID
        db: Database client (InMemoryDB for testing)
    
    Returns:
        SyncResult with all synced data and statistics
    """
    db = db or InMemoryDB()
    
    logger.info(f"Starting backfill for org={org_id}, connection={connection_id}")

    def on_progress(progress):
        """Log progress updates (in production, push to WebSocket/SSE)."""
        logger.info(
            f"Backfill progress: {progress.phase} — "
            f"{progress.detail} ({progress.progress_pct:.0f}%)"
        )

    async with SquareClient(access_token=access_token) as client:
        engine = SyncEngine(
            client=client,
            org_id=org_id,
            pos_connection_id=connection_id,
            on_progress=on_progress,
        )

        result = await engine.run_initial_backfill()

    # ── Persist to database ──────────────────────────────
    for loc in result.locations:
        await db.upsert_location(loc)

    for cat in result.categories:
        await db.upsert_category(cat)

    for product in result.products:
        await db.upsert_product(product)

    for txn in result.transactions:
        items = [
            item for item in result.transaction_items
            if item["transaction_id"] == txn["id"]
        ]
        await db.upsert_transaction(txn, items)

    for snapshot in result.inventory_snapshots:
        await db.upsert_inventory(snapshot)

    logger.info(f"Backfill complete for org={org_id}: {result.summary}")
    logger.info(f"DB stats: {db.stats()}")

    return result


async def run_backfill_cli():
    """CLI entry point for manual backfill testing."""
    from ..config import square as sq_config

    db = InMemoryDB()
    result = await run_backfill(
        access_token=sq_config.access_token,
        org_id="test-org-001",
        connection_id="test-conn-001",
        db=db,
    )

    print("\n" + "=" * 60)
    print("BACKFILL RESULTS")
    print("=" * 60)
    print(json.dumps(result.summary, indent=2))
    print("\nDB Stats:")
    print(json.dumps(db.stats(), indent=2))

    if db.transactions:
        print("\nTop Products:")
        for p in db.top_products(5):
            print(f"  {p['name']}: {p['times_sold']} sold, ${p['revenue_cents']/100:,.2f}")

    return result, db
