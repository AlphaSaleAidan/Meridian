"""Durable store for the Canada phone-lead dialing pool + booking calendar.

Unlike dialer_store (sessions/calls telemetry, which can run in an in-memory
preview store), this data is DURABLE and always hits Supabase with the
service-role key:
  * canada_phone_leads — the dialing pool (capture / recapture / enrichment).
  * dialer_appointments — booked demos.
  * canada_leads / us_leads — READ never; WRITE only via promote() (the one
    deliberate bridge from the pool into the market's real pipeline).

All mutations are backend-only (RLS gives reps/managers scoped SELECT for
Realtime). The router owns auth + hierarchy scoping; this layer is CRUD.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

import httpx

logger = logging.getLogger("meridian.services.phone_leads_store")

# Pool statuses that are still workable (surface in the dialer queue).
ACTIVE_STATUSES = ("new", "attempting", "contacted", "callback")

_LEAD_COLS = (
    "id,business_name,contact_name,phone_e164,contact_email,city,province,"
    "vertical,pos_system,pos_source,website,est_monthly_value,notes,status,"
    "attempts,last_attempt_at,last_disposition,next_action_at,rep_id,source,"
    "converted_lead_id,converted_at,created_at,updated_at"
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _env() -> tuple[str, str]:
    url = os.environ.get("SUPABASE_URL", "")
    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
           or os.environ.get("SUPABASE_SERVICE_KEY", ""))
    return url, key


async def _req(method: str, table: str, params: dict | None = None,
               json: dict | list | None = None, prefer: str = "return=representation") -> list[dict]:
    url, key = _env()
    if not url or not key:
        raise RuntimeError("Supabase env missing for phone-leads store")
    headers = {"Authorization": f"Bearer {key}", "apikey": key, "Prefer": prefer}
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.request(method, f"{url}/rest/v1/{table}",
                                    headers=headers, params=params or {}, json=json)
    if resp.status_code not in (200, 201, 204):
        logger.error("phone-leads %s %s: %s %s", method, table, resp.status_code, resp.text[:300])
        raise RuntimeError(f"phone-leads {table} {resp.status_code}: {resp.text[:200]}")
    if resp.status_code == 204 or not resp.text:
        return []
    body = resp.json()
    return body if isinstance(body, list) else [body]


# ── canada_phone_leads ────────────────────────────────────────────────────────

async def queue_for_rep(rep_id: str, limit: int = 200) -> list[dict]:
    """Workable leads owned by this rep (or shared, rep_id NULL), whose
    recapture clock is due (next_action_at null or in the past). Ordered so
    the most-overdue re-attempts and never-tried leads come first."""
    now = _now()
    # PostgREST: (rep_id = me OR rep_id is null) AND status in active AND
    # (next_action_at is null OR next_action_at <= now)
    params = {
        "select": _LEAD_COLS,
        "or": f"(rep_id.eq.{rep_id},rep_id.is.null)",
        "status": f"in.({','.join(ACTIVE_STATUSES)})",
        "and": f"(or(next_action_at.is.null,next_action_at.lte.{now}))",
        "order": "next_action_at.asc.nullsfirst,attempts.asc,created_at.asc",
        "limit": str(limit),
    }
    return await _req("GET", "canada_phone_leads", params=params)


async def list_for_rep(rep_id: str, status: str | None = None, limit: int = 500) -> list[dict]:
    params = {"select": _LEAD_COLS, "or": f"(rep_id.eq.{rep_id},rep_id.is.null)",
              "order": "created_at.desc", "limit": str(limit)}
    if status:
        params["status"] = f"eq.{status}"
    return await _req("GET", "canada_phone_leads", params=params)


async def get(lead_id: str) -> dict | None:
    rows = await _req("GET", "canada_phone_leads",
                      params={"id": f"eq.{lead_id}", "select": _LEAD_COLS})
    return rows[0] if rows else None


async def create(fields: dict) -> dict:
    rows = await _req("POST", "canada_phone_leads", json={**fields, "updated_at": _now()})
    return rows[0]


async def bulk_create(rows: list[dict]) -> list[dict]:
    stamped = [{**r, "updated_at": _now()} for r in rows]
    return await _req("POST", "canada_phone_leads", json=stamped)


async def update(lead_id: str, fields: dict, rep_guard: str | None = None) -> dict | None:
    params = {"id": f"eq.{lead_id}"}
    if rep_guard:
        # own OR shared — prevents editing another rep's assigned lead.
        params["or"] = f"(rep_id.eq.{rep_guard},rep_id.is.null)"
    rows = await _req("PATCH", "canada_phone_leads", params=params,
                      json={**fields, "updated_at": _now()})
    return rows[0] if rows else None


async def dedupe_phones(rep_id: str, phones: list[str]) -> set[str]:
    """Phones already in this rep's pool (avoid importing duplicates)."""
    if not phones:
        return set()
    rows = await _req("GET", "canada_phone_leads", params={
        "select": "phone_e164",
        "or": f"(rep_id.eq.{rep_id},rep_id.is.null)",
        "phone_e164": f"in.({','.join(phones)})",
    })
    return {r["phone_e164"] for r in rows}


async def promote_to_pipeline(lead: dict, rep_id: str,
                              table: str = "canada_leads") -> dict:
    """The one-click bridge: create a pipeline row (canada_leads, or us_leads
    for US-market phone leads — same column shape) from a phone lead, link
    both, mark the phone lead converted. Returns the new lead row.

    Idempotent-ish: if already converted, returns the existing linkage without
    inserting a duplicate."""
    if lead.get("converted_lead_id"):
        return {"id": lead["converted_lead_id"], "already": True}

    dollars = round((lead.get("est_monthly_value") or 0) / 100)
    pipeline_row = {
        "business_name": lead.get("business_name") or "",
        "contact_name": lead.get("contact_name") or "",
        "contact_email": lead.get("contact_email") or f"{lead['id'][:8]}@phone-lead.invalid",
        "contact_phone": lead.get("phone_e164") or "",
        "vertical": lead.get("vertical") or "",
        "stage": "appointment_set",
        "monthly_value": dollars,
        "city": lead.get("city") or "",
        "province": lead.get("province") or "",
        "source": f"auto-dialer:{lead.get('source') or 'phone-lead'}",
        "notes": (lead.get("notes") or "") + (
            f"\n[from phone dialer — POS: {lead.get('pos_system') or 'unknown'}]"),
        "rep_id": rep_id,
    }
    created = await _req("POST", table, json=pipeline_row)
    new_lead = created[0]
    await update(lead["id"], {
        "status": "converted",
        "converted_lead_id": new_lead["id"],
        "converted_at": _now(),
    })
    return new_lead


# ── dialer_appointments ───────────────────────────────────────────────────────

async def create_appointment(fields: dict) -> dict:
    rows = await _req("POST", "dialer_appointments", json={**fields, "updated_at": _now()})
    return rows[0]


async def list_appointments(rep_ids: list[str] | None, from_iso: str | None = None,
                            to_iso: str | None = None, limit: int = 500) -> list[dict]:
    params: dict = {"select": "*", "order": "scheduled_at.asc", "limit": str(limit)}
    if rep_ids is not None:
        if not rep_ids:
            return []
        params["rep_id"] = f"in.({','.join(rep_ids)})"
    if from_iso:
        params["scheduled_at"] = f"gte.{from_iso}"
    if to_iso:
        # second filter on same column needs the and() form
        params["and"] = f"(scheduled_at.lte.{to_iso})"
    return await _req("GET", "dialer_appointments", params=params)


async def update_appointment(appt_id: str, fields: dict, rep_guard: str | None = None) -> dict | None:
    params = {"id": f"eq.{appt_id}"}
    if rep_guard:
        params["rep_id"] = f"eq.{rep_guard}"
    rows = await _req("PATCH", "dialer_appointments", params=params,
                      json={**fields, "updated_at": _now()})
    return rows[0] if rows else None
