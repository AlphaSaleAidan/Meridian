"""
Database Client — Supabase/PostgreSQL operations for Meridian.

In production, this connects to Supabase via asyncpg.
For sandbox testing, operations are collected in-memory.
"""
import logging
from datetime import datetime

logger = logging.getLogger("meridian.db")


class InMemoryDB:
    """
    In-memory database for sandbox testing.
    
    Mimics the interface of a production DB client
    while storing everything in dictionaries.
    
    Usage:
        db = InMemoryDB()
        await db.upsert_location(location_dict)
        print(db.stats())
    """
    
    def __init__(self):
        self.locations: dict[str, dict] = {}        # id → row
        self.categories: dict[str, dict] = {}       # id → row
        self.products: dict[str, dict] = {}          # id → row
        self.transactions: dict[str, dict] = {}      # id → row
        self.transaction_items: dict[str, dict] = {} # id → row
        self.inventory_snapshots: dict[str, dict] = {}
        self.pos_connections: dict[str, dict] = {}
        
        # Lookup indexes (simulating DB indexes)
        self._ext_products: dict[str, str] = {}      # external_id → id
        self._ext_categories: dict[str, str] = {}    # external_id → id
        self._ext_transactions: dict[str, str] = {}  # external_id → id

    async def upsert_location(self, row: dict) -> str:
        self.locations[row["id"]] = row
        return row["id"]

    async def upsert_category(self, row: dict) -> str:
        ext_id = row.get("external_id")
        # Check for existing by external_id
        if ext_id and ext_id in self._ext_categories:
            existing_id = self._ext_categories[ext_id]
            self.categories[existing_id].update(row)
            return existing_id
        
        self.categories[row["id"]] = row
        if ext_id:
            self._ext_categories[ext_id] = row["id"]
        return row["id"]

    async def upsert_product(self, row: dict) -> str:
        ext_id = row.get("external_id")
        if ext_id and ext_id in self._ext_products:
            existing_id = self._ext_products[ext_id]
            self.products[existing_id].update(row)
            return existing_id
        
        self.products[row["id"]] = row
        if ext_id:
            self._ext_products[ext_id] = row["id"]
        return row["id"]

    async def upsert_transaction(self, txn: dict, items: list[dict]) -> str:
        ext_id = txn.get("external_id")
        if ext_id and ext_id in self._ext_transactions:
            existing_id = self._ext_transactions[ext_id]
            self.transactions[existing_id].update(txn)
        else:
            self.transactions[txn["id"]] = txn
            if ext_id:
                self._ext_transactions[ext_id] = txn["id"]
        
        for item in items:
            self.transaction_items[item["id"]] = item
        
        return txn["id"]

    async def upsert_inventory(self, row: dict) -> str:
        self.inventory_snapshots[row["id"]] = row
        return row["id"]

    def stats(self) -> dict:
        """Summary statistics."""
        total_revenue = sum(
            t.get("total_cents", 0) for t in self.transactions.values()
        )
        return {
            "locations": len(self.locations),
            "categories": len(self.categories),
            "products": len(self.products),
            "transactions": len(self.transactions),
            "transaction_items": len(self.transaction_items),
            "inventory_snapshots": len(self.inventory_snapshots),
            "total_revenue_cents": total_revenue,
            "total_revenue_dollars": f"${total_revenue / 100:,.2f}",
        }

    def top_products(self, limit: int = 10) -> list[dict]:
        """Top products by revenue (from transaction items)."""
        product_revenue: dict[str, dict] = {}
        
        for item in self.transaction_items.values():
            name = item.get("product_name", "Unknown")
            if name not in product_revenue:
                product_revenue[name] = {
                    "name": name,
                    "times_sold": 0,
                    "revenue_cents": 0,
                }
            product_revenue[name]["times_sold"] += 1
            product_revenue[name]["revenue_cents"] += item.get("total_cents", 0)
        
        sorted_products = sorted(
            product_revenue.values(),
            key=lambda x: x["revenue_cents"],
            reverse=True,
        )
        return sorted_products[:limit]

    def payment_breakdown(self) -> dict[str, int]:
        """Transactions by payment method."""
        breakdown: dict[str, int] = {}
        for txn in self.transactions.values():
            method = txn.get("payment_method", "unknown")
            breakdown[method] = breakdown.get(method, 0) + 1
        return breakdown

    def hourly_distribution(self) -> dict[int, int]:
        """Transaction count by hour of day."""
        hours: dict[int, int] = {}
        for txn in self.transactions.values():
            ts = txn.get("transaction_at", "")
            if ts:
                try:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    hour = dt.hour
                    hours[hour] = hours.get(hour, 0) + 1
                except (ValueError, AttributeError):
                    pass
        return dict(sorted(hours.items()))
