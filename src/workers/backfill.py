"""
Backfill Worker — Runs initial data import for a new connection.

This is triggered after a merchant completes the OAuth flow.
Runs as a background task — can take 1-30 minutes depending on
transaction volume (18 months of history).
"""
import asyncio
import json
import logging
import os
from datetime import datetime, timezone

from ..square.client import SquareClient
from ..square.sync_engine import SyncEngine, SyncResult
from ..db import get_db

logger = logging.getLogger("meridian.workers.backfill")


async def run_backfill(
    access_token: str,
    org_id: str,
    connection_id: str,
) -> SyncResult:
    """
    Execute full initial backfill for a merchant.

    Args:
        access_token: Square OAuth access token
        org_id: Meridian organization UUID
        connection_id: POS connection UUID

    Returns:
        SyncResult with all synced data and statistics
    """
    logger.info(f"Starting backfill for org={org_id}, connection={connection_id}")

    db = get_db()

    def on_progress(progress):
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

    # ── Persist to Supabase ──────────────────────────────
    if result.locations:
        await db.batch_upsert(
            "locations",
            result.locations,
            on_conflict="org_id,external_id",
        )

    if result.categories:
        await db.batch_upsert(
            "categories",
            result.categories,
            on_conflict="org_id,external_id",
        )

    if result.products:
        await db.batch_upsert(
            "products",
            result.products,
            on_conflict="org_id,external_id",
        )

    if result.transactions:
        await db.batch_upsert(
            "transactions",
            result.transactions,
            on_conflict="org_id,external_id",
        )

    if result.transaction_items:
        await db.batch_upsert(
            "transaction_items",
            result.transaction_items,
            on_conflict="transaction_id,external_id",
        )

    if result.inventory_snapshots:
        await db.batch_upsert(
            "inventory_snapshots",
            result.inventory_snapshots,
            on_conflict="org_id,product_id,location_id,snapshot_date",
        )

    logger.info(f"Backfill persisted for org={org_id}: {result.summary}")

    # ── Mark import complete ─────────────────────────────
    await db.update(
        "pos_connections",
        {
            "historical_import_complete": True,
            "last_sync_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
        filters={"id": f"eq.{connection_id}"},
    )
    logger.info(f"Marked connection {connection_id} historical_import_complete=True")

    # ── Trigger AI pipeline ──────────────────────────────
    try:
        from ..pipeline import MeridianPipeline

        pipeline = MeridianPipeline(
            org_id=org_id,
            square_token=access_token,
            supabase_url=os.environ.get("SUPABASE_URL", ""),
            supabase_key=os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
                or os.environ.get("SUPABASE_SERVICE_KEY", ""),
            pos_connection_id=connection_id,
        )
        await pipeline.run_full_sync()
        logger.info(f"AI pipeline completed for org={org_id}")
    except Exception as e:
        logger.error(f"AI pipeline failed for org={org_id}: {e}", exc_info=True)

    return result


async def run_backfill_cli():
    """CLI entry point for manual backfill testing."""
    from ..config import square as sq_config
    from ..db import init_db

    await init_db()

    result = await run_backfill(
        access_token=sq_config.access_token,
        org_id="test-org-001",
        connection_id="test-conn-001",
    )

    print("\n" + "=" * 60)
    print("BACKFILL RESULTS")
    print("=" * 60)
    print(json.dumps(result.summary, indent=2))

    return result
