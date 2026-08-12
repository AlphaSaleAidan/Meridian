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
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from .. import hierarchy
from ..auth import require_jwt
from ...services import dialer_compliance as compliance
from ...services.dialer_store import dev_store_active, get_store
from ...services.phone_safety import normalize_e164

logger = logging.getLogger("meridian.api.dialer")

router = APIRouter(prefix="/api/dialer", tags=["dialer"])

# Stages a lead can be power-dialed in — exclusion list so both markets'
# vocabularies (canada_leads legacy+portal stages, us_leads) stay covered.
# Deliberately narrow: onboarding-stage customers (walkthrough/checkout/
# pos_connected) are legitimate follow-up calls; only closed pipelines are out.
_UNDIALABLE_STAGES = {"closed_won", "closed_lost"}
_LEAD_TABLES = {"canada": "canada_leads", "us": "us_leads"}
_LEAD_COLS = ("id,business_name,contact_name,contact_phone,contact_email,"
              "vertical,stage,city,province,notes,rep_id,updated_at")
_ATTEMPT_COOLDOWN_HOURS = 4
_DISPOSITIONS = {"meeting_booked", "interested", "callback", "left_voicemail",
                 "no_answer", "busy", "bad_number", "not_interested", "dnc", "other"}
# Stages a disposition may advance a lead to (rep's own lead only).
_ADVANCE_STAGES = {"contacted", "appointment_set", "demo_scheduled"}


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


def _user_token(request: Request) -> str:
    auth_header = request.headers.get("authorization", "")
    return auth_header.removeprefix("Bearer ").strip() if auth_header.startswith("Bearer ") else ""


def _anon_key() -> str:
    return (os.environ.get("SUPABASE_ANON_KEY", "")
            or os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
            or os.environ.get("SUPABASE_SERVICE_KEY", ""))


async def _fetch_own_leads(request: Request, market: str, rep_id: str) -> list[dict]:
    """Rep's leads via PostgREST WITH THE CALLER'S JWT (RLS plane enforced)."""
    supabase_url = os.environ.get("SUPABASE_URL", "")
    token = _user_token(request)
    if not supabase_url or not token:
        return []
    table = _LEAD_TABLES[market]
    headers = {"Authorization": f"Bearer {token}", "apikey": _anon_key()}
    params = {
        "select": _LEAD_COLS,
        "rep_id": f"eq.{rep_id}",
        "contact_phone": "neq.",
        "order": "updated_at.desc",
        "limit": "150",
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{supabase_url}/rest/v1/{table}",
                                    headers=headers, params=params)
            if resp.status_code == 200:
                return resp.json()
            logger.warning("dialer queue lead fetch failed: %s %s",
                           resp.status_code, resp.text[:200])
    except Exception as exc:  # noqa: BLE001
        logger.warning("dialer queue lead fetch error: %s", exc)
    return []


@router.get("/queue")
async def get_queue(request: Request, market: str = Query(pattern="^(canada|us)$"),
                    user: dict = Depends(require_jwt)):
    """Due callbacks first, then the rep's callable leads. Every entry is
    annotated with the dial-time gate result so the UI can show why a lead is
    skipped (DNC / outside window) before the rep ever hits Dial."""
    scope = await _rep_scope(user)
    store = get_store()
    now = datetime.now(timezone.utc)

    leads = await _fetch_own_leads(request, market, scope.rep_id)
    leads = [ld for ld in leads if (ld.get("stage") or "") not in _UNDIALABLE_STAGES]

    cooldown_since = (now - timedelta(hours=_ATTEMPT_COOLDOWN_HOURS)).isoformat()
    attempted = await store.last_attempts(scope.rep_id, cooldown_since)

    callbacks = await store.list_callbacks(rep_ids=[scope.rep_id], status="pending")
    due = [cb for cb in callbacks if cb["due_at"] <= (now + timedelta(minutes=15)).isoformat()]

    phones = ([normalize_e164(cb["phone_e164"]) for cb in due]
              + [normalize_e164(ld.get("contact_phone") or "") for ld in leads])
    dnc = await store.dnc_filter([p for p in phones if p])

    def _annotate(phone: str) -> dict:
        norm = normalize_e164(phone)
        check = compliance.check_calling_window(norm)
        return {
            "phone_e164": norm,
            "on_dnc": norm in dnc,
            "callable_now": bool(norm) and norm not in dnc and check.allowed,
            "gate_reason": "dnc" if norm in dnc else check.reason,
            "local_time": check.local_time,
            "window_label": check.window_label,
            "country": check.country,
        }

    queue_callbacks = [{**cb, "kind": "callback", **_annotate(cb["phone_e164"])} for cb in due]
    queue_leads = []
    for ld in leads:
        entry = {"kind": "lead", **ld, **_annotate(ld.get("contact_phone") or "")}
        entry["recently_attempted"] = ld.get("id") in attempted
        queue_leads.append(entry)
    # Cooled-down leads sink to the back but stay visible.
    queue_leads.sort(key=lambda e: e["recently_attempted"])

    return {
        "callbacks": queue_callbacks,
        "leads": queue_leads,
        "dev_store": dev_store_active(),
    }


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


async def _advance_lead_stage(call: dict, rep_id: str, stage: str) -> bool:
    """Service-role lead-stage advance, guarded to the caller's own lead row."""
    supabase_url = os.environ.get("SUPABASE_URL", "")
    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
           or os.environ.get("SUPABASE_SERVICE_KEY", ""))
    if not supabase_url or not key or not call.get("lead_id") or not call.get("lead_table"):
        return False
    # Prefer=representation so a guard miss (0 rows matched — e.g. a crafted
    # lead_id owned by another rep) reports False instead of a silent "success"
    # (PostgREST returns 2xx for zero-row updates; caught in the 08-12 E2E run).
    headers = {"Authorization": f"Bearer {key}", "apikey": key,
               "Prefer": "return=representation"}
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.patch(
                f"{supabase_url}/rest/v1/{call['lead_table']}",
                headers=headers,
                params={"id": f"eq.{call['lead_id']}", "rep_id": f"eq.{rep_id}"},
                json={"stage": stage, "updated_at": datetime.now(timezone.utc).isoformat()},
            )
        return resp.status_code == 200 and bool(resp.json())
    except Exception as exc:  # noqa: BLE001
        logger.warning("dialer stage advance failed: %s", exc)
        return False


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
        market = "canada" if call.get("lead_table") == "canada_leads" else "us"
        await store.dnc_add(call["phone_e164"], market,
                            f"rep disposition on call {call_id}", scope.rep_id)
        side_effects["dnc_added"] = True
    if body.disposition == "callback" and body.callback:
        check = compliance.check_calling_window(call["phone_e164"])
        cb = await store.create_callback({
            "rep_id": scope.rep_id,
            "lead_id": call.get("lead_id"),
            "lead_table": call.get("lead_table"),
            "call_id": call_id,
            "phone_e164": call["phone_e164"],
            "business_name": call.get("business_name") or "",
            "contact_name": call.get("contact_name") or "",
            "due_at": body.callback.due_at,
            "timezone": check.tz,
            "note": body.callback.note[:1000],
        })
        side_effects["callback"] = cb
    if body.advance_stage:
        if body.advance_stage not in _ADVANCE_STAGES:
            raise HTTPException(400, f"Stage '{body.advance_stage}' cannot be set from the dialer")
        side_effects["stage_advanced"] = await _advance_lead_stage(
            call, scope.rep_id, body.advance_stage)

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
