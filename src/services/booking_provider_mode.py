"""Booking THROUGH the merchant's own system, when that system owns the truth.

Three modes exist and the distinction matters:

  native          We own the calendar. The merchant's other tools, if any, are
                  imported as busy time. Our exclusion constraint is the
                  guarantee.

  provider        THEIR system owns the calendar. We ask it what is free and
                  we write into it. This module is that path.

  external_link   We read the caller a URL. No integration at all.

Provider mode exists because a barbershop already living in Square
Appointments will not migrate, and should not have to. Their staff keep the
app on their phone; the only thing that changes is that the phone now gets
answered and the booking appears the same way it always did.

WHO IS AUTHORITATIVE DECIDES WHAT A FAILURE MEANS.
In native mode our database refusing a write means the slot is gone, and the
caller must be told. In provider mode Square has already accepted the booking
by the time we write our mirror row — so a mirror failure is OUR problem, not
the caller's, and it must never turn a successful booking into an apology. The
mirror exists for reminders, today's book, and analytics; it is a copy, not
the record.
"""
from __future__ import annotations

import logging
from datetime import date as date_cls
from datetime import datetime, time, timedelta, timezone

from src.services import booking_engine as be
from src.services.booking_providers.base import ProviderError
from src.services.booking_providers.registry import get_provider
from src.services.booking_store import (
    SlotTaken,
    generate_confirmation_code,
    get_booking_store,
)

logger = logging.getLogger("meridian.services.booking_provider_mode")


class ProviderUnavailable(Exception):
    """The merchant's booking system could not be reached or used."""


async def active_connection(merchant_id: str) -> dict | None:
    """The connection that owns this merchant's calendar, if any."""
    store = get_booking_store()
    try:
        connections = await store.list_connections(merchant_id)
    except Exception as e:  # noqa: BLE001
        logger.warning("could not list connections for %s: %s", merchant_id, e)
        return None
    for connection in connections or []:
        if (connection.get("status") or "") != "connected":
            continue
        if (connection.get("direction") or "read") == "read":
            continue
        provider = get_provider(connection.get("provider") or "")
        if provider and provider.capabilities.write_booking:
            return connection
    return None


def _mapped_service(connection: dict, party_size: int) -> dict | None:
    config = connection.get("config") or {}
    default = config.get("default_service")
    if default:
        return default
    # With several services and no default, the phone agent has no basis to
    # pick one — booking the wrong service onto someone's day is worse than
    # falling back to our own calendar.
    service_map = config.get("service_map") or {}
    if len(service_map) == 1:
        return next(iter(service_map.values()))
    return None


async def provider_slots(
    setup: be.MerchantBookingSetup,
    connection: dict,
    day: date_cls,
    party_size: int = 1,
    *,
    now: datetime | None = None,
    limit: int = 40,
) -> list[be.Slot]:
    """Open times according to the merchant's own system."""
    now = now or datetime.now(timezone.utc)
    provider = get_provider(connection.get("provider") or "")
    if not provider or not hasattr(provider, "search_availability"):
        raise ProviderUnavailable("provider cannot report availability")

    mapping = _mapped_service(connection, party_size)
    if not mapping:
        raise ProviderUnavailable("no service mapping configured")

    start_local = be._local_dt(day, time(0, 0), setup.tz)
    start = max(start_local.astimezone(timezone.utc),
                now + timedelta(minutes=be.MIN_LEAD_MINUTES))
    end = start_local.astimezone(timezone.utc) + timedelta(days=1)
    if end <= start:
        return []

    team_ids = _team_filter(connection)
    try:
        raw = await provider.search_availability(
            connection, start, end,
            service_variation_id=mapping["service_variation_id"],
            team_member_ids=team_ids,
        )
    except ProviderError as e:
        raise ProviderUnavailable(str(e)) from e

    slots: list[be.Slot] = []
    for entry in raw:
        starts_at = entry.get("starts_at")
        if not isinstance(starts_at, datetime):
            continue
        duration = int(entry.get("duration_minutes") or 60)
        slots.append(be.Slot(
            starts_at=starts_at,
            ends_at=starts_at + timedelta(minutes=duration),
            resource_id=str(entry.get("team_member_id") or ""),
            resource_name="",
            service_id=None,
            duration_minutes=duration,
            local_label=be._speak_time(starts_at.astimezone(setup.tz)),
        ))
    slots.sort(key=lambda s: s.starts_at)
    return slots[:limit]


def _team_filter(connection: dict) -> list[str] | None:
    config = connection.get("config") or {}
    default = config.get("default_service") or {}
    if default.get("team_member_id"):
        return [default["team_member_id"]]
    ids = [t.get("team_member_id") for t in (config.get("team_members") or [])
           if t.get("is_bookable") and t.get("team_member_id")]
    return ids or None


async def provider_reserve(
    setup: be.MerchantBookingSetup,
    connection: dict,
    start_utc: datetime,
    party_size: int,
    customer_name: str,
    *,
    customer_phone: str | None = None,
    notes: str | None = None,
    vapi_call_id: str | None = None,
) -> dict:
    """Write the booking into the merchant's system, then mirror it locally."""
    provider = get_provider(connection.get("provider") or "")
    if not provider:
        raise ProviderUnavailable("unknown provider")

    mapping = _mapped_service(connection, party_size)
    if not mapping:
        raise ProviderUnavailable("no service mapping configured")

    duration = int(mapping.get("duration_minutes") or 0) or _default_duration(setup, party_size)
    code = generate_confirmation_code()

    draft = {
        "id": None,
        "starts_at": start_utc.isoformat(),
        "ends_at": (start_utc + timedelta(minutes=duration)).isoformat(),
        "duration_minutes": duration,
        "customer_name": customer_name,
        "customer_phone": customer_phone,
        "notes": notes,
        "confirmation_code": code,
        "service_id": None,
        "resource_id": None,
    }

    try:
        ref = await provider.push_booking(connection, draft)
    except ProviderError as e:
        raise ProviderUnavailable(str(e)) from e
    if not ref or not ref.provider_booking_id:
        raise ProviderUnavailable("provider did not return a booking")

    mirror = await _mirror(
        setup, connection, start_utc, duration, party_size, customer_name,
        customer_phone, notes, code, ref.provider_booking_id, vapi_call_id,
    )
    # Square has confirmed. Whatever happened to our copy, the caller has a
    # booking, so the return value is built from what WE know is true.
    return mirror or {
        "confirmation_code": code,
        "starts_at": start_utc.isoformat(),
        "local_time": be._speak_time(start_utc.astimezone(setup.tz)),
        "provider": connection.get("provider"),
        "provider_booking_id": ref.provider_booking_id,
        "mirrored": False,
    }


def _default_duration(setup: be.MerchantBookingSetup, party_size: int) -> int:
    service = be.select_service(setup, party_size)
    duration, _buffer = be._service_duration(service)
    return duration


async def _mirror(setup, connection, start_utc, duration, party_size,
                  customer_name, customer_phone, notes, code,
                  provider_booking_id, vapi_call_id) -> dict | None:
    """Best-effort local copy, for reminders and today's book.

    Every failure here is swallowed on purpose. The alternative — telling a
    caller their booking failed when the merchant's system already holds it —
    would create a guest who does not show up for a slot that is genuinely
    reserved.
    """
    store = get_booking_store()
    try:
        resource = await _resource_for(setup.merchant_id, connection)
        if not resource:
            return None
        row = await store.create_booking({
            "merchant_id": setup.merchant_id,
            "resource_id": resource,
            "starts_at": start_utc.isoformat(),
            "ends_at": (start_utc + timedelta(minutes=duration)).isoformat(),
            "duration_minutes": duration,
            "party_size": party_size,
            "customer_name": customer_name[:200],
            "customer_phone": customer_phone,
            "notes": (notes or "")[:1000] or None,
            "status": "confirmed",
            "source": "phone",
            "confirmation_code": code,
            "provider": connection.get("provider"),
            "provider_booking_id": provider_booking_id,
            "vapi_call_id": vapi_call_id,
        })
        row["local_time"] = be._speak_time(start_utc.astimezone(setup.tz))
        row["mirrored"] = True
        return row
    except SlotTaken:
        logger.warning(
            "mirror collided for provider booking %s — provider is "
            "authoritative, booking stands", provider_booking_id)
        return None
    except Exception as e:  # noqa: BLE001
        logger.warning("could not mirror provider booking %s: %s",
                       provider_booking_id, e)
        return None


async def _resource_for(merchant_id: str, connection: dict) -> str | None:
    """A local resource to hang the mirror row on.

    Provider-mode merchants have no reason to have configured our resources,
    so one is created on demand and tagged with the provider. It is bookkeeping
    for the mirror, not a second calendar.
    """
    store = get_booking_store()
    provider_key = connection.get("provider") or "provider"
    try:
        resources = await store.list_resources(merchant_id)
    except Exception:  # noqa: BLE001
        return None

    for r in resources:
        if (r.get("metadata") or {}).get("provider") == provider_key:
            return str(r["id"])
    if resources:
        return str(resources[0]["id"])

    try:
        created = await store.create_resource({
            "merchant_id": merchant_id,
            "name": "Booked in your own system",
            "kind": "staff",
            "seats": 1,
            "metadata": {"provider": provider_key, "auto_created": True},
        })
        return str(created["id"]) if created else None
    except Exception as e:  # noqa: BLE001
        logger.warning("could not create mirror resource for %s: %s", merchant_id, e)
        return None
