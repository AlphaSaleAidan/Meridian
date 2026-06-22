"""
Tests for CARD ON THE PHONE (keypad/DTMF backup payment).

Covers the engine surface the IVR drives — validation, the capture state machine,
the demo-safe charge (approve + each decline reason), and the fallback decision —
with no network and no real charge.
"""
import sys
from pathlib import Path

import pytest

_DIR = str(Path(__file__).resolve().parents[1])
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)

import card_on_phone as cop  # noqa: E402

VISA_OK = "4242424242424242"
VISA_DECLINE = "4000000000000002"
VISA_NSF = "4000000000009995"


# ─── Validation helpers ──────────────────────────────────────────────────────

def test_luhn_accepts_valid_rejects_typo():
    assert cop.luhn_ok(VISA_OK)
    assert cop.luhn_ok("4242 4242 4242 4242")          # spaces stripped
    assert not cop.luhn_ok("4242424242424241")          # bad checksum
    assert not cop.luhn_ok("123")                        # too short


def test_card_brand_detection():
    assert cop.card_brand(VISA_OK) == "visa"
    assert cop.card_brand("5500000000000004") == "mastercard"
    assert cop.card_brand("371449635398431") == "amex"
    assert cop.card_brand("6011000990139424") == "discover"
    assert cop.card_brand("9999000000000000") == "unknown"


def test_mask_pan_only_last4():
    masked = cop.mask_pan(VISA_OK)
    assert masked.endswith("4242")
    assert "4242424242" not in masked  # full PAN never exposed


def test_parse_expiry_and_future():
    assert cop.parse_expiry("1229") == (12, 29)
    assert cop.parse_expiry("1325") is None              # month 13 invalid
    assert cop.parse_expiry("123") is None               # wrong length
    assert cop.expiry_in_future(6, 30, now=(26, 6))      # future year
    assert cop.expiry_in_future(6, 26, now=(26, 6))      # same month ok
    assert not cop.expiry_in_future(5, 26, now=(26, 6))  # past


def test_valid_cvv_and_postal():
    assert cop.valid_cvv("123")
    assert cop.valid_cvv("1234", brand="amex")
    assert not cop.valid_cvv("12")
    assert cop.valid_postal("90210")
    assert cop.valid_postal("12")  is False


# ─── Capture state machine ───────────────────────────────────────────────────

def test_capture_lifecycle_and_wipe():
    sid = "call-capture-1"
    cop.clear_capture(sid)
    cap = cop.start_capture(sid, order_ref="MRD-1", merchant_id="m1", amount_cents=1798)
    cap.pan, cap.cvv = VISA_OK, "123"
    assert cop.get_capture(sid) is cap
    cop.clear_capture(sid)
    assert cop.get_capture(sid) is None        # gone after clear
    # And the sensitive fields were wiped on the object.
    assert cap.pan == "" and cap.cvv == ""


# ─── Charge (demo-safe simulate) ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_charge_approves_good_card():
    r = await cop.charge(VISA_OK, "1230", "123", "90210", 1798, merchant_id="demo-merchant")
    assert r.approved and r.last4 == "4242" and r.txn_id
    assert "approv" in r.spoken.lower()


@pytest.mark.asyncio
async def test_charge_declines_test_pan():
    r = await cop.charge(VISA_DECLINE, "1230", "123", "90210", 1798, merchant_id="demo-merchant")
    assert not r.approved and r.decline_reason == "card_declined"


@pytest.mark.asyncio
async def test_charge_declines_insufficient_funds():
    r = await cop.charge(VISA_NSF, "1230", "123", "90210", 1798, merchant_id="demo-merchant")
    assert not r.approved and r.decline_reason == "insufficient_funds"


@pytest.mark.asyncio
async def test_charge_rejects_bad_luhn_before_gateway():
    r = await cop.charge("4242424242424241", "1230", "123", "90210", 1798, merchant_id="demo-merchant")
    assert not r.approved and r.decline_reason == "invalid_number"


@pytest.mark.asyncio
async def test_charge_rejects_expired_card():
    r = await cop.charge(VISA_OK, "0120", "123", "90210", 1798, merchant_id="demo-merchant")
    assert not r.approved and r.decline_reason == "expired_card"


# ─── Fallback decision ───────────────────────────────────────────────────────

def test_should_offer_card_fallback(monkeypatch):
    monkeypatch.setattr(cop, "CARD_PAYMENT_ENABLED", True)
    # SMS failed on a pay-now merchant → offer the keypad backup.
    assert cop.should_offer_card_fallback(sms_sent=False, payment_mode="pay_now")
    # SMS delivered → no need for the backup.
    assert not cop.should_offer_card_fallback(sms_sent=True, payment_mode="pay_now")
    # pay-at-pickup merchant → never.
    assert not cop.should_offer_card_fallback(sms_sent=False, payment_mode="pay_at_pickup")
    # Feature off → never, even if SMS failed.
    monkeypatch.setattr(cop, "CARD_PAYMENT_ENABLED", False)
    assert not cop.should_offer_card_fallback(sms_sent=False, payment_mode="pay_now")


def test_attempts_exhausted():
    cap = cop.start_capture("call-attempts", order_ref="MRD-9")
    assert not cop.attempts_exhausted(cap)
    cap.attempts = 2
    assert cop.attempts_exhausted(cap)
    cop.clear_capture("call-attempts")
