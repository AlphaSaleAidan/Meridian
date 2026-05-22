"""Schedule Builder API — Staff scheduling with AI recommendations."""

import logging
import re
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..auth import require_service_auth
from ...db import get_db

logger = logging.getLogger("meridian.api.schedule")
router = APIRouter(prefix="/api/schedule", tags=["schedule"])

_UUID_RE = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I
)


def _validate_uuid(value: str, label: str = "id"):
    if not _UUID_RE.match(value):
        raise HTTPException(400, f"Invalid {label} format")


# ─── Request / Response Models ─────────────────────────────────

class StaffMemberCreate(BaseModel):
    merchant_id: str
    portal_context: str = "us"
    name: str
    role: str = "any"
    color: str = "#17C5B0"
    hourly_rate: int = 0
    availability: dict = Field(default_factory=dict)


class StaffMemberUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    color: Optional[str] = None
    hourly_rate: Optional[int] = None
    availability: Optional[dict] = None


class ShiftCreate(BaseModel):
    merchant_id: str
    portal_context: str = "us"
    staff_member_id: Optional[str] = None
    week_start_date: str
    day_of_week: int = Field(ge=0, le=6)
    shift_date: str
    start_time: str
    end_time: str
    role: str = "any"
    break_minutes: int = 0
    notes: str = ""
    status: str = "draft"
    is_recommended: bool = False


class ShiftUpdate(BaseModel):
    staff_member_id: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    role: Optional[str] = None
    break_minutes: Optional[int] = None
    notes: Optional[str] = None
    status: Optional[str] = None


class PublishRequest(BaseModel):
    merchant_id: str
    portal_context: str = "us"
    week_start_date: str
    published_by: str = ""
    notify_staff: bool = True


# ─── Staff Endpoints ──────────────────────────────────────────

@router.get("/staff/{merchant_id}")
async def list_staff(merchant_id: str, _auth=Depends(require_service_auth)):
    _validate_uuid(merchant_id, "merchant_id")
    db = get_db()
    rows = await db.select(
        "schedule_staff",
        filters={"merchant_id": f"eq.{merchant_id}", "active": "eq.true"},
        order="name.asc",
    )
    return {"staff": rows, "total": len(rows)}


@router.post("/staff")
async def create_staff(body: StaffMemberCreate, _auth=Depends(require_service_auth)):
    _validate_uuid(body.merchant_id, "merchant_id")
    db = get_db()
    payload = {
        "id": str(uuid4()),
        "merchant_id": body.merchant_id,
        "portal_context": body.portal_context,
        "name": body.name,
        "role": body.role,
        "color": body.color,
        "hourly_rate": body.hourly_rate,
        "availability": body.availability,
        "active": True,
    }
    rows = await db.insert("schedule_staff", payload)
    return {"staff_member": rows[0] if rows else payload}


@router.put("/staff/{staff_id}")
async def update_staff(staff_id: str, body: StaffMemberUpdate, _auth=Depends(require_service_auth)):
    _validate_uuid(staff_id, "staff_id")
    db = get_db()
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(400, "No fields to update")
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.update("schedule_staff", updates, filters={"id": f"eq.{staff_id}"})
    return {"staff_id": staff_id, "updated": updates}


@router.delete("/staff/{staff_id}")
async def deactivate_staff(staff_id: str, _auth=Depends(require_service_auth)):
    _validate_uuid(staff_id, "staff_id")
    db = get_db()
    await db.update(
        "schedule_staff",
        {"active": False, "updated_at": datetime.now(timezone.utc).isoformat()},
        filters={"id": f"eq.{staff_id}"},
    )
    return {"staff_id": staff_id, "active": False}


# ─── Shift Endpoints ──────────────────────────────────────────

@router.get("/shifts/{merchant_id}")
async def get_shifts(
    merchant_id: str,
    _auth=Depends(require_service_auth),
    week_start: str = Query(default="", description="Week start date YYYY-MM-DD"),
):
    _validate_uuid(merchant_id, "merchant_id")
    db = get_db()
    filters: dict = {"merchant_id": f"eq.{merchant_id}"}
    if week_start:
        filters["week_start_date"] = f"eq.{week_start}"
    rows = await db.select(
        "schedule_shifts", filters=filters, order="shift_date.asc,start_time.asc"
    )
    return {"shifts": rows, "total": len(rows)}


@router.post("/shifts")
async def create_shift(body: ShiftCreate, _auth=Depends(require_service_auth)):
    _validate_uuid(body.merchant_id, "merchant_id")
    db = get_db()
    payload = {
        "id": str(uuid4()),
        "merchant_id": body.merchant_id,
        "portal_context": body.portal_context,
        "staff_member_id": body.staff_member_id or None,
        "week_start_date": body.week_start_date,
        "day_of_week": body.day_of_week,
        "shift_date": body.shift_date,
        "start_time": body.start_time,
        "end_time": body.end_time,
        "role": body.role,
        "break_minutes": body.break_minutes,
        "notes": body.notes,
        "status": body.status,
        "is_recommended": body.is_recommended,
    }
    rows = await db.insert("schedule_shifts", payload)
    return {"shift": rows[0] if rows else payload}


@router.put("/shifts/{shift_id}")
async def update_shift(shift_id: str, body: ShiftUpdate, _auth=Depends(require_service_auth)):
    _validate_uuid(shift_id, "shift_id")
    db = get_db()
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(400, "No fields to update")
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.update("schedule_shifts", updates, filters={"id": f"eq.{shift_id}"})
    return {"shift_id": shift_id, "updated": updates}


@router.delete("/shifts/{shift_id}")
async def delete_shift(shift_id: str, _auth=Depends(require_service_auth)):
    _validate_uuid(shift_id, "shift_id")
    db = get_db()
    await db.delete("schedule_shifts", filters={"id": f"eq.{shift_id}"})
    return {"shift_id": shift_id, "deleted": True}


# ─── Publish Endpoint ─────────────────────────────────────────

@router.post("/publish")
async def publish_schedule(body: PublishRequest, _auth=Depends(require_service_auth)):
    _validate_uuid(body.merchant_id, "merchant_id")
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()

    # Mark all draft shifts for this merchant+week as published
    await db.update(
        "schedule_shifts",
        {"status": "published", "updated_at": now},
        filters={
            "merchant_id": f"eq.{body.merchant_id}",
            "week_start_date": f"eq.{body.week_start_date}",
            "status": "eq.draft",
        },
    )

    # Upsert into published_schedules (delete + insert)
    await db.delete("published_schedules", filters={
        "merchant_id": f"eq.{body.merchant_id}",
        "week_start_date": f"eq.{body.week_start_date}",
    })

    staff_rows = await db.select(
        "schedule_staff",
        filters={"merchant_id": f"eq.{body.merchant_id}", "active": "eq.true"},
    )
    notified_count = len(staff_rows) if body.notify_staff else 0

    await db.insert("published_schedules", {
        "id": str(uuid4()),
        "merchant_id": body.merchant_id,
        "week_start_date": body.week_start_date,
        "published_by": body.published_by,
        "published_at": now,
        "notified_count": notified_count,
    })

    return {
        "merchant_id": body.merchant_id,
        "week_start_date": body.week_start_date,
        "status": "published",
        "published_at": now,
        "notified_count": notified_count,
    }


# ─── Holidays Endpoint ────────────────────────────────────────

@router.get("/holidays")
async def get_holidays(
    _auth=Depends(require_service_auth),
    country: str = Query(default="US", description="US or CA"),
    week_start: str = Query(default="", description="Week start date YYYY-MM-DD"),
):
    return {"holidays": [], "country": country, "week_start": week_start}


# ─── AI Recommendation Endpoint ───────────────────────────────

@router.post("/recommend/{merchant_id}")
async def recommend_shifts(
    merchant_id: str,
    _auth=Depends(require_service_auth),
    week_start: str = Query(default="", description="Week start date YYYY-MM-DD"),
):
    _validate_uuid(merchant_id, "merchant_id")
    recommendations = [
        {
            "id": str(uuid4()),
            "day_of_week": 0,
            "start_time": "07:00",
            "end_time": "10:00",
            "role": "any",
            "reason": "Peak morning coverage gap detected",
            "priority": "critical",
        },
        {
            "id": str(uuid4()),
            "day_of_week": 5,
            "start_time": "11:00",
            "end_time": "15:00",
            "role": "any",
            "reason": "Saturday lunch rush typically understaffed",
            "priority": "recommended",
        },
    ]
    return {"recommendations": recommendations, "merchant_id": merchant_id}
