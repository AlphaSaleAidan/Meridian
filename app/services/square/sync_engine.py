"""
Sync engine — orchestrates the three sync modes:

  1. Initial backfill  (18 months of history on first connect)
  2. Incremental sync  (every 15 minutes via cron)
  3. Real-time webhook (instant, handled in webhook_handlers.py)

This module contains the core logic; workers/square_backfill.py and
workers/square_incremental.py call into these functions.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from .client import SquareClient
from .mappers import (
    build_employee_lookup,
    map_category,
    map_inventory_count,
    map_location,
    map_organization_from_location,
    map_payment_enrichment,
    map_product_from_item,
    map_transaction,
    map_transaction_items,
)

logger = logging.getLogger("meridian.square.sync_engine")


# ---------------------------------------------------------------------------
# Sync result container
# ---------------------------------------------------------------------------
@dataclass
class SyncResult:
    """Accumulates stats from a sync run."""
    locations: int = 0
    categories: int = 0
    products: int = 0
    transactions: int = 0
    transaction_items: int = 0
    inventory_snapshots: int = 0
    team_members: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def summary(self) -> str:
        parts = []
        if self.locations:
            parts.append(f"{self.locations} locations")
        if self.categories:
            parts.append(f"{self.categories} categories")
        if self.products:
            parts.append(f"{self.products} products")
        if self.transactions:
            parts.append(f"{self.transactions} transactions")
        if self.transaction_items:
            parts.append(f"{self.transaction_items} line items")
        if self.inventory_snapshots:
            parts.append(f"{self.inventory_snapshots} inventory snapshots")
        if self.team_members:
            parts.append(f"{self.team_members} team members")
        return ", ".join(parts) or "nothing synced"


# ---------------------------------------------------------------------------
# Lookup caches (populated during sync, used across modules)
# ---------------------------------------------------------------------------
@dataclass
class SyncContext:
    """Mutable lookup tables built during a sync run."""
    org_id: str
    pos_connection_id: str | None = None
    # square_external_id → meridian UUID
    location_lookup: dict[str, str] = field(default_factory=dict)
    category_lookup: dict[str, str] = field(default_factory=dict)
    product_lookup: dict[str, str] = field(default_factory=dict)
    employee_lookup: dict[str, str] = field(default_factory=dict)
    # square_location_id list (needed for order queries)
    location_ids: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Phase 1: Locations
# ---------------------------------------------------------------------------
async def sync_locations(client: SquareClient, ctx: SyncContext) -> list[dict]:
    """Pull all Square locations and return mapped rows."""
    sq_locations = await client.list_locations()
    rows: list[dict] = []
    for sq_loc in sq_locations:
        row = map_location(sq_loc, ctx.org_id)
        ext_id = sq_loc["id"]
        ctx.location_lookup[ext_id] = row["id"]
        ctx.location_ids.append(ext_id)
        rows.append(row)
    logger.info("Mapped %d locations", len(rows))
    return rows


# ---------------------------------------------------------------------------
# Phase 2: Catalog
# ---------------------------------------------------------------------------
async def sync_catalog(client: SquareClient, ctx: SyncContext) -> tuple[list[dict], list[dict]]:
    """Pull full catalog; returns (category_rows, product_rows)."""
    objects = await client.list_catalog(types=["CATEGORY", "ITEM", "ITEM_VARIATION", "IMAGE"])

    # Separate by type
    categories_raw = [o for o in objects if o.get("type") == "CATEGORY"]
    items_raw = [o for o in objects if o.get("type") == "ITEM"]
    images_raw = [o for o in objects if o.get("type") == "IMAGE"]

    # Build image lookup
    image_lookup: dict[str, str] = {}
    for img in images_raw:
        img_data = img.get("image_data", {})
        if img_data.get("url"):
            image_lookup[img["id"]] = img_data["url"]

    # Map categories
    category_rows: list[dict] = []
    for sq_cat in categories_raw:
        row = map_category(sq_cat, ctx.org_id)
        ctx.category_lookup[sq_cat["id"]] = row["id"]
        category_rows.append(row)

    # Map products (items → variations)
    product_rows: list[dict] = []
    for sq_item in items_raw:
        rows = map_product_from_item(sq_item, ctx.org_id, ctx.category_lookup, image_lookup)
        for r in rows:
            ctx.product_lookup[r["metadata"]["square_item_id"]] = r["id"]
            if r.get("external_id"):
                ctx.product_lookup[r["external_id"]] = r["id"]
        product_rows.extend(rows)

    logger.info("Mapped %d categories, %d products", len(category_rows), len(product_rows))
    return category_rows, product_rows


# ---------------------------------------------------------------------------
# Phase 3: Team Members
# ---------------------------------------------------------------------------
async def sync_team_members(client: SquareClient, ctx: SyncContext) -> dict[str, str]:
    """Pull team members and return employee name lookup."""
    try:
        sq_members = await client.search_team_members()
        ctx.employee_lookup = build_employee_lookup(sq_members)
        logger.info("Cached %d team member names", len(ctx.employee_lookup))
    except Exception as exc:
        logger.warning("Could not fetch team members: %s", exc)
        ctx.employee_lookup = {}
    return ctx.employee_lookup


# ---------------------------------------------------------------------------
# Phase 4: Orders (the big one)
# ---------------------------------------------------------------------------
async def sync_orders_range(
    client: SquareClient,
    ctx: SyncContext,
    start_at: datetime,
    end_at: datetime,
) -> tuple[list[dict], list[dict]]:
    """
    Fetch orders in [start_at, end_at) and return
    (transaction_rows, transaction_item_rows).
    """
    body: dict[str, Any] = {
        "location_ids": ctx.location_ids,
        "query": {
            "filter": {
                "date_time_filter": {
                    "updated_at": {
                        "start_at": start_at.isoformat(),
                        "end_at": end_at.isoformat(),
                    }
                },
                "state_filter": {"states": ["COMPLETED", "CANCELED"]},
            },
            "sort": {"sort_field": "UPDATED_AT", "sort_order": "ASC"},
        },
        "limit": 500,
    }

    sq_orders = await client.search_orders(body)

    txn_rows: list[dict] = []
    item_rows: list[dict] = []

    for sq_order in sq_orders:
        txn = map_transaction(
            sq_order, ctx.org_id, ctx.location_lookup,
            ctx.employee_lookup, ctx.pos_connection_id,
        )
        txn_rows.append(txn)

        items = map_transaction_items(
            sq_order, ctx.org_id, txn["id"],
            txn["transaction_at"], ctx.product_lookup,
        )
        item_rows.extend(items)

    logger.info("Range %s→%s: %d orders, %d line items",
                start_at.date(), end_at.date(), len(txn_rows), len(item_rows))
    return txn_rows, item_rows


async def sync_orders_since(
    client: SquareClient,
    ctx: SyncContext,
    since: datetime,
) -> tuple[list[dict], list[dict]]:
    """Incremental order sync — everything updated since `since`."""
    return await sync_orders_range(client, ctx, since, datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Phase 5: Inventory
# ---------------------------------------------------------------------------
async def sync_inventory(
    client: SquareClient,
    ctx: SyncContext,
) -> list[dict]:
    """Pull current inventory counts for all catalog items."""
    catalog_ids = list(ctx.product_lookup.keys())
    if not catalog_ids:
        return []

    # Batch in groups of 100 (Square limit)
    rows: list[dict] = []
    for i in range(0, len(catalog_ids), 100):
        chunk = catalog_ids[i:i + 100]
        body = {
            "catalog_object_ids": chunk,
            "location_ids": ctx.location_ids,
        }
        try:
            counts = await client.batch_retrieve_inventory_counts(body)
            for c in counts:
                row = map_inventory_count(c, ctx.org_id, ctx.product_lookup, ctx.location_lookup)
                if row:
                    rows.append(row)
        except Exception as exc:
            logger.warning("Inventory batch error for chunk %d: %s", i, exc)

    logger.info("Mapped %d inventory snapshots", len(rows))
    return rows


# ---------------------------------------------------------------------------
# Full Backfill Orchestrator
# ---------------------------------------------------------------------------
BACKFILL_MONTHS = 18


async def run_initial_backfill(
    client: SquareClient,
    org_id: str,
    pos_connection_id: str | None = None,
) -> SyncResult:
    """
    Full initial backfill — called once when a merchant first connects.
    Pulls 18 months of data in monthly chunks.
    """
    ctx = SyncContext(org_id=org_id, pos_connection_id=pos_connection_id)
    result = SyncResult()

    # Phase 1: Locations
    try:
        location_rows = await sync_locations(client, ctx)
        result.locations = len(location_rows)
    except Exception as exc:
        result.errors.append(f"Locations: {exc}")
        logger.error("Locations sync failed: %s", exc)

    # Phase 2: Catalog
    try:
        cat_rows, prod_rows = await sync_catalog(client, ctx)
        result.categories = len(cat_rows)
        result.products = len(prod_rows)
    except Exception as exc:
        result.errors.append(f"Catalog: {exc}")
        logger.error("Catalog sync failed: %s", exc)

    # Phase 3: Team Members
    try:
        emp_lookup = await sync_team_members(client, ctx)
        result.team_members = len(emp_lookup)
    except Exception as exc:
        result.errors.append(f"Team members: {exc}")

    # Phase 4: Orders — chunked by month
    start_date = datetime.now(timezone.utc) - timedelta(days=30 * BACKFILL_MONTHS)
    current = start_date
    while current < datetime.now(timezone.utc):
        end = min(current + timedelta(days=30), datetime.now(timezone.utc))
        try:
            txn_rows, item_rows = await sync_orders_range(client, ctx, current, end)
            result.transactions += len(txn_rows)
            result.transaction_items += len(item_rows)
        except Exception as exc:
            result.errors.append(f"Orders ({current.date()}→{end.date()}): {exc}")
            logger.error("Order sync chunk failed: %s", exc)
        current = end

    # Phase 5: Inventory
    try:
        inv_rows = await sync_inventory(client, ctx)
        result.inventory_snapshots = len(inv_rows)
    except Exception as exc:
        result.errors.append(f"Inventory: {exc}")
        logger.error("Inventory sync failed: %s", exc)

    logger.info("Backfill complete: %s", result.summary)
    return result


# ---------------------------------------------------------------------------
# Incremental Sync Orchestrator
# ---------------------------------------------------------------------------
async def run_incremental_sync(
    client: SquareClient,
    org_id: str,
    last_sync_at: datetime,
    pos_connection_id: str | None = None,
    location_ids: list[str] | None = None,
    location_lookup: dict[str, str] | None = None,
    product_lookup: dict[str, str] | None = None,
    employee_lookup: dict[str, str] | None = None,
) -> SyncResult:
    """
    Incremental sync — fetch new/updated orders since last run.
    Called every 15 minutes by the cron worker.
    """
    ctx = SyncContext(org_id=org_id, pos_connection_id=pos_connection_id)

    # Use cached lookups or rebuild
    if location_ids and location_lookup:
        ctx.location_ids = location_ids
        ctx.location_lookup = location_lookup
    else:
        await sync_locations(client, ctx)

    if product_lookup:
        ctx.product_lookup = product_lookup
    if employee_lookup:
        ctx.employee_lookup = employee_lookup

    result = SyncResult()

    try:
        txn_rows, item_rows = await sync_orders_since(client, ctx, last_sync_at)
        result.transactions = len(txn_rows)
        result.transaction_items = len(item_rows)
    except Exception as exc:
        result.errors.append(f"Incremental orders: {exc}")
        logger.error("Incremental sync failed: %s", exc)

    logger.info("Incremental sync: %s", result.summary)
    return result
