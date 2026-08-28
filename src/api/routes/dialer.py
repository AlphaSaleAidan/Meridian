"""SR auto dialer — rep-facing API (power dial over the rep's own leads).

Flow: the Auto Dialer tab opens a session, pulls /queue (due callbacks first,
then the rep's callable leads), then for each lead POSTs /calls — which is the
COMPLIANCE GATE: internal DNC + CRTC/TCPA calling-window check in the lead's
local time, hard block (a blocked row is still written, for audit). The
browser softphone (Telnyx WebRTC, or the labeled SIM mode when
TELNYX_WEBRTC_CONNECTION_ID is unset) drives status transitions via
PATCH /calls/{id}, and every call ends in a one-click disposition whose side
effects (DNC write, callback schedule, lead-stage advance) land server-side.

Scoping: all rows are keyed on the caller's sales_reps id resolved via
hierarchy.resolve_scope (backend plane; RLS is the independent DB plane).
Storage: services/dialer_store (Supabase, or in-memory preview store when
DIALER_DEV_STORE=1 — lets previews run before the migration is hand-applied).
"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from .. import hierarchy
from ..auth import require_jwt
from ...services import dialer_compliance as compliance
from ...services import phone_leads_store
from ...services.dialer_store import dev_store_active, get_store
from ...services.phone_safety import normalize_e164

logger = logging.getLogger("meridian.api.dialer")

router = APIRouter(prefix="/api/dialer", tags=["dialer"])

# The dialer works the canada_phone_leads pool (see routes/dialer_leads.py).
# A call's lead_id points at a canada_phone_leads row; dispositions update that
# pool row (recapture), never canada_leads.
_LEAD_TABLES = {"canada": "canada_phone_leads", "us": "canada_phone_leads"}
_DISPOSITIONS = {"meeting_booked", "interested", "callback", "left_voicemail",
                 "no_answer", "busy", "bad_number", "not_interested", "dnc", "other"}

# Disposition -> (pool status, recapture delay in hours or None to hold out).
# None delay = clear next_action_at (lead leaves the active queue).
_RECAPTURE = {
    "no_answer": ("attempting", 4),
    "busy": ("attempting", 2),
    "left_voicemail": ("attempting", 24),
    "interested": ("contacted", 24),
    "other": ("attempting", 24),
    "callback": ("callback", None),          # next_action_at set to the callback time
    "meeting_booked": ("booked", None),
    "not_interested": ("not_interested", None),
    "bad_number": ("bad_number", None),
    "dnc": ("dnc", None),
}


class SessionStart(BaseModel):
    market: str = Field(pattern="^(canada|us)$")
    wrap_up_seconds: int = Field(default=15, ge=0, le=300)


class SessionPatch(BaseModel):
    status: str = Field(pattern="^(active|paused|ended)$")


class CallStart(BaseModel):
    session_id: str
    market: str = Field(pattern="^(canada|us)$")
    phone: str
    lead_id: str | None = None
    business_name: str = ""
    contact_name: str = ""
    sim: bool = False


class CallPatch(BaseModel):
    status: str | None = Field(default=None, pattern="^(dialing|ringing|connected|ended|failed)$")
    telnyx_call_id: str | None = None
    duration_seconds: int | None = Field(default=None, ge=0)
    talk_seconds: int | None = Field(default=None, ge=0)


class CallbackSpec(BaseModel):
    due_at: str
    note: str = ""


class DispositionBody(BaseModel):
    disposition: str
    notes: str = ""
    callback: CallbackSpec | None = None
    advance_stage: str | None = None


class CallbackPatch(BaseModel):
    status: str = Field(pattern="^(pending|done|cancelled)$")


async def _rep_scope(user: dict) -> hierarchy.RepScope:
    scope = await hierarchy.resolve_scope(user)
    if not scope.rep_id:
        raise HTTPException(403, "No sales rep profile for this account")
    return scope


# NOTE: GET /api/dialer/queue now lives in routes/dialer_leads.py — it reads the
# canada_phone_leads dialing pool (with enrichment + recapture), NOT canada_leads.


@router.get("/sessions/current")
async def current_session(market: str = Query(default="canada", pattern="^(canada|us)$"),
                          user: dict = Depends(require_jwt)):
    scope = await _rep_scope(user)
    session = await get_store().current_session(scope.rep_id)
    return {"session": session, "dev_store": dev_store_active()}


@router.post("/sessions")
async def start_session(body: SessionStart, user: dict = Depends(require_jwt)):
    scope = await _rep_scope(user)
    store = get_store()
    existing = await store.current_session(scope.rep_id)
    if existing:
        await store.update_session(existing["id"], {
            "status": "ended", "ended_at": datetime.now(timezone.utc).isoformat(),
        })
    session = await store.create_session({
        "rep_id": scope.rep_id, "market": body.market,
        "wrap_up_seconds": body.wrap_up_seconds,
    })
    return {"session": session}


@router.patch("/sessions/{session_id}")
async def patch_session(session_id: str, body: SessionPatch,
                        user: dict = Depends(require_jwt)):
    scope = await _rep_scope(user)
    store = get_store()
    session = await store.get_session(session_id)
    if not session or session["rep_id"] != scope.rep_id:
        raise HTTPException(404, "Session not found")
    fields: dict = {"status": body.status}
    if body.status == "ended":
        fields["ended_at"] = datetime.now(timezone.utc).isoformat()
    return {"session": await store.update_session(session_id, fields)}


@router.post("/calls")
async def start_call(body: CallStart, user: dict = Depends(require_jwt)):
    """THE compliance gate. Always writes a row; blocked attempts are audited
    with status='blocked' and never produce a call leg (sim or real)."""
    scope = await _rep_scope(user)
    store = get_store()
    session = await store.get_session(body.session_id)
    if not session or session["rep_id"] != scope.rep_id or session["status"] == "ended":
        raise HTTPException(404, "Active session not found")

    norm = normalize_e164(body.phone)
    check = compliance.check_calling_window(norm) if norm else None
    on_dnc = bool(norm) and bool(await store.dnc_filter([norm]))

    blocked_reason = None
    if not norm:
        blocked_reason = "invalid_number"
    elif on_dnc:
        blocked_reason = "dnc"
    elif not check.allowed:
        blocked_reason = check.reason

    call = await store.create_call({
        "session_id": body.session_id,
        "rep_id": scope.rep_id,
        "lead_id": body.lead_id,
        "lead_table": _LEAD_TABLES[body.market],
        "business_name": body.business_name[:200],
        "contact_name": body.contact_name[:200],
        "phone_e164": norm or body.phone[:32],
        "status": "blocked" if blocked_reason else "queued",
        "blocked_reason": blocked_reason,
        "sim": body.sim,
    })
    if not blocked_reason:
        await store.update_session(body.session_id, {"dials": (session.get("dials") or 0) + 1})
    return {
        "call": call,
        "gate": {
            "allowed": blocked_reason is None,
            "reason": blocked_reason or "",
            "local_time": check.local_time if check else "",
            "window_label": check.window_label if check else "",
        },
    }


@router.patch("/calls/{call_id}")
async def patch_call(call_id: str, body: CallPatch, user: dict = Depends(require_jwt)):
    scope = await _rep_scope(user)
    store = get_store()
    call = await store.get_call(call_id)
    if not call or call["rep_id"] != scope.rep_id:
        raise HTTPException(404, "Call not found")

    now_iso = datetime.now(timezone.utc).isoformat()
    fields: dict = {}
    if body.telnyx_call_id:
        fields["telnyx_call_id"] = body.telnyx_call_id
    if body.status:
        fields["status"] = body.status
        if body.status == "connected" and not call.get("answered_at"):
            fields["answered_at"] = now_iso
            session = await store.get_session(call["session_id"]) if call.get("session_id") else None
            if session:
                await store.update_session(session["id"],
                                           {"connects": (session.get("connects") or 0) + 1})
        if body.status in ("ended", "failed"):
            fields["ended_at"] = now_iso
    if body.duration_seconds is not None:
        fields["duration_seconds"] = body.duration_seconds
    if body.talk_seconds is not None:
        fields["talk_seconds"] = body.talk_seconds
        session = await store.get_session(call["session_id"]) if call.get("session_id") else None
        if session:
            base = session.get("talk_seconds") or 0
            prior = call.get("talk_seconds") or 0
            await store.update_session(session["id"],
                                       {"talk_seconds": base - prior + body.talk_seconds})
    return {"call": await store.update_call(call_id, fields)}


async def _recapture_phone_lead(call: dict, rep_id: str, disposition: str,
                                callback_due: str | None) -> None:
    """Update the canada_phone_leads pool row after a call — the recapture
    engine. Sets status + attempts + next_action_at so worked-but-unconverted
    leads re-surface at the right time (or leave the queue). Guarded to the
    caller's own (or shared) pool row inside phone_leads_store.update."""
    lead_id = call.get("lead_id")
    if not lead_id or call.get("lead_table") != "canada_phone_leads":
        return
    status, delay_h = _RECAPTURE.get(disposition, ("attempting", 24))
    fields: dict = {
        "status": status,
        "last_disposition": disposition,
        "last_attempt_at": datetime.now(timezone.utc).isoformat(),
    }
    if disposition == "callback" and callback_due:
        fields["next_action_at"] = callback_due
    elif delay_h is not None:
        fields["next_action_at"] = (
            datetime.now(timezone.utc) + timedelta(hours=delay_h)).isoformat()
    else:
        fields["next_action_at"] = None
    # attempts++ (real attempt only — blocked calls never reach disposition).
    lead = await phone_leads_store.get(lead_id)
    if lead:
        fields["attempts"] = (lead.get("attempts") or 0) + 1
        await phone_leads_store.update(lead_id, fields, rep_guard=rep_id)


@router.post("/calls/{call_id}/disposition")
async def disposition_call(call_id: str, body: DispositionBody,
                           user: dict = Depends(require_jwt)):
    scope = await _rep_scope(user)
    if body.disposition not in _DISPOSITIONS:
        raise HTTPException(400, f"Unknown disposition '{body.disposition}'")
    store = get_store()
    call = await store.get_call(call_id)
    if not call or call["rep_id"] != scope.rep_id:
        raise HTTPException(404, "Call not found")

    now_iso = datetime.now(timezone.utc).isoformat()
    updated = await store.update_call(call_id, {
        "disposition": body.disposition,
        "notes": body.notes[:4000],
        "disposition_at": now_iso,
    })

    side_effects: dict = {}
    if body.disposition == "dnc":
        await store.dnc_add(call["phone_e164"], "canada",
                            f"rep disposition on call {call_id}", scope.rep_id)
        side_effects["dnc_added"] = True
    callback_due = body.callback.due_at if (body.disposition == "callback" and body.callback) else None
    if callback_due:
        check = compliance.check_calling_window(call["phone_e164"])
        cb = await store.create_callback({
            "rep_id": scope.rep_id,
            "lead_id": call.get("lead_id"),
            "lead_table": call.get("lead_table"),
            "call_id": call_id,
            "phone_e164": call["phone_e164"],
            "business_name": call.get("business_name") or "",
            "contact_name": call.get("contact_name") or "",
            "due_at": callback_due,
            "timezone": check.tz,
            "note": body.callback.note[:1000],
        })
        side_effects["callback"] = cb

    # Recapture: update the phone-lead pool row (status / attempts / next dial).
    await _recapture_phone_lead(call, scope.rep_id, body.disposition, callback_due)
    side_effects["recaptured"] = True

    return {"call": updated, **side_effects}


@router.get("/callbacks")
async def list_callbacks(status: str = Query(default="pending", pattern="^(pending|done|cancelled)$"),
                         user: dict = Depends(require_jwt)):
    scope = await _rep_scope(user)
    rows = await get_store().list_callbacks(rep_ids=[scope.rep_id], status=status)
    return {"callbacks": rows}


@router.patch("/callbacks/{callback_id}")
async def patch_callback(callback_id: str, body: CallbackPatch,
                         user: dict = Depends(require_jwt)):
    scope = await _rep_scope(user)
    store = get_store()
    rows = await store.list_callbacks(rep_ids=[scope.rep_id], status="")
    if not any(r["id"] == callback_id for r in rows):
        raise HTTPException(404, "Callback not found")
    return {"callback": await store.update_callback(callback_id, {"status": body.status})}


# ── Softphone credentials ─────────────────────────────────────────────────────

_token_cache: dict[str, tuple[str, float]] = {}  # rep_id -> (token, expiry_epoch)


@router.post("/webrtc-token")
async def webrtc_token(user: dict = Depends(require_jwt)):
    """Mint a Telnyx on-demand telephony-credential token for the browser
    softphone. Without TELNYX_WEBRTC_CONNECTION_ID the dialer runs in SIM mode
    (state machine only, no PSTN traffic) — the UI labels it unmistakably."""
    scope = await _rep_scope(user)
    connection_id = os.environ.get("TELNYX_WEBRTC_CONNECTION_ID", "").strip()
    api_key = os.environ.get("TELNYX_API_KEY", "").strip()
    # Market-aware caller ID: US-portal reps present the US number so US
    # prospects don't see a Canadian caller ID (and vice versa).
    if scope.portal_context == "us":
        caller_id = (os.environ.get("TELNYX_DIALER_CALLER_ID_US", "").strip()
                     or os.environ.get("TELNYX_PHONE_NUMBER", "").strip()
                     or os.environ.get("TELNYX_DIALER_CALLER_ID", "").strip())
    else:
        caller_id = (os.environ.get("TELNYX_DIALER_CALLER_ID", "").strip()
                     or os.environ.get("TELNYX_PHONE_NUMBER_CA", "").strip()
                     or os.environ.get("TELNYX_PHONE_NUMBER", "").strip())
    if not connection_id or not api_key:
        return {"mode": "sim", "caller_id": caller_id}

    cached = _token_cache.get(scope.rep_id)
    if cached and cached[1] > time.time() + 600:
        return {"mode": "webrtc", "token": cached[0], "caller_id": caller_id}

    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            cred = await client.post(
                "https://api.telnyx.com/v2/telephony_credentials",
                headers=headers,
                json={"connection_id": connection_id, "name": f"dialer-{scope.rep_id[:8]}"},
            )
            cred.raise_for_status()
            cred_id = cred.json()["data"]["id"]
            tok = await client.post(
                f"https://api.telnyx.com/v2/telephony_credentials/{cred_id}/token",
                headers=headers,
            )
            tok.raise_for_status()
            token = tok.text.strip().strip('"')
    except Exception as exc:  # noqa: BLE001
        logger.error("telnyx credential mint failed: %s", exc)
        raise HTTPException(502, "Could not mint softphone credentials")
    _token_cache[scope.rep_id] = (token, time.time() + 20 * 3600)
    return {"mode": "webrtc", "token": token, "caller_id": caller_id}
