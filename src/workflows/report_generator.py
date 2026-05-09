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
    """Send weekly report email to merchant via Postal."""
    from ..db import init_db
    db = await init_db()
    if not db:
        return {"org_id": org_id, "status": "error", "error": "DB unavailable"}

    orgs = await db.select("organizations", filters={"id": f"eq.{org_id}"}, limit=1)
    if not orgs:
        return {"org_id": org_id, "status": "error", "error": "Org not found"}

    org = orgs[0]
    email = org.get("email") or org.get("contact_email")
    if not email:
        logger.warning(f"No email for org {org_id} — skipping report email")
        return {"org_id": org_id, "status": "skipped", "reason": "no_email"}

    from ..email.send import send_weekly_report
    result = await send_weekly_report(
        to=email,
        business_name=org.get("name", "Your Business"),
        week_label=report.get("week_label", "This Week"),
        revenue=report.get("revenue", "$0"),
        revenue_change=report.get("revenue_change", "+0%"),
        orders=str(report.get("orders", 0)),
        avg_ticket=report.get("avg_ticket", "$0"),
        top_insights=[i.get("title", i) if isinstance(i, dict) else str(i) for i in report.get("insights", [])[:5]],
        org_id=org_id,
    )
    logger.info(f"Report email for {org_id}: {result.get('status')}")
    return {"org_id": org_id, "status": result.get("status", "sent")}


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
