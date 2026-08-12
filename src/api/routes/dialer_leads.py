"""Canada phone-lead pool: queue, capture/import, recapture, booking, promote.

Separate from dialer.py (session/call telemetry) — this is the DURABLE side:
the dialing pool (canada_phone_leads), the booking calendar
(dialer_appointments), and the one-click bridge into the real pipeline
(canada_leads via promote). All rep-scoped through hierarchy.resolve_scope.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from .. import hierarchy
from ..auth import require_jwt
from ..hierarchy import require_org_admin
from ...services import dialer_compliance as compliance
from ...services import phone_leads_store as store
from ...services.dialer_store import get_store as get_call_store
from ...services.phone_safety import normalize_e164

logger = logging.getLogger("meridian.api.dialer_leads")

router = APIRouter(prefix="/api/dialer", tags=["dialer-leads"])

_POS_VALUES = {"square", "clover", "toast", "lightspeed", "shopify", "none", "unknown"}


class PhoneLeadIn(BaseModel):
    business_name: str = ""
    contact_name: str = ""
    phone: str
    contact_email: str = ""
    city: str = ""
    province: str = ""
    vertical: str = ""
    pos_system: str = "unknown"
    website: str = ""
    est_monthly_value: int = Field(default=0, ge=0)   # cents
    notes: str = ""
    source: str = ""


class ImportIn(BaseModel):
    source: str = ""
    leads: list[PhoneLeadIn]


class PhoneLeadPatch(BaseModel):
    business_name: str | None = None
    contact_name: str | None = None
    pos_system: str | None = None
    vertical: str | None = None
    est_monthly_value: int | None = Field(default=None, ge=0)
    website: str | None = None
    notes: str | None = None
    status: str | None = None


class AppointmentIn(BaseModel):
    phone_lead_id: str
    scheduled_at: str
    duration_min: int = Field(default=30, ge=5, le=240)
    title: str = "Demo"
    notes: str = ""


class AppointmentPatch(BaseModel):
    status: str = Field(pattern="^(booked|completed|cancelled|no_show)$")


async def _scope(user: dict) -> hierarchy.RepScope:
    s = await hierarchy.resolve_scope(user)
    if not s.rep_id:
        raise HTTPException(403, "No sales rep profile for this account")
    return s


def _norm_pos(v: str) -> str:
    v = (v or "unknown").strip().lower()
    return v if v in _POS_VALUES or v else "unknown"


def _lead_fields(p: PhoneLeadIn, rep_id: str, source: str) -> dict:
    return {
        "business_name": p.business_name[:200],
        "contact_name": p.contact_name[:200],
        "phone_e164": normalize_e164(p.phone) or p.phone[:32],
        "contact_email": p.contact_email[:200],
        "city": p.city[:120], "province": p.province[:80],
        "vertical": p.vertical[:80],
        "pos_system": _norm_pos(p.pos_system),
        "pos_source": "rep" if not source else "import",
        "website": p.website[:300],
        "est_monthly_value": p.est_monthly_value,
        "notes": p.notes[:4000],
        "status": "new",
        "rep_id": rep_id,
        "source": (source or p.source or "manual")[:120],
        "created_by_rep_id": rep_id,
    }


# ── Queue (the dialer's calling list) ─────────────────────────────────────────

@router.get("/queue")
async def get_queue(user: dict = Depends(require_jwt)):
    """Recapture-due phone leads for this rep, each annotated with the dial-time
    compliance gate (DNC + calling window) and its enrichment so the UI can show
    'has Square POS', attempts, last outcome before the rep hits Dial."""
    scope = await _scope(user)
    leads = await store.queue_for_rep(scope.rep_id)
    call_store = get_call_store()

    phones = [normalize_e164(ld.get("phone_e164") or "") for ld in leads]
    dnc = await call_store.dnc_filter([p for p in phones if p])

    out = []
    for ld in leads:
        norm = normalize_e164(ld.get("phone_e164") or "")
        check = compliance.check_calling_window(norm)
        on_dnc = norm in dnc
        out.append({
            **ld,
            "kind": "lead",
            "phone_e164": norm,
            "on_dnc": on_dnc,
            "callable_now": bool(norm) and not on_dnc and check.allowed,
            "gate_reason": "dnc" if on_dnc else check.reason,
            "local_time": check.local_time,
            "window_label": check.window_label,
            "country": check.country,
        })
    return {"leads": out, "callbacks": [], "dev_store": False}


# ── Capture / recapture management ────────────────────────────────────────────

@router.post("/phone-leads")
async def create_phone_lead(body: PhoneLeadIn, user: dict = Depends(require_jwt)):
    scope = await _scope(user)
    if not normalize_e164(body.phone):
        raise HTTPException(400, "A valid phone number is required")
    lead = await store.create(_lead_fields(body, scope.rep_id, ""))
    return {"lead": lead}


@router.post("/phone-leads/import")
async def import_phone_leads(body: ImportIn, user: dict = Depends(require_jwt)):
    """Bulk-load a list of numbers into the rep's pool. Skips rows without a
    valid phone and de-dupes against the rep's existing pool."""
    scope = await _scope(user)
    src = (body.source or "import").strip()[:120]
    valid, skipped_invalid = [], 0
    for p in body.leads:
        if not normalize_e164(p.phone):
            skipped_invalid += 1
            continue
        valid.append(p)
    norms = [normalize_e164(p.phone) for p in valid]
    existing = await store.dedupe_phones(scope.rep_id, norms)
    fresh = [_lead_fields(p, scope.rep_id, src) for p, n in zip(valid, norms) if n not in existing]
    created = await store.bulk_create(fresh) if fresh else []
    return {
        "imported": len(created),
        "skipped_duplicate": len(valid) - len(fresh),
        "skipped_invalid": skipped_invalid,
    }


@router.get("/phone-leads")
async def list_phone_leads(status: str | None = None, user: dict = Depends(require_jwt)):
    scope = await _scope(user)
    return {"leads": await store.list_for_rep(scope.rep_id, status=status)}


@router.patch("/phone-leads/{lead_id}")
async def patch_phone_lead(lead_id: str, body: PhoneLeadPatch, user: dict = Depends(require_jwt)):
    scope = await _scope(user)
    fields = {k: v for k, v in body.model_dump(exclude_none=True).items()}
    if "pos_system" in fields:
        fields["pos_system"] = _norm_pos(fields["pos_system"])
    if not fields:
        raise HTTPException(400, "Nothing to update")
    lead = await store.update(lead_id, fields, rep_guard=scope.rep_id)
    if not lead:
        raise HTTPException(404, "Lead not found")
    return {"lead": lead}


# ── Promote to pipeline (the one-click bridge) ────────────────────────────────

@router.post("/phone-leads/{lead_id}/promote")
async def promote_phone_lead(lead_id: str, user: dict = Depends(require_jwt)):
    """One click: create a canada_leads pipeline record from this phone lead,
    link them, mark the phone lead converted. The ONLY write into canada_leads."""
    scope = await _scope(user)
    lead = await store.get(lead_id)
    if not lead or (lead.get("rep_id") not in (None, scope.rep_id) and not scope.is_admin):
        raise HTTPException(404, "Lead not found")
    new_lead = await store.promote_to_pipeline(lead, scope.rep_id)
    return {"pipeline_lead": new_lead, "already_converted": bool(new_lead.get("already"))}


# ── Booking calendar ──────────────────────────────────────────────────────────

@router.post("/appointments")
async def book_appointment(body: AppointmentIn, user: dict = Depends(require_jwt)):
    """Book a demo for a phone lead, mark the lead 'booked', and promote it into
    the pipeline in the same click (so the calendar and the pipeline agree)."""
    scope = await _scope(user)
    lead = await store.get(body.phone_lead_id)
    if not lead or (lead.get("rep_id") not in (None, scope.rep_id) and not scope.is_admin):
        raise HTTPException(404, "Lead not found")

    check = compliance.check_calling_window(lead.get("phone_e164") or "")
    pipeline = await store.promote_to_pipeline(lead, scope.rep_id)
    appt = await store.create_appointment({
        "phone_lead_id": lead["id"],
        "rep_id": scope.rep_id,
        "lead_id": pipeline.get("id"),
        "business_name": lead.get("business_name") or "",
        "contact_name": lead.get("contact_name") or "",
        "phone_e164": lead.get("phone_e164") or "",
        "scheduled_at": body.scheduled_at,
        "duration_min": body.duration_min,
        "timezone": check.tz,
        "title": body.title[:120] or "Demo",
        "notes": body.notes[:2000],
    })
    await store.update(lead["id"], {"status": "booked", "next_action_at": None},
                       rep_guard=scope.rep_id)
    return {"appointment": appt, "pipeline_lead_id": pipeline.get("id")}


@router.get("/appointments")
async def list_my_appointments(days: int = Query(default=30, ge=1, le=120),
                               user: dict = Depends(require_jwt)):
    scope = await _scope(user)
    now = datetime.now(timezone.utc)
    from_iso = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    rows = await store.list_appointments([scope.rep_id], from_iso=from_iso)
    return {"appointments": rows}


@router.patch("/appointments/{appt_id}")
async def patch_appointment(appt_id: str, body: AppointmentPatch, user: dict = Depends(require_jwt)):
    scope = await _scope(user)
    row = await store.update_appointment(appt_id, {"status": body.status}, rep_guard=scope.rep_id)
    if not row:
        raise HTTPException(404, "Appointment not found")
    return {"appointment": row}


# ── Admin views ───────────────────────────────────────────────────────────────

admin_router = APIRouter(prefix="/api/dialer/admin", tags=["dialer-leads-admin"],
                         dependencies=[Depends(require_org_admin)])


@admin_router.get("/appointments")
async def all_appointments(days: int = Query(default=30, ge=1, le=120)):
    now = datetime.now(timezone.utc)
    from_iso = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    return {"appointments": await store.list_appointments(None, from_iso=from_iso)}
