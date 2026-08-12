"""SR auto dialer — admin console API ("admin or better", Canada-side).

Everything here is gated router-wide by hierarchy.require_org_admin
(role=='admin' OR the ADMIN_EMAILS allowlist — same doctrine as /api/team).
The console's live board takes its initial snapshot from /live and stays
fresh over Supabase Realtime (dialer_sessions / dialer_calls are in the
publication); these endpoints are also the polling fallback when the preview
runs on the in-memory dev store (no Realtime there).
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from .. import hierarchy
from ..hierarchy import require_org_admin
from ...services.dialer_store import dev_store_active, get_store
from ...services.phone_safety import normalize_e164

logger = logging.getLogger("meridian.api.dialer_admin")

router = APIRouter(prefix="/api/dialer/admin", tags=["dialer-admin"],
                   dependencies=[Depends(require_org_admin)])

_DISPOSITIONS = {"meeting_booked", "interested", "callback", "left_voicemail",
                 "no_answer", "busy", "bad_number", "not_interested", "dnc", "other"}


class AdminCallPatch(BaseModel):
    disposition: str | None = None
    notes: str | None = None


class DncAdd(BaseModel):
    phone: str
    market: str = Field(default="canada", pattern="^(canada|us)$")
    reason: str = ""


async def _rep_directory() -> dict[str, dict]:
    """id -> {name, email, role, portal_context} for labeling console rows."""
    rows = await hierarchy._service_get({  # noqa: SLF001 — same-package service plane
        "select": "id,name,email,role,portal_context,is_active",
    })
    return {r["id"]: r for r in rows if r.get("id")}


@router.get("/live")
async def live_board():
    """Snapshot for the live board: non-ended sessions, their reps, and any
    call currently in flight."""
    store = get_store()
    sessions = await store.live_sessions()
    live_calls = await store.list_calls(live_only=True, limit=100)
    # A rep who closes the tab mid-call leaves the row in dialing/ringing/
    # connected forever — don't show ghosts older than 15 minutes.
    stale_cutoff = (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat()
    live_calls = [c for c in live_calls if (c.get("started_at") or "") >= stale_cutoff]
    reps = await _rep_directory()
    by_session: dict[str, dict] = {}
    for call in live_calls:
        sid = call.get("session_id")
        if sid and sid not in by_session:
            by_session[sid] = call
    out = []
    for s in sessions:
        rep = reps.get(s["rep_id"], {})
        out.append({
            **s,
            "rep_name": rep.get("name") or "Unknown rep",
            "rep_role": rep.get("role") or "sales_rep",
            "current_call": by_session.get(s["id"]),
        })
    return {"sessions": out, "dev_store": dev_store_active()}


@router.get("/calls")
async def call_history(rep_id: str | None = None,
                       disposition: str | None = None,
                       days: int = Query(default=7, ge=1, le=90),
                       limit: int = Query(default=200, ge=1, le=1000)):
    store = get_store()
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    rep_ids = [rep_id] if rep_id else None
    calls = await store.list_calls(rep_ids=rep_ids, disposition=disposition,
                                   since=since, limit=limit)
    reps = await _rep_directory()
    for c in calls:
        c["rep_name"] = (reps.get(c["rep_id"]) or {}).get("name") or "Unknown rep"
    return {"calls": calls}


@router.patch("/calls/{call_id}")
async def admin_patch_call(call_id: str, body: AdminCallPatch,
                           user: dict = Depends(require_org_admin)):
    """Post-hoc processing: admins can correct a disposition or append notes.
    disposition_by records the admin's rep id (audit trail)."""
    store = get_store()
    call = await store.get_call(call_id)
    if not call:
        raise HTTPException(404, "Call not found")
    fields: dict = {}
    if body.disposition is not None:
        if body.disposition not in _DISPOSITIONS:
            raise HTTPException(400, f"Unknown disposition '{body.disposition}'")
        scope = await hierarchy.resolve_scope(user)
        fields["disposition"] = body.disposition
        fields["disposition_by"] = scope.rep_id
        fields["disposition_at"] = datetime.now(timezone.utc).isoformat()
    if body.notes is not None:
        fields["notes"] = body.notes[:4000]
    if not fields:
        raise HTTPException(400, "Nothing to update")
    return {"call": await store.update_call(call_id, fields)}


@router.get("/analytics")
async def analytics(days: int = Query(default=7, ge=1, le=90)):
    """Per-rep and total dialer KPIs over the window: dials, connects,
    connect rate, talk time, dispositions breakdown, blocked count."""
    store = get_store()
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    calls = await store.list_calls(since=since, limit=5000)
    reps = await _rep_directory()

    per_rep: dict[str, dict] = defaultdict(lambda: {
        "dials": 0, "connects": 0, "talk_seconds": 0, "blocked": 0,
        "dispositions": defaultdict(int),
    })
    for c in calls:
        bucket = per_rep[c["rep_id"]]
        if c["status"] == "blocked":
            bucket["blocked"] += 1
            continue
        bucket["dials"] += 1
        if c.get("answered_at") or c["status"] == "connected":
            bucket["connects"] += 1
        bucket["talk_seconds"] += c.get("talk_seconds") or 0
        if c.get("disposition"):
            bucket["dispositions"][c["disposition"]] += 1

    rep_rows = []
    totals = {"dials": 0, "connects": 0, "talk_seconds": 0, "blocked": 0,
              "dispositions": defaultdict(int)}
    for rid, b in per_rep.items():
        rep = reps.get(rid, {})
        connect_rate = round(b["connects"] / b["dials"], 3) if b["dials"] else 0.0
        rep_rows.append({
            "rep_id": rid,
            "rep_name": rep.get("name") or "Unknown rep",
            "rep_role": rep.get("role") or "sales_rep",
            "dials": b["dials"], "connects": b["connects"],
            "connect_rate": connect_rate,
            "talk_seconds": b["talk_seconds"], "blocked": b["blocked"],
            "dispositions": dict(b["dispositions"]),
        })
        for k in ("dials", "connects", "talk_seconds", "blocked"):
            totals[k] += b[k]
        for d, n in b["dispositions"].items():
            totals["dispositions"][d] += n
    rep_rows.sort(key=lambda r: r["dials"], reverse=True)
    totals["connect_rate"] = (round(totals["connects"] / totals["dials"], 3)
                              if totals["dials"] else 0.0)
    totals["dispositions"] = dict(totals["dispositions"])
    return {"days": days, "reps": rep_rows, "totals": totals}


@router.get("/callbacks")
async def all_callbacks(status: str = Query(default="pending", pattern="^(pending|done|cancelled)$")):
    store = get_store()
    rows = await store.list_callbacks(rep_ids=None, status=status, limit=500)
    reps = await _rep_directory()
    for r in rows:
        r["rep_name"] = (reps.get(r["rep_id"]) or {}).get("name") or "Unknown rep"
    return {"callbacks": rows}


@router.get("/dnc")
async def dnc_list():
    return {"entries": await get_store().dnc_list()}


@router.post("/dnc")
async def dnc_add(body: DncAdd, user: dict = Depends(require_org_admin)):
    norm = normalize_e164(body.phone)
    if not norm:
        raise HTTPException(400, "Invalid phone number")
    scope = await hierarchy.resolve_scope(user)
    await get_store().dnc_add(norm, body.market, body.reason[:500] or "admin console",
                              scope.rep_id)
    return {"ok": True, "phone_e164": norm}


@router.delete("/dnc/{phone}")
async def dnc_remove(phone: str):
    norm = normalize_e164(phone)
    if not norm:
        raise HTTPException(400, "Invalid phone number")
    await get_store().dnc_remove(norm)
    return {"ok": True}
