"""Bookings API — the merchant's side of reservations and appointments.

Everything the portal needs to set booking up (resources, services, hours,
closures, pacing) and to run a service (today's book, walk-ins, cancellations,
reassignment).

Auth is the house pattern: require_service_auth authenticates, and
enforce_service_member authorizes against the owning merchant. Sub-resources
keyed by their own uuid resolve their merchant from the row first, because a
booking id in a URL is otherwise a straight BOLA — booking rows carry customer
names and phone numbers.

merchant_id is TEXT here, matching phone_agent_config.merchant_id (live values
mix 'maple-tandoor-demo', 'biz_<hex>' and bare uuids), so this router does NOT
use schedule.py's _validate_uuid on it.
"""
from __future__ import annotations

import logging
import os
import re
from datetime import date as date_cls
from datetime import datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from src.services import booking_engine as be
from src.services.booking_store import (
    BookingStoreError,
    SlotTaken,
    get_booking_store,
)

from ...db import get_db
from ..auth import enforce_service_member, require_service_auth

logger = logging.getLogger("meridian.api.bookings")
router = APIRouter(prefix="/api/bookings", tags=["bookings"])

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I
)
_MERCHANT_ID_RE = re.compile(r"^[A-Za-z0-9_\-]{1,64}$")

_RESOURCE_KINDS = ("table", "staff", "chair", "bay", "room")


def _validate_uuid(value: str, label: str = "id") -> None:
    if not _UUID_RE.match(value or ""):
        raise HTTPException(400, f"Invalid {label} format")


def _validate_merchant(value: str) -> None:
    if not _MERCHANT_ID_RE.match(value or ""):
        raise HTTPException(400, "Invalid merchant_id format")


async def _enforce_row_member(principal, table: str, row_id: str) -> dict | None:
    """Resolve a row's owning merchant and authorize against it."""
    db = get_db()
    rows = await db.select(table, filters={"id": f"eq.{row_id}"}, limit=1)
    if rows and rows[0].get("merchant_id"):
        await enforce_service_member(principal, rows[0]["merchant_id"])
        return rows[0]
    return None


async def _setup_for(merchant_id: str) -> be.MerchantBookingSetup:
    """Load the merchant's booking configuration, timezone included."""
    db = get_db()
    rows = await db.select(
        "phone_agent_config",
        columns="business_timezone,booking_noun,booking_mode",
        filters={"merchant_id": f"eq.{merchant_id}"},
        limit=1,
    )
    cfg = rows[0] if rows else {}
    return await be.load_setup(
        merchant_id,
        cfg.get("business_timezone") or "",
        noun=cfg.get("booking_noun") or "reservation",
        mode=cfg.get("booking_mode") or "native",
    )


# ─── Models ───────────────────────────────────────────────────

class ResourceCreate(BaseModel):
    merchant_id: str
    name: str = Field(min_length=1, max_length=120)
    kind: str = "table"
    seats: int = Field(default=1, ge=1, le=100)
    sort_order: int = 0

    @field_validator("kind")
    @classmethod
    def _kind(cls, v: str) -> str:
        if v not in _RESOURCE_KINDS:
            raise ValueError(f"kind must be one of {_RESOURCE_KINDS}")
        return v


class ResourceUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    seats: int | None = Field(default=None, ge=1, le=100)
    sort_order: int | None = None
    active: bool | None = None


class ServiceCreate(BaseModel):
    merchant_id: str
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    duration_minutes: int = Field(ge=5, le=1440)
    buffer_minutes: int = Field(default=0, ge=0, le=240)
    price_cents: int | None = Field(default=None, ge=0)
    resource_kind: str | None = None
    min_party: int = Field(default=1, ge=1, le=100)
    max_party: int = Field(default=1, ge=1, le=100)
    sort_order: int = 0

    @field_validator("resource_kind")
    @classmethod
    def _kind(cls, v: str | None) -> str | None:
        if v is not None and v not in _RESOURCE_KINDS:
            raise ValueError(f"resource_kind must be one of {_RESOURCE_KINDS}")
        return v


class ServiceUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    duration_minutes: int | None = Field(default=None, ge=5, le=1440)
    buffer_minutes: int | None = Field(default=None, ge=0, le=240)
    price_cents: int | None = Field(default=None, ge=0)
    min_party: int | None = Field(default=None, ge=1, le=100)
    max_party: int | None = Field(default=None, ge=1, le=100)
    active: bool | None = None


class HoursRow(BaseModel):
    weekday: int = Field(ge=0, le=6)
    opens_at: str
    closes_at: str
    slot_minutes: int = Field(default=15, ge=5, le=240)


class HoursReplace(BaseModel):
    merchant_id: str
    rows: list[HoursRow]


class ClosureCreate(BaseModel):
    merchant_id: str
    starts_at: datetime
    ends_at: datetime
    reason: str | None = Field(default=None, max_length=200)
    resource_id: str | None = None


class BookingCreate(BaseModel):
    """A booking typed in by staff — a walk-in, or a call they took themselves."""
    merchant_id: str
    starts_at: datetime
    party_size: int = Field(default=1, ge=1, le=100)
    customer_name: str = Field(min_length=1, max_length=200)
    customer_phone: str | None = None
    customer_email: str | None = None
    notes: str | None = Field(default=None, max_length=1000)
    service_id: str | None = None
    source: str = "portal"


class BookingUpdate(BaseModel):
    status: str | None = None
    starts_at: datetime | None = None
    resource_id: str | None = None
    party_size: int | None = Field(default=None, ge=1, le=100)
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("status")
    @classmethod
    def _status(cls, v: str | None) -> str | None:
        allowed = ("confirmed", "seated", "completed", "cancelled", "no_show")
        if v is not None and v not in allowed:
            raise ValueError(f"status must be one of {allowed}")
        return v


# ─── Resources ────────────────────────────────────────────────

@router.get("/resources/{merchant_id}")
async def list_resources(merchant_id: str, include_inactive: bool = False,
                         principal=Depends(require_service_auth)):
    _validate_merchant(merchant_id)
    await enforce_service_member(principal, merchant_id)
    rows = await get_booking_store().list_resources(
        merchant_id, active_only=not include_inactive)
    return {"resources": rows, "total": len(rows)}


@router.post("/resources")
async def create_resource(body: ResourceCreate,
                          principal=Depends(require_service_auth)):
    _validate_merchant(body.merchant_id)
    await enforce_service_member(principal, body.merchant_id)
    row = await get_booking_store().create_resource(body.model_dump())
    return {"resource": row}


@router.patch("/resources/{resource_id}")
async def update_resource(resource_id: str, body: ResourceUpdate,
                          principal=Depends(require_service_auth)):
    _validate_uuid(resource_id, "resource_id")
    await _enforce_row_member(principal, "booking_resources", resource_id)
    fields = body.model_dump(exclude_none=True)
    if not fields:
        raise HTTPException(400, "nothing to update")
    row = await get_booking_store().update_resource(resource_id, fields)
    return {"resource": row}


# ─── Services ─────────────────────────────────────────────────

@router.get("/services/{merchant_id}")
async def list_services(merchant_id: str, include_inactive: bool = False,
                        principal=Depends(require_service_auth)):
    _validate_merchant(merchant_id)
    await enforce_service_member(principal, merchant_id)
    rows = await get_booking_store().list_services(
        merchant_id, active_only=not include_inactive)
    return {"services": rows, "total": len(rows)}


@router.post("/services")
async def create_service(body: ServiceCreate,
                         principal=Depends(require_service_auth)):
    _validate_merchant(body.merchant_id)
    await enforce_service_member(principal, body.merchant_id)
    if body.max_party < body.min_party:
        raise HTTPException(400, "max_party must be at least min_party")
    row = await get_booking_store().create_service(body.model_dump())
    return {"service": row}


@router.patch("/services/{service_id}")
async def update_service(service_id: str, body: ServiceUpdate,
                         principal=Depends(require_service_auth)):
    _validate_uuid(service_id, "service_id")
    await _enforce_row_member(principal, "booking_services", service_id)
    fields = body.model_dump(exclude_none=True)
    if not fields:
        raise HTTPException(400, "nothing to update")
    row = await get_booking_store().update_service(service_id, fields)
    return {"service": row}


# ─── Hours, closures, pacing ──────────────────────────────────

@router.get("/hours/{merchant_id}")
async def list_hours(merchant_id: str, principal=Depends(require_service_auth)):
    _validate_merchant(merchant_id)
    await enforce_service_member(principal, merchant_id)
    return {"hours": await get_booking_store().list_hours(merchant_id)}


@router.put("/hours")
async def replace_hours(body: HoursReplace,
                        principal=Depends(require_service_auth)):
    """Hours are saved as a whole week — the portal edits them as one grid."""
    _validate_merchant(body.merchant_id)
    await enforce_service_member(principal, body.merchant_id)
    rows = []
    for row in body.rows:
        opens = _parse_hhmm(row.opens_at)
        closes = _parse_hhmm(row.closes_at)
        if closes <= opens:
            raise HTTPException(
                400,
                "closing time must be after opening time — for service past "
                "midnight, add a second row on the following day",
            )
        rows.append({
            "merchant_id": body.merchant_id,
            "weekday": row.weekday,
            "opens_at": row.opens_at,
            "closes_at": row.closes_at,
            "slot_minutes": row.slot_minutes,
            "active": True,
        })
    saved = await get_booking_store().replace_hours(body.merchant_id, rows)
    return {"hours": saved, "total": len(saved)}


def _parse_hhmm(value: str) -> time:
    try:
        parts = [int(p) for p in str(value).split(":")[:2]]
        return time(parts[0], parts[1] if len(parts) > 1 else 0)
    except (ValueError, IndexError):
        raise HTTPException(400, f"invalid time {value!r} — use HH:MM")


@router.get("/closures/{merchant_id}")
async def list_closures(merchant_id: str,
                        start: datetime = Query(...), end: datetime = Query(...),
                        principal=Depends(require_service_auth)):
    _validate_merchant(merchant_id)
    await enforce_service_member(principal, merchant_id)
    rows = await get_booking_store().list_closures(
        merchant_id, start.isoformat(), end.isoformat())
    return {"closures": rows}


@router.post("/closures")
async def create_closure(body: ClosureCreate,
                         principal=Depends(require_service_auth)):
    _validate_merchant(body.merchant_id)
    await enforce_service_member(principal, body.merchant_id)
    if body.ends_at <= body.starts_at:
        raise HTTPException(400, "ends_at must be after starts_at")
    row = await get_booking_store().create_closure({
        "merchant_id": body.merchant_id,
        "resource_id": body.resource_id,
        "starts_at": body.starts_at.isoformat(),
        "ends_at": body.ends_at.isoformat(),
        "reason": body.reason,
    })
    return {"closure": row}


@router.delete("/closures/{closure_id}")
async def delete_closure(closure_id: str,
                         principal=Depends(require_service_auth)):
    _validate_uuid(closure_id, "closure_id")
    await _enforce_row_member(principal, "booking_closures", closure_id)
    await get_booking_store().delete_closure(closure_id)
    return {"deleted": True}


# ─── Availability ─────────────────────────────────────────────

@router.get("/availability/{merchant_id}")
async def availability(merchant_id: str,
                       day: date_cls = Query(..., description="Local date, YYYY-MM-DD"),
                       party_size: int = Query(1, ge=1, le=100),
                       service_id: str | None = None,
                       principal=Depends(require_service_auth)):
    """Open times on a local date. A snapshot — only a write reserves."""
    _validate_merchant(merchant_id)
    await enforce_service_member(principal, merchant_id)
    setup = await _setup_for(merchant_id)
    slots = await be.find_slots(setup, day, party_size, service_id)
    return {
        "timezone": setup.tz_name,
        "day": day.isoformat(),
        "slots": [
            {
                "starts_at": s.starts_at.isoformat(),
                "ends_at": s.ends_at.isoformat(),
                "local_label": s.local_label,
                "resource_id": s.resource_id,
                "resource_name": s.resource_name,
                "duration_minutes": s.duration_minutes,
            }
            for s in slots
        ],
    }


# ─── Bookings ─────────────────────────────────────────────────

@router.get("/list/{merchant_id}")
async def list_bookings(merchant_id: str,
                        start: datetime = Query(...), end: datetime = Query(...),
                        include_cancelled: bool = False,
                        principal=Depends(require_service_auth)):
    _validate_merchant(merchant_id)
    await enforce_service_member(principal, merchant_id)
    rows = await get_booking_store().list_bookings(
        merchant_id, start.isoformat(), end.isoformat(),
        live_only=not include_cancelled)
    return {"bookings": rows, "total": len(rows)}


@router.post("/create")
async def create_booking(body: BookingCreate,
                         principal=Depends(require_service_auth)):
    """Take a booking from the portal. Goes through the same engine the phone
    agent uses, so a walk-in typed in at the host stand cannot double-book a
    table the agent is about to offer."""
    _validate_merchant(body.merchant_id)
    await enforce_service_member(principal, body.merchant_id)
    setup = await _setup_for(body.merchant_id)
    starts_at = body.starts_at
    if starts_at.tzinfo is None:
        starts_at = starts_at.replace(tzinfo=timezone.utc)
    try:
        row = await be.reserve(
            setup, starts_at.astimezone(timezone.utc), body.party_size,
            body.customer_name,
            customer_phone=body.customer_phone,
            customer_email=body.customer_email,
            notes=body.notes,
            service_id=body.service_id,
            source=body.source if body.source in ("portal", "walk_in", "web") else "portal",
        )
    except be.BookingClosed:
        raise HTTPException(409, "closed at that time")
    except be.NoAvailability:
        raise HTTPException(409, "no resource free at that time")
    except BookingStoreError as e:
        logger.error("portal booking failed: %s", e)
        raise HTTPException(502, "could not save the booking")

    # Mirror it into the merchant's own calendar, exactly as a phone booking
    # is. A walk-in typed at the host stand that never reaches their Square
    # calendar means the owner has to check two places all evening.
    from src.services.booking_agent import _spawn_push
    _spawn_push(body.merchant_id, row)
    return {"booking": row}


@router.patch("/{booking_id}")
async def update_booking(booking_id: str, body: BookingUpdate,
                         principal=Depends(require_service_auth)):
    """Change a booking — seat it, mark a no-show, move it, reassign a table.

    A time or resource change re-enters the exclusion constraint exactly as a
    new booking does, so a 409 here means the target is genuinely taken.
    """
    _validate_uuid(booking_id, "booking_id")
    await _enforce_row_member(principal, "bookings", booking_id)
    fields = body.model_dump(exclude_none=True)
    if not fields:
        raise HTTPException(400, "nothing to update")

    if body.resource_id is not None:
        _validate_uuid(body.resource_id, "resource_id")

    store = get_booking_store()

    # Undo. Bringing a booking back from cancelled/no_show has to put it back
    # on the merchant's calendar as well, because marking it took it off — and
    # a mis-tapped no-show that leaves the guest missing from Square is worse
    # than no undo at all. Only a REVIVAL re-pushes: seated -> confirmed never
    # left their calendar, and pushing again would duplicate the booking.
    revived = False
    if body.status == "confirmed":
        before = await store.get_booking(booking_id)
        revived = bool(before and before.get("status") in ("cancelled", "no_show"))

    if body.starts_at is not None:
        # Moving a booking must move its END too, or the row would keep the
        # old duration and quietly overlap the next one.
        current = await store.get_booking(booking_id)
        if not current:
            raise HTTPException(404, "booking not found")
        duration = int(current.get("duration_minutes") or 60)
        old_start = be._parse_ts(current.get("starts_at"))
        old_end = be._parse_ts(current.get("ends_at"))
        hold = int((old_end - old_start).total_seconds() // 60) if old_start and old_end else duration
        new_start = body.starts_at
        if new_start.tzinfo is None:
            new_start = new_start.replace(tzinfo=timezone.utc)
        new_start = new_start.astimezone(timezone.utc)
        fields["starts_at"] = new_start.isoformat()
        fields["ends_at"] = (new_start + timedelta(minutes=hold)).isoformat()

    if body.status == "cancelled":
        fields["cancelled_at"] = datetime.now(timezone.utc).isoformat()

    try:
        row = await store.update_booking(booking_id, fields)
    except SlotTaken:
        raise HTTPException(409, "that time is already taken on this resource")

    if revived:
        from src.services.booking_agent import _spawn_push
        _spawn_push(row.get("merchant_id") or "", row)

    if body.status in ("cancelled", "no_show"):
        merchant_id = row.get("merchant_id") or ""
        # A booking that stops occupying the table has to stop occupying it in
        # the merchant's calendar too, or their staff keep holding it.
        from src.services.booking_agent import _spawn_recovery, _spawn_withdraw
        _spawn_withdraw(merchant_id, row)
        # And the freed slot goes to the waiting list, exactly as it does when
        # a caller cancels by phone. A no-show marked at 7:10pm frees a table
        # that somebody wants RIGHT NOW — that is the moment the waitlist is
        # worth the most, and leaving it to the phone path meant a table freed
        # at the host stand quietly recovered nothing.
        _spawn_recovery(merchant_id, row)

    return {"booking": row}


# ─── Waitlist / cancellation recovery ─────────────────────────

class WaitlistCreate(BaseModel):
    merchant_id: str
    customer_name: str = Field(min_length=1, max_length=200)
    customer_phone: str = Field(min_length=5, max_length=32)
    party_size: int = Field(default=1, ge=1, le=100)
    window_start: datetime
    window_end: datetime
    min_notice_minutes: int = Field(default=60, ge=0, le=10080)
    notes: str | None = Field(default=None, max_length=1000)
    service_id: str | None = None


@router.get("/waitlist/{merchant_id}")
async def list_waitlist(merchant_id: str, status: str = "waiting",
                        principal=Depends(require_service_auth)):
    _validate_merchant(merchant_id)
    await enforce_service_member(principal, merchant_id)
    if status not in ("waiting", "offered", "booked", "declined",
                      "expired", "cancelled", ""):
        raise HTTPException(400, "unknown status")
    rows = await get_booking_store().list_waitlist(merchant_id, status=status)
    return {"waitlist": rows, "total": len(rows)}


@router.post("/waitlist")
async def add_to_waitlist(body: WaitlistCreate,
                          principal=Depends(require_service_auth)):
    _validate_merchant(body.merchant_id)
    await enforce_service_member(principal, body.merchant_id)
    if body.window_end <= body.window_start:
        raise HTTPException(400, "window_end must be after window_start")
    row = await get_booking_store().create_waitlist_entry({
        "merchant_id": body.merchant_id,
        "customer_name": body.customer_name,
        "customer_phone": body.customer_phone,
        "party_size": body.party_size,
        "window_start": body.window_start.isoformat(),
        "window_end": body.window_end.isoformat(),
        "min_notice_minutes": body.min_notice_minutes,
        "notes": body.notes,
        "service_id": body.service_id,
        "status": "waiting",
        "source": "portal",
    })
    return {"entry": row}


@router.delete("/waitlist/{entry_id}")
async def remove_from_waitlist(entry_id: str,
                               principal=Depends(require_service_auth)):
    _validate_uuid(entry_id, "entry_id")
    await _enforce_row_member(principal, "booking_waitlist", entry_id)
    row = await get_booking_store().update_waitlist(entry_id, {"status": "cancelled"})
    return {"entry": row}


@router.post("/waitlist/{merchant_id}/recover/{booking_id}")
async def recover_now(merchant_id: str, booking_id: str,
                      principal=Depends(require_service_auth)):
    """Offer a freed slot to the waitlist by hand.

    The automatic path fires on cancellation; this exists for the case a host
    actually has — a no-show at 7:20 that frees the table for the rest of the
    evening, which no cancellation event ever announced.
    """
    from src.services.booking_waitlist import recover_slot

    _validate_merchant(merchant_id)
    _validate_uuid(booking_id, "booking_id")
    await enforce_service_member(principal, merchant_id)

    booking = await get_booking_store().get_booking(booking_id)
    if not booking or booking.get("merchant_id") != merchant_id:
        raise HTTPException(404, "booking not found")
    return await recover_slot(merchant_id, booking)


# ─── Integrations ─────────────────────────────────────────────

@router.get("/integrations/{merchant_id}")
async def list_integrations(merchant_id: str,
                            principal=Depends(require_service_auth)):
    """What this merchant is connected to, what they could connect, and the
    truth about the tools we cannot reach."""
    from src.services.booking_providers.registry import (
        available_providers,
        unavailable_tools,
    )
    _validate_merchant(merchant_id)
    await enforce_service_member(principal, merchant_id)
    connections = await get_booking_store().list_connections(merchant_id)
    # Never let an encrypted credential leave the server, even to an
    # authorized merchant — nothing in the portal needs it.
    safe = [
        {k: v for k, v in c.items() if k != "credentials_encrypted"}
        for c in connections
    ]
    return {
        "connections": safe,
        "available": available_providers(),
        "unavailable": unavailable_tools(),
    }


class IcsConnect(BaseModel):
    merchant_id: str
    url: str = Field(min_length=8, max_length=2000)
    resource_id: str | None = None


@router.post("/integrations/ics")
async def connect_ics(body: IcsConnect,
                      principal=Depends(require_service_auth)):
    """Connect a read-only calendar feed. No vendor approval needed."""
    _validate_merchant(body.merchant_id)
    await enforce_service_member(principal, body.merchant_id)
    if not re.match(r"^(https?|webcal)://", body.url.strip(), re.I):
        raise HTTPException(400, "feed URL must start with https:// or webcal://")
    row = await get_booking_store().upsert_connection({
        "merchant_id": body.merchant_id,
        "provider": "ics_feed",
        "status": "connected",
        "direction": "read",
        "config": {"url": body.url.strip(), "resource_id": body.resource_id},
    })
    # Sync immediately so the merchant sees it work rather than trusting it.
    from src.services.booking_sync import sync_connection
    result = await sync_connection(row or {})
    return {"connection": {k: v for k, v in (row or {}).items()
                           if k != "credentials_encrypted"},
            "sync": result}


@router.post("/feed/{merchant_id}/enable")
async def enable_feed(merchant_id: str, principal=Depends(require_service_auth)):
    """Mint (or rotate) the subscribe-anywhere calendar URL.

    Rotating is how a leaked feed is revoked: the old token stops resolving
    the moment this returns.
    """
    from src.services.booking_feed import generate_feed_token
    _validate_merchant(merchant_id)
    await enforce_service_member(principal, merchant_id)
    token = generate_feed_token()
    db = get_db()
    await db.update("phone_agent_config", {"booking_feed_token": token},
                    {"merchant_id": f"eq.{merchant_id}"})
    base = (os.getenv("PUBLIC_PAY_BASE") or "https://api.meridian.tips").rstrip("/")
    return {"feed_url": f"{base}/api/bookings/feed/{token}.ics"}


@router.get("/feed/{token}.ics")
async def booking_feed(token: str):
    """PUBLIC by necessity — calendar clients cannot send an auth header, so
    the 32-hex token in the path is the credential. Rotatable via
    /feed/{merchant_id}/enable. Listed in the CC6.6 public-endpoint baseline.
    """
    from fastapi.responses import Response

    from src.services.booking_feed import feed_for_token

    result = await feed_for_token(token)
    if not result:
        # 404 rather than 403: an attacker probing tokens learns nothing about
        # whether a merchant exists.
        raise HTTPException(404, "not found")
    _name, ics = result
    return Response(
        content=ics,
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": 'inline; filename="meridian-bookings.ics"',
            "Cache-Control": "private, max-age=300",
        },
    )


@router.get("/busy/{merchant_id}")
async def list_busy(
    merchant_id: str,
    start: str = Query(...),
    end: str = Query(...),
    principal=Depends(require_service_auth),
):
    """Time taken in the merchant's OTHER systems, imported by the sync.

    This is what makes the book one book. A merchant on external_link mode
    takes no bookings through us at all, and a merchant on native mode still
    has a personal calendar — in both cases the owner's real question is "what
    is happening tonight", and an answer that only counts our own rows is a
    half-answer that quietly teaches them not to trust the screen.

    Read-only by construction: these rows are owned by the sync and are
    replaced wholesale on every run, so nothing here is editable.
    """
    _validate_merchant(merchant_id)
    await enforce_service_member(principal, merchant_id)
    rows = await get_booking_store().list_busy_blocks(merchant_id, start, end)
    conns = {c["id"]: c for c in await get_booking_store().list_connections(merchant_id)}
    for r in rows:
        conn = conns.get(r.get("connection_id")) or {}
        r["provider"] = conn.get("provider") or ""
    return {"busy": rows}


class BookingLinkRequest(BaseModel):
    url: str = Field("", max_length=500)


@router.get("/link/{merchant_id}")
async def get_booking_link(merchant_id: str, principal=Depends(require_service_auth)):
    """The external booking link, and whether callers actually open it.

    The counts are the point. A merchant who hands bookings off to their own
    website otherwise has no way to tell whether the phone agent did anything
    at all, because every booking it produced landed in somebody else's
    system under the customer's own name.
    """
    from src.services.booking_links import get_link_service

    _validate_merchant(merchant_id)
    await enforce_service_member(principal, merchant_id)

    db = get_db()
    rows = await db.select(
        "phone_agent_config",
        {"merchant_id": f"eq.{merchant_id}",
         "select": "booking_mode,booking_link_url,reservation_config"},
    )
    row = rows[0] if rows else {}
    resv = row.get("reservation_config") or {}
    url = (row.get("booking_link_url") or "").strip()
    inherited = False
    if not url and resv.get("on_website"):
        url = (resv.get("website_url") or "").strip()
        inherited = bool(url)

    stats = await get_link_service().stats(merchant_id)
    return {
        "url": url,
        # True when the URL came from the onboarding questionnaire rather than
        # this screen — worth showing, because the merchant did not type it here
        # and may not recognise it.
        "inherited": inherited,
        "mode": row.get("booking_mode") or "off",
        "sent": stats["sent"],
        "opened": stats["opened"],
        "failed": stats["failed"],
        "recent": [
            {
                "code": r.get("code"),
                "created_at": r.get("created_at"),
                "clicked_at": r.get("clicked_at"),
                "delivery": r.get("delivery"),
            }
            for r in stats["recent"]
        ],
    }


@router.post("/link/{merchant_id}")
async def set_booking_link(
    merchant_id: str,
    req: BookingLinkRequest,
    principal=Depends(require_service_auth),
):
    """Set where the texted link points.

    Saving a URL switches the merchant into external_link mode, and clearing it
    switches them back off — because a link mode with nowhere to send anyone is
    an agent that promises a text it cannot deliver. Merchants already booking
    through us (native/provider) are never switched: this screen setting must
    not be able to silently disable a working calendar.
    """
    _validate_merchant(merchant_id)
    await enforce_service_member(principal, merchant_id)

    url = (req.url or "").strip()
    if url:
        if not re.match(r"^(https?://)?[\w.-]+\.[a-z]{2,}(/\S*)?$", url, re.I):
            raise HTTPException(400, "that does not look like a web address")
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"
        if len(url) > 500:
            raise HTTPException(400, "url too long")

    db = get_db()
    rows = await db.select(
        "phone_agent_config",
        {"merchant_id": f"eq.{merchant_id}", "select": "booking_mode"},
    )
    current = (rows[0].get("booking_mode") if rows else "off") or "off"

    fields: dict = {"booking_link_url": url or None}
    if current in ("off", "external_link"):
        fields["booking_mode"] = "external_link" if url else "off"

    await db.update("phone_agent_config", fields,
                    {"merchant_id": f"eq.{merchant_id}"})
    return {"url": url, "mode": fields.get("booking_mode", current)}


@router.get("/detail/{booking_id}")
async def get_booking(booking_id: str, principal=Depends(require_service_auth)):
    _validate_uuid(booking_id, "booking_id")
    row = await _enforce_row_member(principal, "bookings", booking_id)
    if not row:
        raise HTTPException(404, "booking not found")
    full = await get_booking_store().get_booking(booking_id)
    return {"booking": full}
