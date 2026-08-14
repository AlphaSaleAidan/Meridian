"""Two-way sync with the merchant's own booking tool.

IN: fetch their busy time and store it as booking_busy_blocks, so the phone
agent never offers a chair that is already filled in their system.

OUT: push bookings we took into their calendar, so the owner sees them where
they already look rather than in a portal they have to remember to open.

FAIL-SOFT IS THE RULE. Every provider call here is wrapped. A merchant's
Google token being revoked, a calendar feed 404ing, or a vendor having an
outage must degrade booking to our own calendar — it must never take down the
phone line or block a caller from booking. The cost of that choice is the
possibility of a double-booking against a stale external view, which is
recorded on the connection as last_error and surfaced in the portal, rather
than being hidden.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from src.services.booking_providers.base import ProviderError
from src.services.booking_providers.registry import get_provider
from src.services.booking_store import get_booking_store

logger = logging.getLogger("meridian.services.booking_sync")

# How far ahead to import. Matching the booking horizon would import a year of
# a merchant's personal calendar for no gain; nobody books a haircut in March.
SYNC_WINDOW_DAYS = 60


async def sync_connection(connection: dict, *, now: datetime | None = None) -> dict:
    """Import one connection's busy time. Never raises."""
    now = now or datetime.now(timezone.utc)
    store = get_booking_store()
    key = connection.get("provider") or ""
    provider = get_provider(key)

    if not provider:
        return {"provider": key, "ok": False, "error": "unknown provider"}
    if not provider.capabilities.read_busy:
        return {"provider": key, "ok": True, "imported": 0, "note": "write-only"}
    if (connection.get("status") or "") == "disabled":
        return {"provider": key, "ok": True, "imported": 0, "note": "disabled"}

    start = now - timedelta(hours=1)
    end = now + timedelta(days=SYNC_WINDOW_DAYS)

    try:
        blocks = await provider.fetch_busy(connection, start, end)
    except ProviderError as e:
        await _mark_error(connection, str(e))
        logger.warning("booking sync failed for %s/%s: %s",
                       connection.get("merchant_id"), key, e)
        return {"provider": key, "ok": False, "error": str(e)}
    except Exception as e:  # noqa: BLE001
        await _mark_error(connection, f"unexpected: {e}")
        logger.exception("booking sync crashed for %s/%s",
                         connection.get("merchant_id"), key)
        return {"provider": key, "ok": False, "error": "unexpected"}

    resource_id = (connection.get("config") or {}).get("resource_id") or None
    rows = [
        {
            "merchant_id": connection.get("merchant_id"),
            "connection_id": connection.get("id"),
            "resource_id": resource_id,
            "starts_at": b.starts_at.isoformat(),
            "ends_at": b.ends_at.isoformat(),
            "external_id": b.external_id,
            "summary": b.summary or None,
        }
        for b in blocks
    ]

    try:
        count = await store.replace_busy_blocks(str(connection["id"]), rows)
    except Exception as e:  # noqa: BLE001
        logger.error("could not store busy blocks for %s: %s", key, e)
        return {"provider": key, "ok": False, "error": "store failed"}

    await _mark_ok(connection)
    return {"provider": key, "ok": True, "imported": count}


async def sync_all(*, now: datetime | None = None) -> dict:
    """Sweep every connected integration. Used by the Celery beat."""
    from src.db import get_db

    db = get_db()
    try:
        connections = await db.select(
            "booking_provider_connections",
            filters={"status": "eq.connected"},
        )
    except Exception as e:  # noqa: BLE001
        logger.error("could not list booking connections: %s", e)
        return {"connections": 0, "ok": 0, "failed": 0}

    ok = failed = 0
    for connection in connections or []:
        result = await sync_connection(connection, now=now)
        if result.get("ok"):
            ok += 1
        else:
            failed += 1

    logger.info("booking sync: %d connections, %d ok, %d failed",
                len(connections or []), ok, failed)
    return {"connections": len(connections or []), "ok": ok, "failed": failed}


async def push_booking(merchant_id: str, booking: dict) -> None:
    """Mirror a new booking into every write-capable connection.

    Best-effort by design and called after the booking is already committed
    to our database. A push failure must never roll back or invalidate a
    booking the customer has been told is confirmed — the row in our calendar
    is the booking; the merchant's calendar is a convenience copy.
    """
    store = get_booking_store()
    try:
        connections = await store.list_connections(merchant_id)
    except Exception as e:  # noqa: BLE001
        logger.warning("could not list connections for push: %s", e)
        return

    for connection in connections or []:
        if (connection.get("status") or "") != "connected":
            continue
        if (connection.get("direction") or "read") == "read":
            continue
        provider = get_provider(connection.get("provider") or "")
        if not provider or not provider.capabilities.write_booking:
            continue
        try:
            ref = await provider.push_booking(connection, booking)
        except Exception as e:  # noqa: BLE001
            await _mark_error(connection, f"push failed: {e}")
            logger.warning("booking push failed for %s: %s",
                           connection.get("provider"), e)
            continue
        if ref and ref.provider_booking_id:
            try:
                await store.update_booking(str(booking["id"]), {
                    "provider": connection.get("provider"),
                    "provider_booking_id": ref.provider_booking_id,
                })
            except Exception as e:  # noqa: BLE001
                logger.warning("could not record provider ref: %s", e)


async def _mark_ok(connection: dict) -> None:
    from src.db import get_db
    try:
        await get_db().update(
            "booking_provider_connections",
            {"last_sync_at": datetime.now(timezone.utc).isoformat(),
             "last_error": None, "status": "connected"},
            {"id": f"eq.{connection['id']}"},
        )
    except Exception:  # noqa: BLE001
        pass


async def _mark_error(connection: dict, message: str) -> None:
    """Record why a connection is unhappy so the portal can say so.

    A revoked Google grant is singled out because it is the one failure the
    merchant must act on personally — retrying cannot fix it, only
    reconnecting can, and a connection stuck silently retrying is a
    double-booking waiting to happen.
    """
    from src.db import get_db
    status = "error"
    if "google_reauth_required" in message:
        message = "Google access was removed — please reconnect the calendar."
    try:
        await get_db().update(
            "booking_provider_connections",
            {"last_error": message[:500], "status": status},
            {"id": f"eq.{connection['id']}"},
        )
    except Exception:  # noqa: BLE001
        pass
