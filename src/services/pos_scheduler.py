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


def _acquire_lock(key: str, ttl_seconds: int) -> bool:
    """Best-effort cross-worker lock: the scheduler runs in EVERY uvicorn worker
    (--workers 4), so without this all 4 would sync/backfill the same connection
    at once. Returns True (proceed) if Redis is unavailable."""
    try:
        from ..db.cache import dashboard_cache
        r = getattr(dashboard_cache, "_redis", None)
        if r is None or not getattr(dashboard_cache, "_use_redis", False):
            return True
        return bool(r.set(f"lock:possync:{key}", "1", nx=True, ex=int(ttl_seconds)))
    except Exception:
        return True


async def _recover_backfill(org_id: str, provider: str, conn: dict):
    """A connection whose initial import never completed (historical_import_complete
    is false — backfill errored or the flag was never set) would otherwise be
    skipped forever and never sync new sales. Re-run the backfill: on success it
    sets historical_import_complete=true and incremental sync takes over; on
    failure run_backfill marks status=error so this won't loop."""
    if provider != "square":
        return  # only Square backfill is wired here; others heal via their own paths
    logger.info(f"Recovery backfill for {org_id}/{provider} (historical_import_complete=false)")
    try:
        from ..security.encryption import decrypt_token
        creds = conn.get("credentials_encrypted") or {}
        token = decrypt_token(creds.get("access_token", "") or conn.get("access_token_enc", ""))
        if not token:
            logger.warning(f"No token to recover backfill for {org_id}")
            return
        from ..workers.backfill import run_backfill
        await run_backfill(access_token=token, org_id=org_id, connection_id=conn["id"])
    except Exception as e:
        logger.error(f"Recovery backfill failed for {org_id}/{provider}: {e}")


async def _check_and_sync():
    """Find all connections due for sync and run them."""
    from ..db import _db_instance as db
    if not db:
        return

    try:
        # Include connections that never finished their initial import — they
        # used to be filtered out (historical_import_complete=true only) and so
        # were stranded forever, never syncing new sales.
        connections = await db.select(
            "pos_connections",
            filters={"status": "eq.connected"},
        )
    except Exception as e:
        logger.warning(f"Could not fetch connections (will retry next cycle): {e}")
        return

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

        # Only one worker handles a given connection per cycle.
        if not _acquire_lock(str(conn.get("id")), frequency * 60):
            continue

        if not conn.get("historical_import_complete"):
            await _recover_backfill(org_id, provider, conn)
            continue

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
