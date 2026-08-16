"""Zero-per-order (minutes licensing) pricing — migration 077.

Covers:
  • the canonical card mirrors Aidan's settled 2026-08-09 numbers (CA) and the
    ÷1.4 derivation (US)
  • resolve_fee_terms: order fee FORCED to 0, monthly clamped to
    [card floor, retail + headroom], bucket fields filled; the legacy
    per-order path is byte-for-byte unchanged
  • _term_row_fields: per-order rows carry the exact pre-077 columns
    (deploy-safe against an unmigrated database); zero-per-order rows add the
    three new columns
  • lead-row round-trip keeps the locked model
  • vapi_webhook._bill_monthly_bucket: whole-minute metering, bucket-crossing
    overage math, hard-cap clamp, retry idempotency

Run:  python -m pytest tests/test_zero_per_order_pricing.py -v
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.billing import fee_terms as ft  # noqa: E402


# ── Canonical card ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("market,tier,minutes,overage", [
    ("ca", "premium", 600, 20),   # $0.20/min both markets (Aidan 2026-08-10)
    ("ca", "command", 1000, 20),
    ("us", "premium", 600, 20),
    ("us", "command", 1000, 20),
])
def test_canonical_zero_per_order_card(market, tier, minutes, overage):
    card = ft.ZERO_PER_ORDER_TERMS[market][tier]
    assert card["included_monthly_min"] == minutes
    assert card["monthly_overage_cents_per_min"] == overage
    # Wholesale monthlies (CA$175/220) are what a partner org pays on the
    # backend — they must NEVER appear as merchant pricing.
    assert "monthly_fee_cents" not in card


def test_standard_tier_has_no_card():
    assert "standard" not in ft.ZERO_PER_ORDER_TERMS["ca"]
    assert "standard" not in ft.ZERO_PER_ORDER_TERMS["us"]


# ── normalize_pricing_model ──────────────────────────────────────────────────

@pytest.mark.parametrize("raw,expected", [
    ("zero_per_order", "zero_per_order"),
    ("ZERO_PER_ORDER", "zero_per_order"),
    ("per_order", None),   # explicit per-order stores as None = legacy
    (None, None),
    ("", None),
    ("free_orders", None),  # unknown → legacy, never a crash
])
def test_normalize_pricing_model(raw, expected):
    assert ft.normalize_pricing_model(raw) == expected


# ── resolve_fee_terms: zero-per-order path ───────────────────────────────────

def test_zpo_defaults_keep_retail_monthly_and_fill_bucket():
    t = ft.resolve_fee_terms("ca", plan_tier="premium", pricing_model="zero_per_order")
    assert t["pricing_model"] == "zero_per_order"
    assert t["monthly_fee_cents"] == 50000  # the SAME retail monthly as per-order
    assert t["order_fee_cents"] == 0
    assert t["included_monthly_min"] == 600
    assert t["monthly_overage_cents_per_min"] == 20


def test_zpo_forces_order_fee_to_zero_even_when_client_sends_one():
    t = ft.resolve_fee_terms("ca", plan_tier="premium",
                             pricing_model="zero_per_order", order_fee_cents=75)
    assert t["order_fee_cents"] == 0


def test_zpo_monthly_clamps_exactly_like_per_order():
    # Floor = tier retail (a crafted request can't discount to wholesale) …
    t = ft.resolve_fee_terms("ca", plan_tier="premium",
                             pricing_model="zero_per_order", monthly_fee_cents=17500)
    assert t["monthly_fee_cents"] == 50000
    # … cap = retail + rep headroom, same as the legacy path.
    t = ft.resolve_fee_terms("ca", plan_tier="premium",
                             pricing_model="zero_per_order", monthly_fee_cents=99999)
    assert t["monthly_fee_cents"] == 65000


def test_zpo_standard_tier_coerces_to_default_tier():
    t = ft.resolve_fee_terms("ca", plan_tier="standard", pricing_model="zero_per_order")
    assert t["plan_tier"] == ft.DEFAULT_PLAN_TIER
    assert t["pricing_model"] == "zero_per_order"


# ── resolve_fee_terms: legacy path untouched ─────────────────────────────────

def test_per_order_resolution_is_unchanged_and_model_is_none():
    t = ft.resolve_fee_terms("ca", plan_tier="premium", order_fee_cents=75)
    assert t["pricing_model"] is None
    assert t["included_monthly_min"] is None
    assert t["monthly_overage_cents_per_min"] is None
    assert t["order_fee_cents"] == 50
    assert t["monthly_fee_cents"] == 50000


def test_explicit_per_order_request_resolves_like_legacy():
    a = ft.resolve_fee_terms("us", plan_tier="command", pricing_model="per_order")
    b = ft.resolve_fee_terms("us", plan_tier="command")
    assert a == b


# ── _term_row_fields: deploy-safe row shapes ─────────────────────────────────

def test_per_order_row_has_exact_pre_077_columns():
    t = ft.resolve_fee_terms("ca", plan_tier="premium")
    row = ft._term_row_fields(t)
    assert set(row) == set(ft.FEE_TERM_FIELDS)  # no new keys → works unmigrated


def test_zpo_row_adds_the_three_077_columns():
    t = ft.resolve_fee_terms("ca", plan_tier="command", pricing_model="zero_per_order")
    row = ft._term_row_fields(t)
    assert set(row) == set(ft.FEE_TERM_FIELDS) | set(ft.ZERO_PER_ORDER_TERM_FIELDS)
    assert row["pricing_model"] == "zero_per_order"
    assert row["order_fee_cents"] == 0


# ── Lead-row round-trip ──────────────────────────────────────────────────────

def test_terms_from_lead_row_keeps_locked_zpo_model():
    lead = {
        "plan_tier": "command",
        "monthly_fee_cents": 70000,  # retail — the monthly a zpo deal actually closes at
        "order_fee_cents": 0,
        "call_overage_cents_per_min": 0,
        "included_call_min": 3,
        "pricing_model": "zero_per_order",
        "included_monthly_min": 1000,
        "monthly_overage_cents_per_min": 35,
    }
    t = ft.terms_from_lead_row("ca", lead)
    assert t["pricing_model"] == "zero_per_order"
    assert t["order_fee_cents"] == 0
    assert t["included_monthly_min"] == 1000
    assert t["monthly_overage_cents_per_min"] == 35
    assert t["monthly_fee_cents"] == 70000


def test_terms_from_lead_row_legacy_lead_stays_legacy():
    lead = {"plan_tier": "premium", "monthly_fee_cents": 50000, "order_fee_cents": 75}
    t = ft.terms_from_lead_row("ca", lead)
    assert t["pricing_model"] is None


# ── vapi_webhook._bill_monthly_bucket ────────────────────────────────────────

from src.api.routes import vapi_webhook as vw  # noqa: E402


class BucketDB:
    """Fake db for voice_monthly_calls: in-memory rows, records inserts."""

    def __init__(self):
        self.rows: list[dict] = []

    async def select(self, table, columns="*", filters=None, order=None,
                     limit=None, offset=None):
        assert table == "voice_monthly_calls"
        f = filters or {}
        out = self.rows
        if "vapi_call_id" in f:
            want = f["vapi_call_id"].removeprefix("eq.")
            out = [r for r in out if r["vapi_call_id"] == want]
        if "merchant_id" in f:
            want = f["merchant_id"].removeprefix("eq.")
            out = [r for r in out if r["merchant_id"] == want]
        if "month" in f:
            want = f["month"].removeprefix("eq.")
            out = [r for r in out if r["month"] == want]
        return list(out[:limit] if limit else out)

    async def insert(self, table, data, return_data=True):
        self.rows.append(dict(data))
        return [dict(data)]


class _Cfg:
    max_call_minutes = None  # env default cap


ZPO_TERMS = {"pricing_model": "zero_per_order",
             "included_monthly_min": 10, "monthly_overage_cents_per_min": 35}


@pytest.fixture
def bucket_env(monkeypatch):
    db = BucketDB()
    credits: list[tuple] = []

    async def fake_credit(merchant_id, cents, source="", ref=None, note=None):
        credits.append((merchant_id, cents, source, ref))
        return True

    import src.db as dbmod
    import src.services.voice_ledger as vl
    monkeypatch.setattr(dbmod, "get_db", lambda: db)
    monkeypatch.setattr(vl, "credit", fake_credit)
    monkeypatch.setattr(vw, "VOICE_MAX_CALL_MIN", 5, raising=False)
    return db, credits


@pytest.mark.asyncio
async def test_bucket_no_overage_inside_the_bucket(bucket_env):
    db, credits = bucket_env
    await vw._bill_monthly_bucket("m1", "call-1", 2.4, _Cfg(), ZPO_TERMS)
    assert db.rows[0]["billed_min"] == 3  # ceil(2.4)
    assert credits == []  # 3/10 min — inside the bucket


@pytest.mark.asyncio
async def test_bucket_crossing_call_bills_only_the_minutes_past_it(bucket_env):
    db, credits = bucket_env
    for i, dur in enumerate([4.0, 4.0]):  # 8 min used
        await vw._bill_monthly_bucket("m1", f"call-{i}", dur, _Cfg(), ZPO_TERMS)
    assert credits == []
    # 3rd call: 8 → 12 min; bucket is 10 → 2 min over @ 35¢ = 70¢
    await vw._bill_monthly_bucket("m1", "call-2", 4.0, _Cfg(), ZPO_TERMS)
    assert credits == [("m1", 70, "monthly_overage", "call-2")]


@pytest.mark.asyncio
async def test_bucket_fully_over_bills_whole_call(bucket_env):
    db, credits = bucket_env
    for i in range(3):
        await vw._bill_monthly_bucket("m1", f"call-{i}", 4.0, _Cfg(), ZPO_TERMS)
    credits.clear()
    await vw._bill_monthly_bucket("m1", "call-3", 3.0, _Cfg(), ZPO_TERMS)
    assert credits == [("m1", 3 * 35, "monthly_overage", "call-3")]


@pytest.mark.asyncio
async def test_bucket_retry_is_idempotent(bucket_env):
    db, credits = bucket_env
    for i in range(3):
        await vw._bill_monthly_bucket("m1", f"call-{i}", 4.0, _Cfg(), ZPO_TERMS)
    await vw._bill_monthly_bucket("m1", "call-x", 4.0, _Cfg(), ZPO_TERMS)
    n_rows, n_credits = len(db.rows), len(credits)
    await vw._bill_monthly_bucket("m1", "call-x", 4.0, _Cfg(), ZPO_TERMS)  # Vapi retry
    assert len(db.rows) == n_rows and len(credits) == n_credits


@pytest.mark.asyncio
async def test_bucket_minutes_clamped_to_hard_call_cap(bucket_env):
    db, credits = bucket_env
    # 7.5-min report with a 5-min cap → 5 billed minutes, not 8.
    await vw._bill_monthly_bucket("m1", "call-long", 7.5, _Cfg(), ZPO_TERMS)
    assert db.rows[0]["billed_min"] == 5


@pytest.mark.asyncio
async def test_bucket_zero_rate_meters_but_never_bills(bucket_env):
    db, credits = bucket_env
    terms = dict(ZPO_TERMS, included_monthly_min=0, monthly_overage_cents_per_min=0)
    await vw._bill_monthly_bucket("m1", "call-1", 4.0, _Cfg(), terms)
    assert db.rows and credits == []
