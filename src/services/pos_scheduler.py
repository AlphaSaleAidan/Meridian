"""
POS Sync Scheduler — Runs incremental syncs for all active connections.

Checks every 15 minutes. Each connection syncs at its own frequency
(Square: 15min, Toast: 30min, Clover: 30min — configurable per connection).

Started by the FastAPI lifespan handler in app.py.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("meridian.services.pos_scheduler")

_scheduler_task: asyncio.Task | None = None
_running = False

CHECK_INTERVAL_SECONDS = 900  # 15 minutes

PROVIDER_SYNC_MINUTES = {
    "square": 15,
    "toast": 30,
    "clover": 30,
    # All other API systems default to 60 minutes via .get(provider, 60)
}


async def _sync_loop():
    """Main scheduler loop — runs forever, checks for due syncs."""
    global _running
    _running = True
    logger.info("POS sync scheduler started (checking every %ds)", CHECK_INTERVAL_SECONDS)

    while _running:
        try:
            await _check_and_sync()
        except Exception as e:
            logger.error(f"Scheduler cycle error: {e}", exc_info=True)
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)


async def _check_and_sync():
    """Find all connections due for sync and run them."""
    from ..db import _db_instance as db
    if not db:
        return

    connections = await db.select(
        "pos_connections",
        filters={
            "status": "eq.connected",
            "historical_import_complete": "eq.true",
        },
    )

    if not connections:
        return

    now = datetime.now(timezone.utc)

    for conn in connections:
        provider = conn.get("provider", "")
        last_sync = conn.get("last_sync_at")
        frequency = PROVIDER_SYNC_MINUTES.get(provider, 60)

        if last_sync:
            if isinstance(last_sync, str):
                last_sync_dt = datetime.fromisoformat(last_sync.replace("Z", "+00:00"))
            else:
                last_sync_dt = last_sync
            due_at = last_sync_dt + timedelta(minutes=frequency)
            if now < due_at:
                continue

        org_id = conn.get("org_id", "")
        logger.info(f"Sync due for {org_id}/{provider} — starting incremental sync")

        try:
            from .pos_sync_runner import run_incremental
            await run_incremental(org_id, provider, conn)
        except Exception as e:
            logger.error(f"Scheduled sync failed for {org_id}/{provider}: {e}")


def start_scheduler():
    """Start the background sync scheduler. Call from app lifespan."""
    global _scheduler_task
    if _scheduler_task is not None:
        return
    _scheduler_task = asyncio.create_task(_sync_loop())
    logger.info("POS sync scheduler task created")


def stop_scheduler():
    """Stop the background sync scheduler."""
    global _running, _scheduler_task
    _running = False
    if _scheduler_task:
        _scheduler_task.cancel()
        _scheduler_task = None
    logger.info("POS sync scheduler stopped")
