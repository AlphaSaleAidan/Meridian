"""
Email sending functions — all outbound email routes through here.

Each function renders a template, sends via Postal, and logs the result.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from .postal_client import PostalClient
from .templates import (
    welcome,
    onboarding_reminder,
    onboarding_complete,
    weekly_report,
    anomaly_alert,
    pos_connected,
    password_reset,
    invite,
    lead_assigned,
    trial_expiring,
    payment_receipt,
)

logger = logging.getLogger("meridian.email.send")

_client = PostalClient()
_FRONTEND = "https://meridian.tips"


async def _log_send(
    to: str,
    template: str,
    subject: str,
    result: dict,
    *,
    org_id: Optional[str] = None,
    tag: Optional[str] = None,
) -> None:
    """Log email send to the email_send_log table."""
    try:
        from ..db import init_db
        db = await init_db()
        if not db:
            return
        from uuid import uuid4
        await db.insert("email_send_log", {
            "id": str(uuid4()),
            "org_id": org_id,
            "to_address": to,
            "template": template,
            "subject": subject,
            "tag": tag,
            "status": result.get("status", "unknown"),
            "postal_message_id": result.get("message_id"),
            "error_detail": result.get("reason") or result.get("detail"),
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as exc:
        logger.debug("Email log write failed (non-critical): %s", exc)


async def send_welcome_email(
    to: str,
    first_name: str,
    *,
    org_id: Optional[str] = None,
    connect_url: Optional[str] = None,
) -> dict:
    login_url = f"{_FRONTEND}/customer/login"
    html = welcome.render(
        first_name=first_name,
        login_url=login_url,
        connect_url=connect_url or login_url,
    )
    subject = f"Welcome to Meridian, {first_name}!"
    result = await _client.send(to, subject, html, tag="welcome")
    await _log_send(to, "welcome", subject, result, org_id=org_id, tag="welcome")
    return result


async def send_onboarding_reminder(
    to: str,
    first_name: str,
    *,
    org_id: Optional[str] = None,
    portal: str = "us",
) -> dict:
    if portal == "canada":
        url = f"{_FRONTEND}/canada/portal/onboarding"
    else:
        url = f"{_FRONTEND}/customer/login"
    html = onboarding_reminder.render(first_name=first_name, onboarding_url=url)
    subject = f"{first_name}, finish your Meridian setup"
    result = await _client.send(to, subject, html, tag="onboarding_reminder")
    await _log_send(to, "onboarding_reminder", subject, result, org_id=org_id, tag="onboarding_reminder")
    return result


async def send_onboarding_complete(
    to: str,
    first_name: str,
    *,
    org_id: Optional[str] = None,
    portal: str = "us",
) -> dict:
    dashboard = f"{_FRONTEND}/canada/portal/dashboard" if portal == "canada" else f"{_FRONTEND}/app"
    html = onboarding_complete.render(first_name=first_name, dashboard_url=dashboard)
    subject = f"You're all set, {first_name}!"
    result = await _client.send(to, subject, html, tag="onboarding_complete")
    await _log_send(to, "onboarding_complete", subject, result, org_id=org_id, tag="onboarding_complete")
    return result


async def send_weekly_report(
    to: str,
    business_name: str,
    week_label: str,
    revenue: str,
    revenue_change: str,
    orders: str,
    avg_ticket: str,
    top_insights: list[str],
    *,
    org_id: Optional[str] = None,
) -> dict:
    html = weekly_report.render(
        business_name=business_name,
        week_label=week_label,
        revenue=revenue,
        revenue_change=revenue_change,
        orders=orders,
        avg_ticket=avg_ticket,
        top_insights=top_insights,
        dashboard_url=f"{_FRONTEND}/app",
    )
    subject = f"Weekly Report — {business_name}"
    result = await _client.send(to, subject, html, tag="weekly_report")
    await _log_send(to, "weekly_report", subject, result, org_id=org_id, tag="weekly_report")
    return result


async def send_anomaly_alert(
    to: str,
    business_name: str,
    alert_title: str,
    alert_detail: str,
    severity: str = "medium",
    *,
    org_id: Optional[str] = None,
) -> dict:
    html = anomaly_alert.render(
        business_name=business_name,
        alert_title=alert_title,
        alert_detail=alert_detail,
        severity=severity,
        dashboard_url=f"{_FRONTEND}/app/anomalies",
    )
    subject = f"[{severity.upper()}] {alert_title} — {business_name}"
    result = await _client.send(to, subject, html, tag="anomaly_alert")
    await _log_send(to, "anomaly_alert", subject, result, org_id=org_id, tag="anomaly_alert")
    return result


async def send_pos_connected(
    to: str,
    first_name: str,
    pos_name: str,
    location_name: str,
    *,
    org_id: Optional[str] = None,
) -> dict:
    html = pos_connected.render(
        first_name=first_name,
        pos_name=pos_name,
        location_name=location_name,
        dashboard_url=f"{_FRONTEND}/app",
    )
    subject = f"{pos_name} Connected — You're All Set!"
    result = await _client.send(to, subject, html, tag="pos_connected")
    await _log_send(to, "pos_connected", subject, result, org_id=org_id, tag="pos_connected")
    return result


async def send_password_reset(
    to: str,
    reset_url: str,
    *,
    org_id: Optional[str] = None,
) -> dict:
    html = password_reset.render(reset_url=reset_url)
    subject = "Reset Your Meridian Password"
    result = await _client.send(to, subject, html, tag="password_reset")
    await _log_send(to, "password_reset", subject, result, org_id=org_id, tag="password_reset")
    return result


async def send_invite(
    to: str,
    inviter_name: str,
    role: str,
    portal: str,
    invite_url: str,
    *,
    org_id: Optional[str] = None,
) -> dict:
    html = invite.render(
        inviter_name=inviter_name,
        role=role,
        portal=portal,
        invite_url=invite_url,
    )
    portal_label = "Meridian Canada" if portal == "canada" else "Meridian"
    subject = f"{inviter_name} invited you to {portal_label}"
    result = await _client.send(to, subject, html, tag="invite")
    await _log_send(to, "invite", subject, result, org_id=org_id, tag="invite")
    return result


async def send_lead_assigned(
    to: str,
    rep_name: str,
    lead_name: str,
    lead_business: str,
    lead_phone: str,
    lead_id: str,
    *,
    org_id: Optional[str] = None,
) -> dict:
    html = lead_assigned.render(
        rep_name=rep_name,
        lead_name=lead_name,
        lead_business=lead_business,
        lead_phone=lead_phone,
        portal_url=f"{_FRONTEND}/canada/portal/leads/{lead_id}",
    )
    subject = f"New Lead: {lead_name} at {lead_business}"
    result = await _client.send(to, subject, html, tag="lead_assigned")
    await _log_send(to, "lead_assigned", subject, result, org_id=org_id, tag="lead_assigned")
    return result


async def send_trial_expiring(
    to: str,
    first_name: str,
    days_remaining: int,
    *,
    org_id: Optional[str] = None,
) -> dict:
    html = trial_expiring.render(
        first_name=first_name,
        days_remaining=days_remaining,
        billing_url=f"{_FRONTEND}/app/settings",
    )
    subject = f"Your Meridian trial ends in {days_remaining} day{'s' if days_remaining != 1 else ''}"
    result = await _client.send(to, subject, html, tag="trial_expiring")
    await _log_send(to, "trial_expiring", subject, result, org_id=org_id, tag="trial_expiring")
    return result


async def send_payment_receipt(
    to: str,
    business_name: str,
    plan_name: str,
    amount: str,
    period: str,
    invoice_url: str,
    *,
    org_id: Optional[str] = None,
) -> dict:
    html = payment_receipt.render(
        business_name=business_name,
        plan_name=plan_name,
        amount=amount,
        period=period,
        invoice_url=invoice_url,
    )
    subject = f"Payment Receipt — {amount}"
    result = await _client.send(to, subject, html, tag="payment_receipt")
    await _log_send(to, "payment_receipt", subject, result, org_id=org_id, tag="payment_receipt")
    return result
