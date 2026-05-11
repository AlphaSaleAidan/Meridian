"""
Queue Basket Agent — Correlates queue wait time with basket size and abandonment.

Measures how waiting in the checkout queue affects final purchase amount
and whether long waits cause last-item removals or complete abandonment.
"""
from .base import BaseCrossRefAgent


class QueueBasketAgent(BaseCrossRefAgent):
    name = "queue_basket"
    description = "Correlates checkout queue wait time with basket size and abandonment"
    tier = 3

    async def analyze(self) -> dict:
        if not self.journeys:
            return self._insufficient_data("Customer journey data with checkout zone tracking")

        with_checkout = [
            j for j in self.journeys
            if any(s.get("zone_name") == "checkout" for s in j.get("zone_stops", []))
        ]

        if not with_checkout:
            return self._insufficient_data("Journeys through checkout zone")

        wait_data = []
        for j in with_checkout:
            for stop in j.get("zone_stops", []):
                if stop.get("zone_name") == "checkout":
                    wait_data.append({
                        "wait_seconds": stop.get("dwell_seconds", 0),
                        "converted": j.get("converted", False),
                        "basket_cents": j.get("transaction_total_cents", 0),
                    })
                    break

        short_wait = [d for d in wait_data if d["wait_seconds"] < 120]
        long_wait = [d for d in wait_data if d["wait_seconds"] >= 120]

        short_conv = sum(1 for d in short_wait if d["converted"]) / max(len(short_wait), 1)
        long_conv = sum(1 for d in long_wait if d["converted"]) / max(len(long_wait), 1)

        short_baskets = [d["basket_cents"] for d in short_wait if d["converted"] and d["basket_cents"]]
        long_baskets = [d["basket_cents"] for d in long_wait if d["converted"] and d["basket_cents"]]

        avg_short_basket = sum(short_baskets) / max(len(short_baskets), 1)
        avg_long_basket = sum(long_baskets) / max(len(long_baskets), 1)

        avg_wait = sum(d["wait_seconds"] for d in wait_data) / max(len(wait_data), 1)
        abandoned = sum(1 for d in wait_data if not d["converted"])
        abandon_rate = abandoned / max(len(wait_data), 1)

        insights = []
        recommendations = []

        if long_conv < short_conv * 0.8 and long_wait:
            drop = short_conv - long_conv
            insights.append({
                "type": "queue_abandonment",
                "detail": (
                    f"2+ min queue wait drops conversion from {short_conv:.0%} to {long_conv:.0%}. "
                    f"{abandoned} customers abandoned after reaching checkout."
                ),
            })
            est_lost = int(abandoned * avg_short_basket)
            recommendations.append({
                "action": "Open additional checkout lane when queue exceeds 2 minutes",
                "impact_cents": est_lost,
            })

        if avg_long_basket and avg_short_basket and avg_long_basket < avg_short_basket * 0.85:
            shrink = (1 - avg_long_basket / avg_short_basket)
            insights.append({
                "type": "queue_basket_shrink",
                "detail": (
                    f"Long waits shrink basket by {shrink:.0%} "
                    f"(${avg_long_basket / 100:.2f} vs ${avg_short_basket / 100:.2f} with short wait)"
                ),
            })

        if avg_wait > 180:
            insights.append({
                "type": "high_avg_wait",
                "detail": f"Average checkout wait is {avg_wait / 60:.1f} minutes — above 3-min comfort threshold",
            })
            recommendations.append({
                "action": "Deploy mobile POS or self-checkout to reduce average wait below 3 minutes",
                "impact_cents": 0,
            })

        self.emit_finding(
            "queue_impact",
            f"Avg wait {avg_wait:.0f}s, {abandon_rate:.0%} abandon rate",
            {"avg_wait": avg_wait, "abandon_rate": abandon_rate},
        )

        score = max(0, 100 - int(abandon_rate * 80) - max(0, int(avg_wait / 60) - 2) * 10)

        return self._result(
            summary=f"Avg wait {avg_wait / 60:.1f}min, {abandon_rate:.0%} abandon, basket shrinks {((1 - avg_long_basket / max(avg_short_basket, 1)) * 100):.0f}% with long wait",
            score=score,
            insights=insights,
            recommendations=recommendations,
            data={
                "total_checkout_visits": len(wait_data),
                "avg_wait_seconds": round(avg_wait, 1),
                "short_wait_conversion": round(short_conv, 3),
                "long_wait_conversion": round(long_conv, 3),
                "avg_basket_short_wait_cents": int(avg_short_basket),
                "avg_basket_long_wait_cents": int(avg_long_basket),
                "abandoned_count": abandoned,
                "abandon_rate": round(abandon_rate, 3),
            },
            confidence=min(0.75, 0.3 + len(wait_data) / 100),
        )
