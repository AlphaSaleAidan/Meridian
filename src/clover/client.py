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
from datetime import datetime, timedelta
from typing import Any

import httpx

from ..config import clover as cl_config, retry as retry_config
from .rate_limiter import CloverRateLimiter, standard_limiter

logger = logging.getLogger("meridian.clover.client")

# Clover silently caps every time-filtered query to the most recent 90 days: a
# wider requested range is auto-adjusted to the latest 90 days, so anything older
# is dropped without error. We window long ranges into <=90-day slices and
# concatenate. https://docs.clover.com/dev/docs/applying-filters
CLOVER_MAX_WINDOW_DAYS = 90


def _time_windows(
    start: datetime | None,
    end: datetime | None,
    max_days: int = CLOVER_MAX_WINDOW_DAYS,
):
    """Yield (win_start, win_end) sub-ranges each no longer than max_days.

    If either bound is missing there's no finite range to slice, so yield the
    pair unchanged (the single-bound or unbounded query is valid as-is).
    """
    if start is None or end is None or start >= end:
        yield (start, end)
        return
    cur = start
    step = timedelta(days=max_days)
    while cur < end:
        nxt = min(cur + step, end)
        yield (cur, nxt)
        cur = nxt


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

    async def _list_time_filtered(
        self,
        path: str,
        time_field: str,
        start_time: datetime | None,
        end_time: datetime | None,
        extra_params: dict | None = None,
        max_items: int | None = None,
    ) -> list[dict]:
        """Paginate a time-filtered list endpoint, windowed to Clover's 90-day cap.

        Filters are emitted as REPEATED ``filter=`` query params (Clover's
        documented syntax: ``?filter=a>=X&filter=a<=Y``). Passing the list to
        httpx serializes it as separate params; joining into one value would let
        httpx URL-encode the ``&`` and Clover would see a single malformed filter.
        """
        results: list[dict] = []
        for win_start, win_end in _time_windows(start_time, end_time):
            if max_items is not None and len(results) >= max_items:
                break
            params: dict[str, Any] = dict(extra_params or {})
            filters: list[str] = []
            if win_start is not None:
                filters.append(f"{time_field}>={int(win_start.timestamp() * 1000)}")
            if win_end is not None:
                filters.append(f"{time_field}<={int(win_end.timestamp() * 1000)}")
            if filters:
                params["filter"] = filters  # repeated filter= params (NOT &-joined)
            remaining = None if max_items is None else max_items - len(results)
            page = await self._paginate(
                path, "elements", params=params, max_items=remaining
            )
            results.extend(page)
        if max_items is not None:
            results = results[:max_items]
        return results

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

    # ─── Merchant Configuration (read-only lookups) ───────────

    async def list_order_types(self) -> list[dict]:
        """List merchant-configured order types (e.g. Dine In, Take Out, Delivery).

        Orders carry an `orderType` reference; this resolves its id → label so
        transactions can be segmented by service style. Small, merchant-level set.
        """
        return await self._paginate("/order_types", "elements")

    async def list_tenders(self) -> list[dict]:
        """List merchant-configured tenders (cash, credit card, plus any custom).

        A tender has id, label, and labelKey (canonical for Clover system tenders:
        com.clover.tender.cash / com.clover.tender.check). Used to map a payment's
        tender → payment_method authoritatively instead of inferring from the label.
        """
        return await self._paginate("/tenders", "elements")

    async def list_tax_rates(self) -> list[dict]:
        """List merchant-configured tax rates (id, name, rate, isDefault).

        Read-only reference used to validate computed tax during reconciliation;
        not a write path.
        """
        return await self._paginate("/tax_rates", "elements")

    async def list_item_stocks(self) -> list[dict]:
        """List current inventory stock counts."""
        return await self._paginate("/item_stocks", "elements")

    # ─── Orders ───────────────────────────────────────────────

    async def list_orders(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        # Nested expansion is REQUIRED for tax: line-item taxRates/discounts are
        # not populated unless dotted-path expanded. This is 5 expansions (Clover
        # guideline is ~3-4) — deliberate: we want tax + order discounts + correct
        # subtotal + multi-register attribution with no breakdown left blank.
        expand: str = "lineItems.taxRates,payments,discounts,serviceCharges,device",
        max_items: int | None = None,
    ) -> list[dict]:
        """
        List orders within a time range.

        Clover orders use clientCreatedTime (milliseconds since epoch). Ranges
        wider than 90 days are windowed automatically (Clover's cap).
        """
        return await self._list_time_filtered(
            "/orders",
            "clientCreatedTime",
            start_time,
            end_time,
            extra_params={"expand": expand, "orderBy": "clientCreatedTime DESC"},
            max_items=max_items,
        )

    async def get_order(
        self,
        order_id: str,
        expand: str = "lineItems.taxRates,payments,discounts,serviceCharges,device",
    ) -> dict:
        """Get a single order with line items (+ taxRates), payments, discounts,
        service charges, and device."""
        return await self._get(f"/orders/{order_id}", params={"expand": expand})

    async def list_refunds(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        max_items: int | None = None,
    ) -> list[dict]:
        """List refunds in a time range. Each refund carries orderRef.id + amount.

        Clover caps this endpoint to the most recent 90 days per query, so wide
        ranges are windowed into <=90-day slices and concatenated.
        """
        return await self._list_time_filtered(
            "/refunds",
            "createdTime",
            start_time,
            end_time,
            max_items=max_items,
        )

    # ─── Payments ─────────────────────────────────────────────

    async def list_payments(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        max_items: int | None = None,
    ) -> list[dict]:
        """List payments within a time range (windowed to Clover's 90-day cap)."""
        return await self._list_time_filtered(
            "/payments",
            "createdTime",
            start_time,
            end_time,
            max_items=max_items,
        )

    # ─── Employees ────────────────────────────────────────────

    async def list_employees(self) -> list[dict]:
        """List all employees."""
        return await self._paginate("/employees", "elements")

    # ─── Customers ────────────────────────────────────────────

    async def list_customers(self, max_items: int | None = None) -> list[dict]:
        """List all customers."""
        return await self._paginate("/customers", "elements", max_items=max_items)
