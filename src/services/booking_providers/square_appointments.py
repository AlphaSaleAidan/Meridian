"""Square Appointments — the one vertical booking API a small platform can get.

Square is the only major booking system in this space with a self-serve API:
no partner agreement, no sales call, per-merchant OAuth we already run for POS.
That makes it the highest-value vertical integration available to us, and the
only one where a barbershop already living in Square keeps its existing system
of record while our phone agent books into it.

TWO ACCESS LEVELS, AND THE DIFFERENCE DECIDES WHAT A MERCHANT CAN HAVE
----------------------------------------------------------------------
Square splits the Bookings API in two, and this is the single most important
fact about integrating it:

  BUYER-LEVEL   APPOINTMENTS_READ + APPOINTMENTS_WRITE
                Works on EVERY Square Appointments plan, including the free
                one. Grants SearchAvailability, CreateBooking, CancelBooking —
                i.e. the entire booking loop. It is the same access Square's
                own public booking page uses.

  SELLER-LEVEL  APPOINTMENTS_ALL_READ + APPOINTMENTS_ALL_WRITE
                Requires the merchant to pay for Appointments PLUS or PREMIUM.
                Adds reading bookings the merchant took elsewhere, which is
                what makes busy-import possible.

So the honest product statement is not "Square booking needs a paid plan". A
free-plan barbershop can have the whole thing — the agent checks Square's real
availability and writes a real Square booking. What the paid plan adds is our
ability to SEE their other bookings, which only matters when we are also
running our own calendar alongside. `detect_access_level()` probes this and
the portal tells the merchant the truth either way.

SCOPES ARE REQUESTED SEPARATELY FROM THE POS CONNECTION, ON PURPOSE
-------------------------------------------------------------------
src/config.py:232 declares the POS scopes read-only with the comment "never
write to merchant POS", and that is a promise worth keeping. Booking write
access is a different decision by the merchant, so it gets its own
authorization and its own row in booking_provider_connections. A merchant who
wants analytics but not booking is never asked to grant write.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone

from .base import BusyBlock, Capabilities, ProviderError, ProviderRef

logger = logging.getLogger("meridian.booking.providers.square")

# Pinned separately from src/square/client.py (2025-04-16) so the analytics
# client's contract is never disturbed by a booking-driven bump. Verified
# current against Square's changelog 2026-08-15.
SQUARE_VERSION = "2026-07-15"

BUYER_SCOPES = ("APPOINTMENTS_READ", "APPOINTMENTS_WRITE")
SELLER_SCOPES = ("APPOINTMENTS_ALL_READ", "APPOINTMENTS_ALL_WRITE")
# Reading the merchant's service catalogue and staff list, which we need to map
# our services onto theirs. Both are read-only.
SUPPORT_SCOPES = ("ITEMS_READ", "MERCHANT_PROFILE_READ")

ALL_BOOKING_SCOPES = BUYER_SCOPES + SELLER_SCOPES + SUPPORT_SCOPES

# Square rejects an availability query wider than 32 days.
MAX_AVAILABILITY_DAYS = 31


def _base_url(environment: str = "production") -> str:
    return ("https://connect.squareup.com" if environment == "production"
            else "https://connect.squareupsandbox.com")


class SquareAppointmentsProvider:
    key = "square_appointments"
    label = "Square Appointments"
    capabilities = Capabilities(
        read_busy=True,          # seller-level only; degraded at runtime
        write_booking=True,
        cancel_booking=True,
        webhooks=True,
        self_serve=True,
        summary=(
            "Two-way with Square Appointments. The phone agent checks your real "
            "Square availability and writes real Square bookings, so your staff "
            "see them in the app they already use."
        ),
    )

    # ─── credentials ──────────────────────────────────────────

    def _credentials(self, connection: dict) -> dict:
        from src.security.encryption import decrypt_token

        blob = connection.get("credentials_encrypted") or ""
        if not blob:
            raise ProviderError("no stored Square credentials")
        try:
            return json.loads(decrypt_token(blob))
        except Exception as e:  # noqa: BLE001
            raise ProviderError("stored Square credentials could not be read") from e

    async def _token(self, connection: dict) -> str:
        """A usable access token, refreshed when it is close to expiry.

        Square access tokens last 30 days and the refresh token rotates on
        every exchange, so a refresh MUST persist the new pair or the next
        refresh fails permanently. That persistence is why this returns
        through _store_refreshed rather than just handing back a string.
        """
        creds = self._credentials(connection)
        expires_at = _parse_ts(creds.get("expires_at"))
        if expires_at and expires_at - datetime.now(timezone.utc) < timedelta(days=3):
            refreshed = await self._refresh(connection, creds)
            if refreshed:
                return refreshed
        token = creds.get("access_token") or ""
        if not token:
            raise ProviderError("square_reauth_required")
        return token

    async def _refresh(self, connection: dict, creds: dict) -> str | None:
        from src.config import square as sq_config

        refresh_token = creds.get("refresh_token") or ""
        if not (refresh_token and sq_config.app_id and sq_config.app_secret):
            return None

        import httpx
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(
                    f"{_base_url(sq_config.environment)}/oauth2/token",
                    headers={"Square-Version": SQUARE_VERSION},
                    json={
                        "client_id": sq_config.app_id,
                        "client_secret": sq_config.app_secret,
                        "refresh_token": refresh_token,
                        "grant_type": "refresh_token",
                    },
                )
        except Exception as e:  # noqa: BLE001
            logger.warning("square token refresh unreachable: %s", e)
            return None

        if resp.status_code != 200:
            # A revoked authorization cannot be retried out of — the merchant
            # must reconnect, and saying so precisely is what lets the portal
            # show that instead of a spinner forever.
            logger.warning("square token refresh failed: %s %s",
                           resp.status_code, resp.text[:200])
            raise ProviderError("square_reauth_required")

        data = resp.json()
        merged = {
            **creds,
            "access_token": data.get("access_token", ""),
            "refresh_token": data.get("refresh_token", refresh_token),
            "expires_at": data.get("expires_at", ""),
        }
        await _store_credentials(connection, merged)
        return merged["access_token"]

    async def _call(self, connection: dict, method: str, path: str,
                    json_body: dict | None = None,
                    params: dict | None = None) -> dict:
        from src.config import square as sq_config

        token = await self._token(connection)
        import httpx
        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                resp = await client.request(
                    method,
                    f"{_base_url(sq_config.environment)}{path}",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Square-Version": SQUARE_VERSION,
                        "Content-Type": "application/json",
                    },
                    json=json_body,
                    params=params,
                )
        except Exception as e:  # noqa: BLE001
            raise ProviderError(f"could not reach Square: {e}") from e

        if resp.status_code == 401:
            raise ProviderError("square_reauth_required")
        if resp.status_code == 403:
            # The documented signal that this merchant is on the free plan and
            # we asked for something seller-level. Distinct from a real error:
            # the caller degrades instead of alarming the merchant.
            raise ProviderError("square_plan_required")
        if resp.status_code not in (200, 201):
            detail = _first_error(resp)
            raise ProviderError(f"Square {resp.status_code}: {detail}")
        return resp.json() or {}

    # ─── discovery ────────────────────────────────────────────

    async def detect_access_level(self, connection: dict) -> str:
        """'seller' when the merchant pays for Appointments Plus/Premium.

        Probed rather than assumed, because it decides what we can promise. A
        one-row ListBookings is the cheapest seller-level call there is.
        """
        try:
            await self._call(connection, "GET", "/v2/bookings",
                             params={"limit": 1})
            return "seller"
        except ProviderError as e:
            if "square_plan_required" in str(e):
                return "buyer"
            raise

    async def business_profile(self, connection: dict) -> dict:
        data = await self._call(
            connection, "GET", "/v2/bookings/business-booking-profile")
        return data.get("business_booking_profile") or {}

    async def list_team_members(self, connection: dict) -> list[dict]:
        """Bookable staff — these map onto our resources."""
        data = await self._call(
            connection, "GET", "/v2/bookings/team-member-booking-profiles",
            params={"bookable_only": "true", "limit": 100},
        )
        return [
            {
                "team_member_id": p.get("team_member_id"),
                "display_name": p.get("display_name") or "",
                "is_bookable": bool(p.get("is_bookable")),
            }
            for p in (data.get("team_member_booking_profiles") or [])
        ]

    async def list_services(self, connection: dict) -> list[dict]:
        """Bookable services — these map onto our services.

        service_variation_version is carried because CreateBooking REQUIRES it
        and Square rejects a stale one, so it has to travel with the id rather
        than be looked up later from a cached mapping.
        """
        data = await self._call(
            connection, "POST", "/v2/catalog/search",
            json_body={
                "object_types": ["ITEM"],
                "query": {
                    "exact_query": {
                        "attribute_name": "product_type",
                        "attribute_value": "APPOINTMENTS_SERVICE",
                    }
                },
                "limit": 200,
            },
        )
        out: list[dict] = []
        for item in data.get("objects") or []:
            item_data = item.get("item_data") or {}
            name = item_data.get("name") or ""
            for variation in item_data.get("variations") or []:
                vdata = variation.get("item_variation_data") or {}
                duration_ms = vdata.get("service_duration") or 0
                out.append({
                    "service_variation_id": variation.get("id"),
                    "service_variation_version": variation.get("version"),
                    "name": f"{name} — {vdata.get('name')}" if vdata.get("name") else name,
                    "duration_minutes": int(duration_ms // 60000) if duration_ms else None,
                    "team_member_ids": vdata.get("team_member_ids") or [],
                })
        return out

    # ─── availability ─────────────────────────────────────────

    async def search_availability(self, connection: dict, start: datetime,
                                  end: datetime, *,
                                  service_variation_id: str,
                                  team_member_ids: list[str] | None = None) -> list[dict]:
        """Square's own free slots. Works at buyer level, so every plan."""
        config = connection.get("config") or {}
        location_id = config.get("location_id")
        if not location_id:
            raise ProviderError("no Square location configured")

        span = end - start
        if span > timedelta(days=MAX_AVAILABILITY_DAYS):
            end = start + timedelta(days=MAX_AVAILABILITY_DAYS)

        segment: dict = {"service_variation_id": service_variation_id}
        if team_member_ids:
            segment["team_member_id_filter"] = {"any": team_member_ids}

        data = await self._call(
            connection, "POST", "/v2/bookings/availability/search",
            json_body={
                "query": {
                    "filter": {
                        "start_at_range": {
                            "start_at": start.astimezone(timezone.utc).isoformat(),
                            "end_at": end.astimezone(timezone.utc).isoformat(),
                        },
                        "location_id": location_id,
                        "segment_filters": [segment],
                    }
                }
            },
        )
        out = []
        for a in data.get("availabilities") or []:
            starts_at = _parse_ts(a.get("start_at"))
            if not starts_at:
                continue
            segments = a.get("appointment_segments") or []
            out.append({
                "starts_at": starts_at,
                "team_member_id": (segments[0] or {}).get("team_member_id") if segments else None,
                "duration_minutes": (segments[0] or {}).get("duration_minutes") if segments else None,
            })
        return out

    async def fetch_busy(self, connection: dict, start: datetime,
                         end: datetime) -> list[BusyBlock]:
        """Existing Square bookings as busy time. SELLER-LEVEL ONLY.

        Returns [] rather than raising on a free-plan merchant: not being able
        to read their other bookings is a known limitation of their plan, not a
        fault, and alarming them about it every 20 minutes would be noise.
        """
        config = connection.get("config") or {}
        params = {
            "start_at_min": start.astimezone(timezone.utc).isoformat(),
            "start_at_max": end.astimezone(timezone.utc).isoformat(),
            "limit": 200,
        }
        if config.get("location_id"):
            params["location_id"] = config["location_id"]

        blocks: list[BusyBlock] = []
        cursor: str | None = None
        for _ in range(10):  # bounded: 2,000 bookings is far past any real window
            if cursor:
                params["cursor"] = cursor
            try:
                data = await self._call(connection, "GET", "/v2/bookings", params=params)
            except ProviderError as e:
                if "square_plan_required" in str(e):
                    logger.info("square busy import skipped — buyer-level plan")
                    return []
                raise

            for booking in data.get("bookings") or []:
                block = _booking_to_block(booking)
                if block:
                    blocks.append(block)

            cursor = data.get("cursor")
            if not cursor:
                break
        return blocks

    # ─── write ────────────────────────────────────────────────

    async def push_booking(self, connection: dict, booking: dict) -> ProviderRef | None:
        """Create a real Square booking.

        Square requires a service_variation_id, its exact version, and a
        team_member_id — there is no "just block this time" call. Those come
        from the mapping the merchant confirmed at connect time; without one we
        return None rather than guessing, because guessing writes a booking for
        the wrong service onto the wrong person's day.
        """
        config = connection.get("config") or {}
        location_id = config.get("location_id")
        mapping = _mapping_for(config, booking)
        if not (location_id and mapping):
            logger.info("square push skipped — no service mapping for booking %s",
                        booking.get("id"))
            return None

        segment = {
            "team_member_id": mapping["team_member_id"],
            "service_variation_id": mapping["service_variation_id"],
            "service_variation_version": mapping["service_variation_version"],
        }
        if booking.get("duration_minutes"):
            segment["duration_minutes"] = int(booking["duration_minutes"])

        note_bits = [
            f"Booked by the Meridian phone agent for {booking.get('customer_name') or 'a caller'}.",
            f"Phone: {booking.get('customer_phone')}" if booking.get("customer_phone") else "",
            f"Confirmation: {booking.get('confirmation_code')}" if booking.get("confirmation_code") else "",
        ]

        data = await self._call(
            connection, "POST", "/v2/bookings",
            json_body={
                # Our booking id as the idempotency key: a retried push can
                # never create a second Square booking for the same row.
                "idempotency_key": str(booking.get("id") or uuid.uuid4())[:255],
                "booking": {
                    "location_id": location_id,
                    "start_at": booking.get("starts_at"),
                    "customer_note": (booking.get("notes") or "")[:4096] or None,
                    "seller_note": " ".join(b for b in note_bits if b)[:4096],
                    "appointment_segments": [segment],
                },
            },
        )
        created = data.get("booking") or {}
        booking_id = created.get("id")
        if not booking_id:
            return None
        return ProviderRef(provider_booking_id=booking_id, raw=created)

    async def cancel_booking(self, connection: dict, provider_booking_id: str) -> bool:
        """Cancel on Square's side.

        Square uses optimistic concurrency, so the current version has to be
        read immediately before the cancel; sending a stale version is refused.
        """
        if not provider_booking_id:
            return False
        try:
            current = await self._call(
                connection, "GET", f"/v2/bookings/{provider_booking_id}")
        except ProviderError as e:
            # Already gone is the outcome we wanted.
            if "404" in str(e):
                return True
            raise

        version = (current.get("booking") or {}).get("version")
        await self._call(
            connection, "POST", f"/v2/bookings/{provider_booking_id}/cancel",
            json_body={
                "idempotency_key": f"cancel-{provider_booking_id}"[:255],
                "booking_version": version,
            },
        )
        return True


# ─── helpers ──────────────────────────────────────────────────

def _mapping_for(config: dict, booking: dict) -> dict | None:
    """Resolve our service/resource onto Square's ids.

    Falls back to the connection's default mapping so a merchant with one
    service (the common barbershop case) never has to map anything.
    """
    mappings = config.get("service_map") or {}
    entry = mappings.get(str(booking.get("service_id") or "")) or config.get("default_service")
    if not entry:
        return None
    team_member_id = (
        (config.get("resource_map") or {}).get(str(booking.get("resource_id") or ""))
        or entry.get("team_member_id")
    )
    if not (entry.get("service_variation_id") and team_member_id):
        return None
    return {
        "service_variation_id": entry["service_variation_id"],
        "service_variation_version": entry.get("service_variation_version"),
        "team_member_id": team_member_id,
    }


def _booking_to_block(booking: dict) -> BusyBlock | None:
    status = (booking.get("status") or "").upper()
    # Square's terminal states free the slot; treating them as busy would hide
    # availability the merchant actually has.
    if status in ("CANCELLED_BY_CUSTOMER", "CANCELLED_BY_SELLER", "DECLINED", "NO_SHOW"):
        return None

    start = _parse_ts(booking.get("start_at"))
    if not start:
        return None

    minutes = 0
    for segment in booking.get("appointment_segments") or []:
        minutes += int(segment.get("duration_minutes") or 0)
    minutes += int(booking.get("transition_time_minutes") or 0)
    if minutes <= 0:
        minutes = 60

    booking_id = booking.get("id") or ""
    return BusyBlock(
        starts_at=start,
        ends_at=start + timedelta(minutes=minutes),
        external_id=f"sq:{booking_id}",
        summary="Square booking",
        resource_hint=_first_team_member(booking),
    )


def _first_team_member(booking: dict) -> str:
    for segment in booking.get("appointment_segments") or []:
        if segment.get("team_member_id"):
            return str(segment["team_member_id"])
    return ""


def _first_error(resp) -> str:
    try:
        errors = (resp.json() or {}).get("errors") or []
        if errors:
            e = errors[0]
            return f"{e.get('code')}: {e.get('detail')}"
    except Exception:  # noqa: BLE001
        pass
    return resp.text[:200]


def _parse_ts(value) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not value:
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


async def _store_credentials(connection: dict, creds: dict) -> None:
    """Persist a rotated token pair. Square rotates the refresh token on every
    exchange, so losing this write bricks the connection at the next refresh."""
    from src.db import get_db
    from src.security.encryption import encrypt_token

    try:
        await get_db().update(
            "booking_provider_connections",
            {"credentials_encrypted": encrypt_token(json.dumps(creds)),
             "updated_at": datetime.now(timezone.utc).isoformat()},
            {"id": f"eq.{connection['id']}"},
        )
        connection["credentials_encrypted"] = encrypt_token(json.dumps(creds))
    except Exception as e:  # noqa: BLE001
        logger.error("could not persist refreshed Square credentials: %s", e)
        raise ProviderError("could not persist refreshed Square credentials") from e
