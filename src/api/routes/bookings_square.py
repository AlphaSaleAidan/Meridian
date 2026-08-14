"""Square Appointments connect flow — its own OAuth, separate from POS.

Deliberately NOT folded into the existing Square POS connection. src/config.py
declares the POS scopes read-only with the comment "never write to merchant
POS", and that promise is worth keeping intact: a merchant who wants revenue
analytics should never be asked to grant booking-write as a side effect. So
booking gets its own authorization, its own consent screen, and its own row in
booking_provider_connections.

The callback is browser-redirect and therefore unauthenticated by necessity —
there is no session on the way back from Square. It is protected by an
HMAC-signed, expiring `state` (src/pos_connect/oauth.sign_state) that carries
the merchant id, exactly as every other OAuth callback in this codebase does,
and it is listed in the CC6.6 public-endpoint baseline under `oauth`.
"""
from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from src.services.booking_providers.square_appointments import (
    ALL_BOOKING_SCOPES,
    SquareAppointmentsProvider,
)
from src.services.booking_store import get_booking_store

from ...pos_connect.oauth import sign_state, verify_state
from ...security.encryption import encrypt_token
from ..auth import enforce_service_member, require_service_auth

logger = logging.getLogger("meridian.api.bookings.square")
router = APIRouter(prefix="/api/bookings/square", tags=["bookings"])

_MERCHANT_ID_RE = re.compile(r"^[A-Za-z0-9_\-]{1,64}$")
_PROVIDER = "square_appointments"


def _frontend() -> str:
    return os.environ.get(
        "FRONTEND_URL", os.environ.get("FRONTEND_ORIGIN", "https://meridian.tips")
    ).rstrip("/")


def _redirect_uri(request: Request) -> str:
    base = os.environ.get("API_PUBLIC_URL") or str(request.base_url).rstrip("/")
    return f"{base}/api/bookings/square/callback"


@router.get("/authorize")
async def authorize(request: Request, merchant_id: str,
                    return_to: str = "/canada/merchant/bookings?view=setup",
                    principal=Depends(require_service_auth)):
    """Start the booking-specific Square authorization."""
    from src.config import square as sq_config

    if not _MERCHANT_ID_RE.match(merchant_id or ""):
        raise HTTPException(400, "Invalid merchant_id format")
    await enforce_service_member(principal, merchant_id)

    if not (sq_config.app_id and sq_config.app_secret):
        raise HTTPException(503, "Square app is not configured on this server")

    state = sign_state(_PROVIDER, merchant_id, return_to)
    params = {
        "client_id": sq_config.app_id,
        "scope": " ".join(ALL_BOOKING_SCOPES),
        # Seller-level scopes are requested up front. Square grants only what
        # the merchant's plan supports, so asking is free — and asking later
        # would mean a second consent screen the day they upgrade.
        "session": "false",
        "state": state,
        "redirect_uri": _redirect_uri(request),
    }
    url = f"{sq_config.oauth_authorize_url}?{urlencode(params)}"
    return {"authorize_url": url}


@router.get("/callback")
async def callback(request: Request, code: str = "", state: str = "",
                   error: str = ""):
    """Square redirects the merchant's browser here. PUBLIC by necessity."""
    from src.config import square as sq_config

    verified = verify_state(state) if state else None
    if not verified or verified[0] != _PROVIDER:
        # Never proceed on an unverified state — it is the only thing binding
        # this callback to a merchant who actually asked for it.
        logger.warning("square booking callback with bad state")
        return RedirectResponse(
            f"{_frontend()}/canada/merchant/bookings?view=setup&square=invalid_state")

    _provider, merchant_id, return_to = verified
    target = f"{_frontend()}{return_to or '/canada/merchant/bookings?view=setup'}"

    if error or not code:
        return RedirectResponse(f"{target}&square=denied" if "?" in target
                                else f"{target}?square=denied")

    import httpx
    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.post(
                f"{sq_config.base_url}/oauth2/token",
                json={
                    "client_id": sq_config.app_id,
                    "client_secret": sq_config.app_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": _redirect_uri(request),
                },
            )
    except Exception as e:  # noqa: BLE001
        logger.error("square booking token exchange unreachable: %s", e)
        return RedirectResponse(_with(target, "square=error"))

    if resp.status_code != 200:
        logger.error("square booking token exchange failed: %s %s",
                     resp.status_code, resp.text[:300])
        return RedirectResponse(_with(target, "square=error"))

    data = resp.json()
    creds = {
        "access_token": data.get("access_token", ""),
        "refresh_token": data.get("refresh_token", ""),
        "expires_at": data.get("expires_at", ""),
        "merchant_id": data.get("merchant_id", ""),
    }

    store = get_booking_store()
    connection = await store.upsert_connection({
        "merchant_id": merchant_id,
        "provider": _PROVIDER,
        "status": "connected",
        "direction": "both",
        "external_account_id": creds["merchant_id"],
        "credentials_encrypted": encrypt_token(json.dumps(creds)),
        "config": {},
    })

    # Discover what this merchant can actually do, and pre-fill the mapping.
    # Doing it here rather than on first use means the portal can show the
    # truth immediately instead of "connected" followed by a silent failure.
    try:
        await _bootstrap(connection)
    except Exception as e:  # noqa: BLE001
        logger.warning("square booking bootstrap incomplete for %s: %s",
                       merchant_id, e)

    return RedirectResponse(_with(target, "square=connected"))


def _with(url: str, param: str) -> str:
    return f"{url}&{param}" if "?" in url else f"{url}?{param}"


async def _bootstrap(connection: dict) -> None:
    """Detect access level, location, staff and services; store the mapping."""
    provider = SquareAppointmentsProvider()
    store = get_booking_store()

    access_level = await provider.detect_access_level(connection)

    profile = await provider.business_profile(connection)
    booking_enabled = bool(profile.get("booking_enabled"))

    # Location comes from the seller's booking profile when present; otherwise
    # the first bookable location. A wrong location silently books into the
    # wrong shop, so it is stored explicitly rather than defaulted at call time.
    location_id = ""
    try:
        data = await provider._call(
            connection, "GET", "/v2/bookings/location-booking-profiles",
            params={"limit": 10})
        profiles = data.get("location_booking_profiles") or []
        for p in profiles:
            if p.get("booking_enabled"):
                location_id = p.get("location_id") or ""
                break
        if not location_id and profiles:
            location_id = profiles[0].get("location_id") or ""
    except Exception as e:  # noqa: BLE001
        logger.info("square location profile lookup failed: %s", e)

    team = await provider.list_team_members(connection)
    services = await provider.list_services(connection)

    config = {
        "access_level": access_level,
        "booking_enabled": booking_enabled,
        "location_id": location_id,
        "team_members": team,
        "services": services,
    }

    # One service and one bookable person is the common barbershop case, and
    # mapping it automatically is the difference between "connected" and
    # "working" for most merchants. Anything more ambiguous is left for the
    # merchant to choose — guessing writes bookings for the wrong service.
    if len(services) == 1 and len(team) == 1:
        config["default_service"] = {
            "service_variation_id": services[0]["service_variation_id"],
            "service_variation_version": services[0]["service_variation_version"],
            "team_member_id": team[0]["team_member_id"],
        }

    # PATCH, not upsert: credentials_encrypted must not be in this payload and
    # must survive it. See booking_store.update_connection.
    await store.update_connection(str(connection["id"]), {
        "status": "connected",
        "direction": "both" if access_level == "seller" else "write",
        "config": config,
    })


@router.get("/options/{merchant_id}")
async def options(merchant_id: str, principal=Depends(require_service_auth)):
    """Square's services and staff, for the mapping UI."""
    if not _MERCHANT_ID_RE.match(merchant_id or ""):
        raise HTTPException(400, "Invalid merchant_id format")
    await enforce_service_member(principal, merchant_id)

    connection = await get_booking_store().get_connection(merchant_id, _PROVIDER)
    if not connection:
        raise HTTPException(404, "Square Appointments is not connected")
    config = connection.get("config") or {}
    return {
        "access_level": config.get("access_level") or "buyer",
        "booking_enabled": config.get("booking_enabled", False),
        "location_id": config.get("location_id") or "",
        "services": config.get("services") or [],
        "team_members": config.get("team_members") or [],
        "service_map": config.get("service_map") or {},
        "resource_map": config.get("resource_map") or {},
        "default_service": config.get("default_service"),
    }


@router.post("/options/{merchant_id}")
async def save_mapping(merchant_id: str, body: dict,
                       principal=Depends(require_service_auth)):
    """Save which of our services and resources map onto Square's."""
    if not _MERCHANT_ID_RE.match(merchant_id or ""):
        raise HTTPException(400, "Invalid merchant_id format")
    await enforce_service_member(principal, merchant_id)

    store = get_booking_store()
    connection = await store.get_connection(merchant_id, _PROVIDER)
    if not connection:
        raise HTTPException(404, "Square Appointments is not connected")

    config = dict(connection.get("config") or {})
    for field in ("service_map", "resource_map", "default_service", "location_id"):
        if field in body:
            config[field] = body[field]

    await store.update_connection(str(connection["id"]), {"config": config})
    return {"saved": True, "config_keys": sorted(config.keys())}


@router.post("/refresh/{merchant_id}")
async def refresh_catalog(merchant_id: str,
                          principal=Depends(require_service_auth)):
    """Re-read Square's services and staff.

    Needed because service_variation_version changes whenever the merchant
    edits a service in Square, and CreateBooking refuses a stale version.
    """
    if not _MERCHANT_ID_RE.match(merchant_id or ""):
        raise HTTPException(400, "Invalid merchant_id format")
    await enforce_service_member(principal, merchant_id)

    connection = await get_booking_store().get_connection(merchant_id, _PROVIDER)
    if not connection:
        raise HTTPException(404, "Square Appointments is not connected")
    try:
        await _bootstrap(connection)
    except Exception as e:  # noqa: BLE001
        logger.warning("square refresh failed for %s: %s", merchant_id, e)
        raise HTTPException(502, "Could not read your Square account just now")
    return {"refreshed": True,
            "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
