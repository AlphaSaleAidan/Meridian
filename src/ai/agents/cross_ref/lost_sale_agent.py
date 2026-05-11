"""
Lost Sale Agent — Identifies revenue lost from walkaway customers.

Analyzes unconverted journeys to find where and why customers leave
without buying. Estimates recoverable revenue.
"""
from collections import Counter, defaultdict
from .base import BaseCrossRefAgent


class LostSaleAgent(BaseCrossRefAgent):
    name = "lost_sale"
    description = "Identifies walkaway patterns and estimates recoverable revenue"
    tier = 3

    async def analyze(self) -> dict:
        if not self.journeys:
            return self._insufficient_data("Customer journey data")

        unconverted = self.unconverted_journeys
        converted = self.converted_journeys

        if not unconverted:
            return self._result(
                summary="No walkaway journeys detected — all visitors converted",
                score=100,
                insights=[{"type": "perfect_conversion", "detail": "Every tracked visitor made a purchase"}],
                recommendations=[],
                data={"walkaway_count": 0},
                confidence=0.5,
            )

        avg_basket = self._avg_basket_cents()

        exit_zones = Counter()
        for j in unconverted:
            zones = j.get("zones_visited", [])
            if zones:
                exit_zones[zones[-1]] += 1
            else:
                exit_zones["entry"] += 1

        dwell_buckets = {"under_30s": 0, "30s_2min": 0, "2min_5min": 0, "over_5min": 0}
        for j in unconverted:
            dwell = j.get("total_dwell_seconds", 0)
            if dwell < 30:
                dwell_buckets["under_30s"] += 1
            elif dwell < 120:
                dwell_buckets["30s_2min"] += 1
            elif dwell < 300:
                dwell_buckets["2min_5min"] += 1
            else:
                dwell_buckets["over_5min"] += 1

        bounce_rate = dwell_buckets["under_30s"] / max(len(unconverted), 1)

        recoverable_est = 0
        high_intent_walkaways = [
            j for j in unconverted
            if j.get("total_dwell_seconds", 0) >= 60
            and len(j.get("zones_visited", [])) >= 2
        ]
        recoverable_est = len(high_intent_walkaways) * avg_basket

        insights = []
        recommendations = []

        top_exit = exit_zones.most_common(1)
        if top_exit:
            zone, count = top_exit[0]
            pct = count / len(unconverted)
            insights.append({
                "type": "top_exit_zone",
                "detail": (
                    f"{pct:.0%} of walkaway customers exit from '{zone}' zone "
                    f"({count} of {len(unconverted)} walkaways)"
                ),
            })
            recommendations.append({
                "action": f"Add staff greeter or promotional signage in '{zone}' zone to intercept walkaways",
                "impact_cents": int(recoverable_est * 0.1),
            })

        if bounce_rate > 0.4:
            insights.append({
                "type": "high_bounce",
                "detail": (
                    f"{bounce_rate:.0%} of non-buyers leave within 30 seconds — "
                    f"they may not find what they're looking for immediately"
                ),
            })
            recommendations.append({
                "action": "Improve entrance merchandising and signage to capture attention in first 30 seconds",
                "impact_cents": 0,
            })

        if high_intent_walkaways:
            insights.append({
                "type": "high_intent_walkaway",
                "detail": (
                    f"{len(high_intent_walkaways)} visitors browsed 2+ zones for 60s+ but didn't buy. "
                    f"Estimated lost revenue: ${recoverable_est / 100:,.0f}"
                ),
            })

        self.emit_finding(
            "lost_sales",
            f"{len(unconverted)} walkaways, ${recoverable_est / 100:,.0f} recoverable",
            {"exit_zones": dict(exit_zones), "high_intent_count": len(high_intent_walkaways)},
            severity="warning",
        )

        walkaway_pct = len(unconverted) / max(len(self.journeys), 1)
        score = max(0, 100 - int(walkaway_pct * 100))

        return self._result(
            summary=f"{len(unconverted)} walkaways ({walkaway_pct:.0%}), ~${recoverable_est / 100:,.0f} recoverable",
            score=score,
            insights=insights,
            recommendations=recommendations,
            data={
                "total_walkaways": len(unconverted),
                "walkaway_rate": round(walkaway_pct, 3),
                "exit_zones": dict(exit_zones),
                "dwell_buckets": dwell_buckets,
                "bounce_rate": round(bounce_rate, 3),
                "high_intent_walkaways": len(high_intent_walkaways),
                "recoverable_revenue_cents": recoverable_est,
                "avg_basket_cents": avg_basket,
            },
            confidence=min(0.8, 0.3 + len(unconverted) / 100),
        )
