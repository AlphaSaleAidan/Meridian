"""
Public "Schedule a Quote" lead capture.

  POST /api/quote-request   → anonymous (no auth) public lead capture

The founder retired the self-serve SaaS pricing tiers on the public marketing
pages in favour of this lightweight flow: a prospect on the US/CAD landing page
requests a sales call inside a 48h window, sales follows up. We persist the lead
to `quote_requests` (migration 034) and email the founders.

Hardening for an unauthenticated endpoint:
  * A honeypot field (`company_website`) that real users never see; any value
    means a bot → reject 400 (and never store / never email).
  * Required-field + email-shape + E.164-ish phone validation → 400.
No secrets, no auth headers, no PII beyond what the prospect typed.

Failure handling: validation failures are the ONLY hard failures. Once a request
is valid we always return {"ok": true} — a DB or email hiccup must never bounce a
real prospect. The row is best-effort persisted first, then the email is
attempted; either failing is logged, not surfaced.
"""
import logging
import re
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...db import get_db
from ...email.send import send_quote_request

logger = logging.getLogger("meridian.api.quote")

router = APIRouter(prefix="/api", tags=["quote"])

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
# E.164-ish: optional leading +, 8–15 digits, no leading zero on the country part.
_PHONE_RE = re.compile(r"^\+?[1-9]\d{7,14}$")
_MAX = 2000  # cap free-text so a bot can't dump megabytes through an open route


class QuoteRequest(BaseModel):
    full_name: str = ""
    business_name: str = ""
    email: str = ""
    phone: str = ""
    preferred_date: str = ""
    preferred_window: str = ""
    notes: str = ""
    source: str = ""
    # Honeypot — hidden in the UI; a non-empty value indicates a bot.
    company_website: str = ""


def _normalize_phone(raw: str) -> str:
    """Strip spaces, dashes, dots, parens so '(782) 358-5534' validates."""
    return re.sub(r"[\s\-().]", "", raw or "")


@router.post("/quote-request")
async def create_quote_request(req: QuoteRequest) -> dict:
    # 1) Honeypot: a filled hidden field == bot. Reject before any work.
    if (req.company_website or "").strip():
        logger.info("quote-request rejected: honeypot tripped")
        raise HTTPException(status_code=400, detail="Invalid request")

    full_name = (req.full_name or "").strip()
    business_name = (req.business_name or "").strip()
    email = (req.email or "").strip()
    phone_norm = _normalize_phone(req.phone)

    # 2) Required fields + shape validation.
    if not full_name or not business_name:
        raise HTTPException(status_code=400, detail="Name and business name are required")
    if not _EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="A valid email is required")
    if not _PHONE_RE.match(phone_norm):
        raise HTTPException(status_code=400, detail="A valid phone number is required")
    if any(len(v or "") > _MAX for v in (req.notes, req.preferred_date, req.preferred_window, req.source)):
        raise HTTPException(status_code=400, detail="Field too long")

    now = datetime.now(timezone.utc).isoformat()
    row = {
        "id": str(uuid4()),
        "full_name": full_name,
        "business_name": business_name,
        "email": email,
        "phone": phone_norm,
        "preferred_date": (req.preferred_date or "").strip(),
        "preferred_window": (req.preferred_window or "").strip(),
        "notes": (req.notes or "").strip(),
        "source": (req.source or "").strip(),
        "created_at": now,
    }

    # 3) Spam dedup (2026-07-15 hunt): same email within 24h → 200 but no
    #    duplicate row / founder email. Best-effort: a dedup-lookup failure
    #    must never drop a real lead.
    try:
        db = get_db()
    except Exception as e:
        logger.warning("quote_requests DB unavailable: %s", e)
        db = None

    if db is not None:
        from ...services.submission_guard import is_recent_duplicate
        if await is_recent_duplicate(db, "quote_requests", email):
            logger.info("Duplicate quote request suppressed: %s (%s)", business_name, email)
            return {"ok": True}

    # 4) Persist (best-effort — never fail the prospect over a DB hiccup).
    try:
        if db is not None:
            await db.insert("quote_requests", row)
    except Exception as e:
        logger.warning("quote_requests insert failed (table may not exist / DB down): %s", e)

    # 5) Notify the founders (best-effort — email errors must not bounce the lead).
    try:
        await send_quote_request(
            full_name=full_name,
            business_name=business_name,
            email=email,
            phone=phone_norm,
            preferred_date=row["preferred_date"],
            preferred_window=row["preferred_window"],
            notes=row["notes"],
            source=row["source"],
        )
    except Exception as e:
        logger.warning("quote request notification email failed: %s", e)

    # 6) Foundry bridge (best-effort): website/CRM-shaped interest also lands
    #    in the build division's pipeline (foundry.meridian.tips). Inert unless
    #    FOUNDRY_INBOUND_URL/KEY are set; a Foundry hiccup never bounces a lead.
    try:
        from ...services.foundry_bridge import forward_quote_lead
        await forward_quote_lead(row)
    except Exception as e:
        logger.warning("foundry bridge failed: %s", e)

    logger.info("quote request received: %s (%s) [source=%s]", business_name, email, row["source"])
    return {"ok": True}
