"""
CASL (Canada Anti-Spam Legislation) consent guard.

Checks consent before sending commercial electronic messages (CEMs).
Transactional messages (receipts, security alerts, etc.) are exempt.
"""
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine

import httpx

logger = logging.getLogger("meridian.compliance.casl")

_SAFE_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")

COMMERCIAL_TYPES: set[str] = {
    "weekly_digest", "monthly_report", "feature_announcement",
    "upgrade_prompt", "lead_outreach", "newsletter",
    "promotional", "demo_followup", "re_engagement",
}

TRANSACTIONAL_TYPES: set[str] = {
    "welcome_sr", "password_reset", "onboarding_complete",
    "phone_order_notification", "breach_notification", "invoice",
    "receipt", "account_suspension", "security_alert",
    "recruit_accepted", "recruit_rejected",
}


def _get_supabase() -> tuple[str, str]:
    url = os.environ.get("SUPABASE_URL", "")
    key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        or os.environ.get("SUPABASE_SERVICE_KEY", "")
    )
    return url, key


def _headers(service_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {service_key}",
        "apikey": service_key,
        "Content-Type": "application/json",
    }


def _validate_email(email: str) -> bool:
    """Validate email format to prevent PostgREST filter injection."""
    return bool(_SAFE_EMAIL_RE.match(email))


async def check_casl_consent(email: str, email_type: str) -> dict[str, Any]:
    """Check whether we can send this email type under CASL."""
    if email_type in TRANSACTIONAL_TYPES:
        return {"can_send": True, "reason": "transactional_exempt", "consent_type": None}
    if email_type not in COMMERCIAL_TYPES:
        logger.warning("Unknown email type '%s' -- treating as commercial", email_type)

    if not _validate_email(email):
        logger.error("Invalid email format for CASL check: %s", email)
        return {"can_send": False, "reason": "invalid_email_format", "consent_type": None}

    supabase_url, service_key = _get_supabase()
    if not supabase_url or not service_key:
        logger.error("Supabase not configured -- blocking commercial send")
        return {"can_send": False, "reason": "supabase_not_configured", "consent_type": None}

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{supabase_url}/rest/v1/casl_consent_records",
            params={"email": f"eq.{email}", "select": "consent_status,consent_given_at"},
            headers=_headers(service_key),
        )

    if resp.status_code != 200:
        logger.error("CASL lookup failed: %s %s", resp.status_code, resp.text)
        return {"can_send": False, "reason": "lookup_failed", "consent_type": None}

    rows = resp.json()
    if not rows:
        return {"can_send": False, "reason": "no_consent_record", "consent_type": None}

    status = rows[0].get("consent_status", "never")
    if status == "express":
        return {"can_send": True, "reason": "express_consent", "consent_type": "express"}
    if status == "implied":
        return {"can_send": True, "reason": "implied_consent", "consent_type": "implied"}
    return {"can_send": False, "reason": f"consent_{status}", "consent_type": None}


async def record_express_consent(
    email: str, user_id: str | None, merchant_id: str | None,
    method: str, form_url: str, ip_address: str, checkbox_text: str = "",
) -> dict[str, Any]:
    """Record express CASL consent with full evidence trail."""
    if not _validate_email(email):
        return {"ok": False, "error": "invalid_email_format"}
    supabase_url, service_key = _get_supabase()
    if not supabase_url or not service_key:
        return {"ok": False, "error": "supabase_not_configured"}

    now = datetime.now(timezone.utc).isoformat()
    evidence = {"checkbox_text": checkbox_text, "merchant_id": merchant_id, "recorded_at": now}
    payload = {
        "email": email, "user_id": user_id,
        "consent_status": "express", "consent_basis": "signup_checkbox",
        "consent_given_at": now, "consent_method": method,
        "consent_ip": ip_address, "consent_form_url": form_url,
        "consent_evidence": evidence, "updated_at": now,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{supabase_url}/rest/v1/casl_consent_records",
            headers={**_headers(service_key), "Prefer": "return=representation,resolution=merge-duplicates"},
            json=payload,
        )
    if resp.status_code not in (200, 201):
        logger.error("CASL consent record failed: %s %s", resp.status_code, resp.text)
        return {"ok": False, "error": resp.text}
    logger.info("CASL express consent recorded for %s via %s", email, method)
    return {"ok": True}


async def process_unsubscribe(email: str, method: str = "email_link") -> dict[str, Any]:
    """Immediately withdraw CASL consent -- CASL requires instant processing."""
    if not _validate_email(email):
        return {"ok": False, "error": "invalid_email_format"}
    supabase_url, service_key = _get_supabase()
    if not supabase_url or not service_key:
        return {"ok": False, "error": "supabase_not_configured"}

    now = datetime.now(timezone.utc).isoformat()
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.patch(
            f"{supabase_url}/rest/v1/casl_consent_records",
            params={"email": f"eq.{email}"},
            headers={**_headers(service_key), "Prefer": "return=representation"},
            json={"consent_status": "withdrawn", "unsubscribed_at": now,
                  "unsubscribe_method": method, "updated_at": now},
        )
    if resp.status_code not in (200, 204):
        logger.error("Unsubscribe failed for %s: %s %s", email, resp.status_code, resp.text)
        return {"ok": False, "error": resp.text}
    logger.info("CASL consent withdrawn for %s via %s", email, method)
    return {"ok": True}


async def casl_wrapped_send(
    to_email: str, email_type: str,
    send_fn: Callable[..., Coroutine[Any, Any, dict]],
    *args: Any, **kwargs: Any,
) -> dict[str, Any]:
    """Wrapper that checks CASL consent before calling the actual send function."""
    consent = await check_casl_consent(to_email, email_type)
    if not consent["can_send"]:
        logger.info("CASL blocked %s to %s: %s", email_type, to_email, consent["reason"])
        return {"status": "blocked", "reason": f"casl_{consent['reason']}", "email_type": email_type}
    return await send_fn(*args, **kwargs)
