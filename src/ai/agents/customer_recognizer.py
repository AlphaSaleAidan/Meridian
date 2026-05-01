from .base import BaseAgent
from collections import defaultdict


class CustomerRecognizerAgent(BaseAgent):
    name = "customer_recognizer"
    description = "Repeat visitor frequency, new vs returning ratio, loyalty without a card"
    tier = 2

    async def analyze(self) -> dict:
        visitors = getattr(self.ctx, "vision_visitors", [])
        visits = getattr(self.ctx, "vision_visits", [])

        if not visitors:
            return self._insufficient_data(
                "Visitor recognition data (requires opt_in_identity compliance mode)"
            )

        total_visitors = len(visitors)
        repeat_visitors = [v for v in visitors if v.get("visit_count", 1) > 1]
        new_visitors = [v for v in visitors if v.get("visit_count", 1) == 1]
        repeat_rate = len(repeat_visitors) / max(total_visitors, 1)

        visit_counts = [v.get("visit_count", 1) for v in visitors]
        avg_visits = sum(visit_counts) / max(len(visit_counts), 1)
        max_visits = max(visit_counts) if visit_counts else 0

        frequency_buckets = {"1_visit": 0, "2_3_visits": 0, "4_10_visits": 0, "10_plus": 0}
        for count in visit_counts:
            if count == 1:
                frequency_buckets["1_visit"] += 1
            elif count <= 3:
                frequency_buckets["2_3_visits"] += 1
            elif count <= 10:
                frequency_buckets["4_10_visits"] += 1
            else:
                frequency_buckets["10_plus"] += 1

        loyal_customers = [v for v in visitors if v.get("visit_count", 1) >= 4]

        converted_visits = [v for v in visits if v.get("converted")]
        repeat_ids = {v["id"] for v in repeat_visitors}
        repeat_conversions = [
            v for v in converted_visits
            if v.get("visitor_id") in repeat_ids
        ]
        new_ids = {v["id"] for v in new_visitors}
        new_conversions = [
            v for v in converted_visits
            if v.get("visitor_id") in new_ids
        ]

        repeat_conv_rate = len(repeat_conversions) / max(len(repeat_visitors), 1)
        new_conv_rate = len(new_conversions) / max(len(new_visitors), 1)

        recency = {}
        for v in visitors:
            last = v.get("last_seen", "")
            first = v.get("first_seen", "")
            if last and first:
                recency[v["id"]] = {"last_seen": last, "first_seen": first}

        insights = []
        recommendations = []

        if repeat_rate < 0.3:
            insights.append({
                "type": "low_repeat_rate",
                "detail": (
                    f"Only {repeat_rate:.0%} of visitors return. "
                    f"Industry target: 30-40% for retail, 50%+ for food service."
                ),
            })
            recommendations.append({
                "action": "Launch a simple loyalty program — even stamp cards increase return rate 20-30%",
                "impact_cents": 0,
            })

        if repeat_conv_rate > new_conv_rate * 1.5 and new_conv_rate > 0:
            insights.append({
                "type": "repeat_conversion_advantage",
                "detail": (
                    f"Repeat visitors convert at {repeat_conv_rate:.0%} vs "
                    f"{new_conv_rate:.0%} for new visitors. "
                    f"Investing in retention has {repeat_conv_rate/max(new_conv_rate,0.01):.1f}x higher ROI."
                ),
            })

        if loyal_customers:
            loyal_pct = len(loyal_customers) / max(total_visitors, 1)
            insights.append({
                "type": "loyal_base",
                "detail": (
                    f"{len(loyal_customers)} loyal customers (4+ visits, "
                    f"{loyal_pct:.0%} of all visitors) — your most valuable segment"
                ),
            })
            recommendations.append({
                "action": f"Create a VIP tier for your {len(loyal_customers)} most frequent visitors",
                "impact_cents": 0,
            })

        score = min(100, 30 + int(repeat_rate * 80) + min(total_visitors, 30))
        confidence = min(0.75, 0.3 + total_visitors / 200)

        return self._result(
            summary=f"{total_visitors} unique visitors, {repeat_rate:.0%} return rate, {len(loyal_customers)} loyalists",
            score=score,
            insights=insights,
            recommendations=recommendations,
            data={
                "total_unique_visitors": total_visitors,
                "new_visitors": len(new_visitors),
                "repeat_visitors": len(repeat_visitors),
                "repeat_rate": round(repeat_rate, 3),
                "loyal_customers": len(loyal_customers),
                "avg_visits_per_visitor": round(avg_visits, 1),
                "max_visits": max_visits,
                "frequency_buckets": frequency_buckets,
                "repeat_conversion_rate": round(repeat_conv_rate, 3),
                "new_conversion_rate": round(new_conv_rate, 3),
            },
            confidence=confidence,
            calculation_path="full" if total_visitors >= 50 else "partial",
        )
