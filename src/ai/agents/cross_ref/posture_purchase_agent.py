"""
Posture Purchase Agent — Correlates body gestures with purchase behavior.

Uses FreeMoCap skeletal data to identify gestures (reaching, browsing,
carrying) and measures how they predict conversion and basket size.
Requires skeletal tracking to be enabled.
"""
from collections import defaultdict
from .base import BaseCrossRefAgent


class PosturePurchaseAgent(BaseCrossRefAgent):
    name = "posture_purchase"
    description = "Correlates body posture/gesture patterns with purchase likelihood"
    tier = 4

    async def analyze(self) -> dict:
        skeletal = self.ctx.skeletal_data
        if not skeletal:
            return self._result(
                summary="No skeletal tracking data — enable FreeMoCap for posture-purchase correlation",
                score=50,
                insights=[{
                    "type": "no_skeletal_data",
                    "detail": "FreeMoCap skeletal tracking not enabled. Install skellytracker for gesture-based analytics.",
                }],
                recommendations=[{
                    "action": "Enable FreeMoCap integration for posture-based purchase prediction",
                    "impact_cents": 0,
                }],
                data={"skeletal_available": False},
                confidence=0.2,
                calculation_path="minimal",
            )

        gesture_counts: dict[str, int] = defaultdict(int)
        gesture_conversions: dict[str, int] = defaultdict(int)
        gesture_baskets: dict[str, list[int]] = defaultdict(list)

        person_gestures: dict[str, set[str]] = defaultdict(set)
        for s in skeletal:
            pid = s.get("person_id", "")
            gesture = s.get("gesture", "unknown")
            if pid and gesture != "unknown":
                person_gestures[pid].add(gesture)

        for j in self.journeys:
            pid = j.get("person_id", "")
            gestures = person_gestures.get(pid, set())
            for g in gestures:
                gesture_counts[g] += 1
                if j.get("converted"):
                    gesture_conversions[g] += 1
                    if j.get("transaction_total_cents"):
                        gesture_baskets[g].append(j["transaction_total_cents"])

        overall_conv = self._conversion_rate()

        gesture_stats = {}
        purchase_signals = []

        for g in gesture_counts:
            total = gesture_counts[g]
            convs = gesture_conversions[g]
            rate = convs / max(total, 1)
            baskets = gesture_baskets.get(g, [])
            avg_basket = sum(baskets) / max(len(baskets), 1)
            lift = (rate / overall_conv - 1) if overall_conv > 0 else 0

            gesture_stats[g] = {
                "total_observed": total,
                "conversions": convs,
                "conversion_rate": round(rate, 3),
                "lift_vs_baseline": round(lift, 3),
                "avg_basket_cents": int(avg_basket),
            }

            if lift > 0.2 and total >= 5:
                purchase_signals.append((g, gesture_stats[g]))

        purchase_signals.sort(key=lambda x: -x[1]["lift_vs_baseline"])

        insights = []
        recommendations = []

        for g, stats in purchase_signals[:3]:
            insights.append({
                "type": "gesture_purchase_signal",
                "detail": (
                    f"'{g}' gesture predicts {stats['lift_vs_baseline']:.0%} higher conversion "
                    f"({stats['conversion_rate']:.0%} vs {overall_conv:.0%} baseline)"
                ),
            })

        if "reaching" in gesture_stats:
            r = gesture_stats["reaching"]
            if r["conversion_rate"] > overall_conv * 1.3:
                recommendations.append({
                    "action": "Ensure products at reach height are high-margin — reaching correlates with purchase intent",
                    "impact_cents": 0,
                })

        if "browsing" in gesture_stats:
            b = gesture_stats["browsing"]
            if b["conversion_rate"] < overall_conv * 0.8:
                recommendations.append({
                    "action": "Browsing posture shows interest but low conversion — add staff assistance triggers for browsers",
                    "impact_cents": 0,
                })

        score = min(100, 40 + len(purchase_signals) * 15 + min(len(skeletal), 20))

        return self._result(
            summary=f"{len(gesture_stats)} gestures tracked, {len(purchase_signals)} purchase signals",
            score=score,
            insights=insights,
            recommendations=recommendations,
            data={
                "gesture_stats": gesture_stats,
                "purchase_signal_gestures": [g[0] for g in purchase_signals],
                "overall_conversion": round(overall_conv, 3),
                "total_skeletal_observations": len(skeletal),
            },
            confidence=min(0.65, 0.2 + len(skeletal) / 200),
        )
