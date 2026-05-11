"""
Generic REST Connector — Config-driven REST API client for POS systems.

Most Tier 1-3 POS systems follow standard REST patterns. This connector
handles auth (Bearer, API key header, Basic), pagination, and field
mapping using a per-system config dict from the registry.
"""
import logging
from datetime import datetime
from typing import Any

import httpx

from .base import BasePOSConnector, POSConnectionConfig, OrderResult

logger = logging.getLogger("meridian.pos.rest")

AUTH_BEARER = "bearer"
AUTH_HEADER = "header"
AUTH_BASIC = "basic"
AUTH_QUERY = "query"
AUTH_OAUTH_CLIENT_CREDENTIALS = "oauth_client_credentials"


class GenericRESTConnector(BasePOSConnector):

    def __init__(self, config: POSConnectionConfig, api_config: dict):
        super().__init__(config)
        self._api = api_config
        self._token: str | None = None
        self._token_expires: datetime | None = None

    async def test_connection(self) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                url = self._build_url(self._api.get("test_endpoint", self._api.get("transactions_endpoint", "/health")))
                headers = await self._auth_headers()
                resp = await client.get(url, headers=headers)

                if resp.status_code < 300:
                    return {"success": True, "message": f"Connected to {self.config.system_name}"}
                return {"success": False, "message": f"HTTP {resp.status_code}: {resp.text[:200]}"}
        except Exception as e:
            return {"success": False, "message": str(e)[:300]}

    async def fetch_transactions(self, start_date: datetime, end_date: datetime) -> list[dict]:
        endpoint = self._api.get("transactions_endpoint", "/api/orders")
        params = self._build_date_params(start_date, end_date)
        return await self._paginated_get(endpoint, params)

    async def fetch_catalog(self) -> list[dict]:
        endpoint = self._api.get("catalog_endpoint")
        if not endpoint:
            return []
        return await self._paginated_get(endpoint)

    async def fetch_employees(self) -> list[dict]:
        endpoint = self._api.get("employees_endpoint")
        if not endpoint:
            return []
        return await self._paginated_get(endpoint)

    async def fetch_customers(self) -> list[dict]:
        endpoint = self._api.get("customers_endpoint")
        if not endpoint:
            return []
        return await self._paginated_get(endpoint)

    async def create_order(self, order_data: dict) -> OrderResult:
        endpoint = self._api.get("order_create_endpoint")
        if not endpoint:
            return OrderResult(
                success=False,
                pos_system=self.config.system_key,
                fallback_used=True,
                fallback_reason=f"{self.config.system_name} order creation not configured",
            )

        try:
            payload = self._build_order_payload(order_data)
            async with httpx.AsyncClient(timeout=30) as client:
                url = self._build_url(endpoint)
                headers = await self._auth_headers()
                headers["Content-Type"] = "application/json"
                resp = await client.post(url, json=payload, headers=headers)

                if resp.status_code < 300:
                    data = resp.json() if resp.text else {}
                    order_id_field = self._api.get("order_id_field", "id")
                    return OrderResult(
                        success=True,
                        order_id=str(data.get(order_id_field, resp.headers.get("Location", ""))),
                        pos_system=self.config.system_key,
                        raw_response=data,
                    )
                return OrderResult(
                    success=False,
                    pos_system=self.config.system_key,
                    fallback_used=True,
                    fallback_reason=f"HTTP {resp.status_code}: {resp.text[:200]}",
                )
        except Exception as e:
            return OrderResult(
                success=False,
                pos_system=self.config.system_key,
                fallback_used=True,
                fallback_reason=str(e)[:300],
            )

    async def _paginated_get(self, endpoint: str, params: dict | None = None) -> list[dict]:
        all_records: list[dict] = []
        url = self._build_url(endpoint)
        params = dict(params) if params else {}
        headers = await self._auth_headers()

        page_param = self._api.get("page_param", "page")
        limit_param = self._api.get("limit_param", "limit")
        data_key = self._api.get("data_key")
        page_size = self._api.get("page_size", 100)
        max_pages = self._api.get("max_pages", 50)

        params[limit_param] = str(page_size)

        async with httpx.AsyncClient(timeout=30) as client:
            for page in range(1, max_pages + 1):
                params[page_param] = str(page)
                resp = await client.get(url, params=params, headers=headers)
                if resp.status_code >= 300:
                    self._logger.warning(f"Page {page} failed: HTTP {resp.status_code}")
                    break

                body = resp.json()
                records = body.get(data_key, body) if data_key else body
                if isinstance(records, dict):
                    records = records.get("results", records.get("data", records.get("items", [records])))
                if not isinstance(records, list):
                    records = [records]

                all_records.extend(records)
                if len(records) < page_size:
                    break

        return all_records

    def _build_url(self, endpoint: str) -> str:
        base = self._api.get("base_url", self.config.base_url).rstrip("/")
        creds = self.config.credentials

        for key, val in creds.items():
            base = base.replace(f"{{{key}}}", str(val))
            endpoint = endpoint.replace(f"{{{key}}}", str(val))

        return f"{base}{endpoint}"

    def _build_date_params(self, start: datetime, end: datetime) -> dict:
        fmt = self._api.get("date_format", "%Y-%m-%dT%H:%M:%SZ")
        start_param = self._api.get("start_date_param", "start_date")
        end_param = self._api.get("end_date_param", "end_date")
        return {
            start_param: start.strftime(fmt),
            end_param: end.strftime(fmt),
        }

    async def _auth_headers(self) -> dict[str, str]:
        auth_type = self._api.get("auth_type", AUTH_BEARER)
        creds = self.config.credentials
        headers = dict(self._api.get("extra_headers", {}))

        if auth_type == AUTH_BEARER:
            token = creds.get("access_token", creds.get("api_key", ""))
            headers["Authorization"] = f"Bearer {token}"

        elif auth_type == AUTH_HEADER:
            header_name = self._api.get("auth_header_name", "X-API-Key")
            headers[header_name] = creds.get("api_key", creds.get("access_token", ""))

        elif auth_type == AUTH_BASIC:
            import base64
            user = creds.get("username", creds.get("api_key", ""))
            pw = creds.get("password", creds.get("api_secret", ""))
            b64 = base64.b64encode(f"{user}:{pw}".encode()).decode()
            headers["Authorization"] = f"Basic {b64}"

        elif auth_type == AUTH_QUERY:
            pass

        elif auth_type == AUTH_OAUTH_CLIENT_CREDENTIALS:
            if not self._token or (self._token_expires and datetime.utcnow() >= self._token_expires):
                await self._refresh_client_credentials()
            if self._token:
                headers["Authorization"] = f"Bearer {self._token}"

        for key, val in creds.items():
            for hdr_name, hdr_val in list(headers.items()):
                headers[hdr_name] = hdr_val.replace(f"{{{key}}}", str(val))

        return headers

    async def _refresh_client_credentials(self):
        token_url = self._api.get("token_url", "")
        creds = self.config.credentials
        if not token_url:
            return

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(token_url, data={
                    "grant_type": "client_credentials",
                    "client_id": creds.get("client_id", ""),
                    "client_secret": creds.get("client_secret", ""),
                })
                if resp.status_code < 300:
                    data = resp.json()
                    self._token = data.get("access_token", data.get("token", ""))
                    expires_in = data.get("expires_in", 3600)
                    from datetime import timedelta
                    self._token_expires = datetime.utcnow() + timedelta(seconds=expires_in - 60)
        except Exception as e:
            self._logger.error(f"Client credentials refresh failed: {e}")

    def _build_order_payload(self, order_data: dict) -> dict:
        template = self._api.get("order_payload_template")
        if template:
            return self._apply_template(template, order_data)

        return {
            "items": [
                {
                    "name": item["name"],
                    "quantity": item.get("quantity", 1),
                    "special_instructions": item.get("special_instructions", ""),
                }
                for item in order_data.get("items", [])
            ],
            "customer_name": order_data.get("customer_name", ""),
            "order_type": order_data.get("order_type", "pickup"),
        }

    def _apply_template(self, template: dict, data: dict) -> dict:
        import json
        s = json.dumps(template)
        for key, val in data.items():
            if isinstance(val, str):
                s = s.replace(f"${{{key}}}", val)
        return json.loads(s)
