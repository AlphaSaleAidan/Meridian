"""Schedule Builder API — Staff scheduling with AI recommendations."""

import asyncio
import logging
import os
import re
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..auth import enforce_service_member, require_service_auth
from ...db import get_db

logger = logging.getLogger("meridian.api.schedule")
router = APIRouter(prefix="/api/schedule", tags=["schedule"])

_UUID_RE = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I
)


def _validate_uuid(value: str, label: str = "id"):
    if not _UUID_RE.match(value):
        raise HTTPException(400, f"Invalid {label} format")


async def _enforce_row_member(principal, table: str, row_id: str) -> None:
    """BOLA guard for sub-resources keyed by their own id (staff_id/shift_id)
    rather than merchant_id: resolve the owning merchant_id from the row and
    authorize the caller against it. No-op for machine principals (admin/service)
    via enforce_service_member, and a no-op if the row doesn't exist (nothing to
    leak; the downstream update/delete is itself a no-op)."""
    db = get_db()
    rows = await db.select(table, filters={"id": f"eq.{row_id}"}, limit=1)
    if rows and rows[0].get("merchant_id"):
        await enforce_service_member(principal, rows[0]["merchant_id"])


# ─── Request / Response Models ─────────────────────────────────

class StaffMemberCreate(BaseModel):
    merchant_id: str
    portal_context: str = "us"
    name: str
    role: str = "any"
    color: str = "#17C5B0"
    hourly_rate: int = 0
    availability: dict = Field(default_factory=dict)
    phone: Optional[str] = None


class StaffMemberUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    color: Optional[str] = None
    hourly_rate: Optional[int] = None
    availability: Optional[dict] = None
    phone: Optional[str] = None


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
async def list_staff(merchant_id: str, principal=Depends(require_service_auth)):
    await enforce_service_member(principal, merchant_id)
    _validate_uuid(merchant_id, "merchant_id")
    db = get_db()
    rows = await db.select(
        "schedule_staff",
        filters={"merchant_id": f"eq.{merchant_id}", "active": "eq.true"},
        order="name.asc",
    )
    return {"staff": rows, "total": len(rows)}


@router.post("/staff")
async def create_staff(body: StaffMemberCreate, principal=Depends(require_service_auth)):
    await enforce_service_member(principal, body.merchant_id)
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
        "phone": body.phone or None,
        "active": True,
    }
    rows = await db.insert("schedule_staff", payload)
    return {"staff_member": rows[0] if rows else payload}


@router.put("/staff/{staff_id}")
async def update_staff(staff_id: str, body: StaffMemberUpdate, principal=Depends(require_service_auth)):
    _validate_uuid(staff_id, "staff_id")
    await _enforce_row_member(principal, "schedule_staff", staff_id)
    db = get_db()
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(400, "No fields to update")
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.update("schedule_staff", updates, filters={"id": f"eq.{staff_id}"})
    return {"staff_id": staff_id, "updated": updates}


@router.delete("/staff/{staff_id}")
async def deactivate_staff(staff_id: str, principal=Depends(require_service_auth)):
    _validate_uuid(staff_id, "staff_id")
    await _enforce_row_member(principal, "schedule_staff", staff_id)
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
    principal=Depends(require_service_auth),
    week_start: str = Query(default="", description="Week start date YYYY-MM-DD"),
):
    await enforce_service_member(principal, merchant_id)
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
async def create_shift(body: ShiftCreate, principal=Depends(require_service_auth)):
    await enforce_service_member(principal, body.merchant_id)
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
async def update_shift(shift_id: str, body: ShiftUpdate, principal=Depends(require_service_auth)):
    _validate_uuid(shift_id, "shift_id")
    await _enforce_row_member(principal, "schedule_shifts", shift_id)
    db = get_db()
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(400, "No fields to update")
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.update("schedule_shifts", updates, filters={"id": f"eq.{shift_id}"})
    return {"shift_id": shift_id, "updated": updates}


@router.delete("/shifts/{shift_id}")
async def delete_shift(shift_id: str, principal=Depends(require_service_auth)):
    _validate_uuid(shift_id, "shift_id")
    await _enforce_row_member(principal, "schedule_shifts", shift_id)
    db = get_db()
    await db.delete("schedule_shifts", filters={"id": f"eq.{shift_id}"})
    return {"shift_id": shift_id, "deleted": True}


# ─── Publish Endpoint ─────────────────────────────────────────

# Day index → label for SMS bodies. Matches frontend's 0=Mon..6=Sun.
_DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _format_shift_time(t: str) -> str:
    """Postgres time -> "7:00 AM"."""
    try:
        hh, mm = t.split(":")[:2]
        h = int(hh)
        suffix = "AM" if h < 12 else "PM"
        h12 = h % 12 or 12
        return f"{h12}:{mm} {suffix}"
    except Exception:
        return t


def _render_shift_sms(business_name: str, week_start: str, shifts: list[dict]) -> str:
    if not shifts:
        return (
            f"{business_name or 'Your team'}: No shifts assigned for the week of "
            f"{week_start}. Enjoy the time off!"
        )
    by_day: dict[int, list[dict]] = {}
    for s in shifts:
        by_day.setdefault(int(s.get("day_of_week", 0)), []).append(s)
    lines = [f"{business_name or 'Your team'} — Schedule for week of {week_start}:"]
    for day in sorted(by_day.keys()):
        for s in sorted(by_day[day], key=lambda x: str(x.get("start_time", ""))):
            start = _format_shift_time(str(s.get("start_time", "")))
            end = _format_shift_time(str(s.get("end_time", "")))
            role = s.get("role") or ""
            role_str = f" ({role})" if role and role != "any" else ""
            lines.append(f"{_DAY_LABELS[day]} {start}-{end}{role_str}")
    lines.append("Reply STOP to opt out.")
    return "\n".join(lines)


async def _send_twilio_sms(
    client: httpx.AsyncClient, account_sid: str, auth_token: str,
    from_number: str, to_number: str, body: str,
) -> bool:
    try:
        res = await client.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json",
            data={"To": to_number, "From": from_number, "Body": body},
            auth=(account_sid, auth_token),
            timeout=10,
        )
        if res.status_code in (200, 201):
            return True
        logger.warning("Twilio SMS %d for %s: %s", res.status_code, to_number, res.text[:200])
    except Exception as e:
        logger.warning("Twilio SMS send to %s failed: %s", to_number, e)
    return False


async def _notify_published_staff(
    merchant_id: str, week_start: str, published_by: str,
) -> int:
    """Send each staff member their week's shifts. Returns count successfully sent."""
    sid = os.environ.get("TWILIO_ACCOUNT_SID", "")
    token = os.environ.get("TWILIO_AUTH_TOKEN", "")
    from_number = os.environ.get("TWILIO_PHONE_NUMBER", "")
    if not (sid and token and from_number):
        logger.info("publish notify: Twilio not configured — skipping SMS")
        return 0

    db = get_db()
    staff_rows = await db.select(
        "schedule_staff",
        filters={"merchant_id": f"eq.{merchant_id}", "active": "eq.true"},
    )
    staff_with_phone = [s for s in staff_rows if s.get("phone")]
    if not staff_with_phone:
        return 0

    shift_rows = await db.select(
        "schedule_shifts",
        filters={
            "merchant_id": f"eq.{merchant_id}",
            "week_start_date": f"eq.{week_start}",
            "status": "eq.published",
        },
    )
    by_staff: dict[str, list[dict]] = {}
    for sh in shift_rows:
        sm = sh.get("staff_member_id")
        if sm:
            by_staff.setdefault(sm, []).append(sh)

    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(*[
            _send_twilio_sms(
                client, sid, token, from_number,
                str(member["phone"]),
                _render_shift_sms(published_by, week_start, by_staff.get(member["id"], [])),
            )
            for member in staff_with_phone
        ])
    return sum(1 for ok in results if ok)


@router.post("/publish")
async def publish_schedule(body: PublishRequest, principal=Depends(require_service_auth)):
    await enforce_service_member(principal, body.merchant_id)
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

    notified_count = 0
    if body.notify_staff:
        try:
            notified_count = await _notify_published_staff(
                body.merchant_id, body.week_start_date, body.published_by,
            )
        except Exception as e:
            # Never fail the publish because a notification went sideways.
            logger.warning("publish notify failed: %s", e)

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


# ─── Holiday Helpers ──────────────────────────────────────────


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """Return the n-th occurrence of *weekday* (0=Mon) in *month*."""
    first = date(year, month, 1)
    # Days until the first occurrence of the target weekday
    offset = (weekday - first.weekday()) % 7
    d = first + timedelta(days=offset + 7 * (n - 1))
    return d


def _last_weekday(year: int, month: int, weekday: int) -> date:
    """Return the last occurrence of *weekday* (0=Mon) in *month*."""
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)
    offset = (last_day.weekday() - weekday) % 7
    return last_day - timedelta(days=offset)


def _easter(year: int) -> date:
    """Compute Easter Sunday via the Anonymous Gregorian algorithm."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7  # noqa: E741
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return date(year, month, day + 1)


def _compute_holidays(year: int, country: str) -> list[dict]:
    """Return federal holidays as ``[{"date": "YYYY-MM-DD", "name": ...}]``."""
    holidays: list[dict] = []

    if country.upper() == "CA":
        # Victoria Day: last Monday on or before May 24
        may24 = date(year, 5, 24)
        victoria_day = may24 - timedelta(days=(may24.weekday() - 0) % 7)

        holidays = [
            {"date": date(year, 1, 1).isoformat(), "name": "New Year's Day"},
            {"date": (_easter(year) - timedelta(days=2)).isoformat(),
             "name": "Good Friday"},
            {"date": victoria_day.isoformat(), "name": "Victoria Day"},
            {"date": date(year, 7, 1).isoformat(), "name": "Canada Day"},
            {"date": _nth_weekday(year, 9, 0, 1).isoformat(),
             "name": "Labour Day"},
            {"date": date(year, 9, 30).isoformat(),
             "name": "National Day for Truth and Reconciliation"},
            {"date": _nth_weekday(year, 10, 0, 2).isoformat(),
             "name": "Thanksgiving"},
            {"date": date(year, 11, 11).isoformat(),
             "name": "Remembrance Day"},
            {"date": date(year, 12, 25).isoformat(), "name": "Christmas Day"},
            {"date": date(year, 12, 26).isoformat(), "name": "Boxing Day"},
        ]
    else:
        holidays = [
            {"date": date(year, 1, 1).isoformat(),
             "name": "New Year's Day"},
            {"date": _nth_weekday(year, 1, 0, 3).isoformat(),
             "name": "Martin Luther King Jr. Day"},
            {"date": _nth_weekday(year, 2, 0, 3).isoformat(),
             "name": "Presidents' Day"},
            {"date": _last_weekday(year, 5, 0).isoformat(),
             "name": "Memorial Day"},
            {"date": date(year, 6, 19).isoformat(), "name": "Juneteenth"},
            {"date": date(year, 7, 4).isoformat(),
             "name": "Independence Day"},
            {"date": _nth_weekday(year, 9, 0, 1).isoformat(),
             "name": "Labor Day"},
            {"date": _nth_weekday(year, 10, 0, 2).isoformat(),
             "name": "Columbus Day"},
            {"date": date(year, 11, 11).isoformat(),
             "name": "Veterans Day"},
            {"date": _nth_weekday(year, 11, 3, 4).isoformat(),
             "name": "Thanksgiving"},
            {"date": date(year, 12, 25).isoformat(),
             "name": "Christmas Day"},
        ]

    holidays.sort(key=lambda h: h["date"])
    return holidays


# ─── Holidays Endpoint ────────────────────────────────────────


@router.get("/holidays")
async def get_holidays(
    _auth=Depends(require_service_auth),
    country: str = Query(default="US", description="US or CA"),
    week_start: str = Query(default="", description="Week start date YYYY-MM-DD"),
):
    year = datetime.now(timezone.utc).year
    if week_start:
        try:
            ws = date.fromisoformat(week_start)
        except ValueError:
            raise HTTPException(400, "Invalid week_start format, expected YYYY-MM-DD")
        year = ws.year
        we = ws + timedelta(days=6)
        all_holidays = _compute_holidays(year, country)
        # If the week spans a year boundary, also grab the next year
        if we.year != year:
            all_holidays += _compute_holidays(we.year, country)
        filtered = [
            h for h in all_holidays
            if ws.isoformat() <= h["date"] <= we.isoformat()
        ]
        return {"holidays": filtered, "country": country, "week_start": week_start}

    holidays = _compute_holidays(year, country)
    return {"holidays": holidays, "country": country, "week_start": week_start}


# ─── Peak Hours (transaction heatmap) ─────────────────────────


async def _fetch_peak_hours(merchant_id: str, weeks_back: int) -> list[dict]:
    db = get_db()
    rows = await db.rpc(
        "schedule_peak_hours",
        {"p_merchant_id": merchant_id, "p_weeks_back": weeks_back},
    )
    if not rows:
        return []
    return [
        {
            "day": int(r["day_of_week"]),
            "hour": int(r["hour"]),
            "intensity": float(r["intensity"]),
            "txn_count": int(r.get("txn_count") or 0),
            "revenue_cents": int(r.get("revenue_cents") or 0),
        }
        for r in rows
    ]


@router.get("/peak-hours/{merchant_id}")
async def get_peak_hours(
    merchant_id: str,
    principal=Depends(require_service_auth),
    weeks: int = Query(8, ge=1, le=26),
):
    """(day_of_week, hour) intensity heatmap derived from real transactions."""
    await enforce_service_member(principal, merchant_id)
    _validate_uuid(merchant_id, "merchant_id")
    peaks = await _fetch_peak_hours(merchant_id, weeks)
    return {
        "merchant_id": merchant_id,
        "weeks": weeks,
        "peaks": peaks,
    }


# ─── Projected Revenue (for labor % KPI) ──────────────────────


@router.get("/projected-revenue/{merchant_id}")
async def get_projected_revenue(
    merchant_id: str,
    principal=Depends(require_service_auth),
    weeks: int = Query(8, ge=1, le=26),
):
    """Trailing-average weekly revenue from POS transactions.

    Used by the schedule UI to compute labor cost percentage:
        labor_pct = scheduled_labor_cents / projected_weekly_cents * 100
    """
    await enforce_service_member(principal, merchant_id)
    _validate_uuid(merchant_id, "merchant_id")
    db = get_db()
    result = await db.rpc(
        "schedule_projected_weekly_revenue",
        {"p_merchant_id": merchant_id, "p_weeks_back": weeks},
    )
    projected = 0
    if isinstance(result, list) and result:
        projected = int(result[0]) if result[0] is not None else 0
    elif isinstance(result, (int, float)):
        projected = int(result)
    return {
        "merchant_id": merchant_id,
        "projected_weekly_cents": projected,
        "weeks_analyzed": weeks,
    }


# ─── AI Recommendation Endpoint ───────────────────────────────


def _required_coverage(intensity: float) -> int:
    """How many staff this hour should be covered by, given intensity 0..1."""
    if intensity >= 0.75:
        return 3
    if intensity >= 0.5:
        return 2
    if intensity >= 0.25:
        return 1
    return 0


def _merge_contiguous(hours: list[int], min_run: int = 2) -> list[tuple[int, int]]:
    """Group sorted ints into [(start_inclusive, end_exclusive)] runs of >= min_run."""
    if not hours:
        return []
    runs: list[tuple[int, int]] = []
    start = hours[0]
    prev = hours[0]
    for h in hours[1:]:
        if h == prev + 1:
            prev = h
            continue
        if prev - start + 1 >= min_run:
            runs.append((start, prev + 1))
        start = prev = h
    if prev - start + 1 >= min_run:
        runs.append((start, prev + 1))
    return runs


def _build_coverage(existing: list[dict]) -> dict[tuple[int, int], int]:
    """Map (day_of_week, hour) -> number of staff already scheduled."""

    def _hours_in_shift(s: dict) -> list[int]:
        try:
            sh = int(str(s["start_time"]).split(":")[0])
            eh = int(str(s["end_time"]).split(":")[0])
        except (KeyError, ValueError):
            return []
        return list(range(sh, eh))

    coverage: dict[tuple[int, int], int] = {}
    for sh in existing:
        try:
            day = int(sh["day_of_week"])
        except (KeyError, ValueError, TypeError):
            continue
        for h in _hours_in_shift(sh):
            coverage[(day, h)] = coverage.get((day, h), 0) + 1
    return coverage


async def _gather_holidays_by_dow(country: str, week_start: str) -> dict[int, str]:
    """day_of_week -> holiday name for holidays falling inside the planning week."""
    if not week_start:
        return {}
    try:
        ws = date.fromisoformat(week_start)
    except ValueError:
        return {}
    we = ws + timedelta(days=6)
    holidays = _compute_holidays(ws.year, country)
    if we.year != ws.year:
        holidays += _compute_holidays(we.year, country)
    out: dict[int, str] = {}
    for h in holidays:
        try:
            d = date.fromisoformat(h["date"])
        except ValueError:
            continue
        if ws <= d <= we:
            out[d.weekday()] = h["name"]
    return out


async def _gather_weather_by_dow(
    lat: float | None, lon: float | None, week_start: str,
) -> tuple[dict, float | None]:
    """Best-effort forecast keyed by day_of_week + the merchant's rain impact.

    Returns ``({}, None)`` on any failure — weather is an optional signal and
    must never break recommendations.
    """
    from ...services.weather_service import WeatherService, WMO_WEATHER_CODES
    from ...ai.scheduling.staffing_recommender import WeatherDay

    if not week_start:
        return {}, None
    try:
        ws = date.fromisoformat(week_start)
    except ValueError:
        return {}, None

    try:
        svc = WeatherService(lat=lat, lon=lon) if lat is not None and lon is not None else WeatherService()
        forecast = await svc.fetch_forecast(lat=lat, lon=lon, days=16)
    except Exception as e:  # pragma: no cover - network best-effort
        logger.warning("weather forecast unavailable: %s", e)
        return {}, None

    we = ws + timedelta(days=6)
    by_dow: dict[int, WeatherDay] = {}
    for day in forecast:
        try:
            d = date.fromisoformat(day["date"])
        except (KeyError, ValueError):
            continue
        if not (ws <= d <= we):
            continue
        code = int(day.get("weathercode") or 0)
        by_dow[d.weekday()] = WeatherDay(
            weathercode=code,
            precipitation=float(day.get("precipitation") or 0.0),
            label=WMO_WEATHER_CODES.get(code, ""),
        )
    return by_dow, None


@router.post("/recommend/{merchant_id}")
async def recommend_shifts(
    merchant_id: str,
    principal=Depends(require_service_auth),
    week_start: str = Query(default="", description="Week start date YYYY-MM-DD"),
    weeks_back: int = Query(8, ge=1, le=26),
    country: str = Query(default="US", description="US or CA — CA enables weather + holiday agent"),
    lat: Optional[float] = Query(default=None, description="Merchant latitude for weather"),
    lon: Optional[float] = Query(default=None, description="Merchant longitude for weather"),
):
    """Recommend shifts to add by comparing peak hours from POS history to
    the currently-scheduled shifts for the given week.

    For ``country=CA`` the agentic engine additionally folds in holidays and
    a best-effort weather forecast. The US path is unchanged: peaks only.
    """
    await enforce_service_member(principal, merchant_id)
    _validate_uuid(merchant_id, "merchant_id")
    peaks = await _fetch_peak_hours(merchant_id, weeks_back)

    is_ca = country.upper() == "CA"
    if not peaks and not is_ca:
        return {
            "recommendations": [],
            "merchant_id": merchant_id,
            "reason": "no_transaction_history",
        }

    db = get_db()
    shift_filters: dict = {"merchant_id": f"eq.{merchant_id}"}
    if week_start:
        shift_filters["week_start_date"] = f"eq.{week_start}"
    existing = await db.select("schedule_shifts", filters=shift_filters)
    coverage = _build_coverage(existing)

    # ── CA: agentic engine (peaks + holidays + weather) ────────────
    if is_ca:
        from ...ai.scheduling.staffing_recommender import build_recommendations

        holidays_by_dow = await _gather_holidays_by_dow(country, week_start)
        # No per-merchant coords yet — default CA to Toronto so the forecast is
        # at least Canadian rather than the Miami service default.
        w_lat = lat if lat is not None else 43.6532
        w_lon = lon if lon is not None else -79.3832
        weather_by_dow, rain_impact_pct = await _gather_weather_by_dow(w_lat, w_lon, week_start)
        result = build_recommendations(
            peaks=peaks,
            coverage=coverage,
            holidays_by_dow=holidays_by_dow,
            weather_by_dow=weather_by_dow,
            rain_impact_pct=rain_impact_pct,
        )
        if not result["recommendations"] and not peaks and not holidays_by_dow:
            return {
                "recommendations": [],
                "signals": [],
                "merchant_id": merchant_id,
                "reason": "no_transaction_history",
            }
        return {
            "recommendations": result["recommendations"],
            "signals": result["signals"],
            "merchant_id": merchant_id,
            "weeks_analyzed": weeks_back,
        }

    # ── US: peaks-only (unchanged) ─────────────────────────────────
    # Identify uncovered peak hours, grouped by day.
    by_day: dict[int, list[tuple[int, float]]] = {}
    for p in peaks:
        need = _required_coverage(p["intensity"])
        if need <= 0:
            continue
        gap = need - coverage.get((p["day"], p["hour"]), 0)
        if gap <= 0:
            continue
        by_day.setdefault(p["day"], []).append((p["hour"], p["intensity"]))

    recommendations: list[dict] = []
    for day, hours_data in by_day.items():
        hours_data.sort(key=lambda x: x[0])
        hours_only = [h for h, _ in hours_data]
        intensities = {h: i for h, i in hours_data}
        for start, end in _merge_contiguous(hours_only, min_run=2):
            window_intensities = [intensities[h] for h in range(start, end) if h in intensities]
            peak_intensity = max(window_intensities) if window_intensities else 0
            if peak_intensity >= 0.75:
                priority = "critical"
                reason = f"Peak demand window — {int(peak_intensity * 100)}% intensity"
            elif peak_intensity >= 0.5:
                priority = "recommended"
                reason = f"High demand window — {int(peak_intensity * 100)}% intensity"
            else:
                priority = "optional"
                reason = f"Moderate demand window — {int(peak_intensity * 100)}% intensity"
            recommendations.append({
                "id": str(uuid4()),
                "day_of_week": day,
                "start_time": f"{start:02d}:00",
                "end_time": f"{end:02d}:00",
                "role": "any",
                "reason": reason,
                "priority": priority,
                "peak_intensity": round(peak_intensity, 3),
            })

    # Sort: critical first, then by day/start
    priority_rank = {"critical": 0, "recommended": 1, "optional": 2}
    recommendations.sort(key=lambda r: (priority_rank.get(r["priority"], 9), r["day_of_week"], r["start_time"]))
    return {
        "recommendations": recommendations,
        "merchant_id": merchant_id,
        "weeks_analyzed": weeks_back,
    }
