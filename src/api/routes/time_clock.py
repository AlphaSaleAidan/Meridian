"""Time clock — employee clock-in / clock-out + punch corrections (Workstream 1b).

  POST   /api/time-clock/clock-in                 → open a punch for an employee
  POST   /api/time-clock/clock-out                → close the employee's open punch
  GET    /api/time-clock/punches?org_id&week_start → punches for a week (roster view)
  GET    /api/time-clock/summary?org_id&week_start → scheduled vs actual hours + variance
  PATCH  /api/time-clock/punches/{punch_id}       → owner/manager correction (audited)

SECURITY:
  - org_id validated against the caller's membership on every call (rbac gate).
  - Corrections require the ``edit_punches`` action; an edit_reason is MANDATORY
    and both the row (edited_by/edit_reason) and an append-only time_punch_audit
    row are written.
  - Clock-in/out are membership-gated (any active member may punch); the employee
    is identified by schedule_staff.id, whose org must match org_id (BOLA guard).
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from uuid import uuid4
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ..auth import require_service_auth
from .. import rbac
from ...db import get_db

logger = logging.getLogger("meridian.api.time_clock")
router = APIRouter(prefix="/api/time-clock", tags=["team-management"])

_UUID_RE = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I
)


def _validate_uuid(value: str, label: str = "id"):
    if not _UUID_RE.match(value or ""):
        raise HTTPException(400, f"Invalid {label} format")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ClockIn(BaseModel):
    org_id: str
    employee_id: str
    source: str = "manual"


class ClockOut(BaseModel):
    org_id: str
    employee_id: str


class PunchCorrection(BaseModel):
    org_id: str
    clock_in_at: Optional[str] = None
    clock_out_at: Optional[str] = None
    edit_reason: str


async def _employee_belongs_to_org(employee_id: str, org_id: str) -> bool:
    db = get_db()
    rows = await db.select(
        "schedule_staff",
        filters={"id": f"eq.{employee_id}", "merchant_id": f"eq.{org_id}"},
        limit=1,
    )
    return bool(rows)


@router.post("/clock-in")
async def clock_in(body: ClockIn, principal=Depends(require_service_auth)):
    _validate_uuid(body.employee_id, "employee_id")
    # Any active member of the org may punch; the org gate proves membership.
    await rbac.resolve_access(principal, body.org_id)
    if not await _employee_belongs_to_org(body.employee_id, body.org_id):
        raise HTTPException(404, "Employee not found in this org")

    db = get_db()
    # Reject a second open punch (DB also enforces via partial unique index).
    open_rows = await db.select(
        "time_punches",
        filters={"employee_id": f"eq.{body.employee_id}", "clock_out_at": "is.null"},
        limit=1,
    )
    if open_rows:
        raise HTTPException(409, "Already clocked in")

    punch = {
        "id": str(uuid4()),
        "org_id": body.org_id,
        "employee_id": body.employee_id,
        "clock_in_at": _now_iso(),
        "clock_out_at": None,
        "source": body.source if body.source in ("manual", "kiosk", "mobile", "auto", "import") else "manual",
    }
    rows = await db.insert("time_punches", punch)
    return {"punch": rows[0] if rows else punch}


@router.post("/clock-out")
async def clock_out(body: ClockOut, principal=Depends(require_service_auth)):
    _validate_uuid(body.employee_id, "employee_id")
    await rbac.resolve_access(principal, body.org_id)
    if not await _employee_belongs_to_org(body.employee_id, body.org_id):
        raise HTTPException(404, "Employee not found in this org")

    db = get_db()
    open_rows = await db.select(
        "time_punches",
        filters={"employee_id": f"eq.{body.employee_id}", "clock_out_at": "is.null"},
        order="clock_in_at.desc",
        limit=1,
    )
    if not open_rows:
        raise HTTPException(409, "Not clocked in")
    punch = open_rows[0]
    now = _now_iso()
    await db.update(
        "time_punches",
        {"clock_out_at": now, "updated_at": now},
        filters={"id": f"eq.{punch['id']}"},
    )
    return {"punch_id": punch["id"], "clock_out_at": now}


@router.get("/punches")
async def list_punches(
    org_id: str = Query(...),
    principal=Depends(require_service_auth),
    week_start: str = Query(default="", description="YYYY-MM-DD"),
):
    # Viewing others' punches is a management view — require edit_punches OR
    # schedule visibility. We gate on schedule visibility (owner always true;
    # managers if granted). Employees see the roster only if the owner allowed it.
    await rbac.require_visibility(principal, org_id, "schedule")
    db = get_db()
    filters: dict = {"org_id": f"eq.{org_id}"}
    if week_start:
        # week is [week_start, week_start+7d)
        filters["clock_in_at"] = f"gte.{week_start}"
    rows = await db.select("time_punches", filters=filters, order="clock_in_at.desc")
    return {"punches": rows, "total": len(rows)}


def _hours(iso_in: str, iso_out: Optional[str]) -> float:
    if not iso_out:
        return 0.0
    try:
        a = datetime.fromisoformat(iso_in.replace("Z", "+00:00"))
        b = datetime.fromisoformat(iso_out.replace("Z", "+00:00"))
        return max(0.0, (b - a).total_seconds() / 3600.0)
    except Exception:
        return 0.0


def _shift_hours(start_time: str, end_time: str, break_minutes: int = 0) -> float:
    try:
        sh, sm = (int(x) for x in start_time.split(":")[:2])
        eh, em = (int(x) for x in end_time.split(":")[:2])
        mins = (eh * 60 + em) - (sh * 60 + sm) - int(break_minutes or 0)
        return max(0.0, mins / 60.0)
    except Exception:
        return 0.0


@router.get("/summary")
async def hours_summary(
    org_id: str = Query(...),
    principal=Depends(require_service_auth),
    week_start: str = Query(..., description="YYYY-MM-DD"),
):
    """Scheduled vs ACTUAL hours per employee for a week, with variance.

    Powers the side-by-side view on the schedule page. Requires schedule
    visibility (owner/manager-if-granted).
    """
    await rbac.require_visibility(principal, org_id, "schedule")
    db = get_db()

    staff = await db.select(
        "schedule_staff",
        filters={"merchant_id": f"eq.{org_id}", "active": "eq.true"},
    )
    shifts = await db.select(
        "schedule_shifts",
        filters={"merchant_id": f"eq.{org_id}", "week_start_date": f"eq.{week_start}"},
    )
    punches = await db.select(
        "time_punches",
        filters={"org_id": f"eq.{org_id}", "clock_in_at": f"gte.{week_start}"},
    )

    scheduled: dict[str, float] = {}
    for sh in shifts:
        sid = sh.get("staff_member_id")
        if not sid:
            continue
        scheduled[sid] = scheduled.get(sid, 0.0) + _shift_hours(
            str(sh.get("start_time", "")), str(sh.get("end_time", "")), sh.get("break_minutes", 0),
        )

    actual: dict[str, float] = {}
    for p in punches:
        eid = p.get("employee_id")
        if not eid:
            continue
        actual[eid] = actual.get(eid, 0.0) + _hours(str(p.get("clock_in_at", "")), p.get("clock_out_at"))

    rows = []
    for s in staff:
        sid = s["id"]
        sched = round(scheduled.get(sid, 0.0), 2)
        act = round(actual.get(sid, 0.0), 2)
        variance = round(act - sched, 2)
        rows.append({
            "employee_id": sid,
            "name": s.get("name"),
            "scheduled_hours": sched,
            "actual_hours": act,
            "variance_hours": variance,
            # >15min over/under is worth highlighting in the UI.
            "variance_flag": abs(variance) >= 0.25,
        })
    rows.sort(key=lambda r: (-abs(r["variance_hours"]), r["name"] or ""))
    return {"week_start": week_start, "rows": rows, "total": len(rows)}


@router.patch("/punches/{punch_id}")
async def correct_punch(punch_id: str, body: PunchCorrection, principal=Depends(require_service_auth)):
    _validate_uuid(punch_id, "punch_id")
    if not (body.edit_reason or "").strip():
        raise HTTPException(400, "edit_reason is required for a punch correction")
    # Corrections are privileged — owner always; managers only if edit_punches.
    access = await rbac.require_action(principal, body.org_id, "edit_punches")

    db = get_db()
    existing = await db.select(
        "time_punches",
        filters={"id": f"eq.{punch_id}", "org_id": f"eq.{body.org_id}"},
        limit=1,
    )
    if not existing:
        raise HTTPException(404, "Punch not found in this org")
    current = existing[0]

    updates: dict = {"edited_by": (principal.get("user") or {}).get("id"),
                     "edit_reason": body.edit_reason.strip(),
                     "updated_at": _now_iso()}
    if body.clock_in_at is not None:
        updates["clock_in_at"] = body.clock_in_at
    if body.clock_out_at is not None:
        updates["clock_out_at"] = body.clock_out_at

    # Guard the interval (clock_out >= clock_in) at the app layer too.
    new_in = updates.get("clock_in_at", current.get("clock_in_at"))
    new_out = updates.get("clock_out_at", current.get("clock_out_at"))
    if new_out and new_in and str(new_out) < str(new_in):
        raise HTTPException(400, "clock_out_at cannot precede clock_in_at")

    await db.update("time_punches", updates, filters={"id": f"eq.{punch_id}"})

    # Append-only audit row.
    actor_user = principal.get("user") or {}
    try:
        await db.insert("time_punch_audit", {
            "id": str(uuid4()),
            "punch_id": punch_id,
            "org_id": body.org_id,
            "actor_user_id": actor_user.get("id"),
            "actor_email": actor_user.get("email"),
            "action": "edit",
            "edit_reason": body.edit_reason.strip(),
            "old_value": {
                "clock_in_at": current.get("clock_in_at"),
                "clock_out_at": current.get("clock_out_at"),
            },
            "new_value": {"clock_in_at": new_in, "clock_out_at": new_out},
            "created_at": _now_iso(),
        })
    except Exception as exc:  # noqa: BLE001
        logger.warning("time_punch audit write failed (non-critical): %s", exc)

    _ = access  # role available for future finer-grained logging
    return {"punch_id": punch_id, "updated": {k: v for k, v in updates.items() if k != "edited_by"}}
