"""Billing invariant: the customer pays exactly what the order was confirmed
at, on every rail — and if any rail ever drifts again, the drift is (a)
corrected at charge time on Stripe, and (b) detected at settlement time for
everything else. Born from the tax/modifier-drop bug (itemized checkouts
billed the raw menu sum while phone_orders recorded the taxed total)."""
import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "phone_agent"))

import payment_links as pl  # noqa: E402
import pay_on_phone as pop  # noqa: E402

aio = pytest.mark.asyncio

ORDER = {
    "merchant_id": "m1", "caller_phone": "+15551234567", "currency": "cad",
    "items": [
        {"name": "Butter Chicken", "quantity": 2, "unit_price": 18.5},
        {"name": "Garlic Naan", "quantity": 3, "unit_price": 4.0},
    ],
    "tax": 6.37,
    "total": 55.37,  # 49.00 items + 6.37 HST
}


def _cfg(**kw):
    base = dict(stripe_account_id="", stripe_charges_enabled=False,
                plan_tier="", fee_allocation_mode=None, order_fee_cents=None,
                pos_system="square", pos_access_token="tok", pos_location_id="loc")
    base.update(kw)
    return SimpleNamespace(**base)


class _StripeObj:
    def __init__(self, **d):
        self._d = d

    def __getitem__(self, k):
        return self._d[k]


# ── layer 1: Stripe choke-point invariant ─────────────────────────────

@aio
async def test_stripe_invariant_collapses_drifted_line_items(monkeypatch, caplog):
    """If a future builder change under-bills again, the session must charge
    the exact confirmed total as a single line — never the drifted sum."""
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
    # simulate a regressed builder that drops the tax delta again
    monkeypatch.setattr(pl, "_stripe_line_items", lambda order, cur: [
        {"quantity": 2, "price_data": {"currency": cur, "unit_amount": 1850,
                                       "product_data": {"name": "Butter Chicken"}}},
        {"quantity": 3, "price_data": {"currency": cur, "unit_amount": 400,
                                       "product_data": {"name": "Garlic Naan"}}},
    ])
    await pl._stripe_checkout(ORDER, _cfg(), "po-1")
    billed = sum(li["price_data"]["unit_amount"] * li["quantity"]
                 for li in captured["line_items"])
    assert billed == 5537
    assert len(captured["line_items"]) == 1  # collapsed to the exact total
    assert "BILLING INVARIANT VIOLATION" in caplog.text


@aio
async def test_stripe_invariant_silent_when_lines_are_exact(monkeypatch, caplog):
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
    await pl._stripe_checkout(ORDER, _cfg(), "po-2")
    billed = sum(li["price_data"]["unit_amount"] * li["quantity"]
                 for li in captured["line_items"])
    assert billed == 5537
    # real builder includes the Tax & extras line — no collapse, no scream
    assert len(captured["line_items"]) == 3
    assert "BILLING INVARIANT VIOLATION" not in caplog.text


# ── layer 2: Square payment-link delta line ───────────────────────────

@aio
async def test_square_link_bills_full_total(monkeypatch):
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
    await pl._square_payment_link(ORDER, "tok", "loc", "po-3")
    lines = sent["order"]["line_items"]
    billed = sum(li["base_price_money"]["amount"] * int(li["quantity"]) for li in lines)
    assert billed == 5537
    assert lines[-1]["name"] == "Tax & extras"
    assert lines[-1]["base_price_money"]["amount"] == 637


# ── layer 3: Clover HCO extras line ───────────────────────────────────

def test_hco_lines_bill_full_total():
    order = dict(ORDER)
    # HCO already handled tax explicitly; give it a modifier-carrying total:
    # items 49.00 + tax 6.37 + toppings 3.00 = 58.37
    order["total"] = 58.37
    lines, subtotal = pl._clover_hco_line_items(order)
    billed = sum(li["price"] * li["unitQty"] for li in lines
                 if li["name"] not in ("Service & processing fee",))
    assert billed == 5837
    names = [li["name"] for li in lines]
    assert "Tax" in names and "Extras" in names


def test_hco_no_extras_when_total_covered():
    lines, _ = pl._clover_hco_line_items(dict(ORDER))  # total == items + tax
    assert "Extras" not in [li["name"] for li in lines]


# ── layer 4: settlement reconciliation ────────────────────────────────

def test_reconcile_flags_underpayment(caplog):
    row = {"pos_order_id": "po-9", "total": 55.37, "business_name": "Debug Bistro"}
    pop._reconcile_paid_amount(row, 4900, "m1")
    assert "UNDERPAYMENT DETECTED" in caplog.text
    assert "4900" in caplog.text and "5537" in caplog.text


def test_reconcile_silent_on_exact_or_overpay(caplog):
    row = {"pos_order_id": "po-9", "total": 55.37}
    pop._reconcile_paid_amount(row, 5537, "m1")
    pop._reconcile_paid_amount(row, 5837, "m1")  # surcharge rides on top
    assert "UNDERPAYMENT" not in caplog.text


def test_reconcile_silent_when_amount_unknown(caplog):
    pop._reconcile_paid_amount({"total": 55.37}, 0, "m1")   # simulate/non-Stripe
    pop._reconcile_paid_amount({"total": 0}, 4900, "m1")     # no recorded total
    assert "UNDERPAYMENT" not in caplog.text


def test_reconcile_never_raises_on_garbage():
    pop._reconcile_paid_amount({"total": "not-a-number"}, 4900, "m1")
    pop._reconcile_paid_amount(None if False else {}, 4900, "")  # empty row
