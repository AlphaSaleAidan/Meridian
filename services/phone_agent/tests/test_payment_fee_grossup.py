"""
Tests for the Case B Stripe-fee gross-up on destination charges.

Verified empirically in Stripe test mode (2026-07-04): a $32.00 destination
charge with application_fee=$0.50 nets Meridian −$0.73 (Stripe debits the
platform); grossing the fee up to $1.73 nets Meridian exactly +$0.50 and the
merchant bears processing in transit. These tests pin the fee math to those
observed numbers.
"""
import sys
from pathlib import Path

# phone_agent dir on path (same trick the live route uses).
_DIR = str(Path(__file__).resolve().parents[1])
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)

import payment_links  # noqa: E402


def _configure(monkeypatch, *, service=50, bps=0, grossup=True,
               stripe_bps=290, stripe_fixed=30):
    monkeypatch.setattr(payment_links, "SERVICE_FEE_CENTS", service)
    monkeypatch.setattr(payment_links, "PLATFORM_FEE_BPS", bps)
    monkeypatch.setattr(payment_links, "STRIPE_GROSSUP_ENABLED", grossup)
    monkeypatch.setattr(payment_links, "STRIPE_FEE_BPS", stripe_bps)
    monkeypatch.setattr(payment_links, "STRIPE_FEE_FIXED_CENTS", stripe_fixed)


def test_grossup_matches_stripe_verified_figure(monkeypatch):
    # $32.00 order → $0.50 + (2.9% = $0.93) + $0.30 = $1.73 (empirically nets +$0.50)
    _configure(monkeypatch)
    assert payment_links.application_fee_cents(3200) == 173


def test_grossup_disabled_is_legacy_behavior(monkeypatch):
    _configure(monkeypatch, grossup=False)
    assert payment_links.application_fee_cents(3200) == 50


def test_platform_bps_composes_with_grossup(monkeypatch):
    # 1% platform fee on $32.00 adds 32¢ on top of service fee + processing.
    _configure(monkeypatch, bps=100)
    assert payment_links.application_fee_cents(3200) == 173 + 32


def test_fee_capped_below_tiny_orders(monkeypatch):
    # $1.00 order: 50 + 3 + 30 = 83¢ fits; $0.60 order caps at amount − 1.
    _configure(monkeypatch)
    assert payment_links.application_fee_cents(100) == 83
    assert payment_links.application_fee_cents(60) == 59


def test_zero_config_still_covers_processing(monkeypatch):
    # Even with no Meridian fee configured, gross-up keeps the platform from
    # eating Stripe's processing on someone else's sale.
    _configure(monkeypatch, service=0)
    assert payment_links.application_fee_cents(3200) == 123
