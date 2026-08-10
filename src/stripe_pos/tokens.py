"""
Stripe Apps OAuth token lifecycle for the POS connector.

App access tokens live 1 hour. Refresh tokens live 1 year and ROLL on every
exchange — Stripe invalidates the old refresh token the moment a new one is
issued, so the rolled token MUST be persisted back to pos_connections or the
connection dies at the next refresh.

Auth on /v1/oauth/token is the app developer account's secret key as the
HTTP-basic username (STRIPE_POS_CLIENT_SECRET — same env the pos_connect
registry entry reads).
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from ..security.encryption import decrypt_token, encrypt_token
from .client import StripePOSAPIError

logger = logging.getLogger("meridian.stripe_pos.tokens")

_TOKEN_URL = "https://api.stripe.com/v1/oauth/token"
# Refresh when the stored token is this close to expiry — a backfill can run
# long, so leave real headroom rather than racing the deadline.
_REFRESH_SKEW = timedelta(minutes=10)
_DEFAULT_TTL_SECONDS = 3600  # Stripe fixes app tokens at 1h; not echoed in the response


def _parse_ts(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


async def _exchange_refresh_token(refresh_token: str, secret_key: str) -> dict[str, Any]:
    """One refresh_token grant against /v1/oauth/token. Split out so tests can
    monkeypatch the network hop."""
    async with httpx.AsyncClient(timeout=30.0) as http:
        resp = await http.post(
            _TOKEN_URL,
            data={"grant_type": "refresh_token", "refresh_token": refresh_token},
            auth=(secret_key, ""),
            headers={"Accept": "application/json"},
        )
    if resp.status_code != 200:
        try:
            message = resp.json().get("error", {}).get("message", "")
        except Exception:
            message = resp.text[:200]
        # 400/401 here means the grant itself is dead (expired/revoked rolled
        # token) — surface as 401 so pos_sync_runner flips the connection to
        # reconnect instead of retrying forever.
        status = 401 if resp.status_code in (400, 401, 403) else resp.status_code
        raise StripePOSAPIError(status, message or "refresh token exchange failed")
    return resp.json()


async def ensure_fresh_access_token(connection: dict) -> str:
    """Return a currently-valid access token for an app-OAuth connection,
    refreshing (and persisting the ROLLED refresh token) when needed.

    Mutates `connection` in place so a caller holding the dict reuses the
    fresh values within the same sweep.
    """
    access = decrypt_token(connection.get("access_token_enc", "") or "")
    expires_at = _parse_ts(connection.get("token_expires_at"))
    if access and expires_at and datetime.now(timezone.utc) + _REFRESH_SKEW < expires_at:
        return access

    refresh = decrypt_token(connection.get("refresh_token_enc", "") or "")
    if not refresh:
        raise StripePOSAPIError(401, "no refresh token stored — merchant must reconnect")
    secret_key = os.environ.get("STRIPE_POS_CLIENT_SECRET", "")
    if not secret_key:
        raise StripePOSAPIError(401, "STRIPE_POS_CLIENT_SECRET unset — cannot refresh")

    body = await _exchange_refresh_token(refresh, secret_key)
    new_access = body["access_token"]
    new_refresh = body.get("refresh_token", "") or refresh
    ttl = int(body.get("expires_in") or _DEFAULT_TTL_SECONDS)
    new_expiry = (datetime.now(timezone.utc) + timedelta(seconds=ttl)).strftime(
        "%Y-%m-%dT%H:%M:%SZ")

    fields = {
        "access_token_enc": encrypt_token(new_access),
        "refresh_token_enc": encrypt_token(new_refresh),
        "token_expires_at": new_expiry,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    connection.update(fields)

    conn_id = connection.get("id", "")
    persisted = False
    try:
        from ..db import _db_instance
        if _db_instance and conn_id:
            await _db_instance.update("pos_connections", fields,
                                      filters={"id": f"eq.{conn_id}"})
            persisted = True
    except Exception as e:
        logger.error("failed persisting rolled Stripe refresh token for %s: %s",
                     conn_id, e)
    if not persisted:
        # The old refresh token is already invalid — without the DB write this
        # connection survives only until the new access token expires.
        logger.error("rolled Stripe refresh token NOT persisted (conn=%s) — "
                     "connection will require reconnect within ~1h", conn_id or "?")
    return new_access
