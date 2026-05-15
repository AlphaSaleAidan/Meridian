"""
Training Scheduler — Keeps the AI swarm evolving.

Integrates with the existing pos_scheduler pattern:
  - Runs alongside POS sync
  - Trains after every nightly analysis
  - Consolidates patterns every 6 hours
  - Triggered by real-time events (webhook calls)

Started by the FastAPI lifespan handler in app.py.
"""
import asyncio
import logging
import time
from datetime import datetime, timezone

logger = logging.getLogger("meridian.services.training_scheduler")

_training_task: asyncio.Task | None = None
_running = False

CONSOLIDATION_INTERVAL = 21600  # 6 hours in seconds
POST_ANALYSIS_DELAY = 30  # seconds to wait after nightly analysis before training


async def _consolidation_loop():
    """Background loop: consolidate patterns every 6 hours."""
    global _running
    _running = True
    logger.info(
        "Training scheduler started (consolidation every %ds)",
        CONSOLIDATION_INTERVAL,
    )

    while _running:
        try:
            await _run_consolidation()
        except Exception as e:
            logger.error(f"Consolidation cycle error: {e}", exc_info=True)
        await asyncio.sleep(CONSOLIDATION_INTERVAL)


async def _run_consolidation():
    """Run pattern consolidation: prune weak patterns, reinforce strong ones."""
    from ..ai.swarm_trainer import get_swarm_trainer

    trainer = get_swarm_trainer()
    outputs = await trainer._fetch_latest_outputs()
    if not outputs:
        logger.debug("No pending outputs for consolidation")
        return

    start = time.monotonic()
    result = await trainer.run_training_cycle(outputs)
    elapsed = time.monotonic() - start

    logger.info(
        "Consolidation complete in %.1fs: %d agents graded, %d patterns stored",
        elapsed,
        result.get("agents_graded", 0),
        result.get("patterns_stored", 0),
    )


async def run_training_cycle(org_id: str | None = None):
    """Run a training cycle, optionally for a specific org.

    Called by:
      - POST /api/intelligence/train (manual trigger)
      - nightly_analysis (post-analysis callback)
      - webhook handlers (real-time learning)
    """
    from ..ai.swarm_trainer import get_swarm_trainer
    from ..db import _db_instance as db

    trainer = get_swarm_trainer(db=db)

    # Try to get org-specific outputs
    outputs = None
    if org_id and db and hasattr(db, "get_latest_agent_outputs"):
        try:
            outputs = await db.get_latest_agent_outputs(org_id)
        except Exception as e:
            logger.warning(f"Failed to fetch outputs for org {org_id}: {e}")

    # Fall back to general pending outputs
    if not outputs:
        outputs = await trainer._fetch_latest_outputs()

    if not outputs:
        logger.info("No agent outputs available for training")
        return {
            "status": "no_data",
            "message": "No pending agent outputs to train on",
            "org_id": org_id,
        }

    start = time.monotonic()
    result = await trainer.run_training_cycle(outputs, ctx_org_id=org_id or "")
    elapsed = time.monotonic() - start

    logger.info(
        "Training cycle for org=%s complete in %.1fs: %s",
        org_id or "all",
        elapsed,
        result,
    )

    return {
        "status": "complete",
        "org_id": org_id,
        "duration_seconds": round(elapsed, 2),
        **result,
    }


async def run_post_analysis_training(org_id: str):
    """Run training immediately after a nightly analysis completes.

    Waits a short delay to ensure all agent outputs are persisted,
    then kicks off a training cycle for the specific org.
    """
    logger.info(
        "Post-analysis training queued for org=%s (delay=%ds)",
        org_id,
        POST_ANALYSIS_DELAY,
    )
    await asyncio.sleep(POST_ANALYSIS_DELAY)

    try:
        result = await run_training_cycle(org_id=org_id)
        logger.info("Post-analysis training for org=%s: %s", org_id, result)
        return result
    except Exception as e:
        logger.error(
            "Post-analysis training failed for org=%s: %s", org_id, e, exc_info=True
        )
        return {"status": "error", "org_id": org_id, "error": str(e)}


async def handle_webhook_training(org_id: str, event_type: str):
    """Handle real-time training triggered by webhook events.

    Certain events (large transactions, anomalies, new products) trigger
    an immediate training cycle to update agent understanding.
    """
    TRAINABLE_EVENTS = {
        "payment.completed",
        "order.created",
        "inventory.count.updated",
        "catalog.version.updated",
        "customer.created",
    }

    if event_type not in TRAINABLE_EVENTS:
        return {"status": "skipped", "reason": f"Event {event_type} not trainable"}

    logger.info(
        "Webhook-triggered training for org=%s, event=%s", org_id, event_type
    )

    try:
        result = await run_training_cycle(org_id=org_id)
        return result
    except Exception as e:
        logger.error(
            "Webhook training failed for org=%s: %s", org_id, e, exc_info=True
        )
        return {"status": "error", "org_id": org_id, "error": str(e)}


def get_scheduler_status() -> dict:
    """Return current state of the training scheduler."""
    from ..ai.swarm_trainer import get_swarm_trainer

    trainer = get_swarm_trainer()
    stats = trainer.get_training_stats()

    return {
        "scheduler_running": _running,
        "consolidation_interval_seconds": CONSOLIDATION_INTERVAL,
        "trainer_stats": stats,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def start_training_scheduler():
    """Start the background training scheduler. Call from app lifespan."""
    global _training_task
    if _training_task is not None:
        return
    _training_task = asyncio.create_task(_consolidation_loop())
    logger.info("Training scheduler task created")


def stop_training_scheduler():
    """Stop the background training scheduler."""
    global _running, _training_task
    _running = False
    if _training_task:
        _training_task.cancel()
        _training_task = None
    logger.info("Training scheduler stopped")
