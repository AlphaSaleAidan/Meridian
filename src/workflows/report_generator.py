"""
Weekly Report Generation Flow — Email-ready merchant reports.

Runs weekly (Sunday evening). Generates and optionally emails
a comprehensive report for each active merchant.
"""
import logging
from datetime import datetime, timezone

from prefect import flow, task

logger = logging.getLogger("meridian.workflows.reports")


@task(retries=3, retry_delay_seconds=30, log_prints=True)
async def generate_merchant_report(org_id: str) -> dict:
    """Generate a weekly report for a single merchant."""
    from ..db import init_db, close_db
    from ..ai.engine import MeridianAI

    db = await init_db()
    if not db:
        return {"org_id": org_id, "status": "error", "error": "DB unavailable"}

    try:
        ai = MeridianAI(db=db)
        result = await ai.analyze_merchant(
            org_id=org_id,
            days=7,
            include_forecasts=True,
            include_report=True,
        )

        if result.weekly_report:
            return {
                "org_id": org_id,
                "status": "generated",
                "report": result.weekly_report,
                "insights_count": len(result.insights),
                "alerts_count": len(result.alerts),
            }
        return {"org_id": org_id, "status": "empty", "reason": "No report generated"}
    finally:
        await close_db()


@task(retries=2, retry_delay_seconds=30, log_prints=True)
async def send_report_email(org_id: str, report: dict) -> dict:
    """Send weekly report email to merchant. Placeholder for email integration."""
    logger.info(f"Email report for {org_id} — {len(report.get('sections', []))} sections")
    return {"org_id": org_id, "status": "sent"}


@flow(
    name="weekly-report-generator",
    description="Generate and email weekly analysis reports for all merchants",
    retries=1,
    retry_delay_seconds=60,
    timeout_seconds=3600,
)
async def weekly_report_flow(send_emails: bool = False):
    """
    Weekly report pipeline.

    1. Fetch all active merchants
    2. Generate weekly report for each
    3. Optionally email reports
    """
    from .nightly_analysis import fetch_active_merchants
    import asyncio

    merchants = await fetch_active_merchants()
    if not merchants:
        return {"status": "skipped", "reason": "no_merchants"}

    logger.info(f"Generating weekly reports for {len(merchants)} merchants")

    results = []
    for merchant in merchants:
        report_result = await generate_merchant_report(merchant["org_id"])
        results.append(report_result)

        if send_emails and report_result.get("status") == "generated":
            await send_report_email(merchant["org_id"], report_result["report"])

    generated = sum(1 for r in results if r.get("status") == "generated")
    logger.info(f"Weekly reports complete: {generated}/{len(merchants)} generated")

    return {
        "status": "complete",
        "total": len(merchants),
        "generated": generated,
        "emailed": generated if send_emails else 0,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
