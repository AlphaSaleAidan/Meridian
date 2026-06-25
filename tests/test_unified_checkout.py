"""
UNIFIED PAYMENTS (Stripe Connect) — checkout-routing + money-math coverage.

Stripe is mocked; these pin the parts that must be right before real money flows:

  1. amount math: prefer order total, else sum item prices (cents).
  2. line items: itemized when items carry prices, else one correct total line.
  3. routing: create_checkout uses Stripe ONLY when enabled + onboarded +
     charges_enabled; otherwise falls back to the per-POS payment link.
  4. the Connect session is a destination charge to the merchant's account with
     the right amount + application fee.
"""
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_DIR = str(Path(__file__).resolve().parents[1] / "services" / "phone_agent")
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)

import payment_links as pl  # noqa: E402

aio = pytest.mark.asyncio

ORDER = {
    "merchant_id": "m1", "caller_phone": "+15551234567", "currency": "cad",
    "items": [
        {"name": "Cheeseburger", "quantity": 2, "unit_price": 9.5, "size": "double"},
        {"name": "Fries", "quantity": 1, "unit_price": 3.5},
    ],
    "total": 22.5,
}


def _cfg(**kw):
    base = dict(stripe_account_id="", stripe_charges_enabled=False,
                pos_system="square", pos_access_token="tok", pos_location_id="loc")
    base.update(kw)
    return SimpleNamespace(**base)


class _StripeObj:
    """Mimics a real Stripe SDK object: subscript access only, NO .get() —
    accessing .get raises AttributeError just like StripeObject, so code that
    calls session.get(...) is caught by tests (it shipped broken once)."""
    def __init__(self, **d):
        self._d = d

    def __getitem__(self, k):
        return self._d[k]


class _FakeStripe:
    captured: dict = {}

    class checkout:
        class Session:
            @staticmethod
            def create(**kwargs):
                _FakeStripe.captured = kwargs
                return _StripeObj(id="cs_test_123", url="https://checkout.stripe.com/pay/cs_test_123")


def test_amount_prefers_total():
    assert pl._order_amount_cents({"total": 22.5}) == 2250


def test_amount_sums_items_when_no_total():
    cents = pl._order_amount_cents({"items": ORDER["items"]})
    assert cents == 2 * 950 + 1 * 350  # 2250


def test_line_items_itemized_when_priced():
    items = pl._stripe_line_items(ORDER, "cad")
    assert len(items) == 2
    assert items[0]["price_data"]["unit_amount"] == 950
    assert items[0]["price_data"]["product_data"]["name"] == "Cheeseburger (double)"
    assert items[0]["quantity"] == 2


def test_line_items_single_total_when_unpriced():
    order = {"total": 22.5, "items": [{"name": "Combo", "quantity": 1}]}
    items = pl._stripe_line_items(order, "cad")
    assert len(items) == 1
    assert items[0]["price_data"]["unit_amount"] == 2250


@aio
async def test_create_checkout_platform_direct_when_not_onboarded(monkeypatch):
    # Key present but merchant has no connected Stripe account (demo / pre-Connect):
    # must STILL produce a real Stripe link — a direct charge on the platform
    # account — NOT fall back to the per-POS link (which strands CAD on a dead page).
    monkeypatch.setattr(pl, "UNIFIED_PAYMENTS_ENABLED", True)
    monkeypatch.setattr(pl, "STRIPE_SECRET_KEY", "sk_test")
    monkeypatch.setattr(pl, "_stripe", lambda: _FakeStripe)

    async def no_record(*a, **k):
        return None

    monkeypatch.setattr(pl, "_record_checkout_session", no_record)

    async def fail_link(*a, **k):
        raise AssertionError("must not fall back to per-POS link when Stripe is ready")

    monkeypatch.setattr(pl, "create_payment_link", fail_link)

    out = await pl.create_checkout(ORDER, _cfg(), "ord_1")
    assert out["method"] == "stripe"
    assert out["url"].startswith("https://checkout.stripe.com")
    # platform-direct => NO destination transfer / application fee
    assert "payment_intent_data" not in _FakeStripe.captured
    assert _FakeStripe.captured["line_items"][0]["price_data"]["currency"] == "cad"


@aio
async def test_create_checkout_falls_back_when_flag_off(monkeypatch):
    monkeypatch.setattr(pl, "UNIFIED_PAYMENTS_ENABLED", False)
    monkeypatch.setattr(pl, "STRIPE_SECRET_KEY", "sk_test")

    async def fake_link(*a, **k):
        return {"url": "x", "method": "square"}

    monkeypatch.setattr(pl, "create_payment_link", fake_link)
    out = await pl.create_checkout(ORDER, _cfg(stripe_account_id="acct_1", stripe_charges_enabled=True), "ord_1")
    assert out["method"] == "square"  # flag off → never Stripe


@aio
async def test_create_checkout_uses_stripe_when_ready(monkeypatch):
    monkeypatch.setattr(pl, "UNIFIED_PAYMENTS_ENABLED", True)
    monkeypatch.setattr(pl, "STRIPE_SECRET_KEY", "sk_test")
    monkeypatch.setattr(pl, "PLATFORM_FEE_BPS", 100)  # 1%
    monkeypatch.setattr(pl, "_stripe", lambda: _FakeStripe)

    async def no_record(*a, **k):
        return None

    monkeypatch.setattr(pl, "_record_checkout_session", no_record)

    out = await pl.create_checkout(
        ORDER, _cfg(stripe_account_id="acct_merchant", stripe_charges_enabled=True), "ord_42")
    assert out["method"] == "stripe"
    assert out["url"].startswith("https://checkout.stripe.com")
    cap = _FakeStripe.captured
    assert cap["mode"] == "payment"
    assert cap["payment_intent_data"]["transfer_data"]["destination"] == "acct_merchant"
    assert cap["payment_intent_data"]["application_fee_amount"] == 22  # 1% of 2250c = 22.5 -> 22 (round half-to-even)
    assert cap["metadata"]["pos_order_id"] == "ord_42"
