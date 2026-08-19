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


def test_line_items_tax_delta_line_charges_full_total():
    # Normalizer totals carry tax (and topping modifiers) that per-item
    # unit_price lines don't — the delta MUST be billed or the merchant
    # silently eats it. 22.50 items + 13% HST → 25.43.
    order = dict(ORDER, total=25.43)
    items = pl._stripe_line_items(order, "cad")
    assert len(items) == 3
    tax = items[-1]
    assert tax["price_data"]["product_data"]["name"] == "Tax & extras"
    assert tax["price_data"]["unit_amount"] == 2543 - 2250
    billed = sum(i["price_data"]["unit_amount"] * i["quantity"] for i in items)
    assert billed == 2543


def test_line_items_no_delta_line_when_total_matches():
    items = pl._stripe_line_items(ORDER, "cad")  # total == items sum
    assert len(items) == 2


def test_line_items_no_negative_delta_line():
    # A discounted/comped total below the items sum must not create a
    # negative line (Stripe rejects it) — items stand as-is.
    order = dict(ORDER, total=20.00)
    items = pl._stripe_line_items(order, "cad")
    assert len(items) == 2


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
async def test_checkout_returns_direct_stripe_link(monkeypatch):
    # The customer-facing url is the CUSTOM STRIPE CHECKOUT LINK directly
    # (checkout.stripe.com/<session>), NOT the /p/ meridian redirect — Aidan
    # 2026-08-20. The checkout_sessions row is still persisted (webhook +
    # phone_orders claim key off session_id), so short_code is still returned.
    monkeypatch.setattr(pl, "UNIFIED_PAYMENTS_ENABLED", True)
    monkeypatch.setattr(pl, "STRIPE_SECRET_KEY", "sk_test")
    monkeypatch.setattr(pl, "PUBLIC_PAY_BASE", "https://api.meridian.tips")
    monkeypatch.setattr(pl, "_stripe", lambda: _FakeStripe)

    recorded_calls = []

    async def recorded(*a, **k):
        recorded_calls.append(1)
        return True

    monkeypatch.setattr(pl, "_record_checkout_session", recorded)
    out = await pl.create_checkout(ORDER, _cfg(), "ord_x")
    assert out["method"] == "stripe"
    assert out["url"].startswith("https://checkout.stripe.com")
    assert out["url"] == out["checkout_url"]          # the direct Stripe URL is what we text
    assert "/p/" not in out["url"]                    # no meridian redirect wrapper
    assert recorded_calls                             # session still persisted for reconciliation
    assert len(out["short_code"]) == 8


@aio
async def test_checkout_falls_back_to_full_url_when_not_recorded(monkeypatch):
    monkeypatch.setattr(pl, "UNIFIED_PAYMENTS_ENABLED", True)
    monkeypatch.setattr(pl, "STRIPE_SECRET_KEY", "sk_test")
    monkeypatch.setattr(pl, "_stripe", lambda: _FakeStripe)

    async def not_recorded(*a, **k):
        return False

    monkeypatch.setattr(pl, "_record_checkout_session", not_recorded)
    out = await pl.create_checkout(ORDER, _cfg(), "ord_y")
    # persistence failed -> customer still gets a working (full) Stripe link
    assert out["url"].startswith("https://checkout.stripe.com")


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
    # 1% of 2250c = 22 (round half-to-even) + the 2.9% processing gross-up
    # (65c). The flat 30c is NOT added: this ORDER is CAD, and Canada's
    # CA$0.75/order is ALL-IN — Meridian absorbs Stripe's flat fee there
    # (Aidan 2026-08-07) rather than grossing it onto the merchant. USD orders
    # still include the 30c — see tests/test_cad_all_in_fee.py.
    assert cap["payment_intent_data"]["application_fee_amount"] == 22 + 65
    assert cap["metadata"]["pos_order_id"] == "ord_42"


@aio
async def test_checkout_sets_backend_return_urls(monkeypatch):
    # success/cancel must point at the backend (api.meridian.tips) — the old
    # meridian.tips/pay/success default fell through to the SPA home page.
    monkeypatch.setattr(pl, "UNIFIED_PAYMENTS_ENABLED", True)
    monkeypatch.setattr(pl, "STRIPE_SECRET_KEY", "sk_test")
    monkeypatch.setattr(pl, "SUCCESS_URL", "https://api.meridian.tips/pay/success?session_id={CHECKOUT_SESSION_ID}")
    monkeypatch.setattr(pl, "CANCEL_URL", "https://api.meridian.tips/pay/cancel")
    monkeypatch.setattr(pl, "_stripe", lambda: _FakeStripe)

    async def no_record(*a, **k):
        return None

    monkeypatch.setattr(pl, "_record_checkout_session", no_record)
    await pl.create_checkout(ORDER, _cfg(), "ord_r")
    cap = _FakeStripe.captured
    assert cap["success_url"].startswith("https://api.meridian.tips/pay/success")
    assert "{CHECKOUT_SESSION_ID}" in cap["success_url"]
    assert cap["cancel_url"] == "https://api.meridian.tips/pay/cancel"
