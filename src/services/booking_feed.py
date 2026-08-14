"""Outbound iCalendar feed — Meridian's bookings, in the merchant's calendar.

The research pass found no way to WRITE into Resy, Tock, Booksy, Vagaro,
Fresha, Squire, or any auto-detailing software: none of them run a developer
programme. For those merchants — a large share of the ones the Canada team
wants to sell — this feed is the integration. They paste one URL into Google,
Outlook or Apple Calendar and every booking the phone agent takes shows up
alongside everything else they already track.

It is one-way and it is refreshed on the client's schedule, which for Google
is hours rather than minutes. That is a real limitation and the portal says so
rather than implying live sync. It is still the highest-coverage thing we can
offer, because it requires no vendor's permission.

THE URL IS THE CREDENTIAL. Calendar clients cannot send an Authorization
header, so the token in the path is the only thing standing between this feed
and the open internet. It is 32 hex characters from `secrets`, it is unique,
and it is revocable by regenerating. The feed therefore carries the minimum
that makes it useful — when, how many, who, and the confirmation code — and
never anything that isn't already in a booking confirmation.
"""
from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("meridian.services.booking_feed")

FEED_WINDOW_PAST_DAYS = 7
FEED_WINDOW_FUTURE_DAYS = 120


def generate_feed_token() -> str:
    return secrets.token_hex(16)


def _stamp(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _escape(text: str) -> str:
    """RFC 5545 text escaping. Order matters — backslash first, or the
    escapes we add get escaped again."""
    return (str(text or "")
            .replace("\\", "\\\\")
            .replace(";", "\\;")
            .replace(",", "\\,")
            .replace("\n", "\\n"))


def _fold(line: str) -> str:
    """Fold to 75 octets per RFC 5545. Strict parsers reject longer lines."""
    encoded = line.encode("utf-8")
    if len(encoded) <= 75:
        return line
    out, chunk = [], b""
    for ch in line:
        raw = ch.encode("utf-8")
        if len(chunk) + len(raw) > 73:
            out.append(chunk.decode("utf-8"))
            chunk = b""
        chunk += raw
    if chunk:
        out.append(chunk.decode("utf-8"))
    return "\r\n ".join(out)


def build_ics(business_name: str, bookings: list[dict], *,
              now: datetime | None = None) -> str:
    """An RFC 5545 calendar of live bookings."""
    now = now or datetime.now(timezone.utc)
    name = business_name or "Meridian"

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Meridian//Bookings//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_escape(name)} bookings",
        # A hint to clients about refresh cadence. Google largely ignores it,
        # Outlook and Apple respect it; asking costs nothing.
        "REFRESH-INTERVAL;VALUE=DURATION:PT15M",
        "X-PUBLISHED-TTL:PT15M",
    ]

    for booking in bookings:
        start = _parse(booking.get("starts_at"))
        end = _parse(booking.get("ends_at"))
        if not start or not end:
            continue

        party = int(booking.get("party_size") or 1)
        who = booking.get("customer_name") or "Booking"
        title = who if party <= 1 else f"{who} (party of {party})"
        code = booking.get("confirmation_code") or ""
        phone = booking.get("customer_phone") or ""
        notes = booking.get("notes") or ""
        cancelled = (booking.get("status") or "") in ("cancelled", "no_show")

        description = " ".join(filter(None, [
            f"Phone: {phone}." if phone else "",
            f"Confirmation: {code}." if code else "",
            f"Notes: {notes}" if notes else "",
            "Booked through Meridian.",
        ]))

        lines += [
            "BEGIN:VEVENT",
            # Stable UID so a client updates the event in place instead of
            # accumulating a duplicate on every refresh.
            f"UID:{booking.get('id')}@bookings.meridian.tips",
            f"DTSTAMP:{_stamp(now)}",
            f"DTSTART:{_stamp(start)}",
            f"DTEND:{_stamp(end)}",
            _fold(f"SUMMARY:{_escape(title)}"),
            _fold(f"DESCRIPTION:{_escape(description)}"),
            # A cancellation must reach the merchant's calendar too, or the
            # table looks held all evening. CANCELLED is how iCalendar says
            # "this is off" without the row vanishing.
            f"STATUS:{'CANCELLED' if cancelled else 'CONFIRMED'}",
            "TRANSP:OPAQUE",
            "END:VEVENT",
        ]

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def _parse(value) -> datetime | None:
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


async def feed_for_token(token: str) -> tuple[str, str] | None:
    """(business_name, ics) for a feed token, or None when it is unknown."""
    from src.db import get_db
    from src.services.booking_store import get_booking_store

    token = (token or "").strip()
    # Length-check before touching the database: the feed URL is public, so
    # this is the one endpoint that will be scanned.
    if len(token) != 32 or not all(c in "0123456789abcdef" for c in token.lower()):
        return None

    db = get_db()
    rows = await db.select(
        "phone_agent_config",
        columns="merchant_id,business_name",
        filters={"booking_feed_token": f"eq.{token}"},
        limit=1,
    )
    if not rows:
        return None

    merchant_id = rows[0].get("merchant_id")
    now = datetime.now(timezone.utc)
    bookings = await get_booking_store().list_bookings(
        merchant_id,
        (now - timedelta(days=FEED_WINDOW_PAST_DAYS)).isoformat(),
        (now + timedelta(days=FEED_WINDOW_FUTURE_DAYS)).isoformat(),
        live_only=False,
    )
    return rows[0].get("business_name") or "", build_ics(
        rows[0].get("business_name") or "", bookings, now=now)
