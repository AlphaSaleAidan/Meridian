"""
Tests for the 3-mode fee allocation model (business_pays / split_5050 /
customer_pays), set by the sales rep at close and FIXED thereafter.

Fee components, per order (all integer cents of the charge currency):
  M  = Meridian's per-order fee — the merchant's effective per-order fee
       (rep-set override, else the plan-tier rate). Sourced from the same
       tier table the split model uses; never re-hardcoded here.
  S  = Stripe's processing fee = round(subtotal × 2.9%) + 30¢.
  F  = M + S  (the total per-order fee to allocate).

Allocation (customer total starts at `subtotal`, business payout is reduced by
whatever it absorbs):
  business_pays  customer surcharge = 0            business absorbs = F
                 (customer total == order subtotal)
  split_5050     customer surcharge = ceil(F / 2)  business absorbs = floor(F / 2)
                 THE ODD CENT GOES TO THE CUSTOMER SIDE (ceil), so the customer
                 pays at most 1¢ more than the business absorbs. Documented +
                 pinned below.
  customer_pays  customer surcharge = F            business absorbs = 0

`fee_allocation_mode = None` means "legacy": the caller keeps the existing
FEE_SPLIT / gross-up behavior byte-for-byte (covered by the sibling
test_payment_fee_split.py / test_payment_fee_grossup.py suites and by
test_none_mode_is_legacy_noop below).

Worked table (subtotal 3200¢ unless noted; S = round(3200×2.9%)+30 = 123¢):
  USD premium  M=149 F=272 | biz cust=0/absorb=272 | 50/50 136/136 | cust 272/0
  USD command  M=100 F=223 | biz cust=0/absorb=223 | 50/50 112/111 | cust 223/0
  CAD premium  M=199 F=322 | biz cust=0/absorb=322 | 50/50 161/161 | cust 322/0
  CAD command  M=139 F=262 | biz cust=0/absorb=262 | 50/50 131/131 | cust 262/0
Odd-cent 50/50: USD premium subtotal 1050 → S=60, F=209 → cust 105, biz 104.
"""
import math
import sys
from pathlib import Path

import pytest

# phone_agent dir on path (same trick the live route uses).
_DIR = str(Path(__file__).resolve().parents[1])
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)

import payment_links  # noqa: E402


# ── Meridian per-order fee (M) resolves off the tier table, not re-hardcoded ──

def test_meridian_fee_uses_tier_table():
    assert payment_links.meridian_fee_cents("premium", "usd") == 149
    assert payment_links.meridian_fee_cents("command", "usd") == 100
    assert payment_links.meridian_fee_cents("premium", "cad") == 199
    assert payment_links.meridian_fee_cents("command", "cad") == 139
    assert payment_links.meridian_fee_cents("standard", "usd") == 0


def test_meridian_fee_honors_rep_override():
    # Rep-set per-merchant fee wins over the tier rate.
    assert payment_links.meridian_fee_cents("premium", "usd", override_cents=90) == 90
    assert payment_links.meridian_fee_cents("premium", "usd", override_cents=0) == 0


# ── Stripe fee (S) = 2.9% + 30¢ ──

@pytest.mark.parametrize("subtotal,expected", [
    (3200, 123),   # round(92.8)=93 + 30
    (1050, 60),    # round(30.45)=30 + 30
    (1000, 59),    # round(29)=29 + 30
    (0, 30),       # fixed only
])
def test_stripe_fee_is_29pct_plus_30(subtotal, expected):
    assert payment_links.stripe_fee_cents(subtotal) == expected


# ── The full allocation table: 3 modes × (USD/CAD × premium/command) ──

# (mode, currency, tier, subtotal, cust_surcharge, biz_absorbed)
_TABLE = [
    # business_pays — customer total == subtotal, business eats F
    ("business_pays", "usd", "premium", 3200, 0, 272),
    ("business_pays", "usd", "command", 3200, 0, 223),
    ("business_pays", "cad", "premium", 3200, 0, 322),
    ("business_pays", "cad", "command", 3200, 0, 262),
    # split_5050 — odd cent to the customer (ceil vs floor)
    ("split_5050", "usd", "premium", 3200, 136, 136),
    ("split_5050", "usd", "command", 3200, 112, 111),  # F=223 odd → 112/111
    ("split_5050", "cad", "premium", 3200, 161, 161),
    ("split_5050", "cad", "command", 3200, 131, 131),
    # customer_pays — customer eats F, business absorbs nothing
    ("customer_pays", "usd", "premium", 3200, 272, 0),
    ("customer_pays", "usd", "command", 3200, 223, 0),
    ("customer_pays", "cad", "premium", 3200, 322, 0),
    ("customer_pays", "cad", "command", 3200, 262, 0),
]


@pytest.mark.parametrize("mode,currency,tier,subtotal,exp_cust,exp_biz", _TABLE)
def test_allocation_table(mode, currency, tier, subtotal, exp_cust, exp_biz):
    alloc = payment_links.allocate_fee(subtotal, tier, currency, mode)
    assert alloc["customer_surcharge_cents"] == exp_cust, "customer surcharge"
    assert alloc["business_absorbed_cents"] == exp_biz, "business absorbed"
    # customer total is always subtotal + their surcharge
    assert alloc["customer_total_cents"] == subtotal + exp_cust
    # F is conserved: whatever the customer doesn't pay, the business absorbs.
    M = payment_links.meridian_fee_cents(tier, currency)
    S = payment_links.stripe_fee_cents(subtotal)
    assert exp_cust + exp_biz == M + S, "F must be fully allocated"


def test_business_pays_customer_total_equals_subtotal():
    for tier in ("premium", "command", "standard"):
        for cur in ("usd", "cad"):
            a = payment_links.allocate_fee(3200, tier, cur, "business_pays")
            assert a["customer_total_cents"] == 3200
            assert a["customer_surcharge_cents"] == 0


def test_customer_pays_business_absorbs_nothing():
    for tier in ("premium", "command"):
        for cur in ("usd", "cad"):
            a = payment_links.allocate_fee(3200, tier, cur, "customer_pays")
            assert a["business_absorbed_cents"] == 0
            assert a["customer_surcharge_cents"] == \
                payment_links.meridian_fee_cents(tier, cur) + \
                payment_links.stripe_fee_cents(3200)


# ── The odd-cent 50/50 rounding rule — pinned explicitly ──

def test_split_5050_odd_cent_goes_to_customer():
    # USD premium, subtotal 1050: S=60, F=149+60=209 (odd).
    a = payment_links.allocate_fee(1050, "premium", "usd", "split_5050")
    assert a["customer_surcharge_cents"] == 105   # ceil(209/2)
    assert a["business_absorbed_cents"] == 104     # floor(209/2)
    # Customer pays exactly one cent more than the business absorbs.
    assert a["customer_surcharge_cents"] - a["business_absorbed_cents"] == 1
    assert a["customer_surcharge_cents"] + a["business_absorbed_cents"] == 209


def test_split_5050_even_fee_splits_exactly():
    # USD premium, subtotal 3200: F=272 (even) → 136/136, no odd cent.
    a = payment_links.allocate_fee(3200, "premium", "usd", "split_5050")
    assert a["customer_surcharge_cents"] == 136
    assert a["business_absorbed_cents"] == 136


@pytest.mark.parametrize("subtotal", [0, 50, 137, 999, 1050, 3450, 9999])
def test_split_5050_ceil_floor_invariant(subtotal):
    # For every subtotal, customer=ceil(F/2), business=floor(F/2), and the
    # customer side never trails the business side.
    a = payment_links.allocate_fee(subtotal, "premium", "cad", "split_5050")
    M = payment_links.meridian_fee_cents("premium", "cad")
    S = payment_links.stripe_fee_cents(subtotal)
    F = M + S
    assert a["customer_surcharge_cents"] == math.ceil(F / 2)
    assert a["business_absorbed_cents"] == math.floor(F / 2)
    assert a["customer_surcharge_cents"] >= a["business_absorbed_cents"]


# ── None / unknown mode is a no-op (legacy path stays authoritative) ──

def test_none_mode_returns_none():
    # None mode → allocate_fee returns None so the caller keeps legacy behavior.
    assert payment_links.allocate_fee(3200, "premium", "usd", None) is None


def test_unknown_mode_returns_none():
    assert payment_links.allocate_fee(3200, "premium", "usd", "bogus") is None


# ── Application fee under the new modes (what Meridian takes from the charge) ──

def test_application_fee_customer_pays_recovers_full_fee():
    # customer_pays: the charge = subtotal + F; Meridian's application fee must
    # recover M + S (the whole fee), capped below the charge total.
    a = payment_links.allocate_fee(3200, "premium", "cad", "customer_pays")
    fee = payment_links.mode_application_fee_cents(3200, a)
    charge = 3200 + a["customer_surcharge_cents"]
    assert fee == 199 + 123   # M + S
    assert fee < charge


def test_application_fee_business_pays_takes_full_fee_from_payout():
    # business_pays: customer charged only subtotal; Meridian still takes M+S,
    # which comes entirely out of the merchant payout.
    a = payment_links.allocate_fee(3200, "premium", "cad", "business_pays")
    fee = payment_links.mode_application_fee_cents(3200, a)
    assert fee == 199 + 123
    assert fee < 3200


def test_application_fee_split_takes_full_fee():
    a = payment_links.allocate_fee(3200, "cad", "command", "split_5050") \
        if False else payment_links.allocate_fee(3200, "command", "cad", "split_5050")
    fee = payment_links.mode_application_fee_cents(3200, a)
    # Whole fee routes to Meridian regardless of who fronted which half.
    assert fee == 139 + 123
