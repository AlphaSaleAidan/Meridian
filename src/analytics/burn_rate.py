"""
Daily Burn Rate Calculator — Tracks platform metrics and estimated costs.
Sends a daily summary email to the admin.
"""
import logging
import os
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("meridian.analytics.burn_rate")

# Leads are stored per market; there is no combined table.
LEAD_TABLES = ("canada_leads", "us_leads")


async def calculate_daily_burn_rate() -> dict:
    from ..db import get_db
    db = get_db()
    now = datetime.now(timezone.utc)
    yesterday = (now - timedelta(days=1)).isoformat()

    orgs = await db.select("organizations", columns="pos_connection_status")
    total_orgs = len(orgs)
    connected_orgs = sum(1 for o in orgs if o.get("pos_connection_status") == "connected")

    insights = await db.select("insights", filters={"created_at": f"gte.{yesterday}"})
    insights_count = len(insights)

    leads_count = 0
    for table in LEAD_TABLES:
        rows = await db.select(table, columns="id", filters={"created_at": f"gte.{yesterday}"})
        leads_count += len(rows)

    notifs = await db.select("notifications", filters={"created_at": f"gte.{yesterday}"})
    notifs_count = len(notifs)

    ai_cost = insights_count * 0.05
    sms_cost = notifs_count * 0.01
    infra_cost = 0.33
    total_daily = ai_cost + sms_cost + infra_cost
    monthly_projected = total_daily * 30

    return {
        "date": now.strftime("%Y-%m-%d"),
        "total_orgs": total_orgs,
        "connected_orgs": connected_orgs,
        "insights_generated": insights_count,
        "new_leads": leads_count,
        "notifications_sent": notifs_count,
        "costs": {
            "ai": round(ai_cost, 2),
            "sms": round(sms_cost, 2),
            "infra": round(infra_cost, 2),
            "total_daily": round(total_daily, 2),
            "monthly_projected": round(monthly_projected, 2),
        },
    }


def _render_html(m: dict) -> str:
    c = m["costs"]
    rows = [
        ("Organizations", f"{m['total_orgs']} ({m['connected_orgs']} POS-connected)"),
        ("New leads", m["new_leads"]),
        ("Insights generated", m["insights_generated"]),
        ("Notifications sent", m["notifications_sent"]),
        ("AI cost", f"${c['ai']:.2f}"),
        ("SMS cost", f"${c['sms']:.2f}"),
        ("Infra cost", f"${c['infra']:.2f}"),
    ]
    cells = "".join(
        f"<tr><td style='padding:6px 16px 6px 0;color:#555'>{label}</td>"
        f"<td style='padding:6px 0;font-weight:600'>{value}</td></tr>"
        for label, value in rows
    )
    return (
        f"<div style='font-family:system-ui,sans-serif;font-size:14px;color:#111'>"
        f"<h2 style='margin:0 0 4px'>Meridian daily burn rate</h2>"
        f"<p style='margin:0 0 16px;color:#666'>{m['date']}</p>"
        f"<table style='border-collapse:collapse'>{cells}</table>"
        f"<p style='margin:16px 0 0;font-size:16px'>"
        f"<strong>${c['total_daily']:.2f}/day</strong> "
        f"<span style='color:#666'>(${c['monthly_projected']:.2f}/mo projected)</span></p>"
        f"</div>"
    )


async def send_burn_rate_report() -> dict:
    """Email the daily burn-rate summary to the admin.

    Raises on failure so the scheduled task surfaces as failed rather than
    reporting success while sending nothing.
    """
    # Importing config is what loads .env; nothing else in the Celery task
    # chain does it, so read the recipient at call time rather than at import.
    from .. import config  # noqa: F401
    from ..email import PostalClient

    admin_email = os.environ.get("ADMIN_EMAIL", "")
    if not admin_email:
        raise RuntimeError("ADMIN_EMAIL not set — cannot deliver daily burn-rate report")

    metrics = await calculate_daily_burn_rate()
    c = metrics["costs"]

    result = await PostalClient().send(
        admin_email,
        f"Meridian daily burn rate — {metrics['date']} (${c['total_daily']:.2f})",
        _render_html(metrics),
        tag="burn_rate",
    )

    if result.get("status") != "sent":
        raise RuntimeError(f"Burn-rate email not delivered: {result}")

    logger.info("Burn rate email sent: daily=$%.2f", c["total_daily"])
    return {"sent": True, "metrics": metrics, "delivery": result}
