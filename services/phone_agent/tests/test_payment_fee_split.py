"""
Tests for the customer/merchant fee split (three-tier pricing model).

Split economics on a destination charge:
  customer pays  subtotal + tier per-order fee + fixed 30¢ (own line item)
  merchant bears 2.99% of the subtotal (via the application fee)
  application_fee = customer surcharge + 2.99% × subtotal

Example pinned below — CA$32.00 order, Premium tier (CA$2.49/order):
  surcharge = 249 + 30 = 279¢ → customer pays CA$34.79
  app fee   = 279 + round(3200 × 2.99%) = 279 + 96 = 375¢
  Stripe's actual processing ≈ 2.9% × 3479 + 30 = 131¢ (platform-debited)
  Meridian nets ≈ 375 − 131 = 244¢ ≈ the CA$2.49 per-order fee.
"""
import sys
from pathlib import Path

# phone_agent dir on path (same trick the live route uses).
_DIR = str(Path(__file__).resolve().parents[1])
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)

import payment_links  # noqa: E402


def _configure(monkeypatch, *, merchant_bps=299, fixed=30, default_tier="premium"):
    monkeypatch.setattr(payment_links, "FEE_SPLIT_ENABLED", True)
    monkeypatch.setattr(payment_links, "MERCHANT_FEE_BPS", merchant_bps)
    monkeypatch.setattr(payment_links, "CUSTOMER_FIXED_FEE_CENTS", fixed)
    monkeypatch.setattr(payment_links, "DEFAULT_ORDER_FEE_TIER", default_tier)


def test_tier_order_fees_per_currency(monkeypatch):
    _configure(monkeypatch)
    assert payment_links.tier_order_fee_cents("standard", "usd") == 0
    assert payment_links.tier_order_fee_cents("premium", "usd") == 149
    assert payment_links.tier_order_fee_cents("command", "usd") == 100
    assert payment_links.tier_order_fee_cents("standard", "cad") == 0
    assert payment_links.tier_order_fee_cents("premium", "cad") == 249
    assert payment_links.tier_order_fee_cents("command", "cad") == 169


def test_unknown_or_missing_tier_defaults_to_premium_rate(monkeypatch):
    _configure(monkeypatch)
    assert payment_links.tier_order_fee_cents("", "cad") == 249
    assert payment_links.tier_order_fee_cents("weekly", "usd") == 149
    # Unknown currency falls back to CAD rates (phone orders default to CAD).
    assert payment_links.tier_order_fee_cents("command", "xyz") == 169


def test_customer_surcharge_is_tier_fee_plus_fixed(monkeypatch):
    _configure(monkeypatch)
    assert payment_links.customer_surcharge_cents("premium", "cad") == 279
    assert payment_links.customer_surcharge_cents("command", "usd") == 130
    # Standard: no per-order Meridian fee — customer still covers the fixed 30¢.
    assert payment_links.customer_surcharge_cents("standard", "usd") == 30


def test_split_fee_matches_worked_example(monkeypatch):
    # CA$32.00 order, Premium: 279 surcharge + 96 merchant-side = 375.
    _configure(monkeypatch)
    surcharge = payment_links.customer_surcharge_cents("premium", "cad")
    assert payment_links.split_application_fee_cents(3200, surcharge) == 375


def test_split_fee_merchant_side_is_299bps_of_subtotal_only(monkeypatch):
    # The 2.99% applies to the merchant's subtotal, never to the surcharge.
    _configure(monkeypatch)
    assert payment_links.split_application_fee_cents(10000, 130) == 130 + 299


def test_split_fee_capped_below_total_charge(monkeypatch):
    # Tiny order: fee can never reach the full charge (subtotal + surcharge).
    _configure(monkeypatch)
    surcharge = payment_links.customer_surcharge_cents("premium", "cad")  # 279
    assert payment_links.split_application_fee_cents(50, surcharge) == 280  # 279 + 1 (=round(50 × 2.99%)) fits under 329
    assert payment_links.split_application_fee_cents(0, surcharge) == surcharge - 1


def test_flag_off_keeps_legacy_grossup_untouched(monkeypatch):
    # With the split disabled, application_fee_cents is byte-for-byte the
    # Case B gross-up model (pinned in test_payment_fee_grossup.py).
    monkeypatch.setattr(payment_links, "FEE_SPLIT_ENABLED", False)
    monkeypatch.setattr(payment_links, "SERVICE_FEE_CENTS", 50)
    monkeypatch.setattr(payment_links, "PLATFORM_FEE_BPS", 0)
    monkeypatch.setattr(payment_links, "STRIPE_GROSSUP_ENABLED", True)
    monkeypatch.setattr(payment_links, "STRIPE_FEE_BPS", 290)
    monkeypatch.setattr(payment_links, "STRIPE_FEE_FIXED_CENTS", 30)
    assert payment_links.application_fee_cents(3200) == 173
