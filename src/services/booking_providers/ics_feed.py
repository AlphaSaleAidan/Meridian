"""iCalendar feed — the universal read-only integration.

This is the lowest common denominator and, per unit of effort, the highest
coverage of anything we can build. Google Calendar, Outlook, Apple Calendar,
Calendly, Acuity, Square Appointments, Cal.com and most of the salon tools
will all hand a merchant a secret .ics URL. It needs no OAuth app, no vendor
approval, no partnership, and no credential we have to store and rotate: the
merchant pastes a link and their existing commitments start blocking our
slots within the hour.

It cannot write. That is the whole trade, and it is a good one — see
base.Capabilities for why importing busy time is the half that actually
prevents double-booking a paying customer.

The parser is deliberately hand-rolled rather than pulling in `icalendar`.
We need exactly four fields out of VEVENT and the file is fetched from a URL
a merchant pasted, which makes every added dependency a new parser exposed to
semi-trusted input. RFC 5545 line unfolding, DATE vs DATE-TIME, and TZID are
handled; anything else is skipped rather than guessed at.

DELIBERATE LIMITATION: recurring events (RRULE) are read as their base
occurrence only. A merchant whose standing Tuesday block is expressed as a
recurrence will have only the first instance imported. Expanding RRULE
correctly means implementing a meaningful slice of RFC 5545 (COUNT, UNTIL,
BYDAY, EXDATE, and DST-aware interval arithmetic), and a half-correct
expansion would block the wrong hours — which is worse than not importing,
because the merchant cannot see why their slots vanished. The portal says
this out loud rather than letting them find out.
"""
from __future__ import annotations

import logging
import re
from datetime import date as date_cls
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .base import BusyBlock, Capabilities, ProviderError

logger = logging.getLogger("meridian.booking.providers.ics")

# A calendar feed is arbitrary text from a URL the merchant supplied. Cap it.
_MAX_BYTES = 4 * 1024 * 1024
_MAX_EVENTS = 5000


class IcsFeedProvider:
    key = "ics_feed"
    label = "Calendar feed (.ics)"
    capabilities = Capabilities(
        read_busy=True,
        write_booking=False,
        cancel_booking=False,
        webhooks=False,
        self_serve=True,
        summary=(
            "Reads your existing calendar so we never book over it. "
            "Works with Google, Outlook, Apple, Calendly, Acuity and most "
            "salon software. We cannot add bookings back into it."
        ),
    )

    async def fetch_busy(self, connection: dict, start: datetime,
                         end: datetime) -> list[BusyBlock]:
        url = ((connection.get("config") or {}).get("url") or "").strip()
        if not url:
            raise ProviderError("no feed URL configured")
        text = await _fetch(url)
        return [b for b in parse_ics(text) if b.ends_at > start and b.starts_at < end]

    async def push_booking(self, connection: dict, booking: dict):
        return None  # read-only by nature

    async def cancel_booking(self, connection: dict, provider_booking_id: str) -> bool:
        return False


async def _fetch(url: str) -> str:
    import httpx

    if not re.match(r"^https?://", url, re.I):
        # webcal:// is what most tools hand out; it is http(s) underneath.
        if url.lower().startswith("webcal://"):
            url = "https://" + url[len("webcal://"):]
        else:
            raise ProviderError("feed URL must be http(s) or webcal")
    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"Accept": "text/calendar"})
    except Exception as e:  # noqa: BLE001
        raise ProviderError(f"could not reach the calendar feed: {e}") from e
    if resp.status_code != 200:
        raise ProviderError(f"calendar feed returned {resp.status_code}")
    raw = resp.content[:_MAX_BYTES]
    return raw.decode("utf-8", errors="replace")


def _unfold(text: str) -> list[str]:
    """RFC 5545 line unfolding: a leading space or tab continues the line."""
    out: list[str] = []
    for raw_line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if raw_line[:1] in (" ", "\t") and out:
            out[-1] += raw_line[1:]
        else:
            out.append(raw_line)
    return out


def _parse_dt(value: str, params: dict[str, str]) -> datetime | None:
    """One DTSTART/DTEND into a tz-aware UTC datetime.

    Three shapes exist in the wild: a UTC stamp ending in Z, a floating local
    stamp qualified by TZID, and a bare DATE for all-day events.
    """
    value = value.strip()
    if not value:
        return None

    if params.get("VALUE") == "DATE" or re.fullmatch(r"\d{8}", value):
        try:
            day = datetime.strptime(value[:8], "%Y%m%d").date()
        except ValueError:
            return None
        tz = _zone(params.get("TZID")) or timezone.utc
        return datetime.combine(day, time(0, 0)).replace(tzinfo=tz).astimezone(timezone.utc)

    m = re.fullmatch(r"(\d{8})T(\d{6})(Z)?", value)
    if not m:
        return None
    try:
        naive = datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S")
    except ValueError:
        return None

    if m.group(3):  # explicit UTC
        return naive.replace(tzinfo=timezone.utc)

    tz = _zone(params.get("TZID"))
    if tz is None:
        # A floating time with no TZID is genuinely ambiguous. Treating it as
        # UTC is the conservative read: it blocks a window somewhere, and a
        # spurious block costs one lost slot, while a missed block costs a
        # double-booked customer.
        return naive.replace(tzinfo=timezone.utc)
    return naive.replace(tzinfo=tz).astimezone(timezone.utc)


def _zone(tzid: str | None) -> ZoneInfo | None:
    if not tzid:
        return None
    try:
        return ZoneInfo(tzid.strip().strip('"'))
    except (ZoneInfoNotFoundError, ValueError):
        logger.debug("unknown TZID in feed: %r", tzid)
        return None


def _split_property(line: str) -> tuple[str, dict[str, str], str] | None:
    """"DTSTART;TZID=America/Toronto:20260914T190000" -> name, params, value."""
    if ":" not in line:
        return None
    head, _, value = line.partition(":")
    parts = head.split(";")
    name = parts[0].strip().upper()
    params: dict[str, str] = {}
    for chunk in parts[1:]:
        if "=" in chunk:
            k, _, v = chunk.partition("=")
            params[k.strip().upper()] = v.strip()
    return name, params, value


def parse_ics(text: str) -> list[BusyBlock]:
    """Every VEVENT that occupies real time, as busy blocks."""
    blocks: list[BusyBlock] = []
    in_event = False
    # VTIMEZONE contains its own DTSTART lines; reading them as events would
    # invent blocks in 1970.
    depth_other = 0
    current: dict = {}

    for line in _unfold(text):
        stripped = line.strip()
        if not stripped:
            continue
        upper = stripped.upper()

        if upper == "BEGIN:VEVENT":
            in_event, current = True, {}
            continue
        if upper == "END:VEVENT":
            block = _event_to_block(current)
            if block:
                blocks.append(block)
                if len(blocks) >= _MAX_EVENTS:
                    logger.warning("ics feed truncated at %d events", _MAX_EVENTS)
                    break
            in_event, current = False, {}
            continue
        if upper.startswith("BEGIN:") and not in_event:
            depth_other += 1
            continue
        if upper.startswith("END:") and not in_event:
            depth_other = max(0, depth_other - 1)
            continue
        if not in_event:
            continue

        parsed = _split_property(stripped)
        if not parsed:
            continue
        name, params, value = parsed
        if name in ("DTSTART", "DTEND", "UID", "SUMMARY", "STATUS",
                    "DURATION", "TRANSP", "RRULE"):
            current[name] = (params, value)

    return blocks


def _event_to_block(event: dict) -> BusyBlock | None:
    if not event:
        return None

    status = (event.get("STATUS", ({}, ""))[1] or "").strip().upper()
    if status == "CANCELLED":
        return None
    # TRANSPARENT means "free" — the organizer explicitly said this does not
    # occupy them, so honouring it is what keeps an all-day "Q3 planning"
    # banner from closing a shop for a day.
    if (event.get("TRANSP", ({}, ""))[1] or "").strip().upper() == "TRANSPARENT":
        return None

    start_params, start_value = event.get("DTSTART", ({}, ""))
    start = _parse_dt(start_value, start_params)
    if not start:
        return None

    end = None
    if "DTEND" in event:
        end_params, end_value = event["DTEND"]
        end = _parse_dt(end_value, end_params)
    if end is None and "DURATION" in event:
        end = start + _parse_duration(event["DURATION"][1])
    if end is None:
        # All-day events carry a DATE start and often no end.
        if start_params.get("VALUE") == "DATE" or re.fullmatch(r"\d{8}", start_value.strip()):
            end = start + timedelta(days=1)
        else:
            return None

    if end <= start:
        return None

    uid = (event.get("UID", ({}, ""))[1] or "").strip()
    summary = (event.get("SUMMARY", ({}, ""))[1] or "").strip()
    if not uid:
        uid = f"{start.isoformat()}|{end.isoformat()}|{summary[:40]}"

    return BusyBlock(
        starts_at=start,
        ends_at=end,
        external_id=uid[:200],
        summary=summary[:200],
    )


def _parse_duration(value: str) -> timedelta:
    """RFC 5545 DURATION, e.g. PT1H30M or P1D."""
    m = re.fullmatch(
        r"[+-]?P(?:(\d+)W)?(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?",
        value.strip().upper(),
    )
    if not m:
        return timedelta(hours=1)
    weeks, days, hours, minutes, seconds = (int(g or 0) for g in m.groups())
    return timedelta(weeks=weeks, days=days, hours=hours,
                     minutes=minutes, seconds=seconds)
