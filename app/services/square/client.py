"""
Square API client — thin wrapper around httpx with:
  * Token management (per-connection access tokens)
  * Automatic retry with exponential back-off
  * Rate limiting via token-bucket
  * Structured error types
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

from .rate_limiter import SquareRateLimiter

logger = logging.getLogger("meridian.square.client")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SANDBOX_BASE = "https://connect.squareupsandbox.com"
PRODUCTION_BASE = "https://connect.squareup.com"

RETRY_STATUS_CODES = {429, 500, 502, 503, 504}
MAX_RETRIES = 5
BACKOFF_BASE = 1.0        # seconds
BACKOFF_MULTIPLIER = 2.0

# Endpoints that count against the *batch* bucket
BATCH_PATHS = {
    "/v2/catalog/search",
    "/v2/catalog/batch-retrieve",
    "/v2/orders/search",
    "/v2/inventory/batch-retrieve-counts",
    "/v2/inventory/batch-retrieve-changes",
}


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------
class SquareAPIError(Exception):
    """Non-retryable error from the Square API."""

    def __init__(self, status_code: int, errors: list[dict] | None = None, body: Any = None):
        self.status_code = status_code
        self.errors = errors or []
        self.body = body
        detail = "; ".join(e.get("detail", str(e)) for e in self.errors) if self.errors else str(body)
        super().__init__(f"Square API {status_code}: {detail}")


class SquareRetryExhaustedError(SquareAPIError):
    """All retries exhausted."""


# ---------------------------------------------------------------------------
# Response wrapper
# ---------------------------------------------------------------------------
@dataclass
class SquareResponse:
    status_code: int
    body: dict[str, Any]
    headers: dict[str, str]
    is_success: bool = field(init=False)

    def __post_init__(self) -> None:
        self.is_success = 200 <= self.status_code < 300

    @property
    def errors(self) -> list[dict]:
        return self.body.get("errors", [])

    @property
    def cursor(self) -> str | None:
        return self.body.get("cursor")


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------
class SquareClient:
    """Async Square REST client with retries and rate limiting."""

    def __init__(
        self,
        access_token: str,
        environment: str = "sandbox",
        rate_limiter: SquareRateLimiter | None = None,
    ) -> None:
        self.access_token = access_token
        self.base_url = SANDBOX_BASE if environment == "sandbox" else PRODUCTION_BASE
        self.rate_limiter = rate_limiter or SquareRateLimiter()
        self._http = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
                "Square-Version": "2025-04-16",
            },
            timeout=httpx.Timeout(30.0, connect=10.0),
        )

    # -- lifecycle ----------------------------------------------------------
    async def close(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> "SquareClient":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()

    # -- low-level ---------------------------------------------------------
    async def _rate_limit(self, path: str) -> None:
        if any(path.startswith(bp) for bp in BATCH_PATHS):
            await self.rate_limiter.acquire_batch()
        else:
            await self.rate_limiter.acquire_standard()

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: dict | None = None,
        params: dict | None = None,
    ) -> SquareResponse:
        """Execute an API call with rate limiting + retries."""
        last_error: Exception | None = None

        for attempt in range(MAX_RETRIES + 1):
            await self._rate_limit(path)
            try:
                resp = await self._http.request(method, path, json=json, params=params)
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout) as exc:
                last_error = exc
                wait = BACKOFF_BASE * (BACKOFF_MULTIPLIER ** attempt)
                logger.warning("Connection error on %s %s (attempt %d): %s — retrying in %.1fs",
                               method, path, attempt + 1, exc, wait)
                await asyncio.sleep(wait)
                continue

            body = resp.json() if resp.content else {}
            sq_resp = SquareResponse(
                status_code=resp.status_code,
                body=body,
                headers=dict(resp.headers),
            )

            if sq_resp.is_success:
                return sq_resp

            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", "60"))
                logger.warning("Rate-limited on %s %s — sleeping %ds", method, path, retry_after)
                await asyncio.sleep(retry_after)
                continue

            if resp.status_code in RETRY_STATUS_CODES:
                wait = BACKOFF_BASE * (BACKOFF_MULTIPLIER ** attempt)
                logger.warning("Retryable %d on %s %s (attempt %d) — retrying in %.1fs",
                               resp.status_code, method, path, attempt + 1, wait)
                await asyncio.sleep(wait)
                last_error = SquareAPIError(resp.status_code, sq_resp.errors, body)
                continue

            # Non-retryable error
            raise SquareAPIError(resp.status_code, sq_resp.errors, body)

        raise SquareRetryExhaustedError(
            status_code=getattr(last_error, "status_code", 0),
            errors=getattr(last_error, "errors", []),
            body=f"All {MAX_RETRIES} retries exhausted: {last_error}",
        )

    # -- convenience verbs --------------------------------------------------
    async def get(self, path: str, **kw: Any) -> SquareResponse:
        return await self.request("GET", path, **kw)

    async def post(self, path: str, **kw: Any) -> SquareResponse:
        return await self.request("POST", path, **kw)

    # -- paginated helpers --------------------------------------------------
    async def get_all_pages(self, path: str, *, result_key: str, params: dict | None = None) -> list[dict]:
        """GET pagination — follows `cursor` param until exhausted."""
        items: list[dict] = []
        params = dict(params or {})
        while True:
            resp = await self.get(path, params=params)
            items.extend(resp.body.get(result_key, []))
            if not resp.cursor:
                break
            params["cursor"] = resp.cursor
        return items

    async def post_all_pages(
        self, path: str, *, body: dict, result_key: str
    ) -> list[dict]:
        """POST pagination — follows `cursor` in request body."""
        items: list[dict] = []
        req = dict(body)
        while True:
            resp = await self.post(path, json=req)
            items.extend(resp.body.get(result_key, []))
            if not resp.cursor:
                break
            req["cursor"] = resp.cursor
        return items

    # -- Square-specific high-level methods --------------------------------
    async def list_locations(self) -> list[dict]:
        resp = await self.get("/v2/locations")
        return resp.body.get("locations", [])

    async def list_catalog(self, types: list[str] | None = None) -> list[dict]:
        params: dict[str, str] = {}
        if types:
            params["types"] = ",".join(types)
        return await self.get_all_pages(
            "/v2/catalog/list", result_key="objects", params=params
        )

    async def search_catalog(self, body: dict) -> list[dict]:
        return await self.post_all_pages(
            "/v2/catalog/search", body=body, result_key="objects"
        )

    async def search_orders(self, body: dict) -> list[dict]:
        return await self.post_all_pages(
            "/v2/orders/search", body=body, result_key="orders"
        )

    async def list_payments(
        self, begin_time: str | None = None, end_time: str | None = None
    ) -> list[dict]:
        params: dict[str, str] = {}
        if begin_time:
            params["begin_time"] = begin_time
        if end_time:
            params["end_time"] = end_time
        return await self.get_all_pages("/v2/payments", result_key="payments", params=params)

    async def batch_retrieve_inventory_counts(self, body: dict) -> list[dict]:
        return await self.post_all_pages(
            "/v2/inventory/batch-retrieve-counts",
            body=body,
            result_key="counts",
        )

    async def search_team_members(self, body: dict | None = None) -> list[dict]:
        return await self.post_all_pages(
            "/v2/team-members/search",
            body=body or {},
            result_key="team_members",
        )

    async def retrieve_order(self, order_id: str) -> dict | None:
        resp = await self.get(f"/v2/orders/{order_id}")
        return resp.body.get("order")
