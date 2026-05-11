"""
Toast Data Mappers — Transform Toast API responses to Meridian schema.

All money values are converted to cents (INTEGER).
All timestamps are converted to UTC ISO 8601.
"""
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger("meridian.toast.mappers")


class ToastDataMapper:

    def __init__(self, org_id: str, pos_connection_id: str):
        self.org_id = org_id
        self.pos_connection_id = pos_connection_id

    def map_order(self, order: dict) -> tuple[dict, list[dict]]:
        """Map a Toast order to a Meridian transaction + items."""
        order_id = str(uuid4())
        external_id = order.get("guid", "")

        opened_at = order.get("openedDate")
        if isinstance(opened_at, (int, float)):
            dt = datetime.fromtimestamp(opened_at / 1000, tz=timezone.utc)
        elif isinstance(opened_at, str):
            dt = datetime.fromisoformat(opened_at.replace("Z", "+00:00"))
        else:
            dt = datetime.now(timezone.utc)

        checks = order.get("checks", [])
        total_cents = 0
        tax_cents = 0
        tip_cents = 0
        discount_cents = 0
        payment_method = None

        for check in checks:
            total_cents += int(round((check.get("totalAmount") or 0) * 100))
            tax_cents += int(round((check.get("taxAmount") or 0) * 100))
            for payment in check.get("payments", []):
                tip_cents += int(round((payment.get("tipAmount") or 0) * 100))
                if not payment_method:
                    payment_method = payment.get("type", "UNKNOWN")
            for discount in check.get("appliedDiscounts", []):
                discount_cents += abs(int(round((discount.get("discountAmount") or 0) * 100)))

        server = order.get("server", {})
        employee_name = None
        employee_ext_id = None
        if server:
            employee_name = f"{server.get('firstName', '')} {server.get('lastName', '')}".strip()
            employee_ext_id = server.get("guid")

        transaction = {
            "id": order_id,
            "org_id": self.org_id,
            "location_id": None,
            "pos_connection_id": self.pos_connection_id,
            "external_id": external_id,
            "type": "SALE",
            "subtotal_cents": total_cents - tax_cents,
            "tax_cents": tax_cents,
            "tip_cents": tip_cents,
            "discount_cents": discount_cents,
            "total_cents": total_cents,
            "payment_method": payment_method,
            "employee_name": employee_name,
            "employee_external_id": employee_ext_id,
            "transaction_at": dt.isoformat(),
            "metadata": {"source": "toast", "toast_guid": external_id},
        }

        items = []
        for check in checks:
            for sel in check.get("selections", []):
                item_id = str(uuid4())
                qty = sel.get("quantity", 1)
                price_cents = int(round((sel.get("price") or 0) * 100))
                items.append({
                    "id": item_id,
                    "transaction_id": order_id,
                    "transaction_at": dt.isoformat(),
                    "org_id": self.org_id,
                    "product_id": None,
                    "product_name": sel.get("displayName") or sel.get("name") or "Unknown",
                    "quantity": qty,
                    "unit_price_cents": price_cents,
                    "total_cents": price_cents * qty,
                    "discount_cents": 0,
                    "modifiers": [m.get("displayName", "") for m in sel.get("modifiers", [])],
                    "metadata": {"toast_guid": sel.get("guid")},
                })

        return transaction, items

    def map_menu_item(self, item: dict) -> dict:
        price_cents = int(round((item.get("price") or item.get("prices", [{}])[0].get("price", 0)) * 100)) if item.get("price") or item.get("prices") else 0

        return {
            "id": str(uuid4()),
            "org_id": self.org_id,
            "category_id": None,
            "external_id": item.get("guid", ""),
            "name": item.get("name", "Unknown"),
            "description": item.get("description", ""),
            "sku": item.get("sku", ""),
            "barcode": None,
            "price_cents": price_cents,
            "has_variants": bool(item.get("childModifierGroups")),
            "variant_of": None,
            "variant_attrs": {},
            "is_active": item.get("visibility", "ALL") != "NONE",
            "is_taxable": True,
            "image_url": item.get("imageUrl"),
            "metadata": {
                "source": "toast",
                "menu_group": item.get("_menu_group", ""),
            },
        }

    def map_employee(self, emp: dict) -> dict:
        return {
            "external_id": emp.get("guid", ""),
            "name": f"{emp.get('firstName', '')} {emp.get('lastName', '')}".strip(),
        }
