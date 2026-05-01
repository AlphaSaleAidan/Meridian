"""
Clover Sync Engine — Orchestrates data flow from Clover → Meridian.

Three modes:
  1. INITIAL BACKFILL — Run once on connect (merchant → catalog → employees → orders → inventory)
  2. INCREMENTAL SYNC — Every 15 min (new/updated orders since last sync)
  3. REAL-TIME WEBHOOKS — Instant (handled by webhook_handlers.py)

Mirrors the Square SyncEngine pattern exactly.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional

from .client import CloverClient
from .mappers import CloverDataMapper
from ..integrations.base.models import SyncProgress, SyncResult

logger = logging.getLogger("meridian.clover.sync_engine")


class CloverSyncEngine:
    """
    Orchestrates Clover → Meridian data sync.

    Usage:
        engine = CloverSyncEngine(
            client=CloverClient(access_token="...", merchant_id="..."),
            org_id="...",
            pos_connection_id="...",
            on_progress=callback,
            db_writer=upsert_fn,
        )

        # Initial backfill
        result = await engine.run_initial_backfill()

        # Incremental sync
        result = await engine.run_incremental_sync(since=last_sync_time)
    """

    def __init__(
        self,
        client: CloverClient,
        org_id: str,
        pos_connection_id: str,
        on_progress: Callable[[SyncProgress], Any] | None = None,
        db_writer: Callable | None = None,
    ):
        self.client = client
        self.org_id = org_id
        self.pos_connection_id = pos_connection_id
        self.on_progress = on_progress
        self.db_writer = db_writer
        self.progress = SyncProgress(pos_connection_id)

    def _emit_progress(self):
        if self.on_progress:
            self.on_progress(self.progress)

    # ─── Initial Backfill ─────────────────────────────────────

    async def run_initial_backfill(
        self,
        backfill_months: int = 18,
    ) -> SyncResult:
        """
        Full backfill: merchant → employees → categories → items → orders → inventory.

        Sequence matters:
          1. Merchant info → creates location
          2. Employees → builds name cache for transaction mapping
          3. Categories → creates category records + lookup
          4. Items → creates product records + lookup  
          5. Orders → creates transactions + line items (needs product lookup)
          6. Inventory → snapshots (needs product lookup)
        """
        result = SyncResult()

        try:
            # Phase 1: Merchant info (= location)
            self.progress.update("merchant", "Fetching merchant profile...", 5)
            self._emit_progress()

            merchant = await self.client.get_merchant()
            mapper = CloverDataMapper(
                org_id=self.org_id,
                pos_connection_id=self.pos_connection_id,
            )
            result.locations = [mapper.map_merchant_to_location(merchant)]
            logger.info(f"Merchant: {merchant.get('name', 'Unknown')}")

            # Phase 2: Employees
            self.progress.update("employees", "Fetching employee list...", 10)
            self._emit_progress()

            try:
                employees = await self.client.list_employees()
                for emp in employees:
                    emp_id = emp.get("id", "")
                    name = emp.get("name", "")
                    if not name:
                        name = f"{emp.get('firstName', '')} {emp.get('lastName', '')}".strip()
                    result.employee_cache[emp_id] = name
                mapper.employee_cache = result.employee_cache
                logger.info(f"Employees: {len(result.employee_cache)} cached")
            except Exception as e:
                logger.warning(f"Could not fetch employees: {e}")
                result.errors.append(f"employees: {e}")

            # Phase 3: Categories
            self.progress.update("categories", "Syncing categories...", 20)
            self._emit_progress()

            try:
                categories = await self.client.list_categories()
                for cat in categories:
                    row = mapper.map_category(cat)
                    result.categories.append(row)
                logger.info(f"Categories: {len(result.categories)} synced")
            except Exception as e:
                logger.warning(f"Category sync failed: {e}")
                result.errors.append(f"categories: {e}")

            # Phase 4: Items (products)
            self.progress.update("products", "Syncing product catalog...", 35)
            self._emit_progress()

            try:
                items = await self.client.list_items()
                for item in items:
                    row = mapper.map_product(item)
                    result.products.append(row)
                    self.progress.items_synced += 1
                logger.info(f"Products: {len(result.products)} synced")
            except Exception as e:
                logger.warning(f"Product sync failed: {e}")
                result.errors.append(f"products: {e}")

            # Phase 5: Orders (transactions) — backfill window
            self.progress.update("orders", f"Backfilling {backfill_months} months of orders...", 50)
            self._emit_progress()

            start_time = datetime.now(timezone.utc) - timedelta(days=backfill_months * 30)
            end_time = datetime.now(timezone.utc)

            try:
                # Fetch in monthly chunks to avoid timeout
                chunk_start = start_time
                total_orders = 0

                while chunk_start < end_time:
                    chunk_end = min(chunk_start + timedelta(days=30), end_time)

                    orders = await self.client.list_orders(
                        start_time=chunk_start,
                        end_time=chunk_end,
                    )

                    for order in orders:
                        txn = mapper.map_order_to_transaction(order)
                        result.transactions.append(txn)

                        # Map line items
                        for li in order.get("lineItems", {}).get("elements", []):
                            li_row = mapper.map_line_item(
                                li,
                                transaction_id=txn["id"],
                                transaction_time=txn["transaction_time"],
                            )
                            result.transaction_items.append(li_row)

                        self.progress.items_synced += 1
                        total_orders += 1

                    # Update progress
                    months_done = (chunk_end - start_time).days / 30
                    months_total = backfill_months
                    pct = 50 + (months_done / months_total) * 35
                    self.progress.update(
                        "orders",
                        f"{total_orders} orders synced ({chunk_end.strftime('%b %Y')})",
                        min(pct, 85),
                    )
                    self._emit_progress()

                    chunk_start = chunk_end

                logger.info(
                    f"Orders: {len(result.transactions)} transactions, "
                    f"{len(result.transaction_items)} line items"
                )

            except Exception as e:
                logger.error(f"Order sync failed: {e}")
                result.errors.append(f"orders: {e}")

            # Phase 6: Inventory snapshots
            self.progress.update("inventory", "Snapshotting current inventory...", 90)
            self._emit_progress()

            try:
                stocks = await self.client.list_item_stocks()
                for stock in stocks:
                    row = mapper.map_item_stock(stock)
                    result.inventory_snapshots.append(row)
                logger.info(f"Inventory: {len(result.inventory_snapshots)} snapshots")
            except Exception as e:
                logger.warning(f"Inventory sync failed: {e}")
                result.errors.append(f"inventory: {e}")

            # Done
            result.completed_at = datetime.now(timezone.utc)
            self.progress.update("complete", f"Backfill done — {self.progress.items_synced} items", 100)
            self._emit_progress()

            logger.info(f"Initial backfill complete: {result.summary}")

        except Exception as e:
            logger.error(f"Backfill failed: {e}", exc_info=True)
            result.errors.append(f"fatal: {e}")
            self.progress.update("error", str(e))
            self._emit_progress()

        return result

    # ─── Incremental Sync ─────────────────────────────────────

    async def run_incremental_sync(
        self,
        since: datetime | None = None,
    ) -> SyncResult:
        """
        Incremental sync: fetch orders since last sync time.

        Default: last 15 minutes.
        """
        result = SyncResult()

        if since is None:
            since = datetime.now(timezone.utc) - timedelta(minutes=15)

        end_time = datetime.now(timezone.utc)

        self.progress.update("incremental", f"Fetching orders since {since.isoformat()}", 10)
        self._emit_progress()

        try:
            # Build mapper with existing lookups (loaded from DB in production)
            mapper = CloverDataMapper(
                org_id=self.org_id,
                pos_connection_id=self.pos_connection_id,
            )

            orders = await self.client.list_orders(
                start_time=since,
                end_time=end_time,
            )

            for order in orders:
                txn = mapper.map_order_to_transaction(order)
                result.transactions.append(txn)

                for li in order.get("lineItems", {}).get("elements", []):
                    li_row = mapper.map_line_item(
                        li,
                        transaction_id=txn["id"],
                        transaction_time=txn["transaction_time"],
                    )
                    result.transaction_items.append(li_row)

                self.progress.items_synced += 1

            result.completed_at = datetime.now(timezone.utc)
            self.progress.update(
                "complete",
                f"Incremental done — {len(result.transactions)} new orders",
                100,
            )
            self._emit_progress()

            logger.info(f"Incremental sync: {result.summary}")

        except Exception as e:
            logger.error(f"Incremental sync failed: {e}", exc_info=True)
            result.errors.append(f"incremental: {e}")
            self.progress.update("error", str(e))
            self._emit_progress()

        return result
