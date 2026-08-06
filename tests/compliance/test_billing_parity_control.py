"""PI1 control — billing parity: every payment-rail builder must bill exactly
the total the order was confirmed at (+ any explicit customer surcharge).

This is a RATCHET, not a unit test: it enumerates every known link builder and
runs a matrix of order shapes (plain, taxed, topping modifiers, discount,
unpriced items) through each. A future change that lets any rail drift from
the confirmed total — the 2026-08-06 incident class, where itemized checkouts
silently dropped tax + modifier charges and merchants ate the difference —
fails CI here before it can reach a real order.

Offline and deterministic: Stripe/Square/httpx are faked; no network.
"""
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "services" / "phone_agent"))

import payment_links as pl  # noqa: E402

aio = pytest.mark.asyncio


def _cents(x: float) -> int:
    return int(round(x * 100))


# ── the order matrix: every shape the normalizer can produce ──────────
# (name, order dict). "total" is the confirmed amount the caller heard.
ORDER_MATRIX = [
    ("plain", {
        "merchant_id": "m1", "currency": "cad",
        "items": [{"name": "Cheese Pizza", "quantity": 1, "unit_price": 20.0}],
        "total": 20.0}),
    ("taxed", {
        "merchant_id": "m1", "currency": "cad",
        "items": [{"name": "Cheese Pizza", "quantity": 1, "unit_price": 20.0}],
        "tax": 2.60, "total": 22.60}),
    ("modifiers_and_tax", {
        "merchant_id": "m1", "currency": "cad",
        "items": [
            {"name": "Large Pepperoni", "quantity": 2, "unit_price": 18.0,
             "modifier_total": 1.5, "line_total": 39.0},
            {"name": "Wings", "quantity": 1, "unit_price": 12.0}],
        "tax": 6.63, "total": 57.63}),
    ("discounted_total", {
        "merchant_id": "m1", "currency": "cad",
        "items": [{"name": "Combo", "quantity": 1, "unit_price": 30.0}],
        "total": 25.0}),
    ("unpriced_items", {
        "merchant_id": "m1", "currency": "cad",
        "items": [{"name": "Chef Special", "quantity": 1}],
        "total": 41.81}),
    ("usd_market", {
        "merchant_id": "m1", "currency": "usd",
        "items": [{"name": "Burger", "quantity": 3, "unit_price": 9.5}],
        "tax": 2.28, "total": 30.78}),
]


def _cfg(**kw):
    base = dict(stripe_account_id="", stripe_charges_enabled=False,
                plan_tier="", fee_allocation_mode=None, order_fee_cents=None)
    base.update(kw)
    return SimpleNamespace(**base)


class _StripeObj:
    def __init__(self, **d):
        self._d = d

    def __getitem__(self, k):
        return self._d[k]


def _total_cents(order: dict) -> int:
    """Stripe-rail expectation: the choke-point invariant guarantees the
    session bills EXACTLY the confirmed total, every shape — itemized lines
    that don't sum to it are collapsed to one exact-total line."""
    return _cents(float(order.get("total") or 0))


def _itemized_floor_cents(order: dict) -> int:
    """Square/HCO expectation: these rails bill line items + positive deltas
    only (no negative lines), so a total below the items sum — which the
    normalizer never produces today (total = subtotal + tax) — floors at the
    items sum. Everything else bills the confirmed total exactly."""
    items_cents = sum(
        _cents(float(i.get("unit_price", 0) or 0)) * int(i.get("quantity", 1) or 1)
        for i in order.get("items", []))
    prices_known = all(i.get("unit_price") is not None or i.get("price") is not None
                      for i in order.get("items", []))
    if prices_known and order.get("items"):
        return max(_total_cents(order), items_cents)
    return _total_cents(order)


# ── rail 1: Stripe checkout ───────────────────────────────────────────

@aio
@pytest.mark.parametrize("name,order", ORDER_MATRIX)
async def test_stripe_rail_bills_confirmed_total(monkeypatch, name, order):
    captured = {}

    class FakeStripe:
        class checkout:
            class Session:
                @staticmethod
                def create(**kwargs):
                    captured.update(kwargs)
                    return _StripeObj(id="cs_x", url="https://checkout.stripe.com/x")

    monkeypatch.setattr(pl, "_stripe", lambda: FakeStripe)
    monkeypatch.setattr(pl, "UNIFIED_PAYMENTS_ENABLED", True)
    monkeypatch.setattr(pl, "STRIPE_SECRET_KEY", "sk_test_x")
    monkeypatch.setattr(pl, "DEMO_TEST_CHARGE_CENTS", 0)
    await pl._stripe_checkout(order, _cfg(), f"ctl-{name}")
    billed = sum(li["price_data"]["unit_amount"] * li["quantity"]
                 for li in captured["line_items"])
    assert billed == _total_cents(order), (
        f"Stripe rail billed {billed}¢ for '{name}' but the confirmed total "
        f"is {_total_cents(order)}¢ — billing drift (see 2026-08-06 incident)")


# ── rail 2: Square payment link ───────────────────────────────────────

@aio
@pytest.mark.parametrize("name,order", ORDER_MATRIX)
async def test_square_rail_bills_confirmed_total(monkeypatch, name, order):
    if not all(i.get("unit_price") is not None for i in order["items"]):
        pytest.skip("square link builder is only used with priced items")
    sent = {}

    class FakeResp:
        status_code = 200

        @staticmethod
        def json():
            return {"payment_link": {"url": "https://square.link/x", "id": "pl1"}}

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, json=None, headers=None, **kw):
            sent.update(json or {})
            return FakeResp()

    monkeypatch.setattr(pl.httpx, "AsyncClient", FakeClient)
    await pl._square_payment_link(order, "tok", "loc", f"ctl-{name}")
    lines = sent["order"]["line_items"]
    billed = sum(li["base_price_money"]["amount"] * int(li["quantity"]) for li in lines)
    assert billed == _itemized_floor_cents(order), (
        f"Square rail billed {billed}¢ for '{name}' but the confirmed total "
        f"is {_itemized_floor_cents(order)}¢ — billing drift")


# ── rail 3: Clover HCO cart ───────────────────────────────────────────

@pytest.mark.parametrize("name,order", ORDER_MATRIX)
def test_clover_hco_rail_bills_confirmed_total(name, order):
    lines, _subtotal = pl._clover_hco_line_items(dict(order))
    billed = sum(li["price"] * li["unitQty"] for li in lines
                 if li["name"] != "Service & processing fee")
    assert billed == _itemized_floor_cents(order), (
        f"Clover HCO rail billed {billed}¢ for '{name}' but the confirmed "
        f"total is {_itemized_floor_cents(order)}¢ — billing drift")


# ── the monitor itself must stay enabled by default ───────────────────

def test_billing_monitor_default_on(monkeypatch):
    monkeypatch.delenv("MERIDIAN_BILLING_MONITOR", raising=False)
    from src.services import billing_monitor
    assert billing_monitor.is_enabled(), (
        "billing monitor must be ON by default — it is the standing watch "
        "for the 2026-08-06 undercharge incident class")
