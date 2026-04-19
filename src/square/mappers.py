"""
Data Mappers — Transform Square API responses into Meridian database records.

Every mapper takes raw Square JSON and returns a dict matching our schema columns.
All money values are stored in cents (INTEGER). External IDs are preserved for
deduplication via ON CONFLICT (org_id, external_id).
"""
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional
from uuid import uuid4

logger = logging.getLogger("meridian.square.mappers")


class DataMapper:
    """
    Transforms Square API objects → Meridian database rows.
    
    Usage:
        mapper = DataMapper(org_id="...", employee_cache={"EMP_ID": "John Doe"})
        
        for sq_location in square_locations:
            row = mapper.map_location(sq_location)
            await db.upsert("locations", row)
    """

    def __init__(
        self,
        org_id: str,
        location_lookup: dict[str, str] | None = None,    # square_location_id → meridian_location_uuid
        product_lookup: dict[str, str] | None = None,      # square_catalog_id → meridian_product_uuid
        category_lookup: dict[str, str] | None = None,     # square_category_id → meridian_category_uuid
        employee_cache: dict[str, str] | None = None,      # square_employee_id → "First Last"
        pos_connection_id: str | None = None,
    ):
        self.org_id = org_id
        self.location_lookup = location_lookup or {}
        self.product_lookup = product_lookup or {}
        self.category_lookup = category_lookup or {}
        self.employee_cache = employee_cache or {}
        self.pos_connection_id = pos_connection_id

    # ─── Location Mapper ──────────────────────────────────────

    def map_location(self, sq_location: dict) -> dict[str, Any]:
        """
        Square Location → Meridian locations table.
        
        Mapping:
          location.id                   → external_id (via pos_connections)
          location.name                 → name
          location.address.*            → address fields
          location.coordinates.*        → latitude, longitude
          location.phone_number         → phone
          location.business_hours       → business_hours (JSONB)
          location.status = "ACTIVE"    → is_active
        """
        address = sq_location.get("address", {})
        coords = sq_location.get("coordinates", {})
        
        # Parse Square business hours into our format
        business_hours = self._parse_business_hours(
            sq_location.get("business_hours", {})
        )

        return {
            "id": str(uuid4()),
            "org_id": self.org_id,
            "name": sq_location.get("name", "Main Location"),
            "is_primary": True,  # First synced location is primary
            "address_line1": address.get("address_line_1", ""),
            "city": address.get("locality", ""),
            "state": address.get("administrative_district_level_1", ""),
            "zip_code": address.get("postal_code", ""),
            "latitude": coords.get("latitude"),
            "longitude": coords.get("longitude"),
            "phone": sq_location.get("phone_number", ""),
            "business_hours": business_hours,
            "is_active": sq_location.get("status") == "ACTIVE",
            "_external_id": sq_location.get("id"),  # stored in pos_connections
        }

    # ─── Category Mapper ──────────────────────────────────────

    def map_category(self, sq_object: dict) -> dict[str, Any]:
        """
        Square CatalogObject (type=CATEGORY) → Meridian product_categories.
        
        Mapping:
          object.id                     → external_id
          object.category_data.name     → name
          object.category_data.parent_category.id → parent_id
          object.is_deleted             → is_active (inverted)
        """
        cat_data = sq_object.get("category_data", {})
        parent_sq_id = (cat_data.get("parent_category") or {}).get("id")

        return {
            "id": str(uuid4()),
            "org_id": self.org_id,
            "name": cat_data.get("name", "Uncategorized"),
            "external_id": sq_object.get("id"),
            "parent_id": self.category_lookup.get(parent_sq_id) if parent_sq_id else None,
            "is_active": not sq_object.get("is_deleted", False),
        }

    # ─── Product Mapper ───────────────────────────────────────

    def map_products(self, sq_object: dict) -> list[dict[str, Any]]:
        """
        Square CatalogObject (type=ITEM) → Meridian products.
        
        IMPORTANT: One Square ITEM can have multiple ITEM_VARIATIONs.
        Each variation becomes a separate row in products.
        
        Returns a list of product dicts (one per variation).
        """
        item_data = sq_object.get("item_data", {})
        variations = item_data.get("variations", [])
        
        if not variations:
            # Item with no variations — create single product
            return [self._map_single_product(sq_object, item_data, None)]

        products = []
        has_variants = len(variations) > 1
        main_product_id = str(uuid4())

        for i, variation in enumerate(variations):
            var_data = variation.get("item_variation_data", {})
            product_id = main_product_id if i == 0 else str(uuid4())
            
            price_money = var_data.get("price_money", {})
            price_cents = price_money.get("amount", 0) if price_money else 0

            product = {
                "id": product_id,
                "org_id": self.org_id,
                "category_id": self.category_lookup.get(item_data.get("category_id")),
                "external_id": variation.get("id"),  # variation ID as external_id
                "name": item_data.get("name", "Unknown Product"),
                "description": item_data.get("description", ""),
                "sku": var_data.get("sku", ""),
                "barcode": var_data.get("upc", ""),
                "price_cents": price_cents,
                "has_variants": has_variants,
                "variant_of": main_product_id if i > 0 else None,
                "variant_attrs": {
                    "variation_name": var_data.get("name", ""),
                    "variation_id": variation.get("id"),
                    "item_id": sq_object.get("id"),
                } if has_variants else {},
                "is_active": not sq_object.get("is_deleted", False),
                "is_taxable": bool(item_data.get("tax_ids")),
                "image_url": self._resolve_image_url(item_data),
                "metadata": {
                    "square_item_id": sq_object.get("id"),
                    "pricing_type": var_data.get("pricing_type", "FIXED_PRICING"),
                },
            }
            products.append(product)

        return products

    def _map_single_product(
        self, sq_object: dict, item_data: dict, var_data: dict | None
    ) -> dict[str, Any]:
        """Map a single item with no variations."""
        return {
            "id": str(uuid4()),
            "org_id": self.org_id,
            "category_id": self.category_lookup.get(item_data.get("category_id")),
            "external_id": sq_object.get("id"),
            "name": item_data.get("name", "Unknown Product"),
            "description": item_data.get("description", ""),
            "sku": "",
            "barcode": "",
            "price_cents": 0,
            "has_variants": False,
            "variant_of": None,
            "variant_attrs": {},
            "is_active": not sq_object.get("is_deleted", False),
            "is_taxable": bool(item_data.get("tax_ids")),
            "image_url": self._resolve_image_url(item_data),
            "metadata": {"square_item_id": sq_object.get("id")},
        }

    # ─── Transaction Mapper ───────────────────────────────────

    def map_transaction(self, sq_order: dict) -> dict[str, Any]:
        """
        Square Order → Meridian transactions table.
        
        Mapping:
          order.id                      → external_id
          order.location_id             → location_id (via lookup)
          order.state                   → type ('sale' or 'void')
          order.total_money.amount      → total_cents
          order.total_tax_money.amount  → tax_cents
          order.total_tip_money.amount  → tip_cents
          order.total_discount_money.amount → discount_cents
          order.created_at              → transaction_at
          order.tenders[0].type         → payment_method
          order.tenders[0].employee_id  → employee_name (via cache)
        """
        # Money fields (default to 0)
        total = self._money(sq_order, "total_money")
        tax = self._money(sq_order, "total_tax_money")
        tip = self._money(sq_order, "total_tip_money")
        discount = self._money(sq_order, "total_discount_money")
        subtotal = total - tax - tip + discount

        # Payment method from first tender
        tenders = sq_order.get("tenders", [])
        payment_method = self._map_payment_method(tenders[0] if tenders else {})

        # Employee
        employee_id = None
        employee_name = None
        if tenders:
            employee_id = tenders[0].get("employee_id")
            if employee_id:
                employee_name = self.employee_cache.get(employee_id)

        # Transaction type
        state = sq_order.get("state", "COMPLETED")
        txn_type = "void" if state == "CANCELED" else "sale"

        # Square location → Meridian location
        sq_location_id = sq_order.get("location_id")
        location_id = self.location_lookup.get(sq_location_id)

        return {
            "id": str(uuid4()),
            "org_id": self.org_id,
            "location_id": location_id,
            "pos_connection_id": self.pos_connection_id,
            "external_id": sq_order.get("id"),
            "type": txn_type,
            "subtotal_cents": subtotal,
            "tax_cents": tax,
            "tip_cents": tip,
            "discount_cents": discount,
            "total_cents": total,
            "payment_method": payment_method,
            "employee_name": employee_name,
            "employee_external_id": employee_id,
            "transaction_at": sq_order.get("created_at"),
            "metadata": self._extract_order_metadata(sq_order, tenders),
        }

    def map_transaction_items(
        self, sq_order: dict, transaction_id: str, transaction_at: str
    ) -> list[dict[str, Any]]:
        """
        Square OrderLineItem[] → Meridian transaction_items rows.
        
        Mapping:
          line_item.catalog_object_id   → product_id (via lookup)
          line_item.name                → product_name
          line_item.quantity            → quantity
          line_item.base_price_money    → unit_price_cents
          line_item.total_money         → total_cents
          line_item.total_discount_money → discount_cents
          line_item.modifiers[]         → modifiers JSONB
        """
        line_items = sq_order.get("line_items", [])
        rows = []

        for item in line_items:
            catalog_id = item.get("catalog_object_id", "")
            product_id = self.product_lookup.get(catalog_id)

            quantity_str = item.get("quantity", "1")
            try:
                quantity = float(Decimal(quantity_str))
            except (ValueError, TypeError):
                quantity = 1.0

            unit_price = (item.get("base_price_money") or {}).get("amount", 0)
            total = (item.get("total_money") or {}).get("amount", 0)
            discount = (item.get("total_discount_money") or {}).get("amount", 0)

            # Map modifiers
            modifiers = []
            for mod in item.get("modifiers", []):
                modifiers.append({
                    "name": mod.get("name", ""),
                    "price": (mod.get("total_price_money") or {}).get("amount", 0),
                })

            rows.append({
                "id": str(uuid4()),
                "transaction_id": transaction_id,
                "transaction_at": transaction_at,
                "org_id": self.org_id,
                "product_id": product_id,
                "product_name": item.get("name", "Unknown Item"),
                "quantity": quantity,
                "unit_price_cents": unit_price,
                "total_cents": total,
                "discount_cents": discount,
                "modifiers": modifiers,
                "metadata": {
                    "square_uid": item.get("uid"),
                    "catalog_object_id": catalog_id,
                },
            })

        return rows

    # ─── Payment Enrichment Mapper ────────────────────────────

    def map_payment_enrichment(self, sq_payment: dict) -> dict[str, Any]:
        """
        Square Payment → enrichment data for existing transaction.
        
        This adds card brand, last 4, processing fees, tip accuracy.
        Returns a dict of fields to UPDATE on the matching transaction.
        """
        card_details = sq_payment.get("card_details", {})
        card = card_details.get("card", {})
        processing_fee = sq_payment.get("processing_fee", [])

        enrichment = {}
        
        # More accurate tip from payment
        tip_money = sq_payment.get("tip_money", {})
        if tip_money:
            enrichment["tip_cents"] = tip_money.get("amount", 0)

        # Card metadata
        metadata_updates = {}
        if card.get("card_brand"):
            metadata_updates["card_brand"] = card["card_brand"]
        if card.get("last_4"):
            metadata_updates["card_last4"] = card["last_4"]
        if processing_fee:
            fee = processing_fee[0].get("amount_money", {})
            metadata_updates["processing_fee_cents"] = fee.get("amount", 0)

        risk = sq_payment.get("risk_evaluation", {})
        if risk.get("risk_level"):
            metadata_updates["risk_level"] = risk["risk_level"]

        if metadata_updates:
            enrichment["metadata_updates"] = metadata_updates

        enrichment["_order_id"] = sq_payment.get("order_id")
        return enrichment

    # ─── Inventory Mapper ─────────────────────────────────────

    def map_inventory_count(self, sq_count: dict) -> dict[str, Any]:
        """
        Square InventoryCount → Meridian inventory_snapshots.
        
        Mapping:
          count.catalog_object_id → product_id (via lookup)
          count.location_id       → location_id (via lookup)
          count.quantity          → quantity_on_hand
          count.calculated_at     → snapshot_at
          count.state             → metadata.state
        """
        catalog_id = sq_count.get("catalog_object_id", "")
        sq_location_id = sq_count.get("location_id", "")

        quantity_str = sq_count.get("quantity", "0")
        try:
            quantity = float(Decimal(quantity_str))
        except (ValueError, TypeError):
            quantity = 0.0

        return {
            "id": str(uuid4()),
            "org_id": self.org_id,
            "location_id": self.location_lookup.get(sq_location_id),
            "product_id": self.product_lookup.get(catalog_id),
            "quantity_on_hand": quantity,
            "snapshot_at": sq_count.get("calculated_at", datetime.now(timezone.utc).isoformat()),
            "metadata": {
                "state": sq_count.get("state", ""),
                "square_catalog_id": catalog_id,
            },
        }

    def map_inventory_adjustment(self, sq_adjustment: dict) -> dict[str, Any]:
        """Map Square InventoryAdjustment to derive deltas."""
        from_state = sq_adjustment.get("from_state", "")
        to_state = sq_adjustment.get("to_state", "")
        
        quantity_str = sq_adjustment.get("quantity", "0")
        try:
            quantity = float(Decimal(quantity_str))
        except (ValueError, TypeError):
            quantity = 0.0

        # Derive delta type
        delta = {
            "quantity_received": 0.0,
            "quantity_sold": 0.0,
            "quantity_wasted": 0.0,
        }

        if from_state == "NONE" and to_state == "IN_STOCK":
            delta["quantity_received"] = quantity
        elif from_state == "IN_STOCK" and to_state == "SOLD":
            delta["quantity_sold"] = quantity
        elif from_state == "IN_STOCK" and to_state == "WASTE":
            delta["quantity_wasted"] = quantity

        return delta

    # ─── Team Member Mapper ───────────────────────────────────

    def map_team_member(self, sq_member: dict) -> tuple[str, str]:
        """
        Square TeamMember → (employee_id, "First Last") for cache.
        """
        member_id = sq_member.get("id", "")
        given = sq_member.get("given_name", "")
        family = sq_member.get("family_name", "")
        full_name = f"{given} {family}".strip() or "Unknown"
        return member_id, full_name

    # ─── Helper Methods ───────────────────────────────────────

    @staticmethod
    def _money(obj: dict, field: str) -> int:
        """Extract money amount in cents from Square money object."""
        money = obj.get(field) or {}
        return money.get("amount", 0)

    @staticmethod
    def _map_payment_method(tender: dict) -> str:
        """Map Square tender type → Meridian payment_method enum."""
        tender_type = tender.get("type", "OTHER")
        mapping = {
            "CARD": "credit_card",
            "CASH": "cash",
            "SQUARE_GIFT_CARD": "gift_card",
            "NO_SALE": "other",
            "WALLET": "mobile_pay",
            "OTHER": "other",
        }
        return mapping.get(tender_type, "other")

    @staticmethod
    def _parse_business_hours(sq_hours: dict) -> dict:
        """Convert Square business_hours format → Meridian JSONB format."""
        periods = sq_hours.get("periods", [])
        hours = {}
        
        day_map = {
            "MON": "monday", "TUE": "tuesday", "WED": "wednesday",
            "THU": "thursday", "FRI": "friday", "SAT": "saturday", "SUN": "sunday",
        }
        
        for period in periods:
            day = day_map.get(period.get("day_of_week", ""), "")
            if day:
                hours[day] = {
                    "open": period.get("start_local_time", ""),
                    "close": period.get("end_local_time", ""),
                }
        
        return hours

    @staticmethod
    def _resolve_image_url(item_data: dict) -> str | None:
        """
        Resolve image URL from item data.
        Square stores images as separate CatalogImage objects;
        for now return None, resolved in batch after catalog sync.
        """
        image_ids = item_data.get("image_ids", [])
        return None  # Resolved in post-processing batch

    @staticmethod
    def _extract_order_metadata(sq_order: dict, tenders: list) -> dict:
        """Extract additional metadata from order."""
        meta: dict[str, Any] = {}

        # Customer name from fulfillments
        fulfillments = sq_order.get("fulfillments", [])
        if fulfillments:
            pickup = fulfillments[0].get("pickup_details", {})
            recipient = pickup.get("recipient", {})
            if recipient.get("display_name"):
                meta["customer_name"] = recipient["display_name"]

        # Source (online, in-person, etc.)
        source = sq_order.get("source", {})
        if source.get("name"):
            meta["source"] = source["name"]

        # Reference ID
        if sq_order.get("reference_id"):
            meta["reference_id"] = sq_order["reference_id"]

        # Tender details
        if tenders:
            t = tenders[0]
            if t.get("card_details", {}).get("card", {}).get("card_brand"):
                meta["card_brand"] = t["card_details"]["card"]["card_brand"]

        return meta
