"""
Clover API Client — Async HTTP wrapper with rate limiting, retries, and error handling.

Single point of contact with Clover's REST API.
All other modules (sync engine, OAuth, webhooks) go through this client.

Clover API differences from Square:
  - REST endpoints under /v3/merchants/{merchant_id}/...
  - Pagination via offset + limit (not cursor-based)
  - Rate limit: 16 req/sec per token (cross-app)
  - Auth via Bearer token or apiAccessKey query param
  - All money in cents (same as Square)
"""
import asyncio
import logging
from datetime import datetime
from typing import Any

import httpx

from ..config import clover as cl_config, retry as retry_config
from .rate_limiter import CloverRateLimiter, standard_limiter

logger = logging.getLogger("meridian.clover.client")


class CloverAPIError(Exception):
    """Raised when Clover returns a non-retryable error."""
    def __init__(self, status_code: int, message: str = "", details: Any = None):
        self.status_code = status_code
        self.details = details
        self.message = message or f"Clover API error {status_code}"
        super().__init__(self.message)


class CloverClient:
    """
    Async Clover API client.

    Usage:
        client = CloverClient(access_token="...", merchant_id="...")
        merchant = await client.get_merchant()
        items = await client.list_items()
        orders = await client.list_orders(start_time=..., end_time=...)
    """

    def __init__(
        self,
        access_token: str | None = None,
        merchant_id: str | None = None,
        environment: str | None = None,
        rate_limiter: CloverRateLimiter | None = None,
    ):
        self.access_token = access_token or cl_config.access_token
        self.merchant_id = merchant_id or cl_config.merchant_id
        self.environment = environment or cl_config.environment
        self.base_url = cl_config.api_base_url
        self.rate_limiter = rate_limiter or standard_limiter
        self._http: httpx.AsyncClient | None = None

    async def _get_http(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                timeout=httpx.Timeout(30.0, connect=10.0),
            )
        return self._http

    async def close(self):
        if self._http and not self._http.is_closed:
            await self._http.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    # ─── Core HTTP Methods ────────────────────────────────────

    async def _request(
        self,
        method: str,
        path: str,
        params: dict | None = None,
        json_body: dict | None = None,
    ) -> dict:
        """
        Make a rate-limited, retried request to Clover API.

        Returns the parsed JSON response body.
        Raises CloverAPIError for non-retryable errors.
        """
        http = await self._get_http()
        url = f"/v3/merchants/{self.merchant_id}{path}"

        last_error: Exception | None = None

        for attempt in range(retry_config.max_retries):
            # Rate limit
            await self.rate_limiter.acquire()

            try:
                response = await http.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_body,
                )

                # Success
                if response.status_code == 200:
                    return response.json()

                # 401 — token invalid/expired
                if response.status_code == 401:
                    raise CloverAPIError(401, "Access token invalid or revoked")

                # 404 — resource not found
                if response.status_code == 404:
                    raise CloverAPIError(404, f"Resource not found: {path}")

                # 429 or 5xx — retryable
                if response.status_code in retry_config.retry_on_status:
                    wait = retry_config.backoff_base * (retry_config.backoff_multiplier ** attempt)
                    logger.warning(
                        f"Clover {response.status_code} on {path} — retry {attempt + 1}/{retry_config.max_retries} in {wait:.1f}s"
                    )
                    last_error = CloverAPIError(response.status_code, response.text[:200])
                    await asyncio.sleep(wait)
                    continue

                # Other errors — non-retryable
                raise CloverAPIError(
                    response.status_code,
                    response.text[:500],
                )

            except httpx.TimeoutException as e:
                wait = retry_config.backoff_base * (retry_config.backoff_multiplier ** attempt)
                logger.warning(f"Clover timeout on {path} — retry {attempt + 1} in {wait:.1f}s")
                last_error = e
                await asyncio.sleep(wait)
                continue

            except httpx.HTTPError as e:
                wait = retry_config.backoff_base * (retry_config.backoff_multiplier ** attempt)
                logger.warning(f"Clover HTTP error on {path}: {e} — retry {attempt + 1} in {wait:.1f}s")
                last_error = e
                await asyncio.sleep(wait)
                continue

        # All retries exhausted
        raise CloverAPIError(
            0,
            f"All {retry_config.max_retries} retries exhausted for {path}: {last_error}",
        )

    async def _get(self, path: str, params: dict | None = None) -> dict:
        return await self._request("GET", path, params=params)

    # ─── Pagination Helper ────────────────────────────────────

    async def _paginate(
        self,
        path: str,
        element_key: str,
        params: dict | None = None,
        limit: int = 100,
        max_items: int | None = None,
    ) -> list[dict]:
        """
        Auto-paginate a Clover list endpoint.

        Clover uses offset-based pagination:
          GET /v3/merchants/{mId}/items?offset=0&limit=100

        Args:
            path: API path (e.g., "/items")
            element_key: JSON key holding the array (e.g., "elements")
            params: Extra query params
            limit: Items per page (max 1000)
            max_items: Stop after this many items (None = all)

        Returns list of all items across pages.
        """
        all_items: list[dict] = []
        offset = 0
        params = dict(params or {})

        while True:
            params["offset"] = offset
            params["limit"] = limit

            data = await self._get(path, params=params)
            elements = data.get(element_key, [])

            if not elements:
                break

            all_items.extend(elements)

            if max_items and len(all_items) >= max_items:
                all_items = all_items[:max_items]
                break

            # Clover returns href metadata; check if more pages
            if len(elements) < limit:
                break

            offset += limit

        return all_items

    # ─── Merchant Info ────────────────────────────────────────

    async def get_merchant(self) -> dict:
        """Get merchant profile (name, address, timezone, etc.)."""
        return await self._get("")

    async def get_merchant_properties(self) -> dict:
        """Get merchant properties (additional settings)."""
        return await self._get("/properties")

    # ─── Locations / Devices ──────────────────────────────────

    async def list_devices(self) -> list[dict]:
        """List all POS devices (Clover treats devices like locations)."""
        return await self._paginate("/devices", "elements")

    # ─── Items (Products) ─────────────────────────────────────

    async def list_items(
        self,
        expand: str = "categories,modifierGroups,tags",
        max_items: int | None = None,
    ) -> list[dict]:
        """
        List all inventory items.
        
        Clover items have: name, price, cost, sku, categories, modifiers.
        Use expand to include related objects in one call.
        """
        return await self._paginate(
            "/items",
            "elements",
            params={"expand": expand},
            max_items=max_items,
        )

    async def list_categories(self) -> list[dict]:
        """List all item categories."""
        return await self._paginate("/categories", "elements")

    async def list_item_stocks(self) -> list[dict]:
        """List current inventory stock counts."""
        return await self._paginate("/item_stocks", "elements")

    # ─── Orders ───────────────────────────────────────────────

    async def list_orders(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        expand: str = "lineItems,payments",
        max_items: int | None = None,
    ) -> list[dict]:
        """
        List orders within a time range.

        Clover orders use clientCreatedTime (milliseconds since epoch).
        """
        params: dict[str, Any] = {"expand": expand}
        filters = []

        if start_time:
            ts_ms = int(start_time.timestamp() * 1000)
            filters.append(f"clientCreatedTime>={ts_ms}")

        if end_time:
            ts_ms = int(end_time.timestamp() * 1000)
            filters.append(f"clientCreatedTime<={ts_ms}")

        if filters:
            params["filter"] = "&".join(filters)
        
        params["orderBy"] = "clientCreatedTime DESC"

        return await self._paginate(
            "/orders",
            "elements",
            params=params,
            max_items=max_items,
        )

    async def get_order(self, order_id: str, expand: str = "lineItems,payments") -> dict:
        """Get a single order with line items and payments."""
        return await self._get(f"/orders/{order_id}", params={"expand": expand})

    # ─── Payments ─────────────────────────────────────────────

    async def list_payments(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        max_items: int | None = None,
    ) -> list[dict]:
        """List payments within a time range."""
        params: dict[str, Any] = {}
        filters = []

        if start_time:
            ts_ms = int(start_time.timestamp() * 1000)
            filters.append(f"createdTime>={ts_ms}")

        if end_time:
            ts_ms = int(end_time.timestamp() * 1000)
            filters.append(f"createdTime<={ts_ms}")

        if filters:
            params["filter"] = "&".join(filters)

        return await self._paginate("/payments", "elements", params=params, max_items=max_items)

    # ─── Employees ────────────────────────────────────────────

    async def list_employees(self) -> list[dict]:
        """List all employees."""
        return await self._paginate("/employees", "elements")

    # ─── Customers ────────────────────────────────────────────

    async def list_customers(self, max_items: int | None = None) -> list[dict]:
        """List all customers."""
        return await self._paginate("/customers", "elements", max_items=max_items)
