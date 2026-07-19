"""
Phone activation: carrier-forwarding verification + funnel instrumentation
+ call-ending telemetry summary.

Forwarding verification flow (the wizard's "Verify forwarding" button):
  1. POST /api/phone/forwarding/verify-start — records a pending
     forwarding_verifications row, then places a short outbound Twilio call
     FROM our verification caller-id (MERIDIAN_FORWARD_VERIFY_CALLER) TO the
     merchant's real store line (phone_agent_config.business_line_number).
  2. If the merchant set up carrier forwarding correctly, the call arrives at
     their Meridian agent DID as an inbound Vapi assistant-request whose
     caller == our verification number. vapi_webhook recognizes it, marks the
     row verified, and answers "Forwarding verified — you're all set."
  3. GET /api/phone/forwarding/verify-status/{merchant_id} — the wizard polls
     this; pending rows older than the timeout report failed.

Funnel events (POST /api/phone/activation-event) are fire-and-forget from the
wizard so stalls between carrier_selected → codes_viewed → verified are
visible in phone_activation_events.
"""

import logging
import os
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, field_validator

from ..auth import (
    enforce_service_member,
    require_admin_jwt,
    require_jwt,
    require_org_member,
    require_service_auth,
)
from ...db import get_db
from ...services.phone_safety import (
    FORWARD_VERIFY_CALLER,
    DISPOSITIONS,
    normalize_e164,
    same_number,
)
from ...services.phone_recommendations import recommend_for_merchant
from .phone_dashboard import _validate_merchant_id

logger = logging.getLogger("meridian.api.phone_activation")

router = APIRouter(prefix="/api/phone", tags=["phone-activation"])

TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_API = "https://api.twilio.com/2010-04-01"

# A pending verification older than this reports "failed" to the poller —
# matches the wizard's 60s countdown.
VERIFY_TIMEOUT_SEC = 60

# TwiML for the outbound test leg: whoever answers (ideally our own Vapi agent,
# via the merchant's forward) hears a short pause, then we hang up. The proof
# of forwarding is the inbound assistant-request, not this leg's outcome.
_VERIFY_TWIML = '<Response><Pause length="3"/><Hangup/></Response>'


class VerifyStartRequest(BaseModel):
    merchant_id: str
    # The merchant's real store line (the number they forwarded FROM). Optional
    # when phone_agent_config.business_line_number is already stored.
    business_line_number: str | None = None


@router.post("/forwarding/verify-start")
async def forwarding_verify_start(req: VerifyStartRequest,
                                  principal=Depends(require_service_auth)):
    """Kick off a live forwarding check by calling the merchant's store line."""
    await enforce_service_member(principal, req.merchant_id)
    _validate_merchant_id(req.merchant_id)

    if not TWILIO_SID or not TWILIO_TOKEN or not FORWARD_VERIFY_CALLER:
        raise HTTPException(503, "Forwarding verification is not configured on this server")

    db = get_db()
    rows = await db.select(
        "phone_agent_config",
        filters={"merchant_id": f"eq.{req.merchant_id}"},
        limit=1,
    )
    row = rows[0] if rows else {}
    agent_did = (row.get("phone_number") or "").strip()
    if not agent_did:
        raise HTTPException(409, "No Meridian agent number provisioned yet — finish the number step first")

    line = normalize_e164(req.business_line_number or row.get("business_line_number") or "")
    if not line:
        raise HTTPException(422, "Enter your store's phone number (the line you forwarded) to verify")
    if same_number(line, agent_did):
        raise HTTPException(
            422,
            "That's your Meridian agent number — enter your own store line "
            "(the number customers already know) instead.",
        )

    now_iso = datetime.now(timezone.utc).isoformat()
    # Persist the store line for next time (and for support visibility).
    if rows and line != normalize_e164(row.get("business_line_number") or ""):
        await db.update(
            "phone_agent_config",
            {"business_line_number": line, "updated_at": now_iso},
            filters={"merchant_id": f"eq.{req.merchant_id}"},
        )

    # Supersede any stale pending attempt so the poller tracks THIS one.
    await db.update(
        "forwarding_verifications",
        {"status": "failed"},
        filters={"merchant_id": f"eq.{req.merchant_id}", "status": "eq.pending"},
    )
    inserted = await db.insert("forwarding_verifications", {
        "merchant_id": req.merchant_id,
        "status": "pending",
        "started_at": now_iso,
    })
    verification_id = (inserted[0].get("id") if isinstance(inserted, list) and inserted else None)

    # Place the test call. If Twilio rejects it, mark the attempt failed so the
    # wizard shows retry guidance instead of spinning for 60s.
    data = {
        "From": FORWARD_VERIFY_CALLER,
        "To": line,
        "Twiml": _VERIFY_TWIML,
        "Timeout": "25",
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        res = await client.post(
            f"{TWILIO_API}/Accounts/{TWILIO_SID}/Calls.json",
            data=data,
            auth=(TWILIO_SID, TWILIO_TOKEN),
        )
    if res.status_code not in (200, 201):
        logger.error("verify-start Twilio call failed %d: %s", res.status_code, res.text[:300])
        await db.update(
            "forwarding_verifications",
            {"status": "failed"},
            filters={"merchant_id": f"eq.{req.merchant_id}", "status": "eq.pending"},
        )
        raise HTTPException(502, "Could not place the verification call — please try again")

    logger.info("forwarding verify-start: merchant=%s line=%s verification=%s",
                req.merchant_id, line, verification_id or "?")
    return {"ok": True, "status": "pending", "verification_id": verification_id,
            "timeout_seconds": VERIFY_TIMEOUT_SEC}


@router.get("/forwarding/verify-status/{merchant_id}")
async def forwarding_verify_status(merchant_id: str,
                                   principal=Depends(require_service_auth)):
    """Latest verification attempt for this merchant. Pending attempts older
    than the timeout report failed (and are marked failed, best-effort)."""
    await enforce_service_member(principal, merchant_id)
    _validate_merchant_id(merchant_id)
    db = get_db()

    rows = await db.select(
        "forwarding_verifications",
        filters={"merchant_id": f"eq.{merchant_id}"},
        order="started_at.desc",
        limit=1,
    )
    if not rows:
        return {"status": "none"}
    row = rows[0]
    status = row.get("status") or "pending"

    if status == "pending":
        try:
            started = datetime.fromisoformat(
                str(row.get("started_at") or "").replace("Z", "+00:00"))
            age = (datetime.now(timezone.utc) - started).total_seconds()
        except ValueError:
            age = VERIFY_TIMEOUT_SEC + 1
        if age > VERIFY_TIMEOUT_SEC:
            status = "failed"
            try:
                await db.update(
                    "forwarding_verifications",
                    {"status": "failed"},
                    filters={"id": f"eq.{row['id']}"},
                )
            except Exception as e:  # noqa: BLE001 — status readout still correct
                logger.warning("could not mark verification %s failed: %s", row.get("id"), e)

    return {
        "status": status,
        "started_at": row.get("started_at"),
        "verified_at": row.get("verified_at"),
    }


# ── activation funnel events ─────────────────────────────────────────

_ALLOWED_STEPS = {
    "wizard_opened", "carrier_selected", "codes_viewed",
    "verify_started", "verified", "verify_failed",
}


class ActivationEventRequest(BaseModel):
    merchant_id: str
    step: str
    meta: dict | None = None

    @field_validator("step")
    @classmethod
    def _valid_step(cls, v: str) -> str:
        s = (v or "").strip().lower()
        if s not in _ALLOWED_STEPS:
            raise ValueError(f"step must be one of {sorted(_ALLOWED_STEPS)}")
        return s


@router.post("/activation-event")
async def record_activation_event(req: ActivationEventRequest,
                                  principal=Depends(require_service_auth)):
    """Fire-and-forget funnel event from the forwarding wizard."""
    await enforce_service_member(principal, req.merchant_id)
    _validate_merchant_id(req.merchant_id)
    db = get_db()
    await db.insert("phone_activation_events", {
        "merchant_id": req.merchant_id,
        "step": req.step,
        "meta": req.meta or {},
    })
    return {"ok": True}


# ── call-ending telemetry summary (admin) ────────────────────────────

async def _call_endings_summary(days: int, merchant_id: str | None) -> dict:
    """Per-merchant disposition counts + avg duration over the window.

    Shared by the admin summary endpoint and the recommendation endpoint so both
    read the telemetry the same way. Pure read (no writes).
    """
    from datetime import timedelta
    db = get_db()
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    filters: dict = {"created_at": f"gte.{since}"}
    if merchant_id:
        _validate_merchant_id(merchant_id)
        filters["merchant_id"] = f"eq.{merchant_id}"
    rows = await db.select(
        "voice_call_endings",
        filters=filters,
        order="created_at.desc",
        limit=10000,
    )

    per_merchant: dict[str, dict] = {}
    for r in rows or []:
        mid = r.get("merchant_id") or "unknown"
        m = per_merchant.setdefault(mid, {
            "merchant_id": mid,
            "total_calls": 0,
            "by_disposition": {d: 0 for d in DISPOSITIONS},
            "cutoff_without_order": 0,
            "_dur_sum": 0,
            "_dur_n": 0,
        })
        m["total_calls"] += 1
        disp = r.get("disposition") or "other"
        m["by_disposition"][disp] = m["by_disposition"].get(disp, 0) + 1
        if disp == "cutoff" and r.get("had_order") is False:
            m["cutoff_without_order"] += 1
        dur = r.get("duration_seconds")
        if isinstance(dur, (int, float)):
            m["_dur_sum"] += dur
            m["_dur_n"] += 1

    merchants = []
    for m in per_merchant.values():
        n = m.pop("_dur_n")
        s = m.pop("_dur_sum")
        m["avg_duration_seconds"] = round(s / n) if n else 0
        merchants.append(m)
    merchants.sort(key=lambda m: -m["total_calls"])

    return {
        "days": days,
        "total_calls": sum(m["total_calls"] for m in merchants),
        "merchants": merchants,
    }


@router.get("/call-endings/summary")
async def call_endings_summary(
    days: int = Query(7, ge=1, le=90),
    merchant_id: str | None = Query(None),
    admin=Depends(require_admin_jwt),
):
    """Counts by disposition + average duration per merchant over a date range.

    The "how many orders was the call cap killing" instrument: the `cutoff`
    bucket (exceeded-max-duration) split by had_order shows calls the wall
    ended before an order landed.
    """
    return await _call_endings_summary(days, merchant_id)


# ── advisory recommendations (org-scoped, READ-ONLY) ─────────────────

@router.get("/recommendations/{merchant_id}")
async def phone_recommendations(
    merchant_id: str,
    days: int = Query(7, ge=1, le=90),
    user: dict = Depends(require_jwt),
):
    """Ranked, evidence-backed cap/fee recommendations for one merchant.

    ADVISORY ONLY — derives signals (raise-cap, agent-quality, pricing-headroom)
    from this merchant's call-ending telemetry over the window and returns them
    with the numbers behind each. Does NOT change any cap/fee; a human decides.

    Org-auth: the caller must be a member/owner of `merchant_id` (or a global
    admin). The org is the path merchant_id, verified against the session JWT.
    """
    _validate_merchant_id(merchant_id)
    await require_org_member(user, merchant_id)

    summary = await _call_endings_summary(days, merchant_id)
    block = next(
        (m for m in summary["merchants"] if m["merchant_id"] == merchant_id),
        None,
    )
    if block is None:
        # No telemetry for this merchant in the window — nothing to advise on.
        return {
            "merchant_id": merchant_id,
            "days": days,
            "total_calls": 0,
            "recommendations": [],
        }

    return {
        "merchant_id": merchant_id,
        "days": days,
        "total_calls": block["total_calls"],
        "recommendations": recommend_for_merchant(block),
    }
