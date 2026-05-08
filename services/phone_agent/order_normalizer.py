"""
Order normalizer — transforms raw LLM function call arguments into a
standardized order structure suitable for POS API submission.
Matches items against the merchant's menu, resolves sizes, and calculates totals.
"""
import logging
from typing import Any

from merchant_config import MerchantPhoneConfig

logger = logging.getLogger("meridian.phone_agent.normalizer")


def normalize_order(raw_order: dict[str, Any], config: MerchantPhoneConfig) -> dict:
    items = []
    subtotal = 0.0

    for raw_item in raw_order.get("items", []):
        item_name = raw_item.get("name", "").strip()
        quantity = max(1, raw_item.get("quantity", 1))
        size = raw_item.get("size", "").strip().lower()
        modifications = raw_item.get("modifications", [])
        special = raw_item.get("special_instructions", "")

        menu_match = _find_menu_item(item_name, config.menu_items)

        if menu_match:
            resolved_name = menu_match["name"]
            unit_price = menu_match.get("price", 0.0)

            available_sizes = [s.lower() for s in menu_match.get("sizes", [])]
            if size and size not in available_sizes and available_sizes:
                size = available_sizes[0]
            elif not size and available_sizes:
                size = available_sizes[0]
        else:
            resolved_name = item_name
            unit_price = 0.0

        line_total = unit_price * quantity
        subtotal += line_total

        items.append({
            "name": resolved_name,
            "quantity": quantity,
            "size": size,
            "unit_price": unit_price,
            "line_total": line_total,
            "modifications": modifications,
            "special_instructions": special,
            "matched_menu_item": bool(menu_match),
        })

    tax_rate = 0.13
    tax = round(subtotal * tax_rate, 2)
    total = round(subtotal + tax, 2)

    return {
        "merchant_id": config.merchant_id,
        "business_name": config.business_name,
        "customer_name": raw_order.get("customer_name", ""),
        "order_type": raw_order.get("order_type", "pickup"),
        "items": items,
        "subtotal": round(subtotal, 2),
        "tax": tax,
        "total": total,
        "delivery_address": raw_order.get("delivery_address", ""),
        "special_requests": raw_order.get("special_requests", ""),
        "caller_phone": raw_order.get("caller_phone", ""),
        "source": "phone_agent",
        "pos_system": config.pos_system,
    }


def _find_menu_item(name: str, menu_items: list[dict]) -> dict | None:
    name_lower = name.lower()

    for item in menu_items:
        if item["name"].lower() == name_lower:
            return item

    for item in menu_items:
        item_words = set(item["name"].lower().split())
        input_words = set(name_lower.split())
        overlap = item_words & input_words
        if len(overlap) >= len(item_words) * 0.6:
            return item

    for item in menu_items:
        if name_lower in item["name"].lower() or item["name"].lower() in name_lower:
            return item

    logger.warning("No menu match found for: %s", name)
    return None
