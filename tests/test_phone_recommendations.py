"""
Call-telemetry → cap/fee recommendation logic (advisory, read-only).

The recommendation engine turns the raw voice_call_endings summary (produced by
GET /api/phone/call-endings/summary) into ranked, evidence-backed suggestions a
human can act on. It NEVER mutates a merchant's cap or fee — it only recommends.

Signals under test (pure functions over one merchant's summary block):

  RAISE_CAP    — cutoff-without-order rate is high: the wall is ending calls
                 before an order lands. Evidence carries the projected orders
                 recoverable per week if the cap were raised one minute.
  AGENT_QUALITY— silence + error dispositions are a meaningful share of calls:
                 the agent (not the cap) is losing calls. Not a pricing lever.
  PRICING_HEADROOM — calls run long (avg near/over the included block) but almost
                 nothing hits the cap: the merchant is using paid AI minutes
                 without overage friction — room to adjust included/overage.

Invariants:
  * A clean merchant (short calls, no cutoffs, no errors) yields ZERO recs.
  * Cutoff-heavy → a RAISE_CAP rec whose evidence numbers match the input.
  * Silence/error-heavy → an AGENT_QUALITY rec, and NOT a RAISE_CAP rec.
  * Thresholds are exclusive at the boundary (just-under does not fire).
  * Low call volume (below MIN_CALLS) suppresses all recs — no acting on noise.
  * Recommendations are ranked (highest-impact first) and every rec is advisory:
    it names a suggested_change but performs no write.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.services.phone_recommendations import (  # noqa: E402
    MIN_CALLS,
    CUTOFF_RATE_THRESHOLD,
    AGENT_QUALITY_RATE_THRESHOLD,
    recommend_for_merchant,
    recommend_from_summary,
)


# ── fixtures: single-merchant summary blocks (shape from call_endings_summary) ──

def _merchant(mid="m1", total=100, by_disp=None, cutoff_without_order=0,
              avg_duration=90):
    base = {d: 0 for d in
            ("cutoff", "caller_hangup", "agent_hangup", "silence", "error", "other")}
    if by_disp:
        base.update(by_disp)
    return {
        "merchant_id": mid,
        "total_calls": total,
        "by_disposition": base,
        "cutoff_without_order": cutoff_without_order,
        "avg_duration_seconds": avg_duration,
    }


CLEAN = _merchant(
    mid="clean",
    total=80,
    by_disp={"agent_hangup": 70, "caller_hangup": 10},
    cutoff_without_order=0,
    avg_duration=95,
)

CUTOFF_HEAVY = _merchant(
    mid="cutoff",
    total=100,
    by_disp={"agent_hangup": 60, "cutoff": 30, "caller_hangup": 10},
    cutoff_without_order=24,   # 24% of calls: wall killed them before an order
    avg_duration=250,
)

SILENCE_HEAVY = _merchant(
    mid="silence",
    total=100,
    by_disp={"agent_hangup": 40, "silence": 35, "error": 15, "caller_hangup": 10},
    cutoff_without_order=1,
    avg_duration=60,
)

PRICING_HEADROOM = _merchant(
    mid="pricing",
    total=120,
    by_disp={"agent_hangup": 110, "caller_hangup": 10},
    cutoff_without_order=0,
    avg_duration=210,          # 3.5 min avg — over the 3-min included block
)

LOW_VOLUME = _merchant(
    total=3,
    by_disp={"cutoff": 3},
    cutoff_without_order=3,
    avg_duration=290,
)


# ── clean merchant: no recommendations ───────────────────────────────

def test_clean_merchant_yields_no_recommendations():
    recs = recommend_for_merchant(CLEAN)
    assert recs == []


# ── cutoff-heavy: RAISE_CAP with matching evidence ───────────────────

def test_cutoff_heavy_yields_raise_cap():
    recs = recommend_for_merchant(CUTOFF_HEAVY)
    kinds = [r["signal"] for r in recs]
    assert "RAISE_CAP" in kinds


def test_raise_cap_evidence_matches_input():
    recs = recommend_for_merchant(CUTOFF_HEAVY)
    rec = next(r for r in recs if r["signal"] == "RAISE_CAP")
    ev = rec["evidence"]
    assert ev["cutoff_without_order"] == 24
    assert ev["total_calls"] == 100
    # rate is cutoff_without_order / total_calls
    assert ev["cutoff_without_order_rate"] == pytest.approx(0.24)
    # projects orders/week recoverable — a positive, integer-ish estimate
    assert ev["projected_orders_recoverable_per_week"] >= 1
    # advisory: names a concrete suggested change, performs no write
    assert "suggested_change" in rec
    assert rec["advisory"] is True


# ── silence/error-heavy: AGENT_QUALITY, not a pricing lever ──────────

def test_silence_heavy_yields_agent_quality():
    recs = recommend_for_merchant(SILENCE_HEAVY)
    kinds = [r["signal"] for r in recs]
    assert "AGENT_QUALITY" in kinds
    # a quality problem must NOT be misread as a cap problem
    assert "RAISE_CAP" not in kinds


def test_agent_quality_evidence_counts_silence_and_error():
    recs = recommend_for_merchant(SILENCE_HEAVY)
    rec = next(r for r in recs if r["signal"] == "AGENT_QUALITY")
    ev = rec["evidence"]
    assert ev["silence"] == 35
    assert ev["error"] == 15
    assert ev["quality_loss_rate"] == pytest.approx(0.50)


# ── pricing headroom: long calls, no cap pressure ────────────────────

def test_pricing_headroom_when_long_calls_no_cutoffs():
    recs = recommend_for_merchant(PRICING_HEADROOM)
    kinds = [r["signal"] for r in recs]
    assert "PRICING_HEADROOM" in kinds
    assert "RAISE_CAP" not in kinds


# ── thresholds ───────────────────────────────────────────────────────

def test_cutoff_just_under_threshold_does_not_fire():
    # rate exactly at the threshold must NOT fire (exclusive boundary)
    n = 100
    at = int(round(CUTOFF_RATE_THRESHOLD * n))
    m = _merchant(total=n, by_disp={"agent_hangup": n - at, "cutoff": at},
                  cutoff_without_order=at, avg_duration=250)
    recs = recommend_for_merchant(m)
    assert "RAISE_CAP" not in [r["signal"] for r in recs]


def test_agent_quality_just_under_threshold_does_not_fire():
    n = 100
    at = int(round(AGENT_QUALITY_RATE_THRESHOLD * n))
    # put the whole quality bucket one call under the threshold
    q = at - 1
    m = _merchant(total=n,
                  by_disp={"agent_hangup": n - q, "silence": q},
                  cutoff_without_order=0, avg_duration=60)
    recs = recommend_for_merchant(m)
    assert "AGENT_QUALITY" not in [r["signal"] for r in recs]


def test_low_volume_suppresses_all_recommendations():
    assert LOW_VOLUME["total_calls"] < MIN_CALLS
    assert recommend_for_merchant(LOW_VOLUME) == []


# ── ranking + batch over full summary ────────────────────────────────

def test_recommendations_are_ranked_by_impact():
    # cutoff-heavy carries both a cap problem and long calls; the highest-impact
    # rec (RAISE_CAP, recoverable orders) must sort first.
    recs = recommend_for_merchant(CUTOFF_HEAVY)
    assert len(recs) >= 1
    scores = [r["impact_score"] for r in recs]
    assert scores == sorted(scores, reverse=True)
    assert recs[0]["signal"] == "RAISE_CAP"


def test_recommend_from_summary_maps_every_merchant():
    summary = {
        "days": 7,
        "total_calls": 400,
        "merchants": [CLEAN, CUTOFF_HEAVY, SILENCE_HEAVY, PRICING_HEADROOM],
    }
    out = recommend_from_summary(summary)
    assert out["days"] == 7
    by_id = {m["merchant_id"]: m for m in out["merchants"]}
    # clean merchant present but empty; others carry recs
    assert by_id[CLEAN["merchant_id"]]["recommendations"] == []
    assert any(r["signal"] == "RAISE_CAP"
               for r in by_id[CUTOFF_HEAVY["merchant_id"]]["recommendations"])
    # every rec across the board is advisory (read-only)
    for m in out["merchants"]:
        for r in m["recommendations"]:
            assert r["advisory"] is True


def test_missing_fields_are_tolerated():
    # a sparse summary block (older rows / partial data) must not crash
    sparse = {"merchant_id": "x", "total_calls": 50}
    recs = recommend_for_merchant(sparse)
    assert isinstance(recs, list)
