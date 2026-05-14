"""
Celery Tasks — Background jobs for POS sync, AI analysis, and reports.

All tasks are async-safe via asyncio.run() bridge.
Rate-limited tasks for Square/Clover API calls.
"""
import asyncio

from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


def run_async(coro):
    """Run an async coroutine from a sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@shared_task(
    bind=True,
    name="src.workers.tasks.sync_pos_data",
    max_retries=3,
    default_retry_delay=30,
    rate_limit="8/s",
)
def sync_pos_data(self, org_id: str, pos_type: str = "square"):
    """Sync POS data for a single merchant. Rate-limited to respect API limits."""
    logger.info(f"Syncing {pos_type} data for {org_id}")

    async def _sync():
        from ..integrations.registry import get_sync_engine
        try:
            engine = get_sync_engine(pos_type)
        except ValueError:
            return {"status": "skipped", "reason": f"Unknown POS: {pos_type}"}

        return await engine.run_incremental_sync(org_id)

    try:
        result = run_async(_sync())
        logger.info(f"Sync complete for {org_id}: {result}")
        return {"org_id": org_id, "status": "synced", **result}
    except Exception as exc:
        logger.error(f"Sync failed for {org_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    name="src.workers.tasks.run_analysis",
    max_retries=3,
    default_retry_delay=30,
)
def run_analysis(self, org_id: str, include_report: bool = False):
    """Run full AI analysis pipeline for a merchant."""
    logger.info(f"Running analysis for {org_id}")

    async def _analyze():
        from ..db import init_db, close_db
        from ..ai.engine import MeridianAI

        db = await init_db()
        if not db:
            return {"org_id": org_id, "status": "error", "error": "DB unavailable"}

        try:
            ai = MeridianAI(db=db)
            result = await ai.analyze_merchant(
                org_id=org_id,
                days=30,
                include_forecasts=True,
                include_report=include_report,
            )
            return {"org_id": org_id, "status": "complete", **result.summary}
        finally:
            await close_db()

    try:
        result = run_async(_analyze())
        logger.info(f"Analysis complete for {org_id}: {result}")
        return result
    except Exception as exc:
        logger.error(f"Analysis failed for {org_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task(
    name="src.workers.tasks.generate_report",
    max_retries=2,
    default_retry_delay=30,
)
def generate_report(org_id: str):
    """Generate a weekly report for a single merchant."""
    logger.info(f"Generating report for {org_id}")

    async def _report():
        from ..db import init_db, close_db
        from ..ai.engine import MeridianAI

        db = await init_db()
        if not db:
            return {"org_id": org_id, "status": "error", "error": "DB unavailable"}

        try:
            ai = MeridianAI(db=db)
            result = await ai.analyze_merchant(
                org_id=org_id, days=7, include_forecasts=True, include_report=True,
            )
            return {"org_id": org_id, "status": "generated", "has_report": result.weekly_report is not None}
        finally:
            await close_db()

    return run_async(_report())


@shared_task(name="src.workers.tasks.run_nightly_analysis")
def run_nightly_analysis():
    """Nightly batch: sync + analyze all active merchants."""
    logger.info("Starting nightly analysis batch")

    async def _batch():
        from ..db import init_db, close_db

        db = await init_db()
        if not db:
            return {"status": "error", "error": "DB unavailable"}

        try:
            orgs = await db.query(
                "organizations",
                select="id, pos_type",
                filters={"status": "eq.active"},
            )

            results = []
            for org in orgs:
                sync_pos_data.apply_async(
                    args=[org["id"], org.get("pos_type", "square")],
                    countdown=0,
                )
                run_analysis.apply_async(
                    args=[org["id"]],
                    countdown=10,
                )
                results.append(org["id"])

            return {"status": "dispatched", "merchant_count": len(results)}
        finally:
            await close_db()

    return run_async(_batch())


@shared_task(name="src.workers.tasks.generate_weekly_reports")
def generate_weekly_reports():
    """Weekly batch: generate reports for all active merchants."""
    logger.info("Starting weekly report generation")

    async def _batch():
        from ..db import init_db, close_db

        db = await init_db()
        if not db:
            return {"status": "error", "error": "DB unavailable"}

        try:
            orgs = await db.query(
                "organizations",
                select="id",
                filters={"status": "eq.active"},
            )

            for org in orgs:
                generate_report.apply_async(args=[org["id"]])

            return {"status": "dispatched", "merchant_count": len(orgs)}
        finally:
            await close_db()

    return run_async(_batch())


@shared_task(
    bind=True,
    name="src.workers.tasks.train_swarm",
    max_retries=2,
    default_retry_delay=60,
)
def train_swarm(self, org_id: str = ""):
    """Run a swarm training cycle on the latest agent outputs."""
    logger.info(f"Training swarm{f' for {org_id}' if org_id else ''}")

    async def _train():
        from ..db import init_db, close_db
        from ..ai.swarm_trainer import get_swarm_trainer

        db = await init_db()
        if not db:
            return {"status": "error", "error": "DB unavailable"}

        try:
            trainer = get_swarm_trainer(db=db)
            outputs = await trainer._fetch_latest_outputs()
            if not outputs:
                return {"status": "skipped", "reason": "No new outputs to train on"}
            result = await trainer.run_training_cycle(outputs, ctx_org_id=org_id)
            return {"status": "trained", **result}
        finally:
            await close_db()

    try:
        result = run_async(_train())
        logger.info(f"Swarm training complete: {result}")
        return result
    except Exception as exc:
        logger.error(f"Swarm training failed: {exc}")
        raise self.retry(exc=exc)


@shared_task(name="src.workers.tasks.process_billing_renewals")
def process_billing_renewals():
    """Daily: create Square invoices for subscriptions due for renewal."""
    logger.info("Processing billing renewals")

    async def _renewals():
        from ..db import init_db, close_db
        from ..billing.billing_service import BillingService

        db = await init_db()
        if not db:
            return {"status": "error", "error": "DB unavailable"}

        try:
            billing = BillingService(db)
            await billing.process_renewals()
            return {"status": "complete"}
        finally:
            await close_db()

    return run_async(_renewals())


@shared_task(name="src.workers.tasks.train_swarm_batch")
def train_swarm_batch():
    """Train swarm on all active merchants' latest outputs."""
    logger.info("Starting batch swarm training")

    async def _batch():
        from ..db import init_db, close_db

        db = await init_db()
        if not db:
            return {"status": "error", "error": "DB unavailable"}

        try:
            orgs = await db.query(
                "organizations",
                select="id",
                filters={"status": "eq.active"},
            )

            for org in orgs:
                train_swarm.apply_async(args=[org["id"]])

            return {"status": "dispatched", "merchant_count": len(orgs)}
        finally:
            await close_db()

    return run_async(_batch())


@shared_task(name="src.workers.tasks.send_daily_burn_rate")
def send_daily_burn_rate():
    """Send daily burn rate SMS to admin."""

    async def _send():
        from ..db import init_db, close_db
        await init_db()
        try:
            from ..analytics.burn_rate import send_burn_rate_sms
            return await send_burn_rate_sms()
        finally:
            await close_db()

    return run_async(_send())


@shared_task(name="src.workers.tasks.ingest_scraped_data")
def ingest_scraped_data():
    """Ingest scraped articles into vector store for RAG."""
    logger.info("Ingesting scraped data into vector store")
    from pathlib import Path
    from ..inference.embeddings import ingest_scraper_output, stats

    data_dir = Path(__file__).parent.parent.parent / "data" / "scraped"
    if not data_dir.exists():
        return {"status": "skipped", "reason": "No scraped data directory"}

    count = ingest_scraper_output(data_dir)
    st = stats()
    logger.info(f"Ingestion complete: {count} new, {st['documents']} total docs")
    return {"status": "complete", "ingested": count, **st}


@shared_task(name="src.workers.tasks.batch_local_inference")
def batch_local_inference(prompts: list, system: str = "You are a business analytics assistant."):
    """Process a batch of prompts through local LLM (zero API cost)."""
    logger.info(f"Running batch local inference: {len(prompts)} prompts")
    from ..inference.local_llm import generate_batch

    results = generate_batch(prompts, system=system)
    return {"status": "complete", "count": len(results), "results": results}
