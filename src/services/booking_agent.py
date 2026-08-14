"""Phone-agent booking handlers — tool arguments in, a spoken sentence out.

This is the layer between what a language model emits mid-call and what the
availability engine will accept. Three jobs:

  1. Coerce loose arguments into real values. The model is instructed to send
     an ISO date and a 24-hour time, and usually does; it also sometimes sends
     "tomorrow", "7pm", or "2026-9-4". Refusing those would fail a caller for
     the model's formatting, so they are parsed tolerantly here — but only
     into unambiguous results. Anything genuinely ambiguous is asked about
     again rather than guessed.

  2. Return ONE plain-English sentence. Vapi speaks the tool result back
     through the model, so the return value is customer-facing copy, not a
     status payload. It is written at an 8th-grade reading level to match the
     rest of the phone product.

  3. Never claim a booking that does not exist. Every failure path — no
     availability, closed, a mid-write collision, an exception — produces an
     honest sentence. This mirrors the order pipeline's honesty gate
     (vapi_webhook._order_reached): a caller who hangs up believing they have
     a table when they do not is the single worst outcome this system can
     produce, worse than any error message.
"""
from __future__ import annotations

import logging
import re
from datetime import date as date_cls
from datetime import datetime, time, timedelta, timezone

from src.services import booking_engine as be
from src.services.booking_store import get_booking_store

logger = logging.getLogger("meridian.services.booking_agent")

# How many times to read out before saying "or another day" — a synthetic
# voice listing eight options is unusable on a phone call.
_SPOKEN_SLOT_LIMIT = 3

_WEEKDAYS = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}


def _noun(setup: be.MerchantBookingSetup) -> str:
    return setup.noun or "reservation"


def parse_date(value: str | None, today: date_cls) -> date_cls | None:
    """A spoken or ISO date. Returns None when it cannot be known.

    Relative words resolve against the MERCHANT's today, not the server's —
    the Contabo box runs on CEST and would otherwise roll "tomorrow" over
    several hours early for every North American merchant.
    """
    if not value:
        return None
    text = str(value).strip().lower()
    if not text:
        return None

    if text in ("today", "tonight", "this evening"):
        return today
    if text == "tomorrow":
        return today + timedelta(days=1)

    iso = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", text)
    if iso:
        try:
            return date_cls(int(iso.group(1)), int(iso.group(2)), int(iso.group(3)))
        except ValueError:
            return None

    # "friday" / "next friday" — the NEXT such weekday, never one in the past.
    words = text.replace("next ", "").replace("this ", "").strip()
    if words in _WEEKDAYS:
        delta = (_WEEKDAYS[words] - today.weekday()) % 7
        if delta == 0:
            delta = 7 if text.startswith("next") else 0
        return today + timedelta(days=delta)

    return None


def parse_time(value: str | None) -> time | None:
    """A spoken or 24-hour time. Returns None when it cannot be known."""
    if not value:
        return None
    text = str(value).strip().lower().replace(".", "")
    if not text:
        return None

    m = re.match(r"^(\d{1,2})[:h]?(\d{2})?\s*(am|pm)?$", text)
    if not m:
        return None
    hour = int(m.group(1))
    minute = int(m.group(2) or 0)
    meridiem = m.group(3)

    if minute > 59:
        return None
    if meridiem:
        if hour < 1 or hour > 12:
            return None
        if meridiem == "pm" and hour != 12:
            hour += 12
        elif meridiem == "am" and hour == 12:
            hour = 0
    elif hour > 23:
        return None

    return time(hour, minute)


def _list_times(slots: list[be.Slot]) -> str:
    labels = []
    for slot in slots[:_SPOKEN_SLOT_LIMIT]:
        if slot.local_label not in labels:
            labels.append(slot.local_label)
    if not labels:
        return ""
    if len(labels) == 1:
        return labels[0]
    return ", ".join(labels[:-1]) + f" or {labels[-1]}"


def _speak_code(code: str) -> str:
    """Space the characters so a TTS voice spells rather than slurs them."""
    return " ".join(code.upper())


def _spawn_push(merchant_id: str, row: dict) -> None:
    """Push to the merchant's calendar in the background, swallowing failures.

    Deliberately does nothing when there is no running loop to attach to
    (tests, sync callers): the push is never load-bearing, so silence is the
    correct behaviour rather than an error the caller has to handle.
    """
    import asyncio

    async def _run():
        try:
            from src.services.booking_sync import push_booking
            await push_booking(merchant_id, row)
        except Exception as e:  # noqa: BLE001
            logger.warning("background booking push failed: %s", e)

    try:
        asyncio.get_running_loop().create_task(_run())
    except RuntimeError:
        pass


async def handle_check_availability(args: dict, setup: be.MerchantBookingSetup,
                                    *, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    today_local = now.astimezone(setup.tz).date()
    noun = _noun(setup)

    day = parse_date(args.get("date"), today_local)
    if not day:
        return "What day were you thinking?"
    if day < today_local:
        return "That day has already passed — what day did you mean?"
    if (day - today_local).days > be.MAX_LEAD_DAYS:
        return f"We only take {noun}s about six months ahead. Could you pick a closer date?"

    party_size = _party_size(args)
    slots = await be.find_slots(setup, day, party_size, now=now)

    if not slots:
        nearby = await _nearby_days(setup, day, party_size, now)
        if nearby:
            return (f"We're full that day. The closest we have is {nearby}. "
                    "Would either of those work?")
        return ("I'm sorry, we don't have anything open that day. "
                "Would you like to try a different date?")

    wanted = parse_time(args.get("time"))
    if wanted:
        exact = [s for s in slots if s.starts_at.astimezone(setup.tz).time() == wanted]
        if exact:
            return f"Yes, {exact[0].local_label} is open. Would you like me to book it?"
        return (f"{_speak_requested(wanted)} isn't open, but I have "
                f"{_list_times(slots)}. Would any of those work?")

    return f"I have {_list_times(slots)}. Which works best?"


def _speak_requested(at: time) -> str:
    hour = at.hour % 12 or 12
    suffix = "AM" if at.hour < 12 else "PM"
    return f"{hour}:{at.minute:02d} {suffix}" if at.minute else f"{hour} {suffix}"


def _party_size(args: dict) -> int:
    try:
        size = int(args.get("party_size") or 1)
    except (TypeError, ValueError):
        size = 1
    return max(1, min(size, 100))


async def _nearby_days(setup: be.MerchantBookingSetup, day: date_cls,
                       party_size: int, now: datetime) -> str:
    """The next day or two that has anything, so a full day is not a dead end."""
    found: list[str] = []
    for offset in (1, 2, -1):
        probe = day + timedelta(days=offset)
        if probe < now.astimezone(setup.tz).date():
            continue
        slots = await be.find_slots(setup, probe, party_size, now=now, limit=3)
        if slots:
            label = probe.strftime("%A")
            found.append(f"{label} at {slots[0].local_label}")
        if len(found) == 2:
            break
    if not found:
        return ""
    return " or ".join(found)


async def handle_book(args: dict, setup: be.MerchantBookingSetup,
                      *, caller_phone: str | None = None,
                      vapi_call_id: str | None = None,
                      now: datetime | None = None) -> str:
    """Take the booking. Returns what the agent says to the caller."""
    now = now or datetime.now(timezone.utc)
    today_local = now.astimezone(setup.tz).date()
    noun = _noun(setup)

    name = (args.get("customer_name") or "").strip()
    if not name:
        return "Can I get a name for the booking?"

    day = parse_date(args.get("date"), today_local)
    at = parse_time(args.get("time"))
    if not day or not at:
        return "What day and time would you like?"
    if day < today_local:
        return "That day has already passed — what day did you mean?"

    party_size = _party_size(args)
    start_utc = be.parse_local_request(day, at, setup)

    if start_utc < now + timedelta(minutes=be.MIN_LEAD_MINUTES):
        return "That's too soon for me to book. Could we make it a bit later?"
    if (day - today_local).days > be.MAX_LEAD_DAYS:
        return f"We only take {noun}s about six months ahead. Could you pick a closer date?"

    phone = (args.get("phone") or caller_phone or "").strip() or None

    try:
        row = await be.reserve(
            setup, start_utc, party_size, name,
            customer_phone=phone,
            notes=(args.get("notes") or "").strip() or None,
            service_id=args.get("service_id") or None,
            source="phone",
            vapi_call_id=vapi_call_id,
        )
    except be.BookingClosed:
        return "We're closed at that time. Would another time work?"
    except be.NoAvailability:
        slots = await be.find_slots(setup, day, party_size, now=now)
        if slots:
            return (f"That time just went. I do have {_list_times(slots)} — "
                    "would any of those work?")
        return ("I'm sorry, we're full then and I don't have anything else that day. "
                "Would you like to try another date?")

    # Mirror it into the merchant's own calendar WITHOUT making the caller
    # wait: Vapi holds the line until this tool returns, and a Google round
    # trip inside that window is dead air. The booking is already committed —
    # the push is a convenience copy, so it is fire-and-forget by design.
    _spawn_push(setup.merchant_id, row)

    code = row.get("confirmation_code", "")
    when = row.get("local_time") or _speak_requested(at)
    people = "" if party_size <= 1 else f" for {party_size}"
    return (f"You're all set, {name.split()[0]} — {when}{people} on "
            f"{day.strftime('%A')}. Your confirmation code is {_speak_code(code)}. "
            "We'll text you a reminder.")


async def handle_cancel(args: dict, setup: be.MerchantBookingSetup,
                        *, caller_phone: str | None = None) -> str:
    """Cancel by confirmation code, or by the number the caller is on."""
    store = get_booking_store()
    noun = _noun(setup)
    code = (args.get("confirmation_code") or "").strip()

    row = None
    if code:
        row = await store.find_by_code(setup.merchant_id, code)
        if not row:
            return ("I couldn't find a booking with that code. "
                    "Could you read it to me once more?")
    elif caller_phone:
        upcoming = await store.find_upcoming_by_phone(setup.merchant_id, caller_phone)
        if not upcoming:
            return f"I don't see a {noun} under this number. Do you have a confirmation code?"
        if len(upcoming) > 1:
            # Cancelling the wrong one is unrecoverable on a phone call, so
            # never guess between several.
            return ("I see more than one booking under this number. "
                    "Which confirmation code should I cancel?")
        row = upcoming[0]
    else:
        return "What's the confirmation code?"

    await store.cancel_booking(str(row["id"]), reason="cancelled by caller on the phone")
    start = be._parse_ts(row.get("starts_at"))
    when = be._speak_time(start.astimezone(setup.tz)) if start else "that time"
    return f"Done — your {noun} at {when} is cancelled. Anything else I can help with?"


async def handle_lookup(args: dict, setup: be.MerchantBookingSetup,
                        *, caller_phone: str | None = None) -> str:
    store = get_booking_store()
    noun = _noun(setup)
    code = (args.get("confirmation_code") or "").strip()

    row = None
    if code:
        row = await store.find_by_code(setup.merchant_id, code)
    elif caller_phone:
        upcoming = await store.find_upcoming_by_phone(setup.merchant_id, caller_phone)
        row = upcoming[0] if upcoming else None

    if not row:
        return f"I don't see a {noun} for you. Would you like to make one?"

    start = be._parse_ts(row.get("starts_at"))
    if not start:
        return f"I found your {noun}, but I can't read the time. Let me get someone to help."
    local = start.astimezone(setup.tz)
    party = int(row.get("party_size") or 1)
    people = "" if party <= 1 else f" for {party}"
    return (f"You're booked{people} on {local.strftime('%A')} at "
            f"{be._speak_time(local)}. Is that what you needed?")
