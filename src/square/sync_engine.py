"""
Sync Engine — Orchestrates data flow from Square → Meridian.

Three modes:
  1. INITIAL BACKFILL — Run once on connect (locations → catalog → team → orders → inventory)
  2. INCREMENTAL SYNC — Every 15 min (new/updated orders since last sync)
  3. REAL-TIME WEBHOOKS — Instant (handled by webhook_handlers.py)
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional

from .client import SquareClient
from .mappers import DataMapper
from ..integrations.base.models import SyncProgress, SyncResult

logger = logging.getLogger("meridian.square.sync_engine")


class SyncEngine:
    """
    Orchestrates data sync from Square to Meridian.
    
    Usage:
        client = SquareClient(access_token="...")
        engine = SyncEngine(client, org_id="...", on_progress=callback)
        
        # Full backfill
        result = await engine.run_initial_backfill()
        
        # Incremental sync
        result = await engine.run_incremental_sync(since=last_sync_at)
    """

    def __init__(
        self,
        client: SquareClient,
        org_id: str,
        pos_connection_id: str | None = None,
        on_progress: Callable[[SyncProgress], Any] | None = None,
    ):
        self.client = client
        self.org_id = org_id
        self.pos_connection_id = pos_connection_id
        self.on_progress = on_progress
        self._progress = SyncProgress(pos_connection_id or org_id)

    # ─── Phase Weights for Progress Bar ───────────────────────

    PHASE_WEIGHTS = {
        "locations": 5,
        "team_members": 5,
        "catalog": 15,
        "orders": 65,
        "inventory": 10,
    }

    # ─── Initial Backfill ─────────────────────────────────────

    async def run_initial_backfill(self) -> SyncResult:
        """
        Full initial data import.
        
        Phases (in order):
          1. Locations (fast, <1 sec)
          2. Team Members (fast, <2 sec)
          3. Catalog — categories + products (5-30 sec)
          4. Orders — THE BIG ONE (1-30 min for 18 months)
          5. Inventory snapshots (5-15 sec)
        """
        result = SyncResult()
        
        try:
            # ── Phase 1: Locations ────────────────────────────
            self._update_progress("locations", "Pulling merchant locations...", 0)
            locations = await self._sync_locations(result)
            location_ids = [loc["_external_id"] for loc in locations if loc.get("_external_id")]
            self._update_progress("locations", f"Synced {len(locations)} locations", 5)

            # ── Phase 2: Team Members ─────────────────────────
            self._update_progress("team_members", "Syncing team members...", 5)
            await self._sync_team_members(result, location_ids)
            self._update_progress("team_members", f"Cached {len(result.employee_cache)} employees", 10)

            # ── Phase 3: Catalog ──────────────────────────────
            self._update_progress("catalog", "Syncing product catalog...", 10)
            await self._sync_catalog(result)
            self._update_progress(
                "catalog",
                f"Synced {len(result.categories)} categories, {len(result.products)} products",
                25,
            )

            # ── Phase 4: Orders (the big one) ─────────────────
            self._update_progress("orders", "Starting order backfill (18 months)...", 25)
            await self._sync_orders_backfill(result, location_ids)
            self._update_progress(
                "orders",
                f"Synced {len(result.transactions)} transactions, "
                f"{len(result.transaction_items)} line items",
                90,
            )

            # ── Phase 5: Inventory ────────────────────────────
            self._update_progress("inventory", "Syncing inventory counts...", 90)
            await self._sync_inventory(result, location_ids)
            self._update_progress(
                "inventory",
                f"Synced {len(result.inventory_snapshots)} inventory snapshots",
                100,
            )

            result.completed_at = datetime.now(timezone.utc)
            self._update_progress("complete", "Backfill complete!", 100)
            logger.info(f"Backfill complete: {result.summary}")

        except Exception as e:
            result.errors.append(f"Backfill failed: {str(e)}")
            logger.error(f"Backfill failed: {e}", exc_info=True)
            self._update_progress("error", str(e), self._progress.progress_pct)
            raise

        return result

    # ─── Incremental Sync ─────────────────────────────────────

    async def run_incremental_sync(
        self,
        since: datetime | str | None = None,
        location_ids: list[str] | None = None,
    ) -> SyncResult:
        """
        Sync new/updated data since last sync.
        
        This is the 15-minute cron job.
        Only fetches orders updated since `since`.
        """
        result = SyncResult()
        
        if isinstance(since, str):
            since = datetime.fromisoformat(since)
        if since is None:
            since = datetime.now(timezone.utc) - timedelta(hours=1)

        since_str = since.isoformat()
        
        # Build lookup tables from existing DB data.
        # If a db_client is available, load real lookups; otherwise
        # fall back to the mapper set on the engine (from full sync).
        location_lookup: dict[str, str] = {}
        product_lookup: dict[str, str] = {}
        employee_cache: dict[str, str] = {}

        if hasattr(self, "db") and self.db is not None:
            try:
                locs = await self.db.select("locations", filters={"org_id": f"eq.{self.org_id}"})
                for loc in locs:
                    ext_id = loc.get("external_id") or loc.get("square_id", "")
                    if ext_id:
                        location_lookup[ext_id] = loc["id"]

                prods = await self.db.select("products", filters={"org_id": f"eq.{self.org_id}"})
                for prod in prods:
                    ext_id = prod.get("external_id", "")
                    if ext_id:
                        product_lookup[ext_id] = prod["id"]

                logger.info(f"Loaded lookups: {len(location_lookup)} locations, {len(product_lookup)} products")
            except Exception as e:
                logger.warning(f"Failed to load lookups from DB: {e}")

        mapper = DataMapper(
            org_id=self.org_id,
            location_lookup=location_lookup,
            product_lookup=product_lookup,
            employee_cache=employee_cache,
            pos_connection_id=self.pos_connection_id,
        )

        try:
            # Fetch locations if not provided
            if not location_ids:
                sq_locations = await self.client.list_locations()
                location_ids = [loc["id"] for loc in sq_locations]

            # Fetch updated orders
            logger.info(f"Incremental sync: fetching orders since {since_str}")
            orders = await self.client.search_all_orders(
                location_ids=location_ids,
                start_at=since_str,
                states=["COMPLETED", "CANCELED"],
            )

            for order in orders:
                txn = mapper.map_transaction(order)
                result.transactions.append(txn)
                
                items = mapper.map_transaction_items(
                    order, txn["id"], txn["transaction_at"]
                )
                result.transaction_items.extend(items)

            result.completed_at = datetime.now(timezone.utc)
            logger.info(
                f"Incremental sync: {len(result.transactions)} transactions, "
                f"{len(result.transaction_items)} items"
            )

        except Exception as e:
            result.errors.append(f"Incremental sync failed: {str(e)}")
            logger.error(f"Incremental sync failed: {e}", exc_info=True)
            raise

        return result

    # ─── Private: Phase Runners ───────────────────────────────

    async def _sync_locations(self, result: SyncResult) -> list[dict]:
        """Phase 1: Sync all merchant locations."""
        sq_locations = await self.client.list_locations()
        
        mapper = DataMapper(org_id=self.org_id, pos_connection_id=self.pos_connection_id)
        
        for i, sq_loc in enumerate(sq_locations):
            loc = mapper.map_location(sq_loc)
            if i > 0:
                loc["is_primary"] = False
            result.locations.append(loc)
            
            # Build location lookup
            mapper.location_lookup[sq_loc["id"]] = loc["id"]

        # Store for other phases
        self._mapper = mapper
        return result.locations

    async def _sync_team_members(
        self, result: SyncResult, location_ids: list[str]
    ) -> None:
        """Phase 2: Sync team members into employee cache."""
        try:
            members = await self.client.search_all_team_members(
                location_ids=location_ids
            )
            
            for member in members:
                emp_id, emp_name = self._mapper.map_team_member(member)
                result.employee_cache[emp_id] = emp_name
            
            # Update mapper with employee cache
            self._mapper.employee_cache = result.employee_cache
            
        except Exception as e:
            # Team member sync is non-critical — log and continue
            logger.warning(f"Team member sync failed (non-critical): {e}")
            result.errors.append(f"Team member sync: {str(e)}")

    async def _sync_catalog(self, result: SyncResult) -> None:
        """Phase 3: Sync full product catalog (categories + products)."""
        # Fetch all catalog objects
        all_objects = await self.client.list_all_catalog(
            types=["CATEGORY", "ITEM", "ITEM_VARIATION"]
        )

        # Sort: categories first, then items
        categories = [o for o in all_objects if o.get("type") == "CATEGORY"]
        items = [o for o in all_objects if o.get("type") == "ITEM"]

        # Phase 3a: Categories
        for sq_cat in categories:
            cat = self._mapper.map_category(sq_cat)
            result.categories.append(cat)
            # Update category lookup for product mapping
            self._mapper.category_lookup[sq_cat["id"]] = cat["id"]

        # Phase 3b: Products
        for sq_item in items:
            products = self._mapper.map_products(sq_item)
            for product in products:
                result.products.append(product)
                # Update product lookup for transaction mapping
                ext_id = product.get("external_id")
                if ext_id:
                    self._mapper.product_lookup[ext_id] = product["id"]

    async def _sync_orders_backfill(
        self, result: SyncResult, location_ids: list[str]
    ) -> None:
        """
        Phase 4: Backfill up to 18 months of order history.
        
        Chunked by month to manage memory and show progress.
        """
        now = datetime.now(timezone.utc)
        start_date = now - timedelta(days=30 * 18)  # 18 months
        current = start_date
        total_months = 18
        months_done = 0

        while current < now:
            end = min(current + timedelta(days=30), now)

            try:
                orders = await self.client.search_all_orders(
                    location_ids=location_ids,
                    start_at=current.isoformat(),
                    end_at=end.isoformat(),
                    states=["COMPLETED", "CANCELED"],
                )

                for order in orders:
                    txn = self._mapper.map_transaction(order)
                    result.transactions.append(txn)

                    items = self._mapper.map_transaction_items(
                        order, txn["id"], txn["transaction_at"]
                    )
                    result.transaction_items.extend(items)

                    self._progress.items_synced += 1

            except Exception as e:
                month_label = current.strftime("%Y-%m")
                result.errors.append(f"Order sync {month_label}: {str(e)}")
                logger.error(f"Order sync failed for {month_label}: {e}")

            current = end
            months_done += 1

            # Update progress (orders are 65% of total, starting at 25%)
            pct = 25 + (months_done / total_months) * 65
            self._update_progress(
                "orders",
                f"Backfill: {months_done}/{total_months} months "
                f"({len(result.transactions)} transactions)...",
                pct,
            )

    async def _sync_inventory(
        self, result: SyncResult, location_ids: list[str]
    ) -> None:
        """Phase 5: Sync current inventory counts."""
        # Get all product external IDs for inventory lookup
        catalog_ids = list(self._mapper.product_lookup.keys())
        
        if not catalog_ids:
            logger.info("No products to check inventory for")
            return

        try:
            # Batch retrieve in chunks of 100
            for i in range(0, len(catalog_ids), 100):
                chunk = catalog_ids[i : i + 100]
                counts = await self.client.batch_retrieve_all_inventory_counts(
                    catalog_object_ids=chunk,
                    location_ids=location_ids,
                )

                for count in counts:
                    snapshot = self._mapper.map_inventory_count(count)
                    if snapshot.get("product_id"):  # Only if product was mapped
                        result.inventory_snapshots.append(snapshot)

        except Exception as e:
            logger.warning(f"Inventory sync failed (non-critical): {e}")
            result.errors.append(f"Inventory sync: {str(e)}")

    # ─── Progress Helpers ─────────────────────────────────────

    def _update_progress(self, phase: str, detail: str, pct: float):
        self._progress.update(phase, detail, pct)
        if self.on_progress:
            self.on_progress(self._progress)
