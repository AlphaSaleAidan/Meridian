"""
Toast Sync Engine — Orchestrates data flow from Toast → Meridian.

Two modes:
  1. INITIAL BACKFILL — Run once on connect (orders + menu + employees)
  2. INCREMENTAL SYNC — Every 30 min (new/updated orders since last sync)

Follows the same BaseSyncEngine pattern as Square and Clover.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from .client import ToastClient
from .mappers import ToastDataMapper
from ..integrations.base.models import SyncProgress, SyncResult

logger = logging.getLogger("meridian.toast.sync_engine")


class ToastSyncEngine:
    """Orchestrates Toast → Meridian data sync."""

    def __init__(
        self,
        client: ToastClient,
        org_id: str,
        pos_connection_id: str,
        on_progress: Callable[[SyncProgress], Any] | None = None,
    ):
        self.client = client
        self.org_id = org_id
        self.pos_connection_id = pos_connection_id
        self.on_progress = on_progress
        self._progress = SyncProgress(pos_connection_id)
        self.mapper = ToastDataMapper(org_id, pos_connection_id)

    def _update_progress(self, phase: str, detail: str, pct: float):
        self._progress.update(phase, detail, pct)
        if self.on_progress:
            self.on_progress(self._progress)

    async def run_initial_backfill(self) -> SyncResult:
        """Full initial data import — menu, employees, 18 months of orders."""
        result = SyncResult()

        try:
            self._update_progress("menu", "Syncing menu items...", 0)
            menu_items = await self.client.get_menu_items()
            for item in menu_items:
                result.products.append(self.mapper.map_menu_item(item))
            self._update_progress("menu", f"Synced {len(result.products)} menu items", 15)

            self._update_progress("employees", "Syncing employees...", 15)
            employees = await self.client.get_employees()
            for emp in employees:
                mapped = self.mapper.map_employee(emp)
                result.employee_cache[mapped["external_id"]] = mapped["name"]
            self._update_progress("employees", f"Cached {len(result.employee_cache)} employees", 20)

            self._update_progress("orders", "Starting order backfill...", 20)
            end = datetime.now(timezone.utc).date()
            start = end - timedelta(days=548)  # ~18 months
            current = start

            while current <= end:
                batch_end = min(current + timedelta(days=7), end)
                page = 1
                while True:
                    orders = await self.client.get_orders(
                        start_date=current.isoformat(),
                        end_date=batch_end.isoformat(),
                        page=page,
                        page_size=100,
                    )
                    if not orders:
                        break
                    for order in orders:
                        txn, items = self.mapper.map_order(order)
                        result.transactions.append(txn)
                        result.transaction_items.extend(items)
                    if len(orders) < 100:
                        break
                    page += 1

                days_done = (batch_end - start).days
                total_days = (end - start).days or 1
                pct = 20 + (days_done / total_days) * 75
                self._update_progress(
                    "orders",
                    f"Synced through {batch_end.isoformat()} — "
                    f"{len(result.transactions)} orders so far",
                    pct,
                )
                current = batch_end + timedelta(days=1)

            self._update_progress(
                "complete",
                f"Backfill complete: {len(result.transactions)} orders, "
                f"{len(result.products)} items",
                100,
            )

        except Exception as e:
            logger.error(f"Toast backfill failed: {e}", exc_info=True)
            result.errors.append(str(e))

        result.completed_at = datetime.now(timezone.utc)
        return result

    async def run_incremental_sync(
        self,
        since: datetime | str | None = None,
        **kwargs,
    ) -> SyncResult:
        """Incremental sync — fetch orders since last sync."""
        result = SyncResult()

        if isinstance(since, str):
            since = datetime.fromisoformat(since.replace("Z", "+00:00"))
        if since is None:
            since = datetime.now(timezone.utc) - timedelta(hours=1)

        start_date = since.date().isoformat()
        end_date = datetime.now(timezone.utc).date().isoformat()

        page = 1
        while True:
            orders = await self.client.get_orders(
                start_date=start_date,
                end_date=end_date,
                page=page,
                page_size=100,
            )
            if not orders:
                break
            for order in orders:
                txn, items = self.mapper.map_order(order)
                result.transactions.append(txn)
                result.transaction_items.extend(items)
            if len(orders) < 100:
                break
            page += 1

        result.completed_at = datetime.now(timezone.utc)
        logger.info(
            f"Toast incremental sync: {len(result.transactions)} orders "
            f"since {start_date}"
        )
        return result
