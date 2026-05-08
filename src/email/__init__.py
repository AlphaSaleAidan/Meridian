"""
Meridian Email — Postal-based email delivery.

All email sending goes through this module. Uses Postal (self-hosted,
MIT-licensed) as the mail delivery platform, replacing Resend/SendGrid.
"""
from .postal_client import PostalClient
from .send import (
    send_welcome_email,
    send_onboarding_reminder,
    send_onboarding_complete,
    send_weekly_report,
    send_anomaly_alert,
    send_pos_connected,
    send_password_reset,
    send_invite,
    send_lead_assigned,
    send_trial_expiring,
    send_payment_receipt,
)

__all__ = [
    "PostalClient",
    "send_welcome_email",
    "send_onboarding_reminder",
    "send_onboarding_complete",
    "send_weekly_report",
    "send_anomaly_alert",
    "send_pos_connected",
    "send_password_reset",
    "send_invite",
    "send_lead_assigned",
    "send_trial_expiring",
    "send_payment_receipt",
]
