"""Google Calendar — the highest-coverage booking integration available.

WHY THIS ONE FIRST. Research (2026-08-14) put it ahead of every vertical
booking API for reasons that are structural rather than incidental:

  * It is the only substrate the long tail actually has. The auto detailers
    the Canada team asked about have NO integrable booking software — Urable
    and Mobile Tech RX run no developer programme — and a large share of
    independent barbershops run a phone and a calendar. Google Calendar is
    what those businesses already use.
  * The OAuth scope is "sensitive", not "restricted". Calendar is absent from
    Google's restricted list (Gmail, Drive, Fit, Chat, Data Portability,
    Photos, Health), so this needs brand verification but NOT the annual CASA
    third-party security assessment that prices small platforms out.
  * The API is free to 1M requests/day, and it does all three things we need:
    freebusy.query to read, events.insert to write, and events.watch for push
    notification instead of polling.
  * It is the back door into tools whose own APIs are closed. A merchant on a
    salon platform that syncs to Google Calendar becomes reachable through
    Google even though the vendor publishes nothing.

WHAT IS NOT DONE HERE. This module speaks the API correctly, but a live
connection needs a Google Cloud OAuth client (GOOGLE_CLIENT_ID /
GOOGLE_CLIENT_SECRET) and a verified consent screen, which is an account
action nobody can take from code. Until those exist, is_configured() is False
and the portal must not offer the connection — offering a button that cannot
work is worse than not showing it.

Refresh tokens are stored AES-GCM encrypted via src/security/encryption.py.
A Google refresh token is a long-lived key to a merchant's whole calendar;
it never touches the database in plaintext.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from .base import BusyBlock, Capabilities, ProviderError, ProviderRef

logger = logging.getLogger("meridian.booking.providers.google")

_TOKEN_URL = "https://oauth2.googleapis.com/token"
_API = "https://www.googleapis.com/calendar/v3"

# Read+write on the merchant's own calendars. Deliberately NOT
# calendar.readonly: pushing our bookings back is half the value.
SCOPES = ("https://www.googleapis.com/auth/calendar.events",
          "https://www.googleapis.com/auth/calendar.readonly")


def client_credentials() -> tuple[str, str]:
    return (os.getenv("GOOGLE_CLIENT_ID", "").strip(),
            os.getenv("GOOGLE_CLIENT_SECRET", "").strip())


def is_configured() -> bool:
    """True only when a real OAuth client exists to authenticate against."""
    cid, secret = client_credentials()
    return bool(cid and secret)


class GoogleCalendarProvider:
    key = "google_calendar"
    label = "Google Calendar"
    capabilities = Capabilities(
        read_busy=True,
        write_booking=True,
        cancel_booking=True,
        webhooks=True,
        self_serve=True,
        summary=(
            "Two-way. We read your calendar so we never book over it, and "
            "every booking we take appears on it straight away."
        ),
    )

    # ─── auth ─────────────────────────────────────────────────

    async def _access_token(self, connection: dict) -> str:
        """A fresh access token, minted from the stored refresh token.

        Access tokens last an hour and connections are used sporadically, so
        there is nothing to gain from caching one here — the refresh call is
        cheap and always-refresh removes a whole class of expiry bug.
        """
        from src.security.encryption import decrypt_token

        cid, secret = client_credentials()
        if not (cid and secret):
            raise ProviderError("Google OAuth client is not configured")

        stored = connection.get("credentials_encrypted") or ""
        if not stored:
            raise ProviderError("no stored Google credentials")
        try:
            refresh_token = decrypt_token(stored)
        except Exception as e:  # noqa: BLE001
            raise ProviderError("stored Google credentials could not be read") from e

        import httpx
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(_TOKEN_URL, data={
                    "client_id": cid,
                    "client_secret": secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                })
        except Exception as e:  # noqa: BLE001
            raise ProviderError(f"could not reach Google: {e}") from e

        if resp.status_code != 200:
            # A revoked grant is permanent: the merchant removed our access in
            # their Google account and the only fix is reconnecting. Saying so
            # precisely is what lets the portal show the right message instead
            # of retrying forever.
            body = resp.text[:300]
            if "invalid_grant" in body:
                raise ProviderError("google_reauth_required")
            raise ProviderError(f"Google token refresh failed: {resp.status_code} {body}")
        return resp.json().get("access_token", "")

    def _calendar_id(self, connection: dict) -> str:
        return ((connection.get("config") or {}).get("calendar_id") or "primary")

    # ─── read ─────────────────────────────────────────────────

    async def fetch_busy(self, connection: dict, start: datetime,
                         end: datetime) -> list[BusyBlock]:
        """Busy spans via freebusy.query.

        freebusy rather than events.list on purpose: it returns only occupied
        intervals, it expands recurring events for us (the thing our .ics
        reader deliberately refuses to do), and it never hands back the
        merchant's event titles — we do not need to know that Tuesday 3pm is a
        dentist appointment, only that it is taken.
        """
        token = await self._access_token(connection)
        calendar_id = self._calendar_id(connection)

        import httpx
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(
                    f"{_API}/freeBusy",
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "timeMin": start.astimezone(timezone.utc).isoformat(),
                        "timeMax": end.astimezone(timezone.utc).isoformat(),
                        "items": [{"id": calendar_id}],
                    },
                )
        except Exception as e:  # noqa: BLE001
            raise ProviderError(f"could not reach Google Calendar: {e}") from e

        if resp.status_code != 200:
            raise ProviderError(f"freebusy failed: {resp.status_code} {resp.text[:200]}")

        payload = resp.json() or {}
        cal = (payload.get("calendars") or {}).get(calendar_id) or {}
        if cal.get("errors"):
            raise ProviderError(f"freebusy error: {cal['errors']}")

        blocks: list[BusyBlock] = []
        for i, span in enumerate(cal.get("busy") or []):
            s = _parse_rfc3339(span.get("start"))
            e = _parse_rfc3339(span.get("end"))
            if not s or not e or e <= s:
                continue
            # freebusy carries no per-span id, so the external_id must be
            # derived from the span itself — stable across resyncs, which is
            # what the (connection_id, external_id) uniqueness needs.
            blocks.append(BusyBlock(
                starts_at=s, ends_at=e,
                external_id=f"fb:{s.isoformat()}:{e.isoformat()}",
                summary="",
            ))
        return blocks

    # ─── write ────────────────────────────────────────────────

    async def push_booking(self, connection: dict, booking: dict) -> ProviderRef | None:
        """Put one of our bookings on the merchant's calendar."""
        token = await self._access_token(connection)
        calendar_id = self._calendar_id(connection)

        party = int(booking.get("party_size") or 1)
        who = booking.get("customer_name") or "Booking"
        title = f"{who}" + (f" (party of {party})" if party > 1 else "")
        phone = booking.get("customer_phone") or ""
        code = booking.get("confirmation_code") or ""

        body = {
            "summary": title,
            "description": "\n".join(filter(None, [
                "Booked by the Meridian phone agent.",
                f"Phone: {phone}" if phone else "",
                f"Confirmation: {code}" if code else "",
                (booking.get("notes") or ""),
            ])),
            "start": {"dateTime": booking.get("starts_at")},
            "end": {"dateTime": booking.get("ends_at")},
            # Our own id, so a resync can recognise events we created and
            # never import our own bookings back as busy time.
            "extendedProperties": {
                "private": {"meridian_booking_id": str(booking.get("id") or "")}
            },
        }

        import httpx
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(
                    f"{_API}/calendars/{calendar_id}/events",
                    headers={"Authorization": f"Bearer {token}"},
                    json=body,
                )
        except Exception as e:  # noqa: BLE001
            raise ProviderError(f"could not reach Google Calendar: {e}") from e

        if resp.status_code not in (200, 201):
            raise ProviderError(f"event insert failed: {resp.status_code} {resp.text[:200]}")
        created = resp.json() or {}
        return ProviderRef(provider_booking_id=str(created.get("id") or ""), raw=created)

    async def cancel_booking(self, connection: dict, provider_booking_id: str) -> bool:
        if not provider_booking_id:
            return False
        token = await self._access_token(connection)
        calendar_id = self._calendar_id(connection)

        import httpx
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.delete(
                    f"{_API}/calendars/{calendar_id}/events/{provider_booking_id}",
                    headers={"Authorization": f"Bearer {token}"},
                )
        except Exception as e:  # noqa: BLE001
            raise ProviderError(f"could not reach Google Calendar: {e}") from e
        # 410 means it is already gone, which is the outcome we wanted.
        return resp.status_code in (200, 204, 404, 410)


def _parse_rfc3339(value: str | None) -> datetime | None:
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
