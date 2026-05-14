"""
Schedule Builder API Routes — Staff scheduling with AI recommendations.

Endpoints:
  GET    /api/schedule/staff/{merchant_id}         → List staff roster
  POST   /api/schedule/staff                       → Add staff member
  PUT    /api/schedule/staff/{staff_id}             → Update staff member
  DELETE /api/schedule/staff/{staff_id}             → Deactivate staff member
  GET    /api/schedule/shifts/{merchant_id}         → Get shifts for week
  POST   /api/schedule/shifts                      → Create shift
  PUT    /api/schedule/shifts/{shift_id}            → Update shift
  DELETE /api/schedule/shifts/{shift_id}            → Delete shift
  POST   /api/schedule/publish                     → Publish schedule for a week
  GET    /api/schedule/holidays                    → Get holidays for week
  POST   /api/schedule/recommend/{merchant_id}     → Generate AI recommendations
"""
import logging
from datetime import date, time, datetime
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger("meridian.api.schedule")

router = APIRouter(prefix="/api/schedule", tags=["schedule"])


# ─── Request / Response Models ─────────────────────────────────

class StaffMemberCreate(BaseModel):
    merchant_id: str
    portal_context: str = "us"
    name: str
    role: str
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
    week_start_date: str  # YYYY-MM-DD
    day_of_week: int = Field(ge=0, le=6)
    shift_date: str
    start_time: str  # HH:MM
    end_time: str
    role: str
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


# ─── Demo Data (used until DB tables are created) ──────────────

_demo_staff = [
    {
        "id": "staff-1", "merchant_id": "demo", "portal_context": "us",
        "name": "Alex", "role": "barista", "color": "#17C5B0",
        "hourly_rate": 1600, "availability": {}, "active": True,
    },
    {
        "id": "staff-2", "merchant_id": "demo", "portal_context": "us",
        "name": "Sam", "role": "barista", "color": "#1A8FD6",
        "hourly_rate": 1650, "availability": {}, "active": True,
    },
    {
        "id": "staff-3", "merchant_id": "demo", "portal_context": "us",
        "name": "Jordan", "role": "bar_lead", "color": "#E06B5E",
        "hourly_rate": 2000, "availability": {}, "active": True,
    },
]


# ─── Staff Endpoints ──────────────────────────────────────────

@router.get("/staff/{merchant_id}")
async def list_staff(merchant_id: str):
    """List staff roster for a merchant."""
    logger.info(f"Listing staff for merchant {merchant_id}")
    # TODO: Query from DB when tables are created
    return {"staff": _demo_staff, "total": len(_demo_staff)}


@router.post("/staff")
async def create_staff(body: StaffMemberCreate):
    """Add a new staff member."""
    logger.info(f"Creating staff member: {body.name}")
    new_id = f"staff-{uuid4().hex[:8]}"
    member = {
        "id": new_id,
        "merchant_id": body.merchant_id,
        "portal_context": body.portal_context,
        "name": body.name,
        "role": body.role,
        "color": body.color,
        "hourly_rate": body.hourly_rate,
        "availability": body.availability,
        "active": True,
    }
    return {"staff_member": member}


@router.put("/staff/{staff_id}")
async def update_staff(staff_id: str, body: StaffMemberUpdate):
    """Update an existing staff member."""
    logger.info(f"Updating staff member {staff_id}")
    # TODO: Update in DB
    updates = body.model_dump(exclude_none=True)
    return {"staff_id": staff_id, "updated": updates}


@router.delete("/staff/{staff_id}")
async def deactivate_staff(staff_id: str):
    """Soft-delete (deactivate) a staff member."""
    logger.info(f"Deactivating staff member {staff_id}")
    # TODO: Set active=False in DB
    return {"staff_id": staff_id, "active": False}


# ─── Shift Endpoints ──────────────────────────────────────────

@router.get("/shifts/{merchant_id}")
async def get_shifts(
    merchant_id: str,
    week_start: str = Query(default="", description="Week start date YYYY-MM-DD"),
):
    """Get all shifts for a merchant's week."""
    logger.info(f"Getting shifts for merchant {merchant_id}, week {week_start}")
    # TODO: Query from DB
    return {"shifts": [], "total": 0}


@router.post("/shifts")
async def create_shift(body: ShiftCreate):
    """Create a new shift."""
    logger.info(f"Creating shift for {body.shift_date} {body.start_time}-{body.end_time}")
    new_id = f"shift-{uuid4().hex[:8]}"
    shift = {
        "id": new_id,
        **body.model_dump(),
    }
    return {"shift": shift}


@router.put("/shifts/{shift_id}")
async def update_shift(shift_id: str, body: ShiftUpdate):
    """Update an existing shift."""
    logger.info(f"Updating shift {shift_id}")
    updates = body.model_dump(exclude_none=True)
    return {"shift_id": shift_id, "updated": updates}


@router.delete("/shifts/{shift_id}")
async def delete_shift(shift_id: str):
    """Delete a shift."""
    logger.info(f"Deleting shift {shift_id}")
    return {"shift_id": shift_id, "deleted": True}


# ─── Publish Endpoint ─────────────────────────────────────────

@router.post("/publish")
async def publish_schedule(body: PublishRequest):
    """Publish the schedule for a week — marks all shifts as published."""
    logger.info(f"Publishing schedule for {body.merchant_id}, week {body.week_start_date}")
    # TODO: Update shift statuses and create published_schedules record
    return {
        "merchant_id": body.merchant_id,
        "week_start_date": body.week_start_date,
        "status": "published",
        "published_at": datetime.utcnow().isoformat(),
    }


# ─── Holidays Endpoint ────────────────────────────────────────

@router.get("/holidays")
async def get_holidays(
    country: str = Query(default="US", description="US or CA"),
    week_start: str = Query(default="", description="Week start date YYYY-MM-DD"),
):
    """Get holidays for a specific week and country."""
    logger.info(f"Getting holidays for {country}, week {week_start}")
    # TODO: Query from holidays table
    return {"holidays": [], "country": country, "week_start": week_start}


# ─── AI Recommendation Endpoint ───────────────────────────────

@router.post("/recommend/{merchant_id}")
async def recommend_shifts(
    merchant_id: str,
    week_start: str = Query(default="", description="Week start date YYYY-MM-DD"),
):
    """Generate AI-powered shift recommendations based on peak hour data."""
    logger.info(f"Generating recommendations for {merchant_id}, week {week_start}")
    # TODO: Integrate with peak hour analysis and generate real recommendations
    recommendations = [
        {
            "id": f"rec-{uuid4().hex[:8]}",
            "day_of_week": 0,
            "start_time": "07:00",
            "end_time": "10:00",
            "role": "any",
            "reason": "Peak morning coverage gap detected",
            "priority": "critical",
        },
        {
            "id": f"rec-{uuid4().hex[:8]}",
            "day_of_week": 5,
            "start_time": "11:00",
            "end_time": "15:00",
            "role": "any",
            "reason": "Saturday lunch rush typically understaffed",
            "priority": "recommended",
        },
    ]
    return {"recommendations": recommendations, "merchant_id": merchant_id}
