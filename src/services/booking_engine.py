"""Availability and booking logic — the part that decides what times exist.

Everything here answers one of two questions:

    "What can I offer this caller?"   -> find_slots()
    "Can I actually hold this one?"   -> reserve()

The split matters because the answers are not equally trustworthy.
find_slots() reads a snapshot and is already stale by the time a synthetic
voice has finished reading it aloud. reserve() is the only thing that makes a
promise, and it makes it by writing a row that Postgres will refuse if the
resource was taken in the meantime (migrations/081_bookings.sql,
bookings_no_double_book). Nothing in this module reports success on the
strength of an availability check alone.

TIME IS LOCAL, STORAGE IS UTC.
A merchant thinks "we open at five". That is a wall-clock fact about their
town and it does not move when the clocks change. So hours are authored as
local times, every candidate slot is constructed in the merchant's
IANA timezone, and only then converted to UTC for storage and comparison.
Doing it the other way — storing 17:00 as a fixed UTC offset — silently
shifts a restaurant's entire evening by an hour twice a year.

Every duration is minutes and every instant is timezone-aware. There are no
naive datetimes in this module; a naive datetime reaching the database is the
bug this docstring exists to prevent.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date as date_cls
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from src.services.booking_store import (
    SlotTaken,
    generate_confirmation_code,
    get_booking_store,
)

logger = logging.getLogger("meridian.services.booking_engine")

DEFAULT_TIMEZONE = "America/Toronto"

# How far ahead a caller may book. A year of lead time is not a feature, it is
# a data-entry accident waiting to fill a calendar with rows nobody honours.
MAX_LEAD_DAYS = 180

# Never offer a slot that starts sooner than this. A caller who is told "in
# four minutes" will not make it, and the kitchen or the chair cannot prepare.
MIN_LEAD_MINUTES = 15


class NoAvailability(Exception):
    """No resource can hold the requested booking."""


class BookingClosed(Exception):
    """The business is not open at the requested time."""


@dataclass
class Slot:
    """One offerable start time, with the resource that would take it."""
    starts_at: datetime          # tz-aware, UTC
    ends_at: datetime            # tz-aware, UTC, INCLUDES the service buffer
    resource_id: str
    resource_name: str
    service_id: str | None
    duration_minutes: int        # what the customer is told, buffer excluded
    local_label: str             # "7:15 PM" in the merchant's timezone


@dataclass
class MerchantBookingSetup:
    """Everything the engine needs about one merchant, fetched once."""
    merchant_id: str
    tz: ZoneInfo
    tz_name: str
    resources: list[dict] = field(default_factory=list)
    services: list[dict] = field(default_factory=list)
    hours: list[dict] = field(default_factory=list)
    pacing: list[dict] = field(default_factory=list)
    noun: str = "reservation"
    # 'native' = we own the calendar; 'provider' = the merchant's own system
    # does and we book into it (src/services/booking_provider_mode.py).
    mode: str = "native"
    # DEPOSITS (migrations/085): copied from phone_agent_config at load so the
    # agent can quote the amount and policy without another query on the
    # assistant hot path (tests/test_vapi_hotpath_perf.py counts queries).
    deposits_enabled: bool = False
    deposit_policy: str = ""
    deposit_hold_minutes: int = 60


def resolve_timezone(tz_name: str | None) -> tuple[ZoneInfo, str]:
    """Merchant timezone, or the Canada-first default.

    A bad or missing timezone is NOT fail-open here, unlike
    merchant_config.is_open_now which deliberately lets calls through rather
    than gate them. Booking is different: guessing wrong does not inconvenience
    a caller, it books them for the wrong hour. Falling back to a fixed default
    at least keeps every slot for that merchant self-consistent.
    """
    name = (tz_name or "").strip() or DEFAULT_TIMEZONE
    try:
        return ZoneInfo(name), name
    except (ZoneInfoNotFoundError, ValueError):
        logger.warning("unknown merchant timezone %r — falling back to %s",
                       name, DEFAULT_TIMEZONE)
        return ZoneInfo(DEFAULT_TIMEZONE), DEFAULT_TIMEZONE


async def load_setup(merchant_id: str, tz_name: str | None,
                     noun: str = "reservation",
                     mode: str = "native",
                     deposits_enabled: bool = False,
                     deposit_policy: str = "",
                     deposit_hold_minutes: int = 60) -> MerchantBookingSetup:
    store = get_booking_store()
    tz, resolved = resolve_timezone(tz_name)
    resources = await store.list_resources(merchant_id)
    services = await store.list_services(merchant_id)
    hours = await store.list_hours(merchant_id)
    pacing = await store.list_pacing_rules(merchant_id)
    return MerchantBookingSetup(
        merchant_id=merchant_id, tz=tz, tz_name=resolved,
        resources=resources, services=services, hours=hours,
        pacing=pacing, noun=noun or "reservation",
        mode=(mode or "native"),
        deposits_enabled=bool(deposits_enabled),
        deposit_policy=(deposit_policy or "").strip(),
        deposit_hold_minutes=int(deposit_hold_minutes or 60),
    )


def _parse_time(value: str | time | None) -> time | None:
    if isinstance(value, time):
        return value
    if not value:
        return None
    text = str(value).strip()
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(text, fmt).time()
        except ValueError:
            continue
    return None


def _parse_ts(value: str | datetime | None) -> datetime | None:
    """Parse a PostgREST timestamptz into a tz-aware UTC datetime."""
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not value:
        return None
    text = str(value).strip().replace(" ", "T")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _local_dt(day: date_cls, at: time, tz: ZoneInfo) -> datetime:
    """A wall-clock local time on a local date, as a real instant.

    On the hour that repeats when clocks go back, Python's default fold=0
    picks the FIRST (still-daylight-saving) occurrence. That is a deliberate,
    documented choice rather than an accident: it is the earlier real instant,
    so a booking made against it can never land in the past relative to the
    slot the caller was offered.
    """
    return datetime.combine(day, at).replace(tzinfo=tz)


def select_service(setup: MerchantBookingSetup, party_size: int,
                   service_id: str | None = None) -> dict | None:
    """The service to book: explicit if named, otherwise the party-size band.

    Restaurants model turn time as one pseudo-service per band ("Table for
    1–4" 90 min), so this is also how a reservation gets its duration.
    """
    if service_id:
        for svc in setup.services:
            if str(svc.get("id")) == str(service_id):
                return svc
    candidates = [
        s for s in setup.services
        if int(s.get("min_party") or 1) <= party_size <= int(s.get("max_party") or 1)
    ]
    if candidates:
        # Narrowest band wins, so "Table for 5-8" beats a catch-all 1-99 row.
        return min(candidates, key=lambda s: int(s.get("max_party") or 1) - int(s.get("min_party") or 1))
    return setup.services[0] if setup.services else None


def _service_duration(service: dict | None) -> tuple[int, int]:
    """(customer-facing minutes, buffer minutes)."""
    if not service:
        return 60, 0
    return (
        int(service.get("duration_minutes") or 60),
        int(service.get("buffer_minutes") or 0),
    )


def _eligible_resources(setup: MerchantBookingSetup, party_size: int,
                        service: dict | None) -> list[dict]:
    """Resources that could physically take this booking, best fit first.

    Smallest sufficient resource wins so a party of two does not consume the
    only six-top; ties break on the merchant's sort_order.
    """
    wanted_kind = (service or {}).get("resource_kind") or None
    out = [
        r for r in setup.resources
        if int(r.get("seats") or 1) >= party_size
        and (not wanted_kind or r.get("kind") == wanted_kind)
    ]
    out.sort(key=lambda r: (int(r.get("seats") or 1), int(r.get("sort_order") or 0)))
    return out


def _windows_for_day(setup: MerchantBookingSetup, day: date_cls) -> list[dict]:
    """Opening windows for a local date. Python weekday() is Mon=0; the
    schema stores Sun=0 to match Postgres' extract(dow), hence the shift."""
    dow = (day.weekday() + 1) % 7
    return [h for h in setup.hours if int(h.get("weekday", -1)) == dow]


def _busy_ranges(rows: list[dict], key_start: str = "starts_at",
                 key_end: str = "ends_at") -> list[tuple[datetime, datetime, str | None]]:
    out = []
    for row in rows:
        start = _parse_ts(row.get(key_start))
        end = _parse_ts(row.get(key_end))
        if start and end:
            out.append((start, end, row.get("resource_id")))
    return out


def _overlaps(a_start: datetime, a_end: datetime,
              b_start: datetime, b_end: datetime) -> bool:
    """Half-open overlap, matching the database's tstzrange '[)' semantics so
    Python and Postgres never disagree about back-to-back bookings."""
    return a_start < b_end and b_start < a_end


def _pacing_cap(setup: MerchantBookingSetup, local_start: datetime) -> tuple[int, int] | None:
    """(max_covers, interval_minutes) governing this instant, or None."""
    dow = (local_start.date().weekday() + 1) % 7
    at = local_start.time()
    for rule in setup.pacing:
        weekday = rule.get("weekday")
        if weekday is not None and int(weekday) != dow:
            continue
        opens = _parse_time(rule.get("starts_at"))
        closes = _parse_time(rule.get("ends_at"))
        if opens and closes and opens <= at < closes:
            return int(rule.get("max_covers") or 0), int(rule.get("interval_minutes") or 15)
    return None


def _pacing_blocked(setup: MerchantBookingSetup, local_start: datetime,
                    start_utc: datetime, party_size: int,
                    existing: list[dict]) -> bool:
    """True when seating this party would breach the covers cap.

    Pacing is about arrivals, not occupancy: it counts parties STARTING in the
    same interval, which is what actually lands on the kitchen at once.
    """
    cap = _pacing_cap(setup, local_start)
    if not cap:
        return False
    max_covers, interval_minutes = cap
    if max_covers <= 0:
        return True
    bucket_start = start_utc
    bucket_end = start_utc + timedelta(minutes=interval_minutes)
    booked = 0
    for row in existing:
        row_start = _parse_ts(row.get("starts_at"))
        if row_start and bucket_start <= row_start < bucket_end:
            booked += int(row.get("party_size") or 1)
    return (booked + party_size) > max_covers


async def find_slots(
    setup: MerchantBookingSetup,
    day: date_cls,
    party_size: int = 1,
    service_id: str | None = None,
    *,
    now: datetime | None = None,
    limit: int = 40,
) -> list[Slot]:
    """Offerable start times on one LOCAL date, soonest first."""
    now = now or datetime.now(timezone.utc)
    service = select_service(setup, party_size, service_id)
    duration, buffer_min = _service_duration(service)
    hold_minutes = duration + buffer_min

    resources = _eligible_resources(setup, party_size, service)
    if not resources:
        return []

    windows = _windows_for_day(setup, day)
    if not windows:
        return []

    # One query per day, widened by the longest possible hold so a booking
    # that started yesterday evening and runs past midnight is still seen.
    day_start = _local_dt(day, time(0, 0), setup.tz).astimezone(timezone.utc)
    day_end = day_start + timedelta(days=1)
    store = get_booking_store()
    window_lo = (day_start - timedelta(hours=24)).isoformat()
    window_hi = day_end.isoformat()

    existing = await store.list_bookings(setup.merchant_id, window_lo, window_hi)
    closures = await store.list_closures(setup.merchant_id, window_lo, window_hi)
    busy = await store.list_busy_blocks(setup.merchant_id, window_lo, window_hi)

    booked_ranges = _busy_ranges(existing)
    blocked_ranges = _busy_ranges(closures) + _busy_ranges(busy)

    earliest = now + timedelta(minutes=MIN_LEAD_MINUTES)
    slots: list[Slot] = []

    for window in windows:
        opens = _parse_time(window.get("opens_at"))
        closes = _parse_time(window.get("closes_at"))
        if not opens or not closes:
            continue
        step = max(5, int(window.get("slot_minutes") or 15))
        close_utc = _local_dt(day, closes, setup.tz).astimezone(timezone.utc)

        cursor_local = _local_dt(day, opens, setup.tz)
        while True:
            start_utc = cursor_local.astimezone(timezone.utc)
            end_utc = start_utc + timedelta(minutes=hold_minutes)

            # The customer-facing appointment must finish by closing time; the
            # trailing buffer may run past it, since cleanup after close is
            # normal and refusing it would drop the last slot of every day.
            customer_end = start_utc + timedelta(minutes=duration)
            if customer_end > close_utc:
                break

            if start_utc >= earliest and not any(
                _overlaps(start_utc, end_utc, b_start, b_end)
                for b_start, b_end, res_id in blocked_ranges
                if res_id is None
            ):
                free = _first_free_resource(
                    resources, start_utc, end_utc, booked_ranges, blocked_ranges
                )
                if free and not _pacing_blocked(
                    setup, cursor_local, start_utc, party_size, existing
                ):
                    slots.append(Slot(
                        starts_at=start_utc,
                        ends_at=end_utc,
                        resource_id=str(free["id"]),
                        resource_name=str(free.get("name") or ""),
                        service_id=str(service["id"]) if service else None,
                        duration_minutes=duration,
                        local_label=_speak_time(cursor_local),
                    ))
                    if len(slots) >= limit:
                        return slots

            cursor_local += timedelta(minutes=step)
            # Guard against a pathological slot_minutes producing an endless
            # walk if a window were ever mis-authored.
            if cursor_local.date() > day + timedelta(days=1):
                break

    slots.sort(key=lambda s: s.starts_at)
    return slots[:limit]


def _first_free_resource(
    resources: list[dict],
    start_utc: datetime,
    end_utc: datetime,
    booked_ranges: list[tuple[datetime, datetime, str | None]],
    blocked_ranges: list[tuple[datetime, datetime, str | None]],
) -> dict | None:
    for resource in resources:
        rid = str(resource["id"])
        clash = any(
            _overlaps(start_utc, end_utc, b_start, b_end)
            for b_start, b_end, res_id in booked_ranges
            if str(res_id) == rid
        ) or any(
            _overlaps(start_utc, end_utc, b_start, b_end)
            for b_start, b_end, res_id in blocked_ranges
            if res_id is not None and str(res_id) == rid
        )
        if not clash:
            return resource
    return None


def _speak_time(local_dt: datetime) -> str:
    """"7:15 PM" — no leading zero, which a TTS voice reads as "oh seven"."""
    hour = local_dt.hour % 12 or 12
    minute = local_dt.minute
    suffix = "AM" if local_dt.hour < 12 else "PM"
    return f"{hour}:{minute:02d} {suffix}" if minute else f"{hour} {suffix}"


def parse_local_request(day: date_cls, at: time, setup: MerchantBookingSetup) -> datetime:
    """A requested local date+time as a UTC instant."""
    return _local_dt(day, at, setup.tz).astimezone(timezone.utc)


async def reserve(
    setup: MerchantBookingSetup,
    start_utc: datetime,
    party_size: int,
    customer_name: str,
    *,
    customer_phone: str | None = None,
    customer_email: str | None = None,
    notes: str | None = None,
    service_id: str | None = None,
    source: str = "phone",
    vapi_call_id: str | None = None,
    extra: dict | None = None,
) -> dict:
    """Hold a specific time. The only function here that promises anything.

    Walks every eligible resource in best-fit order and tries to write. A
    SlotTaken from one resource means that resource was claimed between the
    read and the write, NOT that the time is gone — so it moves to the next
    one. Only when every resource has refused is the time genuinely full, and
    then it raises rather than inventing a confirmation.
    """
    service = select_service(setup, party_size, service_id)
    duration, buffer_min = _service_duration(service)
    end_utc = start_utc + timedelta(minutes=duration + buffer_min)

    resources = _eligible_resources(setup, party_size, service)

    # A caller may pin the resource — a standing appointment with the barber
    # the customer actually books for. Filtering here rather than skipping the
    # engine keeps opening hours, closures and the exclusion constraint in
    # force; the only thing that changes is which resources are eligible.
    pinned = (extra or {}).get("resource_id")
    if pinned:
        resources = [r for r in resources if str(r["id"]) == str(pinned)]

    if not resources:
        raise NoAvailability("no resource can seat this party")

    store = get_booking_store()
    existing = await store.list_bookings(
        setup.merchant_id,
        (start_utc - timedelta(hours=24)).isoformat(),
        end_utc.isoformat(),
    )
    closures = await store.list_closures(
        setup.merchant_id,
        (start_utc - timedelta(hours=24)).isoformat(),
        end_utc.isoformat(),
    )
    busy = await store.list_busy_blocks(
        setup.merchant_id,
        (start_utc - timedelta(hours=24)).isoformat(),
        end_utc.isoformat(),
    )
    blocked = _busy_ranges(closures) + _busy_ranges(busy)

    # A whole-business closure is not a per-resource race; nothing can be held.
    if any(
        _overlaps(start_utc, end_utc, b_start, b_end)
        for b_start, b_end, res_id in blocked if res_id is None
    ):
        raise BookingClosed("closed at that time")

    booked = _busy_ranges(existing)
    for resource in resources:
        rid = str(resource["id"])
        if any(
            _overlaps(start_utc, end_utc, b_start, b_end)
            for b_start, b_end, res_id in booked + blocked
            if res_id is not None and str(res_id) == rid
        ):
            continue
        row = {
            "merchant_id": setup.merchant_id,
            "resource_id": rid,
            "service_id": str(service["id"]) if service else None,
            "starts_at": start_utc.isoformat(),
            "ends_at": end_utc.isoformat(),
            "duration_minutes": duration,
            "party_size": party_size,
            "customer_name": customer_name[:200],
            "customer_phone": customer_phone,
            "customer_email": customer_email,
            "notes": (notes or "")[:1000] or None,
            "status": "confirmed",
            "source": source,
            "confirmation_code": generate_confirmation_code(),
            "vapi_call_id": vapi_call_id,
        }
        # Callers may attach their own columns (series_id, deposit fields).
        # resource_id is filtered out: it selects a resource above rather than
        # overriding the one this iteration proved is free.
        for key, value in (extra or {}).items():
            if key != "resource_id":
                row[key] = value
        try:
            created = await store.create_booking(row)
        except SlotTaken:
            logger.info("resource %s taken mid-write, trying next", rid)
            continue
        created["resource_name"] = resource.get("name")
        created["local_time"] = _speak_time(start_utc.astimezone(setup.tz))
        return created

    raise NoAvailability("every resource is taken at that time")
