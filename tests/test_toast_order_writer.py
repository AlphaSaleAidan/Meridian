"""
Toast order writer — pure mapping tests (no network).

Covers name→GUID resolution, dining-option resolution, the GUID-referenced
payload shape, and the unresolved-item failure signal that drives the SMS
fallback. The live Toast payload is only verified against a real sandbox; these
lock the mapping contract so a rename/refactor can't silently break it.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.toast.order_writer import (  # noqa: E402
    ToastMenuResolver,
    build_toast_order,
    order_writer_enabled,
)

MENU = [
    {"guid": "item-burger", "name": "Cheeseburger", "_menu_group_guid": "grp-mains"},
    {"guid": "item-fries", "name": "Large Fries!", "_menu_group_guid": "grp-sides"},
    {"guid": "", "name": "No GUID Item", "_menu_group_guid": "grp-x"},  # skipped
]
DINING = [
    {"guid": "do-takeout", "name": "Takeout", "behavior": "TAKE_OUT"},
    {"guid": "do-delivery", "name": "Delivery", "behavior": "DELIVERY"},
]


def _resolver():
    return ToastMenuResolver(MENU, DINING)


def test_flag_default_off():
    os.environ.pop("TOAST_ORDER_WRITER_ENABLED", None)
    assert order_writer_enabled() is False
    os.environ["TOAST_ORDER_WRITER_ENABLED"] = "true"
    try:
        assert order_writer_enabled() is True
    finally:
        os.environ.pop("TOAST_ORDER_WRITER_ENABLED", None)


def test_item_resolution_is_normalized():
    r = _resolver()
    # Case + punctuation + whitespace insensitive.
    assert r.resolve_item("cheeseburger") == ("item-burger", "grp-mains")
    assert r.resolve_item("large fries") == ("item-fries", "grp-sides")
    assert r.resolve_item("Unknown Thing") is None


def test_items_without_guid_are_not_indexed():
    r = _resolver()
    assert r.resolve_item("No GUID Item") is None


def test_dining_option_resolution():
    r = _resolver()
    assert r.resolve_dining_option("pickup") == "do-takeout"
    assert r.resolve_dining_option("delivery") == "do-delivery"
    # dine_in has no matching option → falls back to TAKE_OUT.
    assert r.resolve_dining_option("dine_in") == "do-takeout"


def test_build_success_produces_guid_payload():
    order = {
        "merchant_id": "m1", "order_id": "o9", "order_type": "pickup",
        "customer_name": "Jane Doe", "caller_phone": "+15550001111",
        "items": [
            {"name": "Cheeseburger", "quantity": 2, "special_instructions": "no onion"},
            {"name": "Large Fries", "quantity": 1},
        ],
    }
    out = build_toast_order(order, _resolver())
    assert out["ok"] is True
    p = out["payload"]
    assert p["diningOption"] == {"guid": "do-takeout", "entityType": "DiningOption"}
    sels = p["checks"][0]["selections"]
    assert sels[0]["item"] == {"guid": "item-burger", "entityType": "MenuItem"}
    assert sels[0]["itemGroup"] == {"guid": "grp-mains", "entityType": "MenuGroup"}
    assert sels[0]["quantity"] == 2
    assert sels[0]["specialRequest"] == "no onion"
    assert sels[1]["item"]["guid"] == "item-fries"
    cust = p["checks"][0]["customer"]
    assert cust["firstName"] == "Jane" and cust["lastName"] == "Doe"
    assert p["externalId"] == "meridian-phone-m1-o9"


def test_build_fails_on_unresolved_item():
    order = {
        "merchant_id": "m1", "order_type": "pickup",
        "items": [
            {"name": "Cheeseburger", "quantity": 1},
            {"name": "Truffle Risotto", "quantity": 1},  # not on menu
        ],
    }
    out = build_toast_order(order, _resolver())
    assert out["ok"] is False
    assert out["reason"] == "unresolved_items"
    assert out["unresolved"] == ["Truffle Risotto"]


def test_build_fails_when_no_dining_option():
    resolver = ToastMenuResolver(MENU, [])  # no dining options at all
    order = {"order_type": "pickup", "items": [{"name": "Cheeseburger", "quantity": 1}]}
    out = build_toast_order(order, resolver)
    assert out["ok"] is False
    assert out["reason"] == "no_dining_option"


def test_build_fails_on_empty_order():
    out = build_toast_order({"order_type": "pickup", "items": []}, _resolver())
    assert out["ok"] is False
    assert out["reason"] == "no_items"
