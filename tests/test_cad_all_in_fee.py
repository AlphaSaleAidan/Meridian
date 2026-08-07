"""CA$0.75 ALL-IN per-order fee (Aidan 2026-08-07).

Canada advertises CA$0.75/order as the merchant's TOTAL per-order cost — that
fee plus the card-processing percentage they'd pay on any card order, and
nothing else. Stripe's flat 30¢ is absorbed by Meridian (netting CA$0.45)
instead of being grossed up onto the merchant.

USD is deliberately unchanged: it still passes the flat fee through.
"""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "phone_agent"))
os.environ.setdefault("ENCRYPTION_KEY", "0" * 64)

import payment_links as pl  # noqa: E402


@pytest.fixture(autouse=True)
def _fees(monkeypatch):
    monkeypatch.setattr(pl, "STRIPE_GROSSUP_ENABLED", True)
    monkeypatch.setattr(pl, "STRIPE_FEE_BPS", 290)
    monkeypatch.setattr(pl, "STRIPE_FEE_FIXED_CENTS", 30)
    monkeypatch.setattr(pl, "PLATFORM_FEE_BPS", 0)
    monkeypatch.setattr(pl, "FLAT_FEE_ABSORBED_CURRENCIES", {"cad"})
    yield


def test_cad_merchant_pays_fee_plus_percentage_only():
    """CA$50 order, CA$0.75 fee: merchant bears 75¢ + 2.9%, NOT the extra 30¢."""
    fee = pl.application_fee_cents(5000, service_fee_cents=75, currency="cad")
    assert fee == 75 + 145          # 2.9% of 5000 = 145
    assert fee == 220               # CA$2.20 total; the 30¢ is NOT added


def test_cad_meridian_nets_45_cents_after_stripe():
    """Meridian's true take: the app fee minus what Stripe actually charges."""
    amount = 5000
    fee = pl.application_fee_cents(amount, service_fee_cents=75, currency="cad")
    stripe_cost = round(amount * 0.029) + 30      # what Stripe debits the platform
    assert fee - stripe_cost == 45                # CA$0.45 net, as modelled


def test_usd_still_passes_the_flat_fee_through():
    """US pricing is untouched — the flat 30¢ is still grossed up there."""
    fee = pl.application_fee_cents(5000, service_fee_cents=65, currency="usd")
    assert fee == 65 + 145 + 30


def test_unknown_currency_defaults_to_passthrough():
    """Fail safe: an unknown/blank currency keeps the historical behaviour."""
    assert pl.application_fee_cents(5000, service_fee_cents=65, currency="") == 65 + 145 + 30
    assert pl.application_fee_cents(5000, service_fee_cents=65, currency="gbp") == 65 + 145 + 30


def test_cad_case_insensitive():
    assert pl.application_fee_cents(5000, service_fee_cents=75, currency="CAD") == 220


def test_fee_still_capped_below_the_charge():
    """A tiny order can never be consumed entirely by the fee."""
    assert pl.application_fee_cents(50, service_fee_cents=75, currency="cad") <= 49


def test_canonical_backend_terms_say_75_for_ca_premium():
    from src.billing.fee_terms import CANONICAL_FEE_TERMS, ORDER_FEE_FLOOR_CENTS
    assert CANONICAL_FEE_TERMS["ca"]["premium"]["order_fee_cents"] == 75
    # the floor must move with the fee, or the backend clamps it back up to 90
    assert ORDER_FEE_FLOOR_CENTS["ca"]["premium"] == 75
    # US untouched
    assert ORDER_FEE_FLOOR_CENTS["us"]["premium"] == 65
