"""
Stripe API client for the POS-analytics connector.

Raw httpx against api.stripe.com/v1 (no `stripe` SDK dependency — the SDK is
only installed on the payments deployables, and this read-only surface needs
exactly two endpoints).

Auth model (Stripe Connect OAuth, standard accounts): after the merchant
authorizes, API calls are made with the PLATFORM's secret key plus a
`Stripe-Account: acct_…` header — the modern documented pattern. The legacy
per-account `access_token` from the token response also works as a bare key
(no header); the sync runner falls back to it when the platform key env is
unset so a stored connection can still sync.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, AsyncIterator

import httpx

logger = logging.getLogger("meridian.stripe_pos.client")

_BASE_URL = "https://api.stripe.com/v1"
# Pin the response shape. Validated during the registry verified-flip round
# trip (docs/POS_1CLICK_ONBOARDING.md step 3) — bump deliberately, never drift.
_API_VERSION = "2026-04-22.dahlia"
_PAGE_SIZE = 100
# 18 months of a very busy merchant ≈ tens of thousands of charges; this cap
# (pages × page size = 200k charges) is a runaway guard, not a real limit.
_MAX_PAGES = 2000


class StripePOSAPIError(Exception):
    """Stripe API failure. `status_code` is read by pos_sync_runner to tell
    terminal auth failures (401/403 → flip connection to error/reconnect)
    from transient ones (keep connected, retry next sweep)."""

    def __init__(self, status_code: int, message: str):
        super().__init__(f"Stripe API {status_code}: {message}")
        self.status_code = status_code


class StripePOSClient:
    """
    Usage:
        client = StripePOSClient(api_key=platform_sk, account_id="acct_…")
        async for charge in client.iter_charges(created_gte=1710000000):
            ...
        await client.close()

    account_id="" → calls are made with the key alone (legacy per-account
    access-token fallback; no Stripe-Account header).
    """

    def __init__(self, api_key: str, account_id: str = "", timeout: float = 30.0):
        if not api_key:
            raise ValueError("StripePOSClient requires an api_key")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Stripe-Version": _API_VERSION,
            "Accept": "application/json",
        }
        if account_id:
            headers["Stripe-Account"] = account_id
        self.account_id = account_id
        self._http = httpx.AsyncClient(base_url=_BASE_URL, headers=headers, timeout=timeout)

    async def close(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> "StripePOSClient":
        return self

    async def __aexit__(self, *exc) -> None:
        await self.close()

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        # One retry on 429/5xx with a short backoff; Stripe read limits are
        # generous (100 rps live) so sustained throttling means something is
        # actually wrong and should surface.
        for attempt in (1, 2):
            resp = await self._http.get(path, params=params or {})
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code in (429, 500, 502, 503) and attempt == 1:
                await asyncio.sleep(2.0)
                continue
            # Stripe error bodies: {"error": {"message": ..., "type": ...}}
            try:
                message = resp.json().get("error", {}).get("message", "")
            except Exception:
                message = resp.text[:200]
            raise StripePOSAPIError(resp.status_code, message or "request failed")
        raise StripePOSAPIError(500, "unreachable")  # pragma: no cover

    async def get_account(self) -> dict[str, Any]:
        """The connected account itself — used as the connection health check."""
        return await self._get("/account")

    async def iter_charges(
        self,
        created_gte: int | None = None,
        created_lte: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Yield every charge in the window, newest first (Stripe's order),
        paginating via starting_after."""
        params: dict[str, Any] = {"limit": _PAGE_SIZE}
        if created_gte is not None:
            params["created[gte]"] = int(created_gte)
        if created_lte is not None:
            params["created[lte]"] = int(created_lte)

        starting_after: str | None = None
        for _page in range(_MAX_PAGES):
            page_params = dict(params)
            if starting_after:
                page_params["starting_after"] = starting_after
            body = await self._get("/charges", page_params)
            data = body.get("data", []) or []
            for charge in data:
                yield charge
            if not body.get("has_more") or not data:
                return
            starting_after = data[-1].get("id")
        logger.warning(
            "iter_charges hit the %d-page cap for account %s — window truncated",
            _MAX_PAGES, self.account_id or "(token-auth)",
        )
