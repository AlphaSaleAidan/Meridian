"""
Incremental Sync Worker — Runs every 15 minutes.

Fetches new/updated orders since last sync timestamp.
Only runs for connections where historical_import_complete = TRUE.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from ..square.client import SquareClient
from ..square.sync_engine import SyncEngine
from ..db.client import InMemoryDB

logger = logging.getLogger("meridian.workers.incremental")


async def run_incremental_sync(
    access_token: str,
    org_id: str,
    connection_id: str,
    last_sync_at: datetime | None = None,
    location_ids: list[str] | None = None,
    db: InMemoryDB | None = None,
) -> dict:
    """
    Fetch new/updated data since last sync.
    
    This runs every 15 minutes as a cron job.
    In production, iterates over all active connections.
    """
    db = db or InMemoryDB()
    since = last_sync_at or (datetime.now(timezone.utc) - timedelta(minutes=15))

    logger.info(f"Incremental sync for org={org_id} since {since.isoformat()}")

    async with SquareClient(access_token=access_token) as client:
        engine = SyncEngine(
            client=client,
            org_id=org_id,
            pos_connection_id=connection_id,
        )

        result = await engine.run_incremental_sync(
            since=since,
            location_ids=location_ids,
        )

    # Persist
    for txn in result.transactions:
        items = [
            item for item in result.transaction_items
            if item["transaction_id"] == txn["id"]
        ]
        await db.upsert_transaction(txn, items)

    logger.info(f"Incremental sync complete: {result.summary}")
    return result.summary


async def run_all_incremental_syncs():
    """
    Production entry point: iterate all active connections.
    
    Pseudocode (replace with real DB queries):
        connections = await db.query(GET_ACTIVE_CONNECTIONS)
        for conn in connections:
            await run_incremental_sync(
                access_token=decrypt(conn.access_token_enc),
                org_id=conn.org_id,
                connection_id=conn.id,
                last_sync_at=conn.last_sync_at,
            )
    """
    logger.info("Running incremental sync for all active connections...")
    # In production: loop through all connections from DB
    pass
