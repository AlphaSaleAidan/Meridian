"""Booking reminder sweep — the cheapest no-show reduction there is.

Two passes, both idempotent by construction: a booking is only picked up when
its send-marker column is still NULL, and the marker is written immediately
after a successful send. A beat that fires twice, a worker that restarts
mid-sweep, or two workers racing the same window therefore cannot text a
customer twice.

The marker is written ONLY on a successful send. A failed text leaves the
booking eligible for the next sweep, which is the right trade: a duplicate
reminder is a mild annoyance, a missing one is a no-show.

Timing is deliberately asymmetric. The 24-hour note gives someone room to
cancel and free the table; the 2-hour note is the one that actually gets
people out the door. Sending only the day-before version means the freed slot
comes back too late to resell.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from src.services.booking_store import get_booking_store

logger = logging.getLogger("meridian.services.booking_reminders")

# Each pass sweeps a window rather than an instant, so a late or skipped beat
# still catches everything since the last run.
_PASSES = (
    ("reminder_24h_sent_at", 24 * 60, 90),
    ("reminder_2h_sent_at", 2 * 60, 45),
)


async def _merchant_info(merchant_ids: set[str]) -> dict[str, dict]:
    """Business name and timezone for the SMS copy, resolved in one query.

    The timezone has to come from here: bookings store instants, not local
    times, so "7 PM" can only be recovered against the merchant's own zone.
    Reading it per booking would be one query per text.
    """
    if not merchant_ids:
        return {}
    from src.db import get_db
    db = get_db()
    ids = ",".join(sorted(merchant_ids))
    try:
        rows = await db.select(
            "phone_agent_config",
            columns="merchant_id,business_name,business_timezone",
            filters={"merchant_id": f"in.({ids})"},
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("could not resolve merchant info for reminders: %s", e)
        return {}
    return {
        str(r.get("merchant_id")): {
            "name": r.get("business_name") or "",
            "tz": r.get("business_timezone") or "",
        }
        for r in rows
    }


def _compose(business_name: str, booking: dict, tz_name: str, hours_out: int) -> str:
    from src.services.booking_engine import _parse_ts, _speak_time, resolve_timezone

    tz, _ = resolve_timezone(tz_name)
    start = _parse_ts(booking.get("starts_at"))
    when = _speak_time(start.astimezone(tz)) if start else "your booked time"
    day = start.astimezone(tz).strftime("%A") if start else ""
    name = (booking.get("customer_name") or "").split(" ")[0]
    where = business_name or "us"
    party = int(booking.get("party_size") or 1)
    people = f" for {party}" if party > 1 else ""

    if hours_out >= 24:
        lead = f"tomorrow ({day})" if day else "tomorrow"
    else:
        lead = "today"

    greeting = f"Hi {name}, " if name else ""
    return (
        f"{greeting}reminder: you're booked at {where} {lead} at {when}{people}. "
        f"Reply CANCEL if you can't make it. Code {booking.get('confirmation_code', '')}"
    )


async def run_reminder_sweep(*, now: datetime | None = None) -> dict:
    """Send every due reminder. Returns per-pass counts for the task log."""
    now = now or datetime.now(timezone.utc)
    store = get_booking_store()
    from src.sms.client import send_sms

    sent = 0
    skipped = 0
    failed = 0

    for column, minutes_out, width_minutes in _PASSES:
        target = now + timedelta(minutes=minutes_out)
        window_start = target - timedelta(minutes=width_minutes)
        window_end = target + timedelta(minutes=width_minutes)

        try:
            due = await store.due_for_reminder(
                window_start.isoformat(), window_end.isoformat(), column)
        except Exception as e:  # noqa: BLE001
            logger.error("reminder query failed for %s: %s", column, e)
            continue

        if not due:
            continue

        info = await _merchant_info({str(b.get("merchant_id")) for b in due})

        for booking in due:
            phone = (booking.get("customer_phone") or "").strip()
            if not phone:
                # Nothing to send to. Mark it so the sweep does not re-examine
                # this row every 15 minutes for the rest of its life.
                await store.mark_reminder_sent(str(booking["id"]), column)
                skipped += 1
                continue

            merchant = info.get(str(booking.get("merchant_id")), {})
            body = _compose(
                merchant.get("name", ""),
                booking,
                merchant.get("tz", ""),
                minutes_out // 60,
            )
            try:
                result = await send_sms(phone, body)
            except Exception as e:  # noqa: BLE001
                logger.warning("reminder SMS raised for booking %s: %s",
                               booking.get("id"), e)
                failed += 1
                continue

            if result and result.get("sent"):
                await store.mark_reminder_sent(str(booking["id"]), column)
                sent += 1
            else:
                # Left unmarked on purpose — the next sweep retries it.
                logger.warning("reminder SMS not sent for booking %s: %s",
                               booking.get("id"), result)
                failed += 1

    logger.info("booking reminders: sent=%d skipped=%d failed=%d", sent, skipped, failed)
    return {"sent": sent, "skipped": skipped, "failed": failed}
