"""
Call-telemetry → cap/fee recommendations (ADVISORY, READ-ONLY).

This module turns the per-merchant call-ending summary produced by
`GET /api/phone/call-endings/summary` (see phone_activation.call_endings_summary)
into ranked, evidence-backed *suggestions*. It NEVER changes a merchant's cap,
included minutes, or overage rate — it recommends, a human decides.

The summary already computes, per merchant, everything these pure functions need:

    {
      "merchant_id": str,
      "total_calls": int,
      "by_disposition": {cutoff, caller_hangup, agent_hangup, silence, error, other},
      "cutoff_without_order": int,   # cutoff calls that ended before an order landed
      "avg_duration_seconds": int,
    }

so the recommendation layer is a pure transform over that data — no DB, no side
effects, trivially unit-testable against fixture summaries.

Signals
-------
RAISE_CAP
    High rate of `cutoff_without_order` means the hard call cap (default 5 min,
    per-merchant `phone_agent_config.max_call_minutes`) is ending calls before an
    order lands. Raising the cap one minute plausibly recovers those calls;
    evidence projects orders-recoverable-per-week from the observed rate.

AGENT_QUALITY
    A meaningful share of calls end in `silence` (dead air / voicemail /
    silence-timeout) or `error` (pipeline/assistant failure). That is an agent or
    infra problem, NOT a pricing lever — so this signal explicitly excludes a
    RAISE_CAP recommendation.

PRICING_HEADROOM
    Calls run long (avg near/over the included block, default 3 min) but almost
    nothing hits the cap. The merchant is consuming paid AI minutes without
    overage friction — room to revisit included minutes / overage rate. Advisory
    only; no auto-repricing.
"""
from __future__ import annotations

import os

# ── billing anchors (mirror the vapi_webhook defaults so recs speak the same
#    language as the live config; overridable via the same env knobs) ──────────
VOICE_INCLUDED_MIN = int(os.getenv("MERIDIAN_VOICE_INCLUDED_MIN", "3") or 3)
VOICE_MAX_CALL_MIN = int(os.getenv("MERIDIAN_VOICE_MAX_CALL_MIN", "5") or 5)
VOICE_OVERAGE_CENTS_PER_MIN = int(
    os.getenv("MERIDIAN_VOICE_OVERAGE_CENTS_PER_MIN", "0") or 0
)

# ── thresholds (tunable, but fixed for deterministic recs) ───────────────────
# Don't recommend anything off a handful of calls — act on signal, not noise.
MIN_CALLS = 20
# cutoff-without-order rate strictly ABOVE this fires RAISE_CAP.
CUTOFF_RATE_THRESHOLD = 0.15
# combined silence+error rate strictly ABOVE this fires AGENT_QUALITY.
AGENT_QUALITY_RATE_THRESHOLD = 0.20
# avg call duration (seconds) at/above this — with negligible cap pressure —
# fires PRICING_HEADROOM. Anchored just under the included block so a merchant
# routinely reaching the paid tier surfaces.
PRICING_HEADROOM_MIN_AVG_SEC = VOICE_INCLUDED_MIN * 60  # 180s by default
# "negligible cap pressure": cutoff-without-order rate must be at/below this for
# a pricing (not cap) recommendation to be the right lever.
PRICING_HEADROOM_MAX_CUTOFF_RATE = 0.03

_QUALITY_DISPOSITIONS = ("silence", "error")


def _rate(numerator: float, denominator: float) -> float:
    return (numerator / denominator) if denominator else 0.0


def recommend_for_merchant(merchant: dict) -> list[dict]:
    """Derive ranked, advisory recommendations for ONE merchant's summary block.

    Pure function. Returns a list of rec dicts sorted highest-impact first; each
    rec carries: signal, evidence (the numbers behind it), suggested_change,
    impact_score, and advisory=True. Never writes anything.
    """
    total = int(merchant.get("total_calls") or 0)
    if total < MIN_CALLS:
        return []

    by_disp = merchant.get("by_disposition") or {}
    cutoff_without_order = int(merchant.get("cutoff_without_order") or 0)
    avg_dur = int(merchant.get("avg_duration_seconds") or 0)

    silence = int(by_disp.get("silence") or 0)
    error = int(by_disp.get("error") or 0)

    cutoff_rate = _rate(cutoff_without_order, total)
    quality_loss = silence + error
    quality_rate = _rate(quality_loss, total)

    recs: list[dict] = []

    # ── RAISE_CAP ────────────────────────────────────────────────────
    if cutoff_rate > CUTOFF_RATE_THRESHOLD:
        # Raising the cap one minute doesn't magically save every cutoff, but a
        # conservative half of the orders the wall killed is a defensible weekly
        # projection (summary window normalized to 7 days upstream).
        projected = max(1, round(cutoff_without_order * 0.5))
        new_cap = VOICE_MAX_CALL_MIN + 1
        recs.append({
            "signal": "RAISE_CAP",
            "title": "Call cap is ending calls before orders land",
            "evidence": {
                "total_calls": total,
                "cutoff_without_order": cutoff_without_order,
                "cutoff_without_order_rate": round(cutoff_rate, 4),
                "current_cap_minutes": VOICE_MAX_CALL_MIN,
                "projected_orders_recoverable_per_week": projected,
            },
            "suggested_change": (
                f"Raise the {VOICE_MAX_CALL_MIN}-min cap to {new_cap} min — "
                f"could recover ~{projected} order(s)/week the wall is cutting off."
            ),
            "impact_score": round(cutoff_rate * 100, 1),
            "advisory": True,
        })

    # ── AGENT_QUALITY ────────────────────────────────────────────────
    if quality_rate > AGENT_QUALITY_RATE_THRESHOLD:
        recs.append({
            "signal": "AGENT_QUALITY",
            "title": "Calls lost to silence / errors, not the cap",
            "evidence": {
                "total_calls": total,
                "silence": silence,
                "error": error,
                "quality_loss_rate": round(quality_rate, 4),
            },
            "suggested_change": (
                "Investigate agent quality (dead air / pipeline errors) before "
                "touching pricing — the cap is not the bottleneck here."
            ),
            "impact_score": round(quality_rate * 100, 1),
            "advisory": True,
        })

    # ── PRICING_HEADROOM ─────────────────────────────────────────────
    if (
        avg_dur >= PRICING_HEADROOM_MIN_AVG_SEC
        and cutoff_rate <= PRICING_HEADROOM_MAX_CUTOFF_RATE
    ):
        over_included_sec = max(0, avg_dur - VOICE_INCLUDED_MIN * 60)
        recs.append({
            "signal": "PRICING_HEADROOM",
            "title": "Long calls with little cap pressure — pricing headroom",
            "evidence": {
                "total_calls": total,
                "avg_duration_seconds": avg_dur,
                "included_minutes": VOICE_INCLUDED_MIN,
                "avg_seconds_over_included": over_included_sec,
                "cutoff_without_order_rate": round(cutoff_rate, 4),
                "overage_cents_per_min": VOICE_OVERAGE_CENTS_PER_MIN,
            },
            # With the overage retired the only lever left is the cap itself, so
            # the copy must not advertise a 0¢/min charge.
            "suggested_change": (
                f"Calls average {avg_dur}s ({VOICE_INCLUDED_MIN}-min block included) "
                "with almost no cutoffs — room to revisit included minutes or the "
                f"{VOICE_MAX_CALL_MIN}-min call cap."
                if not VOICE_OVERAGE_CENTS_PER_MIN else
                f"Calls average {avg_dur}s ({VOICE_INCLUDED_MIN}-min block included) "
                "with almost no cutoffs — room to revisit included minutes or the "
                f"{VOICE_OVERAGE_CENTS_PER_MIN}¢/min overage."
            ),
            # lowest-priority signal: informational pricing lever, not a leak.
            "impact_score": round(_rate(over_included_sec, avg_dur) * 20, 1),
            "advisory": True,
        })

    recs.sort(key=lambda r: r["impact_score"], reverse=True)
    return recs


def recommend_from_summary(summary: dict) -> dict:
    """Map `call_endings_summary` output to per-merchant recommendations.

    Preserves the window (`days`) and attaches a `recommendations` list to each
    merchant. Pure transform; safe to call on the raw summary payload.
    """
    merchants_out = []
    for m in summary.get("merchants") or []:
        merchants_out.append({
            "merchant_id": m.get("merchant_id"),
            "total_calls": int(m.get("total_calls") or 0),
            "recommendations": recommend_for_merchant(m),
        })
    return {
        "days": summary.get("days"),
        "merchants": merchants_out,
    }
