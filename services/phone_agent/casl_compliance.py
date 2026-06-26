"""
CASL compliance helpers for the SMS path.

Handles three things the spec requires for Canada-to-Canada SMS:
  1. STOP / HELP / START keyword detection and response.
  2. Marketing vs. transactional opt-out tracking (sms_optout_tracking
     table). STOP toggles marketing only; the in-flight payment link is
     transactional and must still go out.
  3. Canadian phone number detection (NANP area code allowlist). Lets us
     refuse inbound SMS from non-Canadian numbers cheaply, without
     paying Twilio Lookup per inbound.

Sender identification ("{business_name} via Meridian: ...") lives at the
call site, not here, because it composes with the LLM-generated reply.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger("meridian.phone_agent.casl")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", "")

# Reserved CASL/CTIA keywords. Match is case-insensitive and ignores
# surrounding whitespace; the body must be ONLY the keyword (carriers
# don't honor "STOP please" as STOP).
STOP_KEYWORDS = frozenset({"stop", "stopall", "unsubscribe", "cancel", "end", "quit"})
HELP_KEYWORDS = frozenset({"help", "info"})
START_KEYWORDS = frozenset({"start", "yes", "unstop"})

# Canadian NANP area codes. Source: CRTC / NANPA, current as of 2026.
# Excludes overlay codes that haven't activated and codes shared with
# Caribbean/US territories. If maintenance becomes a burden, swap for
# Twilio Lookup at $0.005 per inbound — for demo traffic the static
# list is fine.
CANADIAN_AREA_CODES = frozenset({
    "204", "226", "236", "249", "250", "263", "289", "306", "343", "354",
    "365", "367", "368", "382", "403", "416", "418", "428", "431", "437",
    "438", "450", "468", "474", "506", "514", "519", "548", "579", "581",
    "584", "587", "604", "613", "639", "647", "672", "683", "705", "709",
    "742", "753", "778", "780", "782", "807", "819", "825", "867", "873",
    "879", "902", "905",
})


# ───────────────────────────────────────────────────────────────────────
# Keyword detection
# ───────────────────────────────────────────────────────────────────────

def classify_keyword(body: str) -> Optional[str]:
    """Return 'stop' | 'help' | 'start' if body is exactly a reserved
    keyword; None otherwise. Case- and whitespace-insensitive."""
    token = (body or "").strip().lower()
    if token in STOP_KEYWORDS:
        return "stop"
    if token in HELP_KEYWORDS:
        return "help"
    if token in START_KEYWORDS:
        return "start"
    return None


# ───────────────────────────────────────────────────────────────────────
# Canadian number detection
# ───────────────────────────────────────────────────────────────────────

def is_canadian_number(phone: str) -> bool:
    """True if phone is an E.164 NANP number with a Canadian area code.

    Twilio delivers inbound 'From' in E.164 (+15145551234). Strip + and
    country code (1), then check the leading 3 digits.
    """
    if not phone:
        return False
    digits = phone.lstrip("+")
    if len(digits) != 11 or not digits.isdigit() or not digits.startswith("1"):
        return False
    return digits[1:4] in CANADIAN_AREA_CODES


# ───────────────────────────────────────────────────────────────────────
# Opt-out tracking (Supabase)
# ───────────────────────────────────────────────────────────────────────

async def fetch_optout_status(merchant_id: str, customer_phone: str) -> dict:
    """Return {'marketing_optout': bool, 'transactional_optout': bool}.

    Defaults to both False when Supabase is unconfigured or row missing —
    callers should treat that as "no opt-out on record."
    """
    default = {"marketing_optout": False, "transactional_optout": False}
    if not SUPABASE_URL or not SUPABASE_KEY:
        return default
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.get(
                f"{SUPABASE_URL}/rest/v1/sms_optout_tracking"
                f"?merchant_id=eq.{merchant_id}"
                f"&customer_phone=eq.{customer_phone}"
                f"&select=marketing_optout,transactional_optout",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                },
            )
            if res.status_code == 200 and res.json():
                row = res.json()[0]
                return {
                    "marketing_optout": bool(row.get("marketing_optout")),
                    "transactional_optout": bool(row.get("transactional_optout")),
                }
    except Exception as e:
        logger.warning(
            "fetch_optout_status failed for %s/%s: %s",
            merchant_id, customer_phone, e,
        )
    return default


async def record_optout(
    merchant_id: str,
    customer_phone: str,
    *,
    marketing: bool = True,
    transactional: bool = False,
    notes: str = "",
) -> bool:
    """Upsert an opt-out row. Returns True on success."""
    return await _upsert_optout(
        merchant_id=merchant_id,
        customer_phone=customer_phone,
        marketing_optout=marketing,
        transactional_optout=transactional,
        notes=notes,
        stamp_marketing_at=marketing,
        stamp_transactional_at=transactional,
    )


async def record_optin(merchant_id: str, customer_phone: str) -> bool:
    """Clear marketing_optout on START/UNSTOP. Transactional opt-out is
    a hard stop and is NOT cleared by START — would require manual
    intervention to undo, which is the safe default."""
    return await _upsert_optout(
        merchant_id=merchant_id,
        customer_phone=customer_phone,
        marketing_optout=False,
        transactional_optout=None,
        notes="reopened via START",
        stamp_marketing_at=False,
        stamp_transactional_at=False,
    )


async def stamp_last_inbound(merchant_id: str, customer_phone: str) -> None:
    """Best-effort touch of last_inbound_at; failure is non-fatal."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # PATCH if row exists; otherwise insert. Use upsert via merge-duplicates.
            await client.post(
                f"{SUPABASE_URL}/rest/v1/sms_optout_tracking",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "resolution=merge-duplicates,return=minimal",
                },
                json={
                    "merchant_id": merchant_id,
                    "customer_phone": customer_phone,
                    "last_inbound_at": "now()",
                },
                params={"on_conflict": "merchant_id,customer_phone"},
            )
    except Exception as e:
        logger.debug("stamp_last_inbound failed: %s", e)


async def _upsert_optout(
    *,
    merchant_id: str,
    customer_phone: str,
    marketing_optout: bool,
    transactional_optout: Optional[bool],
    notes: str,
    stamp_marketing_at: bool,
    stamp_transactional_at: bool,
) -> bool:
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.warning(
            "Opt-out NOT persisted (no Supabase config): merchant=%s phone=%s marketing=%s",
            merchant_id, customer_phone, marketing_optout,
        )
        return False

    payload: dict = {
        "merchant_id": merchant_id,
        "customer_phone": customer_phone,
        "marketing_optout": marketing_optout,
        "notes": notes,
    }
    if transactional_optout is not None:
        payload["transactional_optout"] = transactional_optout
    if stamp_marketing_at:
        payload["marketing_optout_at"] = "now()"
    if stamp_transactional_at:
        payload["transactional_optout_at"] = "now()"

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.post(
                f"{SUPABASE_URL}/rest/v1/sms_optout_tracking",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "resolution=merge-duplicates,return=minimal",
                },
                json=payload,
                params={"on_conflict": "merchant_id,customer_phone"},
            )
            if res.status_code in (200, 201, 204):
                logger.info(
                    "Opt-out updated: merchant=%s phone=%s marketing=%s transactional=%s",
                    merchant_id, customer_phone, marketing_optout, transactional_optout,
                )
                return True
            logger.error(
                "Opt-out upsert HTTP %d: %s", res.status_code, res.text[:300],
            )
    except Exception as e:
        logger.error("Opt-out upsert failed: %s", e)
    return False


# ───────────────────────────────────────────────────────────────────────
# Sender ID helpers
# ───────────────────────────────────────────────────────────────────────

def prepend_sender_id(business_name: str, body: str) -> str:
    """CASL requires the message to clearly identify the sender. We
    prepend '{business} via Meridian:' to every outbound. If the LLM
    already starts the reply with the business name, we don't double up."""
    name = (business_name or "this restaurant").strip()
    tag = f"{name} via Meridian:"
    if body.startswith(tag):
        return body
    # Skip the tag if the LLM already opened with the business name; the
    # CASL ID requirement is satisfied either way and double-prefixing
    # reads badly.
    if body.lower().startswith(name.lower()):
        return body
    return f"{tag} {body}"


def help_reply(business_name: str) -> str:
    name = (business_name or "this restaurant").strip()
    return (
        f"{name} via Meridian: text 'menu' to see what's available, "
        "or just tell us what you'd like to order. "
        "Reply STOP to opt out of promotional messages."
    )


def stop_ack_reply(business_name: str) -> str:
    name = (business_name or "this restaurant").strip()
    return (
        f"{name} via Meridian: you've been unsubscribed from promotional "
        "messages. You'll still receive transaction confirmations for any "
        "active orders. Reply START to re-subscribe."
    )


def start_ack_reply(business_name: str) -> str:
    name = (business_name or "this restaurant").strip()
    return (
        f"{name} via Meridian: you're re-subscribed to promotional messages. "
        "Reply STOP at any time to opt out again."
    )


def non_canadian_reply() -> str:
    return (
        "Meridian: SMS ordering is currently available to Canadian phone "
        "numbers only. Please call the business directly to place an order."
    )
