"""
Order normalizer — transforms raw LLM function call arguments into a
standardized order structure suitable for POS API submission.
Matches items against the merchant's menu, resolves sizes, and calculates totals.
"""
import logging
from typing import Any

from merchant_config import MerchantPhoneConfig

logger = logging.getLogger("meridian.phone_agent.normalizer")

# Cap a single line's quantity so a mis-heard "nine nine nine" can't produce an
# overflow-scale order/charge; and clamp any unit price to a sane ceiling.
_MAX_QTY = 99
_MAX_UNIT_PRICE = 9999.99

_WORD_NUMBERS = {
    "a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
    "twelve": 12, "dozen": 12, "couple": 2, "few": 3,
}


def _safe_qty(raw: Any) -> int:
    """Coerce an LLM/ASR quantity (int, float, "2", or a word like "two") to a
    bounded int in [1, _MAX_QTY]. Unparseable → 1 (never crash, never 0)."""
    if isinstance(raw, bool):  # bool is an int subclass — treat as 1
        return 1
    if isinstance(raw, (int, float)):
        try:
            n = int(raw)
        except (ValueError, OverflowError):
            return 1
        return max(1, min(n, _MAX_QTY))
    s = str(raw or "").strip().lower()
    if s.isdigit():
        return max(1, min(int(s), _MAX_QTY))
    if s in _WORD_NUMBERS:
        return max(1, min(_WORD_NUMBERS[s], _MAX_QTY))
    return 1


def normalize_order(raw_order: dict[str, Any], config: MerchantPhoneConfig) -> dict:
    items = []
    subtotal = 0.0
    unavailable: list[str] = []
    has_menu = bool(getattr(config, "menu_items", None))

    for raw_item in raw_order.get("items", []):
        item_name = raw_item.get("name", "").strip()
        # LLM/ASR quantity may be a word ("two"), a string, or a float —
        # max(1, "two") raised TypeError and 500'd the whole order before
        # pricing/dispatch. _safe_qty coerces to a bounded int.
        quantity = _safe_qty(raw_item.get("quantity", 1))
        size = raw_item.get("size", "").strip().lower()
        modifications = raw_item.get("modifications", [])
        special = raw_item.get("special_instructions", "")

        menu_match = _find_menu_item(item_name, config.menu_items)

        modifier_total = 0.0
        if menu_match:
            resolved_name = menu_match["name"]

            # Per-size pricing: `size_prices` ({size: price}) takes precedence over
            # a flat `price`. Sizes default to size_prices keys when not listed.
            size_prices = {str(k).lower(): float(v)
                           for k, v in (menu_match.get("size_prices") or {}).items()}
            available_sizes = [s.lower() for s in (menu_match.get("sizes") or list(size_prices))]
            if size and size not in available_sizes and available_sizes:
                size = available_sizes[0]
            elif not size and available_sizes:
                size = available_sizes[0]

            if size_prices:
                unit_price = size_prices.get(size, next(iter(size_prices.values())))
            else:
                unit_price = float(menu_match.get("price", 0.0))

            # Topping/add-on surcharge: `topping_price` × number of modifications
            # (e.g. pizza toppings at +$2 each). Items without it treat
            # modifications as free options.
            topping_price = float(menu_match.get("topping_price", 0.0))
            if topping_price:
                modifier_total = topping_price * len(modifications)
        else:
            # A merchant WITH a menu: an unmatched item must never ride along
            # at $0.00 (the kitchen would make it, the merchant would eat it).
            # Drop it and report it so the agent can tell the caller. Merchants
            # with NO configured menu keep the legacy pass-through behavior.
            if has_menu:
                logger.warning("Dropping off-menu item from order: %r", item_name)
                if item_name:
                    unavailable.append(item_name)
                continue
            resolved_name = item_name
            unit_price = 0.0

        # Clamp the unit price to a sane, non-negative ceiling — a no-menu
        # merchant's item price (or a bad size_prices value) must never go
        # negative or overflow the charge.
        try:
            unit_price = max(0.0, min(float(unit_price), _MAX_UNIT_PRICE))
        except (TypeError, ValueError):
            unit_price = 0.0
        line_total = round((unit_price + max(0.0, modifier_total)) * quantity, 2)
        subtotal += line_total

        items.append({
            "name": resolved_name,
            "quantity": quantity,
            "size": size,
            "unit_price": unit_price,
            "modifier_total": round(modifier_total, 2),
            "line_total": line_total,
            "modifications": modifications,
            "special_instructions": special,
            "matched_menu_item": bool(menu_match),
        })

    # An order with nothing left (all items off-menu, or an empty items list)
    # must not become a $0 order that dispatches to the kitchen. Signal it so
    # the caller (submit_order) can tell the customer instead of confirming an
    # empty order. unavailable[] already carries what was dropped.
    order_is_empty = not items

    tax_rate = config.tax_rate if hasattr(config, 'tax_rate') else 0.13
    tax = round(subtotal * tax_rate, 2)
    total = round(subtotal + tax, 2)

    # A delivery order with no address is invalid — the LLM/ASR sometimes sets
    # "delivery" without collecting an address. Fall back to pickup so we never
    # produce a broken delivery order or text the customer the wrong fulfillment.
    order_type = (raw_order.get("order_type") or "pickup").strip().lower()
    delivery_address = (raw_order.get("delivery_address") or "").strip()
    if order_type == "delivery" and not delivery_address:
        logger.info("delivery order with no address → pickup (order from %s)",
                    raw_order.get("customer_name", "?"))
        order_type = "pickup"

    # Derive currency from merchant config.  Explicit config.currency wins;
    # otherwise infer from country/language indicators (CA/fr → cad).
    _cfg_currency = getattr(config, 'currency', None)
    if _cfg_currency:
        order_currency = _cfg_currency.lower()
    else:
        _country = (getattr(config, 'country', '') or '').upper()
        _language = (getattr(config, 'language', '') or '').lower()
        if _country in ('CA', 'CAN', 'CANADA') or _language == 'fr':
            order_currency = 'cad'
        else:
            order_currency = 'usd'

    return {
        "merchant_id": config.merchant_id,
        "business_name": config.business_name,
        "customer_name": raw_order.get("customer_name", ""),
        "order_type": order_type,
        "items": items,
        "unavailable_items": unavailable,
        # True when nothing priceable remains — callers must NOT dispatch a $0
        # order to the kitchen (submit_order tells the customer instead).
        "is_empty": order_is_empty,
        "subtotal": round(subtotal, 2),
        "tax": tax,
        "total": total,
        "currency": order_currency,
        "delivery_address": delivery_address,
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
