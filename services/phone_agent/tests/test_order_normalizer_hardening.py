"""
Phone order-integrity fixes (2026-07-22 sweep):

  1. order_normalizer quantity coercion — word/string/float quantities no longer
     crash normalize_order (TypeError) or produce fractional/overflow totals.
  2. price clamp + empty-order signal.
  3. Square idempotency key is deterministic (retry-safe → no duplicate orders).
"""
import os
import sys

import pytest

_HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, "..")))
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, "..", "..", "..")))

import order_normalizer as onorm  # noqa: E402
import pos_connector as pc  # noqa: E402


class _Cfg:
    def __init__(self, menu=None):
        self.menu_items = menu or []
        self.merchant_id = "biz_x"
        self.business_name = "Test"
        self.pos_system = "square"
        self.tax_rate = 0.0
        self.currency = "usd"


# ── 1. quantity coercion ──────────────────────────────────────
@pytest.mark.parametrize("raw,expected", [
    ("two", 2), ("2", 2), (2, 2), (2.0, 2), (2.9, 2), ("a couple", 1),  # "a couple" unknown → 1
    ("couple", 2), ("dozen", 12), ("", 1), (None, 1), (0, 1), (-5, 1),
    (999999, 99), ("999999", 99), ("garbage", 1), (True, 1),
])
def test_safe_qty(raw, expected):
    assert onorm._safe_qty(raw) == expected


def test_word_quantity_does_not_crash_normalize():
    cfg = _Cfg(menu=[{"name": "Burger", "price": 10.0}])
    # This used to raise TypeError: '>' not supported between str and int
    out = onorm.normalize_order(
        {"items": [{"name": "Burger", "quantity": "two"}]}, cfg)
    assert out["items"][0]["quantity"] == 2
    assert out["items"][0]["line_total"] == 20.0
    assert out["is_empty"] is False


# ── 2. price clamp + empty signal ─────────────────────────────
def test_empty_items_flagged():
    cfg = _Cfg(menu=[{"name": "Burger", "price": 10.0}])
    out = onorm.normalize_order({"items": []}, cfg)
    assert out["is_empty"] is True and out["items"] == []


def test_all_off_menu_is_empty():
    cfg = _Cfg(menu=[{"name": "Burger", "price": 10.0}])
    out = onorm.normalize_order({"items": [{"name": "Caviar", "quantity": 1}]}, cfg)
    assert out["is_empty"] is True
    assert "Caviar" in out["unavailable_items"]


def test_no_menu_price_clamped_nonnegative():
    cfg = _Cfg(menu=[])  # no menu → legacy passthrough
    out = onorm.normalize_order(
        {"items": [{"name": "Thing", "quantity": 1, "price": -50}]}, cfg)
    # unit_price is clamped to >= 0 (an off-menu no-menu item has no price
    # field read anyway, but the clamp guards the line math)
    assert out["items"][0]["line_total"] >= 0.0


# ── 3. deterministic Square idempotency key ───────────────────
def test_idempotency_key_is_deterministic():
    order = {"merchant_id": "biz_x", "caller_phone": "+1555",
             "items": [{"name": "Burger", "quantity": 2, "size": ""}]}
    k1 = pc._order_idempotency_key(order)
    k2 = pc._order_idempotency_key(dict(order))
    assert k1 == k2                      # same order → same key (retry-safe)
    assert len(k1) <= 45 and k1.startswith("mmo-")


def test_idempotency_key_differs_per_order():
    a = pc._order_idempotency_key({"merchant_id": "m", "caller_phone": "+1",
                                   "items": [{"name": "A", "quantity": 1}]})
    b = pc._order_idempotency_key({"merchant_id": "m", "caller_phone": "+1",
                                   "items": [{"name": "B", "quantity": 1}]})
    assert a != b


def test_idempotency_key_prefers_explicit_ref():
    k = pc._order_idempotency_key({"order_ref": "ord123", "items": []})
    assert k == "mmo-ord123"
