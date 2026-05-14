"""
Daily Burn Rate Calculator — Tracks platform metrics and estimated costs.
Sends daily SMS summary to the admin.
"""
import logging
import os
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("meridian.analytics.burn_rate")

ADMIN_PHONE = os.environ.get("ADMIN_PHONE", "")
ADMIN_NAME = os.environ.get("ADMIN_NAME", "Aidan")


async def calculate_daily_burn_rate() -> dict:
    from ..db import get_db
    db = get_db()
    now = datetime.now(timezone.utc)
    yesterday = (now - timedelta(days=1)).isoformat()

    orgs = await db.select("organizations", filters={"is_active": "eq.true"})
    active_orgs = len(orgs) if orgs else 0

    insights = await db.select("insights", filters={"created_at": f"gte.{yesterday}"})
    insights_count = len(insights) if insights else 0

    leads = await db.select("deals", filters={"created_at": f"gte.{yesterday}"})
    leads_count = len(leads) if leads else 0

    notifs = await db.select("notifications", filters={"created_at": f"gte.{yesterday}"})
    notifs_count = len(notifs) if notifs else 0

    ai_cost = insights_count * 0.05
    sms_cost = notifs_count * 0.01
    infra_cost = 0.33
    total_daily = ai_cost + sms_cost + infra_cost
    monthly_projected = total_daily * 30

    return {
        "date": now.strftime("%Y-%m-%d"),
        "active_orgs": active_orgs,
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


async def send_burn_rate_sms():
    if not ADMIN_PHONE:
        logger.warning("ADMIN_PHONE not set — skipping burn rate SMS")
        return {"sent": False, "reason": "no_admin_phone"}

    from ..sms.client import send_sms

    try:
        metrics = await calculate_daily_burn_rate()
        c = metrics["costs"]

        message = (
            f"Meridian Daily ({metrics['date']})\n"
            f"---\n"
            f"Orgs: {metrics['active_orgs']} | Leads: {metrics['new_leads']}\n"
            f"Insights: {metrics['insights_generated']} | Notifs: {metrics['notifications_sent']}\n"
            f"---\n"
            f"Burn: ${c['total_daily']:.2f}/day (${c['monthly_projected']:.2f}/mo)\n"
            f"AI ${c['ai']:.2f} | SMS ${c['sms']:.2f} | Infra ${c['infra']:.2f}"
        )

        result = await send_sms(ADMIN_PHONE, message)
        logger.info(f"Burn rate SMS sent: daily=${c['total_daily']:.2f}")
        return {**result, "metrics": metrics}
    except Exception as e:
        logger.error(f"Burn rate SMS failed: {e}", exc_info=True)
        return {"sent": False, "reason": str(e)}
