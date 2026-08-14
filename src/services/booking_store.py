"""Storage layer for bookings — reservations and appointments.

PostgREST CRUD with the service-role key. Every booking table is RLS-on with
no policy (migrations/081_bookings.sql), so the service role is the only
reader and writer; the router above owns auth and scoping. This layer is dumb
CRUD plus one thing that is not dumb:

    SlotTaken.

The double-booking guarantee lives in the database as a GiST exclusion
constraint, and Postgres reports a violation as SQLSTATE 23P01, which
PostgREST returns as HTTP 409. That 409 is the single most important response
this module can receive: it is the difference between "your table is booked"
and "someone got that table a quarter-second before you". It must never be
confused with a generic failure, and it must never be swallowed.

It nearly was. ``SupabaseREST._handle_error`` (src/db/supabase_rest.py:774)
deliberately does NOT raise on 409 — it logs and returns, so ``insert()``
hands back an empty list. That behaviour is correct for the upserts it was
written for and quietly catastrophic here: an empty list is indistinguishable
from "wrote nothing", and a caller that shrugged at it would tell a customer
on the phone that a table was reserved when no row exists. So bookings do not
go through the shared client; they use the explicit request path below, where
a 409 becomes SlotTaken and everything else becomes a loud error.
"""
from __future__ import annotations

import logging
import os
import random
import string
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("meridian.services.booking_store")

# Ambiguous characters are omitted: a confirmation code gets read aloud over a
# phone line by a synthetic voice and repeated back by a human in a noisy
# room. O/0, I/1 and S/5 cost more in re-reads than the extra entropy is worth.
_CODE_ALPHABET = "ABCDEFGHJKLMNPQRTUVWXY2346789"
_CODE_LENGTH = 6

LIVE_STATUSES = ("confirmed", "seated")


class BookingStoreError(RuntimeError):
    """Any booking persistence failure that is not a slot collision."""


class SlotTaken(Exception):
    """The exclusion constraint refused the write — that time is gone.

    Raised only for SQLSTATE 23P01. Callers should offer another slot, never
    retry the same one and never report success.
    """


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _supabase_env() -> tuple[str, str]:
    url = os.environ.get("SUPABASE_URL", "")
    key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        or os.environ.get("SUPABASE_SERVICE_KEY", "")
    )
    return url, key


def generate_confirmation_code() -> str:
    return "".join(random.choice(_CODE_ALPHABET) for _ in range(_CODE_LENGTH))


def _is_slot_collision(status_code: int, body: str) -> bool:
    """True when PostgREST is reporting our exclusion constraint, not some
    other conflict.

    Both signals are checked because PostgREST's error shape has changed
    across versions: older builds put the SQLSTATE in ``code``, newer ones
    lead with the constraint name in ``message``/``details``. Matching either
    means a version bump cannot silently downgrade a collision into a generic
    failure — which would turn "that time just went" into "something went
    wrong", the one substitution this system must not make.
    """
    if status_code != 409:
        return False
    haystack = body.lower()
    return "23p01" in haystack or "bookings_no_double_book" in haystack


class BookingStore:
    """PostgREST CRUD with the service key. Every method returns plain dicts."""

    async def _req(
        self,
        method: str,
        table: str,
        params: dict | None = None,
        json: Any = None,
        *,
        collision_aware: bool = False,
        prefer: str = "return=representation",
    ) -> list[dict]:
        import httpx

        url, key = _supabase_env()
        if not url or not key:
            raise BookingStoreError("Supabase env missing for booking store")
        headers = {
            "Authorization": f"Bearer {key}",
            "apikey": key,
            "Prefer": prefer,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.request(
                method,
                f"{url}/rest/v1/{table}",
                headers=headers,
                params=params or {},
                json=json,
            )

        if resp.status_code not in (200, 201, 204):
            body = resp.text[:500]
            if collision_aware and _is_slot_collision(resp.status_code, body):
                logger.info("booking slot collision on %s: %s", table, body[:200])
                raise SlotTaken()
            logger.error(
                "booking store %s %s failed: %s %s",
                method, table, resp.status_code, body[:300],
            )
            raise BookingStoreError(f"booking store {table} {resp.status_code}")

        if resp.status_code == 204 or not resp.text:
            return []
        body_json = resp.json()
        return body_json if isinstance(body_json, list) else [body_json]

    # ─── Resources ────────────────────────────────────────────

    async def list_resources(self, merchant_id: str, *, active_only: bool = True) -> list[dict]:
        params = {
            "merchant_id": f"eq.{merchant_id}",
            "select": "*",
            "order": "sort_order.asc,seats.asc,name.asc",
        }
        if active_only:
            params["active"] = "eq.true"
        return await self._req("GET", "booking_resources", params=params)

    async def create_resource(self, fields: dict) -> dict:
        rows = await self._req("POST", "booking_resources", json=fields)
        return rows[0] if rows else {}

    async def update_resource(self, resource_id: str, fields: dict) -> dict:
        fields = {**fields, "updated_at": _now_iso()}
        rows = await self._req(
            "PATCH", "booking_resources",
            params={"id": f"eq.{resource_id}"}, json=fields,
        )
        return rows[0] if rows else {}

    # ─── Services ─────────────────────────────────────────────

    async def list_services(self, merchant_id: str, *, active_only: bool = True) -> list[dict]:
        params = {
            "merchant_id": f"eq.{merchant_id}",
            "select": "*",
            "order": "sort_order.asc,name.asc",
        }
        if active_only:
            params["active"] = "eq.true"
        return await self._req("GET", "booking_services", params=params)

    async def create_service(self, fields: dict) -> dict:
        rows = await self._req("POST", "booking_services", json=fields)
        return rows[0] if rows else {}

    async def update_service(self, service_id: str, fields: dict) -> dict:
        fields = {**fields, "updated_at": _now_iso()}
        rows = await self._req(
            "PATCH", "booking_services",
            params={"id": f"eq.{service_id}"}, json=fields,
        )
        return rows[0] if rows else {}

    # ─── Hours / closures / pacing ────────────────────────────

    async def list_hours(self, merchant_id: str) -> list[dict]:
        return await self._req("GET", "booking_hours", params={
            "merchant_id": f"eq.{merchant_id}",
            "active": "eq.true",
            "select": "*",
            "order": "weekday.asc,opens_at.asc",
        })

    async def replace_hours(self, merchant_id: str, rows: list[dict]) -> list[dict]:
        """Hours are edited as a whole week, so this is delete-then-insert.

        Not transactional across the two calls: PostgREST has no multi-
        statement transaction. A crash between them leaves the merchant with
        no hours, which fails CLOSED (no slots offered) rather than open — the
        safe direction, and self-healing on the next save.
        """
        await self._req("DELETE", "booking_hours",
                        params={"merchant_id": f"eq.{merchant_id}"})
        if not rows:
            return []
        return await self._req("POST", "booking_hours", json=rows)

    async def list_closures(self, merchant_id: str, start_iso: str, end_iso: str) -> list[dict]:
        return await self._req("GET", "booking_closures", params={
            "merchant_id": f"eq.{merchant_id}",
            "starts_at": f"lt.{end_iso}",
            "ends_at": f"gt.{start_iso}",
            "select": "*",
        })

    async def create_closure(self, fields: dict) -> dict:
        rows = await self._req("POST", "booking_closures", json=fields)
        return rows[0] if rows else {}

    async def delete_closure(self, closure_id: str) -> None:
        await self._req("DELETE", "booking_closures", params={"id": f"eq.{closure_id}"})

    async def list_pacing_rules(self, merchant_id: str) -> list[dict]:
        return await self._req("GET", "booking_pacing_rules", params={
            "merchant_id": f"eq.{merchant_id}",
            "active": "eq.true",
            "select": "*",
        })

    async def list_busy_blocks(self, merchant_id: str, start_iso: str, end_iso: str) -> list[dict]:
        return await self._req("GET", "booking_busy_blocks", params={
            "merchant_id": f"eq.{merchant_id}",
            "starts_at": f"lt.{end_iso}",
            "ends_at": f"gt.{start_iso}",
            "select": "*",
        })

    # ─── Bookings ─────────────────────────────────────────────

    async def list_bookings(
        self,
        merchant_id: str,
        start_iso: str,
        end_iso: str,
        *,
        live_only: bool = True,
    ) -> list[dict]:
        """Every booking OVERLAPPING the window — not merely starting inside
        it. A 3-hour detail that began before the window still occupies its
        bay during it, and omitting it would offer a slot that is not free.
        """
        params = {
            "merchant_id": f"eq.{merchant_id}",
            "starts_at": f"lt.{end_iso}",
            "ends_at": f"gt.{start_iso}",
            "select": "*",
            "order": "starts_at.asc",
        }
        if live_only:
            params["status"] = f"in.({','.join(LIVE_STATUSES)})"
        return await self._req("GET", "bookings", params=params)

    async def create_booking(self, fields: dict) -> dict:
        """Insert a booking. Raises SlotTaken if the resource was just taken."""
        rows = await self._req("POST", "bookings", json=fields, collision_aware=True)
        if not rows:
            # return=representation guarantees a row on success, so an empty
            # body here means the write did not land. Never report success.
            raise BookingStoreError("booking insert returned no row")
        return rows[0]

    async def get_booking(self, booking_id: str) -> dict | None:
        rows = await self._req("GET", "bookings", params={
            "id": f"eq.{booking_id}", "select": "*", "limit": "1",
        })
        return rows[0] if rows else None

    async def find_by_code(self, merchant_id: str, code: str) -> dict | None:
        """Look a booking up by the code the caller reads back."""
        rows = await self._req("GET", "bookings", params={
            "merchant_id": f"eq.{merchant_id}",
            "confirmation_code": f"ilike.{code.strip()}",
            "status": f"in.({','.join(LIVE_STATUSES)})",
            "select": "*",
            "limit": "1",
        })
        return rows[0] if rows else None

    async def find_upcoming_by_phone(self, merchant_id: str, phone: str) -> list[dict]:
        """Live bookings from now on for a caller — how the agent finds
        "my appointment" when they cannot remember the code."""
        return await self._req("GET", "bookings", params={
            "merchant_id": f"eq.{merchant_id}",
            "customer_phone": f"eq.{phone}",
            "status": f"in.({','.join(LIVE_STATUSES)})",
            "starts_at": f"gte.{_now_iso()}",
            "select": "*",
            "order": "starts_at.asc",
            "limit": "5",
        })

    async def update_booking(self, booking_id: str, fields: dict) -> dict:
        """Patch a booking. Collision-aware because moving a booking's time
        re-enters the exclusion constraint exactly as an insert does."""
        fields = {**fields, "updated_at": _now_iso()}
        rows = await self._req(
            "PATCH", "bookings",
            params={"id": f"eq.{booking_id}"}, json=fields,
            collision_aware=True,
        )
        return rows[0] if rows else {}

    async def cancel_booking(self, booking_id: str, reason: str = "") -> dict:
        return await self.update_booking(booking_id, {
            "status": "cancelled",
            "cancelled_at": _now_iso(),
            "cancel_reason": (reason or "")[:500] or None,
        })

    # ─── Reminders (the Celery sweep) ─────────────────────────

    async def due_for_reminder(self, window_start_iso: str, window_end_iso: str,
                               column: str) -> list[dict]:
        """Confirmed bookings starting inside the window that have not yet had
        this reminder sent. `column` is reminder_24h_sent_at or
        reminder_2h_sent_at — the send marker is what makes the sweep
        idempotent, so a beat that fires twice does not text twice.
        """
        if column not in ("reminder_24h_sent_at", "reminder_2h_sent_at"):
            raise ValueError(f"unknown reminder column {column!r}")
        # Two bounds on one column cannot be two dict keys, so they go through
        # PostgREST's and=(...) form instead of a duplicated starts_at param.
        return await self._req("GET", "bookings", params={
            "status": "eq.confirmed",
            "and": f"(starts_at.gte.{window_start_iso},starts_at.lte.{window_end_iso})",
            column: "is.null",
            "select": "*",
            "limit": "500",
        })

    async def mark_reminder_sent(self, booking_id: str, column: str) -> None:
        if column not in ("reminder_24h_sent_at", "reminder_2h_sent_at"):
            raise ValueError(f"unknown reminder column {column!r}")
        await self._req("PATCH", "bookings", params={"id": f"eq.{booking_id}"},
                        json={column: _now_iso()})

    # ─── Provider connections ─────────────────────────────────

    async def list_connections(self, merchant_id: str) -> list[dict]:
        return await self._req("GET", "booking_provider_connections", params={
            "merchant_id": f"eq.{merchant_id}", "select": "*",
        })

    async def get_connection(self, merchant_id: str, provider: str) -> dict | None:
        rows = await self._req("GET", "booking_provider_connections", params={
            "merchant_id": f"eq.{merchant_id}",
            "provider": f"eq.{provider}",
            "select": "*", "limit": "1",
        })
        return rows[0] if rows else None

    async def upsert_connection(self, fields: dict) -> dict:
        rows = await self._req(
            "POST", "booking_provider_connections",
            params={"on_conflict": "merchant_id,provider"},
            json={**fields, "updated_at": _now_iso()},
            # Without resolution=merge-duplicates PostgREST treats the unique
            # index as a plain conflict and 409s instead of updating.
            prefer="return=representation,resolution=merge-duplicates",
        )
        return rows[0] if rows else {}

    async def replace_busy_blocks(self, connection_id: str, rows: list[dict]) -> int:
        """Delete-and-replace everything this connection owns.

        Safe precisely because synced blocks live in their own table: a resync
        can never touch booking_closures, which the merchant typed in by hand.
        """
        await self._req("DELETE", "booking_busy_blocks",
                        params={"connection_id": f"eq.{connection_id}"})
        if not rows:
            return 0
        inserted = await self._req("POST", "booking_busy_blocks", json=rows)
        return len(inserted)


_store: BookingStore | None = None


def get_booking_store() -> BookingStore:
    global _store
    if _store is None:
        _store = BookingStore()
    return _store
