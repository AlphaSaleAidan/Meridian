"""
Nightly Analysis Flow — Full merchant analysis pipeline.

Runs nightly via Prefect scheduler:
  1. Sync POS data for all active merchants
  2. Run 22 AI agents in tiered batches
  3. Generate insights, forecasts, alerts
  4. Persist everything to Supabase
"""
import asyncio
import logging

from prefect import flow, task

logger = logging.getLogger("meridian.workflows.nightly")


@task(retries=3, retry_delay_seconds=30, log_prints=True)
async def sync_pos_data(org_id: str, pos_type: str) -> dict:
    """Sync latest POS data for a merchant."""
    from ..integrations.registry import get_sync_engine
    try:
        engine = get_sync_engine(pos_type)
    except ValueError:
        return {"org_id": org_id, "status": "skipped", "reason": f"Unknown POS: {pos_type}"}

    result = await engine.run_incremental_sync(org_id)
    logger.info(f"Synced {pos_type} data for {org_id}: {result}")
    return {"org_id": org_id, "pos_type": pos_type, "status": "synced", **result}


@task(retries=2, retry_delay_seconds=10, log_prints=True)
async def validate_merchant_data(org_id: str) -> dict:
    """Run data quality checks before AI analysis."""
    from ..db import init_db, close_db

    db = await init_db()
    if not db:
        return {"org_id": org_id, "passed": True, "reason": "DB unavailable — skip validation"}

    try:
        txns = await db.get_transaction_details(org_id, days=30)
        products = await db.get_product_performance(org_id, days=30)

        from ..data_quality.runner import validate_merchant_data as validate
        result = validate(
            transactions=[dict(t) for t in txns],
            products=[dict(p) for p in products],
        )
        result["org_id"] = org_id
        return result
    except Exception as e:
        logger.warning(f"Data validation skipped for {org_id}: {e}")
        return {"org_id": org_id, "overall_passed": True, "reason": f"validation_error: {e}"}
    finally:
        await close_db()


@task(retries=3, retry_delay_seconds=30, log_prints=True)
async def run_merchant_analysis(org_id: str, include_report: bool = False) -> dict:
    """Run full AI analysis pipeline for a single merchant."""
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
        return {
            "org_id": org_id,
            "status": "complete",
            **result.summary,
        }
    finally:
        await close_db()


@task(retries=2, retry_delay_seconds=30, log_prints=True)
async def fetch_active_merchants() -> list[dict]:
    """Get all active merchants with POS connections."""
    from ..db import init_db, close_db

    db = await init_db()
    if not db:
        return []

    try:
        orgs = await db.query(
            "organizations",
            select="id, pos_type",
            filters={"status": "eq.active"},
        )
        return [{"org_id": r["id"], "pos_type": r.get("pos_type", "square")} for r in orgs]
    finally:
        await close_db()


@flow(
    name="nightly-merchant-analysis",
    description="Sync POS data and run full AI analysis for all active merchants",
    retries=1,
    retry_delay_seconds=60,
    timeout_seconds=3600,
)
async def nightly_analysis(batch_size: int = 10, include_reports: bool = False):
    """
    Nightly analysis pipeline.

    1. Fetch all active merchants
    2. Sync POS data in batches (respect rate limits)
    3. Run AI analysis for each merchant
    4. Optionally generate weekly reports (Sunday only)
    """
    merchants = await fetch_active_merchants()
    if not merchants:
        logger.warning("No active merchants found — skipping nightly analysis")
        return {"status": "skipped", "reason": "no_merchants"}

    logger.info(f"Starting nightly analysis for {len(merchants)} merchants")

    sync_results = []
    for i in range(0, len(merchants), batch_size):
        batch = merchants[i : i + batch_size]
        results = await asyncio.gather(
            *[sync_pos_data(m["org_id"], m["pos_type"]) for m in batch],
            return_exceptions=True,
        )
        for r in results:
            if isinstance(r, Exception):
                sync_results.append({"status": "error", "error": str(r)})
            else:
                sync_results.append(r)

    # Step 2: Validate data quality before analysis
    validation_results = []
    for i in range(0, len(merchants), batch_size):
        batch = merchants[i : i + batch_size]
        results = await asyncio.gather(
            *[validate_merchant_data(m["org_id"]) for m in batch],
            return_exceptions=True,
        )
        for r in results:
            if isinstance(r, Exception):
                validation_results.append({"overall_passed": True})
            else:
                validation_results.append(r)

    valid_merchants = [
        m for m, v in zip(merchants, validation_results)
        if v.get("overall_passed", True)
    ]
    logger.info(f"Data quality: {len(valid_merchants)}/{len(merchants)} passed validation")

    # Step 3: Run AI analysis on validated merchants
    analysis_results = []
    for i in range(0, len(valid_merchants), batch_size):
        batch = valid_merchants[i : i + batch_size]
        results = await asyncio.gather(
            *[
                run_merchant_analysis(m["org_id"], include_report=include_reports)
                for m in batch
            ],
            return_exceptions=True,
        )
        for r in results:
            if isinstance(r, Exception):
                analysis_results.append({"status": "error", "error": str(r)})
            else:
                analysis_results.append(r)

    succeeded = sum(1 for r in analysis_results if r.get("status") == "complete")
    failed = len(analysis_results) - succeeded

    # Step 4: Post-analysis training for successfully analyzed merchants
    import os
    if os.environ.get("ENABLE_SWARM_TRAINING", "1") == "1":
        try:
            from ..services.training_scheduler import run_post_analysis_training
            trained_orgs = [
                m["org_id"] for m, r in zip(valid_merchants, analysis_results)
                if r.get("status") == "complete"
            ]
            if trained_orgs:
                training_tasks = await asyncio.gather(
                    *[run_post_analysis_training(oid) for oid in trained_orgs[:batch_size]],
                    return_exceptions=True,
                )
                trained_ok = sum(
                    1 for t in training_tasks
                    if not isinstance(t, Exception) and isinstance(t, dict) and t.get("status") == "complete"
                )
                logger.info(f"Post-analysis training: {trained_ok}/{len(trained_orgs)} orgs trained")
        except Exception as e:
            logger.warning(f"Post-analysis training failed: {e}")

    logger.info(
        f"Nightly analysis complete: {succeeded} succeeded, {failed} failed "
        f"out of {len(merchants)} merchants"
    )

    return {
        "status": "complete",
        "total_merchants": len(merchants),
        "synced": sum(1 for r in sync_results if r.get("status") == "synced"),
        "analyzed": succeeded,
        "failed": failed,
    }
