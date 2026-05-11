"""
Return Customer Agent — Analyzes multi-visit customer behavior.

Cross-references ReID person tracking with POS data to understand
how returning customers differ from first-timers in zones visited,
dwell time, and spend.
"""
from collections import defaultdict
from .base import BaseCrossRefAgent


class ReturnCustomerAgent(BaseCrossRefAgent):
    name = "return_customer"
    description = "Compares returning vs first-time customer journey and spend patterns"
    tier = 3

    async def analyze(self) -> dict:
        visitors = self.ctx.vision_visitors
        if not visitors:
            return self._insufficient_data("Visitor recognition data (requires camera ReID)")

        repeat_ids = {v["id"] for v in visitors if v.get("visit_count", 1) > 1}
        first_ids = {v["id"] for v in visitors if v.get("visit_count", 1) == 1}

        repeat_journeys = [
            j for j in self.journeys
            if j.get("person_id") in repeat_ids
        ]
        first_journeys = [
            j for j in self.journeys
            if j.get("person_id") in first_ids
        ]

        if not repeat_journeys and not first_journeys:
            return self._insufficient_data("Journeys linked to visitor recognition")

        def _stats(jlist):
            converted = [j for j in jlist if j.get("converted")]
            conv_rate = len(converted) / max(len(jlist), 1)
            baskets = [j["transaction_total_cents"] for j in converted if j.get("transaction_total_cents")]
            avg_basket = sum(baskets) / max(len(baskets), 1)
            avg_dwell = sum(j.get("total_dwell_seconds", 0) for j in jlist) / max(len(jlist), 1)
            avg_zones = sum(len(j.get("zones_visited", [])) for j in jlist) / max(len(jlist), 1)
            return {
                "count": len(jlist),
                "converted": len(converted),
                "conversion_rate": round(conv_rate, 3),
                "avg_basket_cents": int(avg_basket),
                "avg_dwell_seconds": round(avg_dwell, 1),
                "avg_zones_visited": round(avg_zones, 1),
            }

        repeat_stats = _stats(repeat_journeys)
        first_stats = _stats(first_journeys)

        insights = []
        recommendations = []

        if repeat_stats["conversion_rate"] > first_stats["conversion_rate"] * 1.2:
            lift = repeat_stats["conversion_rate"] / max(first_stats["conversion_rate"], 0.01) - 1
            insights.append({
                "type": "repeat_conversion_advantage",
                "detail": (
                    f"Returning customers convert {lift:.0%} more often "
                    f"({repeat_stats['conversion_rate']:.0%} vs {first_stats['conversion_rate']:.0%})"
                ),
            })

        if repeat_stats["avg_basket_cents"] > first_stats["avg_basket_cents"] * 1.15:
            diff = repeat_stats["avg_basket_cents"] - first_stats["avg_basket_cents"]
            insights.append({
                "type": "repeat_spend_premium",
                "detail": (
                    f"Returning customers spend ${diff / 100:.2f} more per visit "
                    f"(${repeat_stats['avg_basket_cents'] / 100:.2f} vs ${first_stats['avg_basket_cents'] / 100:.2f})"
                ),
            })
            recommendations.append({
                "action": "Invest in retention — returning customers generate higher ticket sizes",
                "impact_cents": diff * repeat_stats["count"],
            })

        if repeat_stats["avg_zones_visited"] != first_stats["avg_zones_visited"]:
            insights.append({
                "type": "zone_familiarity",
                "detail": (
                    f"Returners visit {repeat_stats['avg_zones_visited']:.1f} zones vs "
                    f"{first_stats['avg_zones_visited']:.1f} for first-timers"
                ),
            })

        self.emit_finding(
            "return_customer_patterns",
            f"Repeat: {repeat_stats['count']} journeys, First: {first_stats['count']}",
            {"repeat": repeat_stats, "first_time": first_stats},
        )

        score = min(100, 40 + min(len(repeat_journeys), 20) + min(len(first_journeys), 20))

        return self._result(
            summary=f"Returners: {repeat_stats['conversion_rate']:.0%} conv, ${repeat_stats['avg_basket_cents'] / 100:.2f} avg | First-timers: {first_stats['conversion_rate']:.0%}, ${first_stats['avg_basket_cents'] / 100:.2f}",
            score=score,
            insights=insights,
            recommendations=recommendations,
            data={"repeat_customers": repeat_stats, "first_time_customers": first_stats},
            confidence=min(0.7, 0.25 + (len(repeat_journeys) + len(first_journeys)) / 200),
        )
