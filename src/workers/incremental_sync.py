"""
Incremental Sync Worker — Runs every 15 minutes.

Fetches new/updated orders since last sync timestamp.
Only runs for connections where historical_import_complete = TRUE.
"""
import logging
from datetime import datetime, timedelta, timezone

from ..square.client import SquareClient
from ..square.sync_engine import SyncEngine
from ..db import get_db

logger = logging.getLogger("meridian.workers.incremental")


async def run_incremental_sync(
    access_token: str,
    org_id: str,
    connection_id: str,
    last_sync_at: datetime | None = None,
    location_ids: list[str] | None = None,
) -> dict:
    """
    Fetch new/updated data since last sync.

    This runs every 15 minutes as a cron job.
    In production, iterates over all active connections.
    """
    db = get_db()
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

    if result.transactions:
        await db.batch_upsert("transactions", result.transactions, on_conflict="org_id,external_id")
    if result.transaction_items:
        await db.batch_upsert("transaction_items", result.transaction_items, on_conflict="transaction_id,external_id")

    logger.info(f"Incremental sync complete: {result.summary}")
    return result.summary


async def run_all_incremental_syncs():
    """Production entry point: iterate all active connections."""
    logger.info("Running incremental sync for all active connections...")

    db = get_db()

    connections = await db.select(
        "pos_connections",
        filters={
            "status": "eq.connected",
            "historical_import_complete": "eq.true",
        },
    )

    if not connections:
        logger.info("No active connections found for incremental sync")
        return

    logger.info(f"Found {len(connections)} connections to sync")

    for conn in connections:
        conn_id = conn.get("id", "unknown")
        org_id = conn.get("org_id", "unknown")
        try:
            from ..security.encryption import decrypt_token
            access_token = decrypt_token(conn.get("access_token_encrypted", ""))

            if not access_token:
                logger.warning(f"No access token for connection {conn_id}")
                continue

            last_sync = None
            if conn.get("last_sync_at"):
                last_sync = datetime.fromisoformat(conn["last_sync_at"].replace("Z", "+00:00"))

            await run_incremental_sync(
                access_token=access_token,
                org_id=org_id,
                connection_id=conn_id,
                last_sync_at=last_sync,
                location_ids=conn.get("location_ids"),
            )

            await db.update(
                "pos_connections",
                {"last_sync_at": datetime.now(timezone.utc).isoformat(), "updated_at": datetime.now(timezone.utc).isoformat()},
                filters={"id": f"eq.{conn_id}"},
            )

            import os
            from ..pipeline import MeridianPipeline
            pipeline = MeridianPipeline(
                org_id=org_id,
                square_token=access_token,
                supabase_url=os.environ.get("SUPABASE_URL", ""),
                supabase_key=os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "") or os.environ.get("SUPABASE_SERVICE_KEY", ""),
                pos_connection_id=conn_id,
            )
            await pipeline.run_full_sync()
            logger.info(f"Incremental sync + AI pipeline complete for org={org_id}")

        except Exception as e:
            logger.error(f"Incremental sync failed for connection {conn_id} (org={org_id}): {e}", exc_info=True)
            continue
