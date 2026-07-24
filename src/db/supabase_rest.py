"""
Supabase REST Client — All database operations via PostgREST API.

Since direct PostgreSQL connections aren't available from all environments,
this client uses the Supabase REST API (PostgREST) for all CRUD operations.
Supports upserts, batch inserts, filtered queries, and RPC function calls.
"""
import logging
import os
from datetime import datetime, timezone
from typing import Any

import httpx

from .org_ids import connection_org_id

logger = logging.getLogger("meridian.db.supabase_rest")

# ─── Per-provider table routing (POS isolation, Option C) ──────────────────
# Each POS system writes to its own canonical table (square_transactions, …) so
# ingestion paths can never overwrite each other. `provider` is a TRANSIENT hint
# stamped on rows by the mappers; it is stripped here before the write (the tables
# carry no provider column). Gated by POS_PER_PROVIDER_TABLES so this is a no-op
# until the per-provider migration + view swap is live — flag OFF = writes go to
# the base table exactly as before. See docs/ARCHITECTURE.md §4.
_PER_PROVIDER_TABLES = {"transactions", "transaction_items"}
_KNOWN_PROVIDERS = {"square", "clover", "toast"}


def _per_provider_enabled() -> bool:
    return os.environ.get("POS_PER_PROVIDER_TABLES", "").lower() in ("1", "true", "yes")


def _route_by_provider(table: str, rows: list[dict]) -> list[tuple[str, list[dict]]]:
    """Split rows into (target_table, rows) groups. For per-provider tables the
    transient `provider` hint is always stripped from each row; when the flag is on,
    rows with a known provider are routed to `{provider}_{table}`. Everything else
    is a single group on the base table (with provider stripped). Returns the
    original (table, rows) untouched for non-per-provider tables."""
    if not rows or table not in _PER_PROVIDER_TABLES:
        return [(table, rows)]
    enabled = _per_provider_enabled()
    groups: dict[str, list[dict]] = {}
    for r in rows:
        prov = str(r.get("provider") or "").lower()
        target = f"{prov}_{table}" if (enabled and prov in _KNOWN_PROVIDERS) else table
        clean = {k: v for k, v in r.items() if k != "provider"}
        groups.setdefault(target, []).append(clean)
    return list(groups.items())


class SupabaseRESTError(Exception):
    """Raised when a Supabase REST API call fails."""
    def __init__(self, status_code: int, message: str, details: str = ""):
        self.status_code = status_code
        self.message = message
        self.details = details
        super().__init__(f"Supabase {status_code}: {message}")


def is_uuid_cast_error(exc: SupabaseRESTError) -> bool:
    """True if a PostgREST error is a UUID type-cast failure (SQLSTATE 22P02).

    PostgREST surfaces ``invalid input syntax for type uuid: "..."`` as HTTP
    400 with Postgres code ``22P02``. This happens when a non-UUID org id
    (e.g. a TEXT ``biz_`` businesses.id) is compared against a UUID ``org_id``
    column — a "no such row" condition, not a server fault. Read-only status
    endpoints should treat it as empty, never as a 500.
    """
    haystack = f"{getattr(exc, 'message', '')} {getattr(exc, 'details', '')}".lower()
    return "22p02" in haystack or (
        "invalid input syntax for type uuid" in haystack
    ) or ("uuid" in haystack and "invalid input syntax" in haystack)


class SupabaseREST:
    """
    Async Supabase client using the PostgREST API.

    Usage:
        db = SupabaseREST(url="https://xxx.supabase.co", service_key="...")
        
        # Insert
        await db.insert("organizations", {"name": "Test", "slug": "test"})
        
        # Upsert (on conflict)
        await db.upsert("products", {"org_id": "...", "external_id": "SQ_123", ...}, 
                         on_conflict="org_id,external_id")
        
        # Batch insert
        await db.batch_insert("transactions", [row1, row2, row3])
        
        # Query
        rows = await db.select("transactions", 
                               filters={"org_id": "eq.xxx"},
                               order="transaction_at.desc",
                               limit=100)
        
        # RPC
        await db.rpc("refresh_analytics_views")
    """

    def __init__(
        self,
        url: str | None = None,
        service_key: str | None = None,
        timeout: float = 30.0,
    ):
        self.url = (url or "").rstrip("/")
        self.service_key = service_key or ""
        self.timeout = timeout
        self._http: httpx.AsyncClient | None = None
        self._request_count = 0
        # Per-instance schema cache (Bug #13: was class-level, shared across instances)
        self._schema_cache: dict[str, set[str]] = {}

    @property
    def _headers(self) -> dict:
        return {
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}",
            "Content-Type": "application/json",
        }

    
    async def _load_schema(self) -> None:
        """Load table column names from PostgREST schema endpoint."""
        if self._schema_cache:
            return
        http = await self._get_http()
        try:
            r = await http.get("/", timeout=10)
            if r.status_code == 200:
                for table_name, defn in r.json().get("definitions", {}).items():
                    self._schema_cache[table_name] = set(defn.get("properties", {}).keys())
                logger.debug(f"Loaded schema for {len(self._schema_cache)} tables")
        except Exception as e:
            logger.warning(f"Schema load failed: {e}")
    
    def _clean_row(self, table: str, data: dict) -> dict:
        """Strip fields not in the table schema. Prevents PostgREST 400 errors."""
        allowed = self._schema_cache.get(table)
        if not allowed:
            # Remove underscore-prefixed internal fields as fallback
            return {k: v for k, v in data.items() if not k.startswith("_")}
        return {k: v for k, v in data.items() if k in allowed}
    
    def _clean_rows(self, table: str, data: dict | list[dict]) -> dict | list[dict]:
        """Clean single row or list of rows."""
        if isinstance(data, list):
            return [self._clean_row(table, row) for row in data]
        return self._clean_row(table, data)

    async def _get_http(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(
                base_url=f"{self.url}/rest/v1",
                headers=self._headers,
                timeout=self.timeout,
            )
        return self._http

    async def close(self):
        if self._http and not self._http.is_closed:
            await self._http.aclose()

    # ─── Core CRUD ────────────────────────────────────────────

    async def insert(
        self,
        table: str,
        data: dict | list[dict],
        return_data: bool = True,
    ) -> list[dict]:
        """Insert one or more rows. Returns inserted rows."""
        await self._load_schema()
        data = self._clean_rows(table, data)
        http = await self._get_http()
        headers = {"Prefer": "return=representation"} if return_data else {}

        r = await http.post(f"/{table}", json=data, headers=headers)
        self._request_count += 1

        if r.status_code in (200, 201):
            return r.json() if return_data else []
        
        self._handle_error(r, f"INSERT into {table}")
        return []

    async def upsert(
        self,
        table: str,
        data: dict | list[dict],
        on_conflict: str = "",
        return_data: bool = True,
        ignore_duplicates: bool = False,
    ) -> list[dict]:
        """
        Insert or update on conflict.

        Args:
            table: Table name
            data: Row dict or list of row dicts
            on_conflict: Comma-separated conflict columns (e.g. "org_id,external_id")
            return_data: Whether to return the upserted rows
            ignore_duplicates: Keep the existing row on conflict instead of
                merging (PostgREST resolution=ignore-duplicates → ON CONFLICT
                DO NOTHING). First write wins.
        """
        await self._load_schema()
        data = self._clean_rows(table, data)
        http = await self._get_http()
        prefer_parts = [
            "resolution=ignore-duplicates" if ignore_duplicates
            else "resolution=merge-duplicates"
        ]
        if return_data:
            prefer_parts.append("return=representation")
        
        headers = {"Prefer": ", ".join(prefer_parts)}
        if on_conflict:
            headers["on-conflict"] = on_conflict  # PostgREST custom header

        # Use query param for on_conflict in PostgREST
        params = {}
        if on_conflict:
            params["on_conflict"] = on_conflict

        r = await http.post(f"/{table}", json=data, headers=headers, params=params)
        self._request_count += 1

        if r.status_code in (200, 201):
            return r.json() if return_data else []
        
        self._handle_error(r, f"UPSERT into {table}")
        return []

    async def update(
        self,
        table: str,
        data: dict,
        filters: dict[str, str],
    ) -> list[dict]:
        """Update rows matching filters."""
        http = await self._get_http()
        params = filters
        headers = {"Prefer": "return=representation"}

        r = await http.patch(f"/{table}", json=data, params=params, headers=headers)
        self._request_count += 1

        if r.status_code == 200:
            return r.json()
        
        self._handle_error(r, f"UPDATE {table}")
        return []

    async def delete(
        self,
        table: str,
        filters: dict[str, str],
    ) -> bool:
        """Delete rows matching filters."""
        http = await self._get_http()
        r = await http.delete(f"/{table}", params=filters)
        self._request_count += 1
        return r.status_code in (200, 204)

    async def select(
        self,
        table: str,
        columns: str = "*",
        filters: dict[str, str] | None = None,
        order: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[dict]:
        """
        Query rows from a table.
        
        Args:
            columns: Comma-separated column names or "*"
            filters: PostgREST filters, e.g. {"org_id": "eq.xxx", "type": "eq.sale"}
            order: e.g. "transaction_at.desc"
            limit: Max rows
        """
        http = await self._get_http()
        params = dict(filters or {})
        params["select"] = columns

        if order:
            params["order"] = order
        if limit:
            params["limit"] = str(limit)
        if offset:
            params["offset"] = str(offset)

        r = await http.get(f"/{table}", params=params)
        self._request_count += 1

        if r.status_code == 200:
            return r.json()
        
        self._handle_error(r, f"SELECT from {table}")
        return []

    async def count(
        self,
        table: str,
        filters: dict[str, str] | None = None,
    ) -> int:
        """Count rows matching filters."""
        http = await self._get_http()
        params = dict(filters or {})
        headers = {"Prefer": "count=exact"}

        r = await http.head(f"/{table}", params=params, headers=headers)
        self._request_count += 1

        if r.status_code == 200:
            content_range = r.headers.get("content-range", "")
            # Format: "0-24/100" or "*/0"
            if "/" in content_range:
                total = content_range.split("/")[1]
                return int(total) if total != "*" else 0
        return 0

    # ─── Batch Operations ─────────────────────────────────────

    async def batch_insert(
        self,
        table: str,
        rows: list[dict],
        chunk_size: int = 500,
        return_data: bool = False,
    ) -> int:
        """
        Insert rows in batches. Returns total inserted count.
        PostgREST handles array inserts natively.
        """
        if not rows:
            return 0

        total = 0
        for target, group in _route_by_provider(table, rows):
            for i in range(0, len(group), chunk_size):
                chunk = group[i : i + chunk_size]
                await self.insert(target, chunk, return_data=return_data)
                total += len(chunk)
                logger.debug(f"Batch insert {target}: {total}/{len(rows)}")

        return total

    async def batch_upsert(
        self,
        table: str,
        rows: list[dict],
        on_conflict: str = "",
        chunk_size: int = 500,
    ) -> int:
        """Upsert rows in batches."""
        if not rows:
            return 0

        total = 0
        for target, group in _route_by_provider(table, rows):
            for i in range(0, len(group), chunk_size):
                chunk = group[i : i + chunk_size]
                await self.upsert(target, chunk, on_conflict=on_conflict, return_data=False)
                total += len(chunk)
                logger.debug(f"Batch upsert {target}: {total}/{len(rows)}")

        return total

    # ─── RPC Functions ────────────────────────────────────────

    async def rpc(
        self,
        function_name: str,
        params: dict | None = None,
    ) -> Any:
        """Call a PostgreSQL function via PostgREST RPC."""
        http = await self._get_http()
        r = await http.post(f"/rpc/{function_name}", json=params or {})
        self._request_count += 1

        if r.status_code in (200, 204):
            try:
                return r.json()
            except Exception:
                return None

        self._handle_error(r, f"RPC {function_name}")

    # ─── Vector Search (pgvector) ────────────────────────────

    async def vector_search(
        self,
        table: str,
        query_embedding: list[float],
        match_column: str = "embedding",
        match_count: int = 10,
        match_threshold: float = 0.7,
        filters: dict | None = None,
    ) -> list[dict]:
        """Similarity search using pgvector (cosine distance)."""
        payload = {
            "query_embedding": query_embedding,
            "match_count": match_count,
            "match_threshold": match_threshold,
        }
        if filters:
            payload["filter_params"] = filters
        return await self.rpc(f"match_{table}", payload)

    # ─── Analytics Helpers ────────────────────────────────────

    async def get_daily_revenue(
        self,
        org_id: str,
        days: int = 30,
    ) -> list[dict]:
        """Get daily revenue aggregates for AI engine."""
        org_id = connection_org_id(org_id) or org_id
        return await self.select(
            "daily_revenue",
            filters={
                "org_id": f"eq.{org_id}",
                "day_bucket": f"gte.{_days_ago(days)}",
            },
            order="day_bucket.asc",
        )

    async def get_hourly_revenue(
        self,
        org_id: str,
        days: int = 30,
    ) -> list[dict]:
        """Get hourly revenue aggregates for AI engine."""
        org_id = connection_org_id(org_id) or org_id
        return await self.select(
            "hourly_revenue",
            filters={
                "org_id": f"eq.{org_id}",
                "hour_bucket": f"gte.{_days_ago(days)}",
            },
            order="hour_bucket.asc",
        )

    async def get_product_performance(
        self,
        org_id: str,
        days: int = 30,
    ) -> list[dict]:
        """Get daily product performance for AI engine."""
        org_id = connection_org_id(org_id) or org_id
        return await self.select(
            "daily_product_performance",
            filters={
                "org_id": f"eq.{org_id}",
                "day_bucket": f"gte.{_days_ago(days)}",
            },
            order="day_bucket.asc",
        )

    async def get_products(self, org_id: str) -> list[dict]:
        """Get all active products for an org."""
        org_id = connection_org_id(org_id) or org_id
        return await self.select(
            "products",
            filters={
                "org_id": f"eq.{org_id}",
                "is_active": "eq.true",
            },
        )

    async def get_recent_transactions(
        self,
        org_id: str,
        days: int = 30,
        limit: int = 5000,
    ) -> list[dict]:
        """Get recent transactions for AI engine."""
        org_id = connection_org_id(org_id) or org_id
        return await self.select(
            "transactions",
            filters={
                "org_id": f"eq.{org_id}",
                "transaction_at": f"gte.{_days_ago(days)}",
            },
            order="transaction_at.desc",
            limit=limit,
        )

    # Aliases used by predictive routes
    async def get_transaction_details(
        self, org_id: str, days: int = 30, limit: int = 5000
    ) -> list[dict]:
        """Alias for get_recent_transactions (used by predictive engine)."""
        return await self.get_recent_transactions(org_id, days, limit)

    async def get_inventory_current(self, org_id: str) -> list[dict]:
        """Latest on-hand quantity per product, from `inventory_snapshots` (the
        table POS sync actually writes) joined to the product catalog.

        The old `inventory` table this read from is never populated by any sync —
        so the Inventory page was permanently empty. Stock here is real; reorder
        point / daily usage / trend aren't tracked yet, so they default (the page
        shows on-hand levels without predictions until that's built)."""
        org_id = connection_org_id(org_id) or org_id
        snapshots = await self.select(
            "inventory_snapshots",
            filters={"org_id": f"eq.{org_id}"},
            order="snapshot_at.desc",
            limit=5000,
        )
        if not snapshots:
            return []

        # Keep the most recent snapshot per product (rows are newest-first).
        latest: dict[str, dict] = {}
        for s in snapshots:
            pid = s.get("product_id")
            if pid and pid not in latest:
                latest[pid] = s

        products = await self.select("products", filters={"org_id": f"eq.{org_id}"})
        pmap = {p["id"]: p for p in products}

        items = []
        for pid, snap in latest.items():
            p = pmap.get(pid, {})
            items.append({
                "id": pid,
                "product_name": p.get("name", "Unknown"),
                "sku": p.get("sku", ""),
                "category": "",
                "current_stock": snap.get("quantity_on_hand", 0) or 0,
                "unit": "units",
                "reorder_point": 0,
                "predicted_daily_usage": 0,
                "trend": "stable",
                "trend_pct": 0,
                "last_updated": snap.get("snapshot_at", ""),
            })
        return items

    # ─── Grounded-engine signal loaders (multi-source) ────────
    # Each is best-effort: a missing table / column / RLS denial returns [] so
    # the Top-Actions engine degrades gracefully instead of failing the whole
    # nightly analysis. org_id / merchant_id / business_id are the same business
    # UUID under different column names across these subsystems.

    async def get_phone_call_logs(self, org_id: str, days: int = 30, limit: int = 500) -> list[dict]:
        """Phone-agent call logs (transcripts, duration, order data) for the merchant."""
        try:
            return await self.select(
                "phone_call_logs",
                filters={"merchant_id": f"eq.{org_id}", "created_at": f"gte.{_days_ago(days)}"},
                order="created_at.desc",
                limit=limit,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("get_phone_call_logs failed for %s: %s", org_id, e)
            return []

    async def get_phone_orders(self, org_id: str, days: int = 30, limit: int = 500) -> list[dict]:
        """Phone-agent orders (incl. POS push success) for the merchant."""
        try:
            return await self.select(
                "phone_orders",
                filters={"merchant_id": f"eq.{org_id}", "created_at": f"gte.{_days_ago(days)}"},
                order="created_at.desc",
                limit=limit,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("get_phone_orders failed for %s: %s", org_id, e)
            return []

    async def get_vision_traffic(self, org_id: str, days: int = 30, limit: int = 2000) -> list[dict]:
        """Camera footfall buckets (entries/exits/occupancy/conversion)."""
        try:
            return await self.select(
                "vision_traffic",
                filters={"org_id": f"eq.{org_id}", "bucket": f"gte.{_days_ago(days)}"},
                order="bucket.desc",
                limit=limit,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("get_vision_traffic failed for %s: %s", org_id, e)
            return []

    async def get_merchant_health(self, org_id: str, limit: int = 12) -> list[dict]:
        """Latest merchant_health scores per category (business_id-scoped)."""
        try:
            return await self.select(
                "merchant_health",
                filters={"business_id": f"eq.{org_id}"},
                order="measured_at.desc",
                limit=limit,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("get_merchant_health failed for %s: %s", org_id, e)
            return []

    async def get_email_engagement(self, org_id: str, days: int = 30, limit: int = 500) -> list[dict]:
        """Outbound email log with open/click/bounce timestamps (org_id is TEXT here)."""
        try:
            return await self.select(
                "email_send_log",
                filters={"org_id": f"eq.{org_id}", "created_at": f"gte.{_days_ago(days)}"},
                order="created_at.desc",
                limit=limit,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("get_email_engagement failed for %s: %s", org_id, e)
            return []

    async def get_recent_action_feedback(self, org_id: str, days: int = 45, limit: int = 200) -> list[dict]:
        """Recent insights' acceptance state so the engine can avoid repeating
        rejected/completed action types (the feedback loop)."""
        try:
            return await self.select(
                "insights",
                filters={"org_id": f"eq.{org_id}", "created_at": f"gte.{_days_ago(days)}"},
                order="created_at.desc",
                limit=limit,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("get_recent_action_feedback failed for %s: %s", org_id, e)
            return []

    async def save_insights(self, insights: list[dict]) -> int:
        """Persist AI-generated insights."""
        if not insights:
            return 0
        return await self.batch_insert("insights", insights)

    async def save_forecasts(self, forecasts: list[dict]) -> int:
        """Persist AI-generated forecasts."""
        if not forecasts:
            return 0
        return await self.batch_insert("forecasts", forecasts)

    async def save_money_left_score(self, score: dict) -> list[dict]:
        """Persist Money Left on Table score."""
        clean = _clean_money_left_for_db(score)
        return await self.insert("money_left_scores", clean)

    async def refresh_views(self):
        """Refresh all materialized views."""
        await self.rpc("refresh_analytics_views")
        logger.info("Materialized views refreshed")

    # ─── Connection Management ────────────────────────────────

    async def get_pos_connection(self, org_id: str) -> dict | None:
        """Get the active POS connection for an org."""
        rows = await self.select(
            "pos_connections",
            filters={
                "org_id": f"eq.{org_id}",
                "status": "eq.connected",
            },
            limit=1,
        )
        return rows[0] if rows else None

    async def update_sync_status(
        self,
        connection_id: str,
        status: str,
        cursor: str | None = None,
        error: str | None = None,
    ):
        """Update POS connection sync status."""
        data = {
            "status": status,
            "last_sync_at": datetime.now(timezone.utc).isoformat(),
        }
        if cursor:
            data["sync_cursor"] = cursor
        if error:
            data["last_error"] = error

        await self.update(
            "pos_connections",
            data,
            filters={"id": f"eq.{connection_id}"},
        )

    # ─── Health Check ─────────────────────────────────────────

    async def health_check(self) -> dict:
        """Check connection and return basic stats."""
        try:
            http = await self._get_http()
            r = await http.get("/", timeout=5)
            if r.status_code == 200:
                schema = r.json()
                table_count = len(schema.get("definitions", {}))
                return {
                    "status": "healthy",
                    "tables": table_count,
                    "requests_made": self._request_count,
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}

        return {"status": "error", "error": f"HTTP {r.status_code}"}

    # ─── Error Handling ───────────────────────────────────────

    def _handle_error(self, response: httpx.Response, context: str = ""):
        """Parse PostgREST error and raise."""
        try:
            body = response.json()
            message = body.get("message", response.text[:200])
            details = body.get("details", "")
            code = body.get("code", "")
        except Exception:
            message = response.text[:200]
            details = ""
            code = ""

        logger.error(f"{context}: {response.status_code} [{code}] {message}")
        
        # Don't raise on 409 (conflict) — expected for upserts
        if response.status_code == 409:
            logger.warning(f"Conflict on {context}: {details}")
            return

        raise SupabaseRESTError(response.status_code, message, details)


# ─── Helpers ──────────────────────────────────────────────────

def _days_ago(days: int) -> str:
    """Return ISO timestamp for N days ago."""
    from datetime import timedelta
    dt = datetime.now(timezone.utc) - timedelta(days=days)
    return dt.isoformat()


def _clean_money_left_for_db(score: dict) -> dict:
    """Map AI money_left_score output to DB columns."""
    return {
        "id": score.get("id"),
        "org_id": score.get("org_id"),
        "location_id": score.get("location_id"),
        "total_score_cents": score.get("total_score_cents", 0),
        "components": score.get("components", {}),
        "scored_at": score.get("scored_at", datetime.now(timezone.utc).isoformat()),
        "model_version": score.get("model_version", "1.0"),
    }


def map_daily_revenue_for_ai(rows: list[dict]) -> list[dict]:
    """Map Supabase daily_revenue rows to AI engine format."""
    result = []
    for r in rows:
        mapped = dict(r)
        # Map day_bucket → date
        if "day_bucket" in mapped:
            mapped["date"] = mapped.pop("day_bucket")
        result.append(mapped)
    return result


def map_hourly_revenue_for_ai(rows: list[dict]) -> list[dict]:
    """Map Supabase hourly_revenue rows to AI engine format."""
    result = []
    for r in rows:
        mapped = dict(r)
        if "hour_bucket" in mapped:
            mapped["date"] = mapped.pop("hour_bucket")
        result.append(mapped)
    return result


def map_product_perf_for_ai(rows: list[dict]) -> list[dict]:
    """Map Supabase daily_product_performance rows to AI engine format."""
    result = []
    for r in rows:
        mapped = dict(r)
        if "day_bucket" in mapped:
            mapped["date"] = mapped.pop("day_bucket")
        result.append(mapped)
    return result
