"""
Toast API Client — Handles authentication and API calls.

Toast uses client_id + client_secret (OAuth2 client_credentials grant)
to get a short-lived access token, then uses that token for API calls.
"""
import logging
from typing import Any

import httpx

logger = logging.getLogger("meridian.toast.client")

TOAST_AUTH_URL = "https://authentication.toasttab.com/authentication/v1/authentication/login"
TOAST_API_BASE = "https://ws-api.toasttab.com"


class ToastAuthError(Exception):
    pass


class ToastClient:
    """
    Toast API client.

    Authenticates via client_credentials, then calls Toast REST APIs
    scoped to a specific restaurant GUID.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        restaurant_guid: str,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.restaurant_guid = restaurant_guid
        self._access_token: str | None = None

    async def __aenter__(self):
        await self._authenticate()
        return self

    async def __aexit__(self, *args):
        self._access_token = None

    async def _authenticate(self):
        async with httpx.AsyncClient(timeout=15.0) as http:
            resp = await http.post(
                TOAST_AUTH_URL,
                json={
                    "clientId": self.client_id,
                    "clientSecret": self.client_secret,
                    "userAccessType": "TOAST_MACHINE_CLIENT",
                },
            )
        if resp.status_code != 200:
            raise ToastAuthError(
                f"Toast authentication failed ({resp.status_code}): {resp.text[:200]}"
            )
        data = resp.json()
        self._access_token = data.get("token", {}).get("accessToken")
        if not self._access_token:
            raise ToastAuthError("No accessToken in Toast auth response")

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Toast-Restaurant-External-ID": self.restaurant_guid,
            "Content-Type": "application/json",
        }

    async def _get(self, path: str, params: dict | None = None) -> Any:
        async with httpx.AsyncClient(timeout=30.0) as http:
            resp = await http.get(
                f"{TOAST_API_BASE}{path}",
                headers=self._headers(),
                params=params,
            )
        if resp.status_code == 401:
            await self._authenticate()
            async with httpx.AsyncClient(timeout=30.0) as http:
                resp = await http.get(
                    f"{TOAST_API_BASE}{path}",
                    headers=self._headers(),
                    params=params,
                )
        if resp.status_code != 200:
            logger.warning("Toast API %d on %s: %s", resp.status_code, path, resp.text[:200])
            return None
        return resp.json()

    async def get_restaurant_info(self) -> dict | None:
        return await self._get(f"/restaurants/v1/restaurants/{self.restaurant_guid}")

    async def get_orders(
        self,
        start_date: str,
        end_date: str,
        page: int = 1,
        page_size: int = 100,
    ) -> list[dict]:
        result = await self._get(
            "/orders/v2/orders",
            params={
                "businessDate": start_date,
                "endDate": end_date,
                "page": page,
                "pageSize": page_size,
            },
        )
        return result if isinstance(result, list) else []

    async def get_menu_items(self) -> list[dict]:
        result = await self._get("/menus/v2/menus")
        if not result:
            return []
        items = []
        for menu in result if isinstance(result, list) else [result]:
            for group in menu.get("groups", []):
                for item in group.get("items", []):
                    item["_menu_group"] = group.get("name", "")
                    # Toast's Orders API needs the group GUID (not name) on
                    # every selection — stash it so the order writer can build
                    # a real GUID-referenced order. Read path ignores it.
                    item["_menu_group_guid"] = group.get("guid", "")
                    items.append(item)
        return items

    async def get_dining_options(self) -> list[dict]:
        """Dining options for this restaurant. Each carries a `guid` + a
        `behavior` (TAKE_OUT / DELIVERY / DINE_IN) — the Orders API wants the
        GUID, so the writer resolves order_type → behavior → guid."""
        result = await self._get("/config/v2/diningOptions")
        return result if isinstance(result, list) else []

    async def _post(self, path: str, body: dict) -> tuple[int, Any]:
        """POST with a single re-auth retry on 401. Returns (status, json|text)."""
        async def _do():
            async with httpx.AsyncClient(timeout=15.0) as http:
                return await http.post(
                    f"{TOAST_API_BASE}{path}", headers=self._headers(), json=body,
                )
        resp = await _do()
        if resp.status_code == 401:
            await self._authenticate()
            resp = await _do()
        try:
            payload = resp.json()
        except Exception:
            payload = resp.text[:500]
        return resp.status_code, payload

    async def create_order(self, order_payload: dict) -> tuple[int, Any]:
        """Write a GUID-referenced order to Toast (Orders API v2)."""
        return await self._post("/orders/v2/orders", order_payload)

    async def get_employees(self) -> list[dict]:
        result = await self._get("/labor/v1/employees")
        return result if isinstance(result, list) else []

    async def get_revenue_centers(self) -> list[dict]:
        result = await self._get("/config/v2/revenueCenters")
        return result if isinstance(result, list) else []
