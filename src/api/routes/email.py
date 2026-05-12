"""
Email API Routes — Frontend-facing endpoints for sending email via Postal.

  POST /api/email/send          → Send an email using a named template
  GET  /api/email/log           → List email send log (admin)
  GET  /api/email/stats         → Aggregate email stats (admin)
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, EmailStr

logger = logging.getLogger("meridian.api.email")

router = APIRouter(prefix="/api/email", tags=["email"])


class SendEmailRequest(BaseModel):
    template: str
    to: EmailStr
    first_name: Optional[str] = None
    org_id: Optional[str] = None
    portal: str = "us"
    extra: dict = {}


@router.post("/send")
async def send_email(req: SendEmailRequest):
    """Send an email using the specified template."""
    from ...email import send as email_send

    fn_map = {
        "welcome": lambda: email_send.send_welcome_email(
            to=req.to, first_name=req.first_name or "there", org_id=req.org_id,
        ),
        "onboarding_reminder": lambda: email_send.send_onboarding_reminder(
            to=req.to, first_name=req.first_name or "there", org_id=req.org_id, portal=req.portal,
        ),
        "onboarding_complete": lambda: email_send.send_onboarding_complete(
            to=req.to, first_name=req.first_name or "there", org_id=req.org_id, portal=req.portal,
        ),
        "password_reset": lambda: email_send.send_password_reset(
            to=req.to, reset_url=req.extra.get("reset_url", ""), org_id=req.org_id,
        ),
        "invite": lambda: email_send.send_invite(
            to=req.to,
            inviter_name=req.extra.get("inviter_name", "A teammate"),
            role=req.extra.get("role", "member"),
            portal=req.portal,
            invite_url=req.extra.get("invite_url", ""),
            org_id=req.org_id,
        ),
        "weekly_report": lambda: email_send.send_weekly_report(
            to=req.to,
            business_name=req.extra.get("business_name", "Your Business"),
            week_label=req.extra.get("week_label", "This Week"),
            revenue=req.extra.get("revenue", "$0"),
            revenue_change=req.extra.get("revenue_change", "+0%"),
            orders=req.extra.get("orders", "0"),
            avg_ticket=req.extra.get("avg_ticket", "$0"),
            top_insights=req.extra.get("top_insights", []),
            org_id=req.org_id,
        ),
        "anomaly_alert": lambda: email_send.send_anomaly_alert(
            to=req.to,
            business_name=req.extra.get("business_name", "Your Business"),
            alert_title=req.extra.get("alert_title", "Anomaly Detected"),
            alert_detail=req.extra.get("alert_detail", ""),
            severity=req.extra.get("severity", "medium"),
            org_id=req.org_id,
        ),
        "pos_connected": lambda: email_send.send_pos_connected(
            to=req.to,
            first_name=req.first_name or "there",
            pos_name=req.extra.get("pos_name", "Square"),
            location_name=req.extra.get("location_name", "Your Location"),
            org_id=req.org_id,
        ),
        "lead_assigned": lambda: email_send.send_lead_assigned(
            to=req.to,
            rep_name=req.extra.get("rep_name", ""),
            lead_name=req.extra.get("lead_name", ""),
            lead_business=req.extra.get("lead_business", ""),
            lead_phone=req.extra.get("lead_phone", ""),
            lead_id=req.extra.get("lead_id", ""),
            org_id=req.org_id,
        ),
        "trial_expiring": lambda: email_send.send_trial_expiring(
            to=req.to,
            first_name=req.first_name or "there",
            days_remaining=int(req.extra.get("days_remaining", "3")),
            org_id=req.org_id,
        ),
        "payment_receipt": lambda: email_send.send_payment_receipt(
            to=req.to,
            business_name=req.extra.get("business_name", "Your Business"),
            plan_name=req.extra.get("plan_name", "Standard"),
            amount=req.extra.get("amount", "$0.00"),
            period=req.extra.get("period", "Monthly"),
            invoice_url=req.extra.get("invoice_url", ""),
            org_id=req.org_id,
        ),
        "sla_signed": lambda: email_send.send_sla_signed(
            to=req.to,
            business_name=req.extra.get("business_name", ""),
            rep_name=req.extra.get("rep_name", ""),
            signed_by=req.extra.get("signed_by", ""),
            signed_date=req.extra.get("signed_date", ""),
            provider_signatory=req.extra.get("provider_signatory", "Aidan Pierce, Founder & CEO"),
            org_id=req.org_id,
        ),
        "customer_credentials": lambda: email_send.send_customer_credentials(
            to=req.to,
            business_name=req.extra.get("business_name", ""),
            email=req.extra.get("email", req.to),
            password=req.extra.get("password", ""),
            login_url=req.extra.get("login_url", "https://meridian.tips/canada/login"),
            rep_name=req.extra.get("rep_name", ""),
            org_id=req.org_id,
        ),
    }

    handler = fn_map.get(req.template)
    if not handler:
        raise HTTPException(400, f"Unknown template: {req.template}")

    result = await handler()
    return result


@router.get("/log")
async def email_log(
    org_id: Optional[str] = Query(None),
    template: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    """Fetch email send log entries."""
    from ...db import get_db
    db = get_db()

    filters = {}
    if org_id:
        filters["org_id"] = f"eq.{org_id}"
    if template:
        filters["template"] = f"eq.{template}"

    rows = await db.select(
        "email_send_log",
        filters=filters,
        limit=limit,
        offset=offset,
        order="created_at.desc",
    )
    return {"data": rows, "count": len(rows)}


@router.get("/stats")
async def email_stats(org_id: Optional[str] = Query(None)):
    """Aggregate email delivery stats."""
    from ...db import get_db
    db = get_db()

    org_filter = f"AND org_id = '{org_id}'" if org_id else ""

    result = await db.execute(f"""
        SELECT
            COUNT(*)::int AS total_sent,
            COUNT(*) FILTER (WHERE postal_status = 'delivered')::int AS delivered,
            COUNT(*) FILTER (WHERE postal_status = 'bounced')::int AS bounced,
            COUNT(*) FILTER (WHERE opened_at IS NOT NULL)::int AS opened,
            COUNT(*) FILTER (WHERE clicked_at IS NOT NULL)::int AS clicked,
            COUNT(*) FILTER (WHERE status = 'error')::int AS errors
        FROM email_send_log
        WHERE 1=1 {org_filter}
    """)

    row = result[0] if result else {}
    total = row.get("total_sent", 0)
    return {
        "total_sent": total,
        "delivered": row.get("delivered", 0),
        "bounced": row.get("bounced", 0),
        "opened": row.get("opened", 0),
        "clicked": row.get("clicked", 0),
        "errors": row.get("errors", 0),
        "open_rate": round(row.get("opened", 0) / total * 100, 1) if total else 0,
        "click_rate": round(row.get("clicked", 0) / total * 100, 1) if total else 0,
    }
