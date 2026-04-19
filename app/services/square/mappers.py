"""
Data mappers: Square API responses → Meridian DB schema.

Six modules, each with a `map_*` function that returns a dict ready for
Supabase upsert (column names match the SQL schema exactly).

All monetary values are kept in *cents* (Square already uses minor units).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _money(obj: dict | None) -> int:
    """Extract cents from a Square Money object (or 0)."""
    if not obj:
        return 0
    return int(obj.get("amount", 0))


def _ts(iso: str | None) -> datetime | None:
    """Parse ISO-8601 timestamp to tz-aware datetime."""
    if not iso:
        return None
    return datetime.fromisoformat(iso.replace("Z", "+00:00"))


def _uuid() -> str:
    return str(uuid.uuid4())


def _safe_decimal(val: str | int | float | None) -> Decimal:
    """Parse a numeric string (Square inventory quantities are strings)."""
    if val is None:
        return Decimal(0)
    return Decimal(str(val))


# ---------------------------------------------------------------------------
# 1. LOCATIONS
# ---------------------------------------------------------------------------
def map_location(sq: dict, org_id: str) -> dict[str, Any]:
    """Square Location → Meridian `locations` row."""
    addr = sq.get("address", {})
    coords = sq.get("coordinates", {})
    return {
        "id": _uuid(),
        "org_id": org_id,
        "name": sq.get("name", "Unnamed Location"),
        "is_primary": sq.get("status") == "ACTIVE",
        "address_line1": addr.get("address_line_1"),
        "city": addr.get("locality"),
        "state": addr.get("administrative_district_level_1"),
        "zip_code": addr.get("postal_code"),
        "latitude": coords.get("latitude"),
        "longitude": coords.get("longitude"),
        "phone": sq.get("phone_number"),
        "business_hours": _map_business_hours(sq.get("business_hours", {})),
        "is_active": sq.get("status") == "ACTIVE",
    }


def _map_business_hours(bh: dict) -> dict:
    """Square BusinessHours → JSONB {monday: {open, close}, …}."""
    result: dict[str, dict] = {}
    for period in bh.get("periods", []):
        day = (period.get("day_of_week") or "").lower()
        if day:
            result[day] = {
                "open": period.get("start_local_time", ""),
                "close": period.get("end_local_time", ""),
            }
    return result


def map_organization_from_location(sq_location: dict) -> dict[str, Any]:
    """Extract org-level fields from the first Square location."""
    return {
        "timezone": sq_location.get("timezone", "America/Los_Angeles"),
        "phone": sq_location.get("phone_number"),
        "business_hours": _map_business_hours(sq_location.get("business_hours", {})),
    }


# ---------------------------------------------------------------------------
# 2. CATALOG  → product_categories + products
# ---------------------------------------------------------------------------
def map_category(sq_obj: dict, org_id: str) -> dict[str, Any]:
    """Square CatalogObject (type=CATEGORY) → `product_categories`."""
    cat_data = sq_obj.get("category_data", {})
    return {
        "id": _uuid(),
        "org_id": org_id,
        "external_id": sq_obj["id"],
        "name": cat_data.get("name", "Uncategorized"),
        "is_active": not sq_obj.get("is_deleted", False),
    }


def map_product_from_item(
    sq_obj: dict,
    org_id: str,
    category_lookup: dict[str, str],
    image_lookup: dict[str, str],
) -> list[dict[str, Any]]:
    """
    Square CatalogObject (type=ITEM) → one or more `products` rows.

    Each ITEM_VARIATION becomes its own row. If there are multiple variations,
    the first is tagged has_variants=True and subsequent get variant_of set.
    """
    item_data = sq_obj.get("item_data", {})
    variations = item_data.get("variations", [])
    sq_category_id = item_data.get("category_id")
    category_id = category_lookup.get(sq_category_id) if sq_category_id else None

    # Resolve first image
    image_ids = item_data.get("image_ids", [])
    image_url = image_lookup.get(image_ids[0]) if image_ids else None

    is_taxable = bool(item_data.get("tax_ids"))
    has_variants = len(variations) > 1

    rows: list[dict[str, Any]] = []
    main_product_id: str | None = None

    for i, var in enumerate(variations):
        var_data = var.get("item_variation_data", {})
        product_id = _uuid()
        if i == 0:
            main_product_id = product_id

        rows.append({
            "id": product_id,
            "org_id": org_id,
            "category_id": category_id,
            "external_id": var["id"],             # variation-level ID
            "name": item_data.get("name", "Unknown Item"),
            "description": item_data.get("description"),
            "sku": var_data.get("sku"),
            "barcode": var_data.get("upc"),
            "price_cents": _money(var_data.get("price_money")),
            "has_variants": has_variants and i == 0,
            "variant_of": main_product_id if i > 0 else None,
            "variant_attrs": {
                "variation_name": var_data.get("name", ""),
                "sku": var_data.get("sku", ""),
            } if has_variants else {},
            "is_active": not sq_obj.get("is_deleted", False),
            "is_taxable": is_taxable,
            "image_url": image_url,
            "metadata": {
                "square_item_id": sq_obj["id"],
                "pricing_type": var_data.get("pricing_type"),
            },
        })

    return rows


# ---------------------------------------------------------------------------
# 3. ORDERS → transactions + transaction_items
# ---------------------------------------------------------------------------
TENDER_MAP = {
    "CARD": "credit_card",
    "CASH": "cash",
    "SQUARE_GIFT_CARD": "gift_card",
    "NO_SALE": "other",
    "WALLET": "mobile_pay",
    "OTHER": "other",
}

STATE_MAP = {
    "COMPLETED": "sale",
    "CANCELED": "void",
    "OPEN": "sale",       # treat open orders as sales-in-progress
}


def map_transaction(
    sq_order: dict,
    org_id: str,
    location_lookup: dict[str, str],
    employee_lookup: dict[str, str],
    pos_connection_id: str | None = None,
) -> dict[str, Any]:
    """Square Order → `transactions` row."""
    tenders = sq_order.get("tenders", [])
    first_tender = tenders[0] if tenders else {}
    tender_type = first_tender.get("type", "OTHER")
    employee_ext = first_tender.get("employee_id") or sq_order.get("employee_id")

    total = _money(sq_order.get("total_money"))
    tax = _money(sq_order.get("total_tax_money"))
    tip = _money(sq_order.get("total_tip_money"))
    discount = _money(sq_order.get("total_discount_money"))
    subtotal = total - tax - tip + discount

    location_ext = sq_order.get("location_id", "")
    transaction_at = _ts(sq_order.get("created_at")) or datetime.now(timezone.utc)

    return {
        "id": _uuid(),
        "org_id": org_id,
        "location_id": location_lookup.get(location_ext),
        "pos_connection_id": pos_connection_id,
        "external_id": sq_order["id"],
        "type": STATE_MAP.get(sq_order.get("state", ""), "sale"),
        "subtotal_cents": max(subtotal, 0),
        "tax_cents": tax,
        "tip_cents": tip,
        "discount_cents": discount,
        "total_cents": total,
        "payment_method": TENDER_MAP.get(tender_type, "other"),
        "employee_name": employee_lookup.get(employee_ext, "") if employee_ext else None,
        "employee_external_id": employee_ext,
        "transaction_at": transaction_at.isoformat(),
        "metadata": _extract_order_metadata(sq_order),
    }


def _extract_order_metadata(sq_order: dict) -> dict:
    meta: dict[str, Any] = {}
    fulfillments = sq_order.get("fulfillments", [])
    if fulfillments:
        pickup = fulfillments[0].get("pickup_details", {})
        recipient = pickup.get("recipient", {})
        if recipient.get("display_name"):
            meta["customer_name"] = recipient["display_name"]
    return meta


def map_transaction_items(
    sq_order: dict,
    org_id: str,
    transaction_id: str,
    transaction_at: str,
    product_lookup: dict[str, str],
) -> list[dict[str, Any]]:
    """Square OrderLineItems → `transaction_items` rows."""
    rows: list[dict[str, Any]] = []
    for li in sq_order.get("line_items", []):
        catalog_obj_id = li.get("catalog_object_id")
        modifiers = [
            {"name": m.get("name", ""), "price": _money(m.get("total_price_money"))}
            for m in li.get("modifiers", [])
        ]
        rows.append({
            "id": _uuid(),
            "transaction_id": transaction_id,
            "transaction_at": transaction_at,
            "org_id": org_id,
            "product_id": product_lookup.get(catalog_obj_id) if catalog_obj_id else None,
            "product_name": li.get("name", "Unknown Item"),
            "quantity": _safe_decimal(li.get("quantity", "1")),
            "unit_price_cents": _money(li.get("base_price_money")),
            "total_cents": _money(li.get("total_money")),
            "discount_cents": _money(li.get("total_discount_money")),
            "modifiers": modifiers,
            "metadata": {"square_uid": li.get("uid")},
        })
    return rows


# ---------------------------------------------------------------------------
# 4. PAYMENTS (enrichment)
# ---------------------------------------------------------------------------
def map_payment_enrichment(sq_payment: dict) -> dict[str, Any]:
    """
    Extract card/risk metadata from a Square Payment to merge into
    the corresponding transaction row's metadata.
    """
    card_details = sq_payment.get("card_details", {})
    card = card_details.get("card", {})
    fees = sq_payment.get("processing_fee", [])
    risk = sq_payment.get("risk_evaluation", {})

    enrichment: dict[str, Any] = {}
    if card.get("card_brand"):
        enrichment["card_brand"] = card["card_brand"]
    if card.get("last_4"):
        enrichment["card_last4"] = card["last_4"]
    if sq_payment.get("tip_money"):
        enrichment["tip_cents_from_payment"] = _money(sq_payment["tip_money"])
    if fees:
        enrichment["processing_fee_cents"] = _money(fees[0].get("amount_money"))
    if risk.get("risk_level"):
        enrichment["risk_level"] = risk["risk_level"]
    return enrichment


# ---------------------------------------------------------------------------
# 5. INVENTORY
# ---------------------------------------------------------------------------
def map_inventory_count(
    sq_count: dict,
    org_id: str,
    product_lookup: dict[str, str],
    location_lookup: dict[str, str],
) -> dict[str, Any] | None:
    """Square InventoryCount → `inventory_snapshots` row."""
    catalog_id = sq_count.get("catalog_object_id")
    product_id = product_lookup.get(catalog_id) if catalog_id else None
    if not product_id:
        return None

    loc_ext = sq_count.get("location_id", "")
    return {
        "id": _uuid(),
        "org_id": org_id,
        "location_id": location_lookup.get(loc_ext),
        "product_id": product_id,
        "quantity_on_hand": _safe_decimal(sq_count.get("quantity")),
        "snapshot_at": (_ts(sq_count.get("calculated_at")) or datetime.now(timezone.utc)).isoformat(),
        "metadata": {"state": sq_count.get("state")},
    }


def derive_inventory_adjustment(
    sq_adj: dict,
    org_id: str,
    product_lookup: dict[str, str],
    location_lookup: dict[str, str],
) -> dict[str, Any] | None:
    """
    Square InventoryAdjustment → delta fields on `inventory_snapshots`.

    from_state → to_state mapping:
      NONE → IN_STOCK    = quantity_received
      IN_STOCK → SOLD    = quantity_sold
      IN_STOCK → WASTE   = quantity_wasted
    """
    catalog_id = sq_adj.get("catalog_object_id")
    product_id = product_lookup.get(catalog_id) if catalog_id else None
    if not product_id:
        return None

    from_state = sq_adj.get("from_state", "")
    to_state = sq_adj.get("to_state", "")
    qty = _safe_decimal(sq_adj.get("quantity"))
    loc_ext = sq_adj.get("location_id", "")

    row: dict[str, Any] = {
        "id": _uuid(),
        "org_id": org_id,
        "location_id": location_lookup.get(loc_ext),
        "product_id": product_id,
        "snapshot_at": (_ts(sq_adj.get("occurred_at")) or datetime.now(timezone.utc)).isoformat(),
    }

    if from_state == "NONE" and to_state == "IN_STOCK":
        row["quantity_received"] = qty
    elif from_state == "IN_STOCK" and to_state == "SOLD":
        row["quantity_sold"] = qty
    elif from_state == "IN_STOCK" and to_state == "WASTE":
        row["quantity_wasted"] = qty
    else:
        row["metadata"] = {"from_state": from_state, "to_state": to_state, "quantity": str(qty)}

    return row


# ---------------------------------------------------------------------------
# 6. TEAM MEMBERS (name cache)
# ---------------------------------------------------------------------------
def build_employee_lookup(sq_team_members: list[dict]) -> dict[str, str]:
    """Square TeamMember list → {team_member_id: 'First Last'}."""
    lookup: dict[str, str] = {}
    for tm in sq_team_members:
        tm_id = tm.get("id", "")
        given = tm.get("given_name", "")
        family = tm.get("family_name", "")
        name = f"{given} {family}".strip() or "Unknown"
        lookup[tm_id] = name
    return lookup
