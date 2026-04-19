"""
Square API Client — Async HTTP wrapper with rate limiting, retries, and error handling.

This is the single point of contact with Square's REST API.
All other modules (sync engine, OAuth, webhooks) go through this client.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from ..config import square as sq_config, retry as retry_config
from .rate_limiter import TokenBucketRateLimiter, standard_limiter, batch_limiter

logger = logging.getLogger("meridian.square.client")


class SquareAPIError(Exception):
    """Raised when Square returns a non-retryable error."""
    def __init__(self, status_code: int, errors: list[dict], message: str = ""):
        self.status_code = status_code
        self.errors = errors
        self.message = message or f"Square API error {status_code}: {errors}"
        super().__init__(self.message)


class SquareClient:
    """
    Async Square API client.
    
    Usage:
        client = SquareClient(access_token="...")
        locations = await client.list_locations()
        orders = await client.search_orders(location_ids=["LOC1"], start_at=..., end_at=...)
    """

    def __init__(
        self,
        access_token: str | None = None,
        environment: str | None = None,
        rate_limiter: TokenBucketRateLimiter | None = None,
    ):
        self.access_token = access_token or sq_config.access_token
        self.environment = environment or sq_config.environment
        self.base_url = (
            "https://connect.squareup.com"
            if self.environment == "production"
            else "https://connect.squareupsandbox.com"
        )
        self.rate_limiter = rate_limiter or standard_limiter
        self._http: httpx.AsyncClient | None = None

    async def _get_http(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Square-Version": "2025-04-16",
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
        json: dict | None = None,
        params: dict | None = None,
        use_batch_limiter: bool = False,
    ) -> dict:
        """
        Make a rate-limited, retried request to Square API.
        
        Returns the parsed JSON response body.
        Raises SquareAPIError on non-retryable failures.
        """
        limiter = batch_limiter if use_batch_limiter else self.rate_limiter
        http = await self._get_http()

        for attempt in range(retry_config.max_retries):
            await limiter.acquire()

            try:
                response = await http.request(
                    method=method,
                    url=path,
                    json=json,
                    params=params,
                )

                # Success
                if response.status_code == 200:
                    return response.json()

                # Rate limited
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", "60"))
                    logger.warning(
                        f"Rate limited on {method} {path}. "
                        f"Retry after {retry_after}s (attempt {attempt + 1})"
                    )
                    await asyncio.sleep(retry_after)
                    continue

                # Retryable server errors
                if response.status_code in retry_config.retry_on_status:
                    wait = retry_config.backoff_base * (
                        retry_config.backoff_multiplier ** attempt
                    )
                    logger.warning(
                        f"Retryable error {response.status_code} on {method} {path}. "
                        f"Waiting {wait}s (attempt {attempt + 1})"
                    )
                    await asyncio.sleep(wait)
                    continue

                # Non-retryable error
                body = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                errors = body.get("errors", [{"detail": response.text}])
                raise SquareAPIError(response.status_code, errors)

            except httpx.ConnectError as e:
                wait = retry_config.backoff_base * (
                    retry_config.backoff_multiplier ** attempt
                )
                logger.warning(f"Connection error on {method} {path}: {e}. Waiting {wait}s")
                await asyncio.sleep(wait)

            except httpx.TimeoutException as e:
                wait = retry_config.backoff_base * (
                    retry_config.backoff_multiplier ** attempt
                )
                logger.warning(f"Timeout on {method} {path}: {e}. Waiting {wait}s")
                await asyncio.sleep(wait)

        # All retries exhausted
        raise SquareAPIError(
            0, [{"detail": f"All {retry_config.max_retries} retries exhausted for {method} {path}"}]
        )

    async def get(self, path: str, params: dict | None = None) -> dict:
        return await self._request("GET", path, params=params)

    async def post(self, path: str, json: dict | None = None, use_batch_limiter: bool = False) -> dict:
        return await self._request("POST", path, json=json, use_batch_limiter=use_batch_limiter)

    # ─── Merchant & Locations ─────────────────────────────────

    async def list_locations(self) -> list[dict]:
        """Get all merchant locations."""
        resp = await self.get("/v2/locations")
        return resp.get("locations", [])

    async def get_merchant(self, merchant_id: str = "me") -> dict:
        """Get merchant profile."""
        resp = await self.get(f"/v2/merchants/{merchant_id}")
        return resp.get("merchant", {})

    # ─── Catalog ──────────────────────────────────────────────

    async def list_catalog(
        self,
        types: list[str] | None = None,
        cursor: str | None = None,
    ) -> tuple[list[dict], str | None]:
        """
        List catalog objects with pagination.
        Returns (objects, next_cursor).
        """
        params = {}
        if types:
            params["types"] = ",".join(types)
        if cursor:
            params["cursor"] = cursor

        resp = await self.get("/v2/catalog/list", params=params)
        objects = resp.get("objects", [])
        next_cursor = resp.get("cursor")
        return objects, next_cursor

    async def list_all_catalog(self, types: list[str] | None = None) -> list[dict]:
        """Fetch entire catalog with automatic pagination."""
        all_objects = []
        cursor = None

        while True:
            objects, cursor = await self.list_catalog(types=types, cursor=cursor)
            all_objects.extend(objects)
            if not cursor:
                break

        return all_objects

    async def batch_retrieve_catalog(self, object_ids: list[str]) -> list[dict]:
        """Fetch specific catalog objects by ID."""
        resp = await self.post(
            "/v2/catalog/batch-retrieve",
            json={"object_ids": object_ids},
            use_batch_limiter=True,
        )
        return resp.get("objects", [])

    # ─── Orders ───────────────────────────────────────────────

    async def search_orders(
        self,
        location_ids: list[str],
        start_at: str | None = None,
        end_at: str | None = None,
        states: list[str] | None = None,
        cursor: str | None = None,
        limit: int = 500,
        sort_field: str = "UPDATED_AT",
        sort_order: str = "ASC",
    ) -> tuple[list[dict], str | None]:
        """
        Search orders with filters and pagination.
        Returns (orders, next_cursor).
        """
        query_filter: dict[str, Any] = {}

        if start_at or end_at:
            date_filter: dict[str, Any] = {}
            if start_at:
                date_filter["start_at"] = start_at
            if end_at:
                date_filter["end_at"] = end_at
            query_filter["date_time_filter"] = {"updated_at": date_filter}

        if states:
            query_filter["state_filter"] = {"states": states}

        body: dict[str, Any] = {
            "location_ids": location_ids,
            "query": {
                "filter": query_filter,
                "sort": {
                    "sort_field": sort_field,
                    "sort_order": sort_order,
                },
            },
            "limit": limit,
        }
        if cursor:
            body["cursor"] = cursor

        resp = await self.post("/v2/orders/search", json=body)
        orders = resp.get("orders", [])
        next_cursor = resp.get("cursor")
        return orders, next_cursor

    async def search_all_orders(
        self,
        location_ids: list[str],
        start_at: str | None = None,
        end_at: str | None = None,
        states: list[str] | None = None,
    ) -> list[dict]:
        """Fetch all matching orders with automatic pagination."""
        all_orders = []
        cursor = None

        while True:
            orders, cursor = await self.search_orders(
                location_ids=location_ids,
                start_at=start_at,
                end_at=end_at,
                states=states,
                cursor=cursor,
            )
            all_orders.extend(orders)
            logger.info(f"Fetched {len(all_orders)} orders so far...")
            if not cursor:
                break

        return all_orders

    # ─── Payments ─────────────────────────────────────────────

    async def list_payments(
        self,
        begin_time: str | None = None,
        end_time: str | None = None,
        location_id: str | None = None,
        cursor: str | None = None,
        limit: int = 100,
    ) -> tuple[list[dict], str | None]:
        """List payments with optional filters."""
        params: dict[str, Any] = {"limit": str(limit)}
        if begin_time:
            params["begin_time"] = begin_time
        if end_time:
            params["end_time"] = end_time
        if location_id:
            params["location_id"] = location_id
        if cursor:
            params["cursor"] = cursor

        resp = await self.get("/v2/payments", params=params)
        return resp.get("payments", []), resp.get("cursor")

    async def get_payment(self, payment_id: str) -> dict:
        """Get a single payment by ID."""
        resp = await self.get(f"/v2/payments/{payment_id}")
        return resp.get("payment", {})

    # ─── Inventory ────────────────────────────────────────────

    async def batch_retrieve_inventory_counts(
        self,
        catalog_object_ids: list[str] | None = None,
        location_ids: list[str] | None = None,
        cursor: str | None = None,
    ) -> tuple[list[dict], str | None]:
        """Retrieve inventory counts for given items/locations."""
        body: dict[str, Any] = {}
        if catalog_object_ids:
            body["catalog_object_ids"] = catalog_object_ids
        if location_ids:
            body["location_ids"] = location_ids
        if cursor:
            body["cursor"] = cursor

        resp = await self.post(
            "/v2/inventory/batch-retrieve-counts",
            json=body,
            use_batch_limiter=True,
        )
        return resp.get("counts", []), resp.get("cursor")

    async def batch_retrieve_all_inventory_counts(
        self,
        catalog_object_ids: list[str] | None = None,
        location_ids: list[str] | None = None,
    ) -> list[dict]:
        """Fetch all inventory counts with pagination."""
        all_counts = []
        cursor = None

        while True:
            counts, cursor = await self.batch_retrieve_inventory_counts(
                catalog_object_ids=catalog_object_ids,
                location_ids=location_ids,
                cursor=cursor,
            )
            all_counts.extend(counts)
            if not cursor:
                break

        return all_counts

    # ─── Team Members ─────────────────────────────────────────

    async def search_team_members(
        self,
        location_ids: list[str] | None = None,
        status: str = "ACTIVE",
        cursor: str | None = None,
    ) -> tuple[list[dict], str | None]:
        """Search team members."""
        body: dict[str, Any] = {
            "query": {
                "filter": {
                    "status": status,
                }
            }
        }
        if location_ids:
            body["query"]["filter"]["location_ids"] = location_ids
        if cursor:
            body["cursor"] = cursor

        resp = await self.post("/v2/team-members/search", json=body)
        return resp.get("team_members", []), resp.get("cursor")

    async def search_all_team_members(
        self,
        location_ids: list[str] | None = None,
        status: str = "ACTIVE",
    ) -> list[dict]:
        """Fetch all team members with pagination."""
        all_members = []
        cursor = None

        while True:
            members, cursor = await self.search_team_members(
                location_ids=location_ids, status=status, cursor=cursor
            )
            all_members.extend(members)
            if not cursor:
                break

        return all_members
