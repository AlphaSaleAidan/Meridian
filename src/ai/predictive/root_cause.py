"""
Root Cause Analyzer — Predictive 3.

When any metric changes significantly, identifies WHAT changed,
WHEN it changed, and WHY by checking correlations across all agents.
Uses Granger-style causality testing (simplified).
"""
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("meridian.ai.predictive.root_cause")


class RootCauseAnalyzer:
    """Diagnose why metrics changed using cross-agent correlation."""

    name = "root_cause"
    tier = 6

    CAUSE_CANDIDATES = [
        {"factor": "product_mix", "agent": "category_mix", "label": "Product mix shift"},
        {"factor": "staffing", "agent": "employee_performance", "label": "Employee roster change"},
        {"factor": "pricing", "agent": "pricing_power", "label": "Pricing change"},
        {"factor": "seasonality", "agent": "seasonality", "label": "Seasonal pattern"},
        {"factor": "day_mix", "agent": "day_of_week", "label": "Day-of-week composition change"},
        {"factor": "discounting", "agent": "discount_analyzer", "label": "Discount rate change"},
    ]

    def __init__(self, ctx, agent_outputs: dict | None = None):
        self.ctx = ctx
        self.outputs = agent_outputs or getattr(ctx, "agent_outputs", {})

    async def analyze(self, metric_name: str = "revenue", change_pct: float | None = None) -> dict:
        """Find the most likely cause of a metric change."""

        # Step 1: Detect what changed (from revenue_trend or alert)
        trend_data = self.outputs.get("revenue_trend", {})
        if change_pct is None:
            change_pct = trend_data.get("data", {}).get("wow_growth_pct", 0)

        if abs(change_pct) < 5:
            return {
                "agent_name": self.name,
                "status": "no_significant_change",
                "summary": f"{metric_name} change of {change_pct:+.1f}% is within normal range",
                "change_pct": change_pct,
            }

        direction = "dropped" if change_pct < 0 else "rose"

        # Step 2: Identify when (change point from trend data)
        change_point = trend_data.get("data", {}).get("trend_break_date")
        if not change_point:
            daily = self.ctx.daily_revenue or []
            if len(daily) >= 14:
                mid = len(daily) // 2
                first_half = [d.get("revenue_cents", 0) for d in daily[:mid]]
                second_half = [d.get("revenue_cents", 0) for d in daily[mid:]]
                if first_half and second_half:
                    avg_first = sum(first_half) / len(first_half)
                    avg_second = sum(second_half) / len(second_half)
                    if abs(avg_second - avg_first) / max(avg_first, 1) > 0.1:
                        change_point = daily[mid].get("date", "mid-period")

        # Step 3: Score each candidate cause
        scored_candidates = []
        for candidate in self.CAUSE_CANDIDATES:
            agent_output = self.outputs.get(candidate["agent"], {})
            if agent_output.get("status") != "complete":
                continue

            score = self._score_candidate(candidate, agent_output, change_pct)
            if score > 0:
                scored_candidates.append({
                    "factor": candidate["factor"],
                    "label": candidate["label"],
                    "correlation_score": round(score, 2),
                    "evidence": self._get_evidence(candidate, agent_output),
                })

        # Sort by score
        scored_candidates.sort(key=lambda c: c["correlation_score"], reverse=True)

        # If nothing explains it, suggest external
        if not scored_candidates or scored_candidates[0]["correlation_score"] < 0.3:
            scored_candidates.append({
                "factor": "external",
                "label": "Possible external event",
                "correlation_score": 0.25,
                "evidence": "No internal factor explains the change — consider weather, competition, construction, or local events",
            })

        root_cause = scored_candidates[0] if scored_candidates else None

        explanation = ""
        if root_cause:
            explanation = (
                f"{metric_name.title()} {direction} {abs(change_pct):.0f}%"
                f"{f' starting {change_point}' if change_point else ''}. "
                f"Most likely cause: {root_cause['label']} "
                f"(confidence: {root_cause['correlation_score']:.0%}). "
                f"{root_cause.get('evidence', '')}"
            )

        return {
            "agent_name": self.name,
            "status": "complete",
            "summary": explanation,
            "metric": metric_name,
            "change_pct": round(change_pct, 1),
            "direction": direction,
            "change_point": change_point,
            "root_cause": root_cause,
            "all_candidates": scored_candidates[:5],
            "confidence": root_cause["correlation_score"] if root_cause else 0,
            "data_quality": 0.6,
        }

    def _score_candidate(self, candidate: dict, agent_output: dict, change_pct: float) -> float:
        """Score how likely this factor caused the observed change."""
        factor = candidate["factor"]
        data = agent_output.get("data", {})
        score = 0.0

        if factor == "product_mix":
            shift = data.get("category_shift_pct", 0)
            if abs(shift) > 5:
                score = min(abs(shift) / 20, 1.0) * 0.8

        elif factor == "staffing":
            perf_gap = data.get("performance_gap_pct", 0)
            if abs(perf_gap) > 10:
                score = min(abs(perf_gap) / 30, 1.0) * 0.7

        elif factor == "pricing":
            ticket_change = data.get("avg_ticket_change_pct", 0)
            volume_change = data.get("volume_change_pct", 0)
            if abs(ticket_change) > 5 and abs(volume_change) < 5:
                score = min(abs(ticket_change) / 15, 1.0) * 0.85

        elif factor == "seasonality":
            seasonal_idx = data.get("current_seasonal_index", 1.0)
            if abs(seasonal_idx - 1.0) > 0.1:
                score = min(abs(seasonal_idx - 1.0) / 0.3, 1.0) * 0.6

        elif factor == "day_mix":
            variance = data.get("dow_variance_pct", 0)
            if variance > 25:
                score = min(variance / 50, 1.0) * 0.5

        elif factor == "discounting":
            discount_change = data.get("discount_rate_change_pct", 0)
            if abs(discount_change) > 2:
                score = min(abs(discount_change) / 10, 1.0) * 0.75

        # Timing match: does this factor's change precede the metric change?
        timing = data.get("change_timing_days_before", 0)
        if 0 < timing <= 7:
            score *= 1.2  # boost if change preceded
        elif timing > 14:
            score *= 0.5  # unlikely if too far back

        return min(score, 1.0)

    def _get_evidence(self, candidate: dict, agent_output: dict) -> str:
        """Extract human-readable evidence from agent output."""
        data = agent_output.get("data", {})
        factor = candidate["factor"]

        if factor == "product_mix":
            return data.get("shift_description", "Category shares shifted during this period")
        elif factor == "staffing":
            return data.get("staffing_note", "Employee performance patterns changed")
        elif factor == "pricing":
            change = data.get("avg_ticket_change_pct", 0)
            return f"Average ticket changed {change:+.1f}% without proportional volume change"
        elif factor == "seasonality":
            idx = data.get("current_seasonal_index", 1.0)
            return f"Current seasonal index: {idx:.2f}x (1.0 = average)"
        elif factor == "discounting":
            rate = data.get("current_discount_rate_pct", 0)
            return f"Discount rate at {rate:.1f}%"
        return agent_output.get("summary", "")
