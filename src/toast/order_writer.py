"""
Toast Order Writer — build a real GUID-referenced Toast Orders-API v2 payload
from a Meridian phone order.

Why this exists: Toast's Orders API does NOT accept item names/prices. Every
selection must reference a live menu-item GUID + its menu-group GUID, and the
order's dining option must reference a dining-option GUID. The phone agent only
knows item *names*, so we resolve names → GUIDs against the merchant's live
Toast menu before writing. Any item we can't resolve means the order can't be
trusted to post correctly — the caller falls back to the SMS/dashboard path.

Flag-gated OFF (TOAST_ORDER_WRITER_ENABLED). Off until verified against a real
Toast sandbox — the wiring, mapping, and fallback are covered by unit tests, but
the live payload shape can only be confirmed against Toast's API.

Pure functions here take already-fetched menu + dining-option lists, so the
resolver is fully testable without network access.
"""
import os
import re


def order_writer_enabled() -> bool:
    return os.environ.get("TOAST_ORDER_WRITER_ENABLED", "").strip().lower() in (
        "1", "true", "yes", "on")


# order_type (Meridian) → Toast dining-option behavior
_ORDER_TYPE_TO_BEHAVIOR = {
    "pickup": "TAKE_OUT",
    "takeout": "TAKE_OUT",
    "take_out": "TAKE_OUT",
    "delivery": "DELIVERY",
    "dine_in": "DINE_IN",
    "reservation": "DINE_IN",
}


def _norm(name: str) -> str:
    """Normalize a menu-item name for matching: lowercase, collapse whitespace,
    drop punctuation. 'Large  Fries!' and 'large fries' resolve to the same key."""
    return re.sub(r"[^a-z0-9 ]", "", (name or "").lower()).strip()


class ToastMenuResolver:
    """Resolves phone-order item names + dining option to live Toast GUIDs."""

    def __init__(self, menu_items: list[dict], dining_options: list[dict]):
        # name → (item_guid, group_guid). Later duplicates don't clobber the
        # first (menus can repeat an item across groups; first wins).
        self._by_name: dict[str, tuple[str, str]] = {}
        for it in menu_items or []:
            guid = it.get("guid")
            if not guid:
                continue
            key = _norm(it.get("name", ""))
            if key and key not in self._by_name:
                self._by_name[key] = (guid, it.get("_menu_group_guid", "") or "")
        # behavior → dining-option guid (first match wins)
        self._dining_by_behavior: dict[str, str] = {}
        for opt in dining_options or []:
            beh = (opt.get("behavior") or "").upper()
            guid = opt.get("guid")
            if beh and guid and beh not in self._dining_by_behavior:
                self._dining_by_behavior[beh] = guid

    def resolve_item(self, name: str) -> tuple[str, str] | None:
        return self._by_name.get(_norm(name))

    def resolve_dining_option(self, order_type: str) -> str | None:
        behavior = _ORDER_TYPE_TO_BEHAVIOR.get((order_type or "pickup").lower(), "TAKE_OUT")
        # Exact behavior match, else fall back to a TAKE_OUT option if present.
        return self._dining_by_behavior.get(behavior) or self._dining_by_behavior.get("TAKE_OUT")


def build_toast_order(order: dict, resolver: ToastMenuResolver) -> dict:
    """Build a GUID-referenced Toast Orders-v2 payload, or a failure marker.

    Returns {"ok": True, "payload": {...}} when every item + the dining option
    resolved to a GUID. Returns {"ok": False, "reason": ..., "unresolved": [...]}
    otherwise, so the caller can fall back to the notification path instead of
    posting a half-mapped order Toast would reject or mis-charge.
    """
    items = order.get("items", []) or []
    if not items:
        return {"ok": False, "reason": "no_items", "unresolved": []}

    dining_guid = resolver.resolve_dining_option(order.get("order_type", "pickup"))
    if not dining_guid:
        return {"ok": False, "reason": "no_dining_option", "unresolved": []}

    selections = []
    unresolved = []
    for item in items:
        resolved = resolver.resolve_item(item.get("name", ""))
        if not resolved:
            unresolved.append(item.get("name", ""))
            continue
        item_guid, group_guid = resolved
        sel = {
            "item": {"guid": item_guid, "entityType": "MenuItem"},
            "quantity": item.get("quantity", 1),
        }
        if group_guid:
            sel["itemGroup"] = {"guid": group_guid, "entityType": "MenuGroup"}
        special = item.get("special_instructions") or ""
        if special:
            sel["specialRequest"] = special
        selections.append(sel)

    if unresolved:
        return {"ok": False, "reason": "unresolved_items", "unresolved": unresolved}

    name = (order.get("customer_name") or "").strip()
    first = name.split()[0] if name else "Phone"
    last = " ".join(name.split()[1:]) if len(name.split()) > 1 else "Order"

    payload = {
        "entityType": "Order",
        "externalId": f"meridian-phone-{order.get('merchant_id', '')}-{order.get('order_id', '')}".rstrip("-"),
        "diningOption": {"guid": dining_guid, "entityType": "DiningOption"},
        "checks": [
            {
                "customer": {
                    "firstName": first,
                    "lastName": last,
                    "phone": order.get("caller_phone", ""),
                },
                "selections": selections,
            }
        ],
    }
    return {"ok": True, "payload": payload}
