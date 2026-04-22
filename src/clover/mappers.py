"""
Data Mappers — Transform Clover API responses into Meridian database records.

Every mapper takes raw Clover JSON and returns a dict matching our schema columns.
All money values are stored in cents (INTEGER). External IDs are preserved for
deduplication via ON CONFLICT (org_id, external_id).

Key Clover ↔ Square differences:
  - Clover uses millisecond timestamps (not ISO strings)
  - Clover items have `price` directly (Square uses variations)
  - Clover orders contain `lineItems` inline (Square needs separate calls)
  - Clover doesn't have a "variation" concept — items are flat
  - Clover categories are many-to-many via item.categories
"""
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional
from uuid import uuid4

logger = logging.getLogger("meridian.clover.mappers")


def _clover_ts_to_dt(ts_ms: int | None) -> datetime | None:
    """Convert Clover millisecond timestamp to datetime."""
    if ts_ms is None:
        return None
    return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)


def _clover_ts_to_iso(ts_ms: int | None) -> str | None:
    """Convert Clover millisecond timestamp to ISO string."""
    dt = _clover_ts_to_dt(ts_ms)
    return dt.isoformat() if dt else None


class CloverDataMapper:
    """
    Transforms Clover API objects → Meridian database rows.

    Usage:
        mapper = CloverDataMapper(org_id="...", employee_cache={"EMP_ID": "John Doe"})

        for cl_item in clover_items:
            row = mapper.map_product(cl_item)
            await db.upsert("products", row)
    """

    def __init__(
        self,
        org_id: str,
        location_id: str | None = None,          # Clover merchant = single "location"
        product_lookup: dict[str, str] | None = None,
        category_lookup: dict[str, str] | None = None,
        employee_cache: dict[str, str] | None = None,
        pos_connection_id: str | None = None,
    ):
        self.org_id = org_id
        self.location_id = location_id
        self.product_lookup = product_lookup or {}
        self.category_lookup = category_lookup or {}
        self.employee_cache = employee_cache or {}
        self.pos_connection_id = pos_connection_id

    # ─── Location Mapper (Merchant → Location) ────────────────

    def map_merchant_to_location(self, cl_merchant: dict) -> dict[str, Any]:
        """
        Clover Merchant → Meridian locations table.

        Clover doesn't have multi-location like Square.
        Each merchant IS a location. Multi-location merchants
        have separate Clover merchant IDs.
        """
        address = cl_merchant.get("address", {})

        # Parse business hours if available
        opening_hours = cl_merchant.get("opening_hours", {})
        business_hours = self._parse_business_hours(opening_hours)

        location_id = str(uuid4())
        self.location_id = location_id  # Cache for product/transaction mapping

        return {
            "id": location_id,
            "org_id": self.org_id,
            "external_id": cl_merchant.get("id", ""),
            "pos_type": "clover",
            "name": cl_merchant.get("name", "Unknown"),
            "address_line1": address.get("address1", ""),
            "address_line2": address.get("address2", ""),
            "city": address.get("city", ""),
            "state": address.get("state", ""),
            "postal_code": address.get("zip", ""),
            "country": address.get("country", "US"),
            "phone": cl_merchant.get("phoneNumber", ""),
            "latitude": cl_merchant.get("latitude"),
            "longitude": cl_merchant.get("longitude"),
            "timezone": cl_merchant.get("timezone", "America/Los_Angeles"),
            "currency": cl_merchant.get("defaultCurrency", "USD"),
            "business_hours": business_hours,
            "is_active": cl_merchant.get("isBillable", True),
            "pos_connection_id": self.pos_connection_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    def _parse_business_hours(self, opening_hours: dict) -> dict:
        """Parse Clover opening_hours → Meridian business_hours format."""
        if not opening_hours:
            return {}
        # Clover stores hours as {elements: [{day: "MON", start: "0900", end: "1700"}, ...]}
        hours = {}
        for period in opening_hours.get("elements", []):
            day = period.get("day", "").upper()[:3]
            start = period.get("start", "")
            end = period.get("end", "")
            if day and start and end:
                if day not in hours:
                    hours[day] = []
                hours[day].append({
                    "open": f"{start[:2]}:{start[2:]}",
                    "close": f"{end[:2]}:{end[2:]}",
                })
        return hours

    # ─── Category Mapper ──────────────────────────────────────

    def map_category(self, cl_category: dict) -> dict[str, Any]:
        """Clover Category → Meridian categories table."""
        cat_id = str(uuid4())
        external_id = cl_category.get("id", "")
        self.category_lookup[external_id] = cat_id

        return {
            "id": cat_id,
            "org_id": self.org_id,
            "external_id": external_id,
            "name": cl_category.get("name", "Uncategorized"),
            "sort_order": cl_category.get("sortOrder", 0),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    # ─── Product Mapper ───────────────────────────────────────

    def map_product(self, cl_item: dict) -> dict[str, Any]:
        """
        Clover Item → Meridian products table.

        Key differences from Square:
          - Clover items have price directly (no variations)
          - cost = item.cost (wholesale cost, if set)
          - sku = item.sku
          - categories via item.categories.elements
        """
        external_id = cl_item.get("id", "")
        product_id = str(uuid4())
        self.product_lookup[external_id] = product_id

        # Get primary category
        categories = cl_item.get("categories", {}).get("elements", [])
        primary_category_ext = categories[0].get("id") if categories else None
        category_id = self.category_lookup.get(primary_category_ext, None) if primary_category_ext else None

        price_cents = cl_item.get("price", 0) or 0
        cost_cents = cl_item.get("cost", 0) or 0

        return {
            "id": product_id,
            "org_id": self.org_id,
            "location_id": self.location_id,
            "external_id": external_id,
            "pos_type": "clover",
            "name": cl_item.get("name", "Unknown Item"),
            "sku": cl_item.get("sku", ""),
            "category_id": category_id,
            "category_name": categories[0].get("name", "") if categories else "",
            "price_cents": price_cents,
            "cost_cents": cost_cents,
            "margin_cents": price_cents - cost_cents if cost_cents else None,
            "is_active": not cl_item.get("hidden", False),
            "is_revenue": not cl_item.get("isRevenue", True) is False,
            "tags": [t.get("name", "") for t in cl_item.get("tags", {}).get("elements", [])],
            "raw_data": cl_item,  # Store original for debugging
            "created_at": _clover_ts_to_iso(cl_item.get("createdTime")),
            "updated_at": _clover_ts_to_iso(cl_item.get("modifiedTime")),
        }

    # ─── Transaction Mapper ───────────────────────────────────

    def map_order_to_transaction(self, cl_order: dict) -> dict[str, Any]:
        """
        Clover Order → Meridian transactions table.

        Mapping:
          order.id             → external_id
          order.total          → total_cents
          order.clientCreatedTime → transaction_time
          order.employee.id    → employee_name (via cache)
          order.state          → status
        """
        external_id = cl_order.get("id", "")
        employee_id = cl_order.get("employee", {}).get("id", "")
        employee_name = self.employee_cache.get(employee_id, "")

        total = cl_order.get("total", 0) or 0
        tax = self._sum_tax(cl_order)
        discount = self._sum_discounts(cl_order)

        # Payment method from payments
        payments = cl_order.get("payments", {}).get("elements", [])
        payment_method = self._determine_payment_method(payments)

        return {
            "id": str(uuid4()),
            "org_id": self.org_id,
            "location_id": self.location_id,
            "external_id": external_id,
            "pos_type": "clover",
            "transaction_time": _clover_ts_to_iso(cl_order.get("clientCreatedTime")),
            "total_cents": total,
            "subtotal_cents": total - tax,
            "tax_cents": tax,
            "discount_cents": abs(discount),
            "tip_cents": self._sum_tips(payments),
            "payment_method": payment_method,
            "employee_name": employee_name,
            "employee_external_id": employee_id,
            "status": self._map_order_state(cl_order.get("state", "")),
            "item_count": len(cl_order.get("lineItems", {}).get("elements", [])),
            "customer_id": cl_order.get("customers", {}).get("elements", [{}])[0].get("id") if cl_order.get("customers") else None,
            "is_online": cl_order.get("isOnline", False),
            "source": cl_order.get("orderType", {}).get("label", "in-store") if cl_order.get("orderType") else "in-store",
            "created_at": _clover_ts_to_iso(cl_order.get("createdTime")),
        }

    def map_line_item(self, cl_line_item: dict, transaction_id: str, transaction_time: str) -> dict[str, Any]:
        """
        Clover LineItem → Meridian transaction_items table.
        """
        item_ref = cl_line_item.get("item", {})
        external_item_id = item_ref.get("id", "")
        product_id = self.product_lookup.get(external_item_id)

        price = cl_line_item.get("price", 0) or 0
        qty = cl_line_item.get("unitQty", 1000) / 1000  # Clover uses 1/1000 units

        return {
            "id": str(uuid4()),
            "org_id": self.org_id,
            "transaction_id": transaction_id,
            "product_id": product_id,
            "external_item_id": external_item_id,
            "name": cl_line_item.get("name", item_ref.get("name", "Unknown")),
            "quantity": qty,
            "unit_price_cents": price,
            "total_cents": int(price * qty),
            "discount_cents": abs(self._line_item_discount(cl_line_item)),
            "is_refund": cl_line_item.get("isRevenue", True) is False,
            "transaction_time": transaction_time,
        }

    # ─── Inventory Mapper ─────────────────────────────────────

    def map_item_stock(self, cl_stock: dict) -> dict[str, Any]:
        """Clover ItemStock → Meridian inventory_snapshots table."""
        item_ref = cl_stock.get("item", {})
        external_item_id = item_ref.get("id", "")

        return {
            "id": str(uuid4()),
            "org_id": self.org_id,
            "location_id": self.location_id,
            "product_id": self.product_lookup.get(external_item_id),
            "external_item_id": external_item_id,
            "quantity": cl_stock.get("quantity", 0),
            "snapshot_time": datetime.now(timezone.utc).isoformat(),
        }

    # ─── Helper Methods ───────────────────────────────────────

    def _sum_tax(self, cl_order: dict) -> int:
        """Sum all tax from line items."""
        total_tax = 0
        for li in cl_order.get("lineItems", {}).get("elements", []):
            for tax in li.get("taxRates", {}).get("elements", []):
                total_tax += tax.get("taxAmount", 0)
        return total_tax

    def _sum_discounts(self, cl_order: dict) -> int:
        """Sum all discounts."""
        total = 0
        for d in cl_order.get("discounts", {}).get("elements", []):
            total += d.get("amount", 0)
        return total

    def _sum_tips(self, payments: list[dict]) -> int:
        """Sum tips across all payments."""
        return sum(p.get("tipAmount", 0) or 0 for p in payments)

    def _line_item_discount(self, cl_line_item: dict) -> int:
        """Get discount on a single line item."""
        total = 0
        for d in cl_line_item.get("discounts", {}).get("elements", []):
            total += d.get("amount", 0)
        return total

    def _determine_payment_method(self, payments: list[dict]) -> str:
        """Determine primary payment method from Clover payments."""
        if not payments:
            return "unknown"
        # Use the first/largest payment's tender type
        payment = payments[0]
        tender = payment.get("tender", {})
        label = tender.get("label", "").lower()

        if "cash" in label:
            return "cash"
        elif "credit" in label or "card" in label:
            return "card"
        elif "debit" in label:
            return "debit"
        elif "gift" in label:
            return "gift_card"
        elif "external" in label or "other" in label:
            return "other"
        else:
            return payment.get("cardTransaction", {}).get("type", "card").lower() if payment.get("cardTransaction") else "other"

    def _map_order_state(self, state: str) -> str:
        """Map Clover order state to Meridian status."""
        state_map = {
            "open": "pending",
            "locked": "completed",
            "paid": "completed",
            "": "completed",  # Default for orders without state
        }
        return state_map.get(state.lower(), "completed")
