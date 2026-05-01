from .base import BaseAgent
from collections import defaultdict


class DwellTimeAgent(BaseAgent):
    name = "dwell_time"
    description = "Average dwell by zone, zone flow heatmaps, browse-to-buy funnel"
    tier = 2

    async def analyze(self) -> dict:
        visits = getattr(self.ctx, "vision_visits", [])

        if not visits:
            return self._insufficient_data("Vision visit data (connect cameras with zone tracking)")

        visits_with_dwell = [v for v in visits if v.get("dwell_seconds") is not None]
        if not visits_with_dwell:
            return self._insufficient_data("Visit records with dwell times")

        dwells = [v["dwell_seconds"] for v in visits_with_dwell]
        avg_dwell = sum(dwells) / len(dwells)
        median_dwell = sorted(dwells)[len(dwells) // 2]
        max_dwell = max(dwells)

        zone_dwells = defaultdict(list)
        for v in visits_with_dwell:
            for zone in v.get("zones_visited", []):
                zone_dwells[zone].append(v["dwell_seconds"])

        zone_stats = {}
        for zone, times in zone_dwells.items():
            zone_stats[zone] = {
                "avg_seconds": round(sum(times) / len(times), 1),
                "visit_count": len(times),
                "median_seconds": sorted(times)[len(times) // 2],
            }

        converted = [v for v in visits_with_dwell if v.get("converted")]
        not_converted = [v for v in visits_with_dwell if not v.get("converted")]

        converted_avg_dwell = (
            sum(v["dwell_seconds"] for v in converted) / max(len(converted), 1)
        )
        not_converted_avg_dwell = (
            sum(v["dwell_seconds"] for v in not_converted) / max(len(not_converted), 1)
        )

        zone_flow = defaultdict(int)
        for v in visits:
            zones = v.get("zones_visited", [])
            for i in range(len(zones) - 1):
                flow_key = f"{zones[i]} → {zones[i+1]}"
                zone_flow[flow_key] += 1

        top_flows = sorted(zone_flow.items(), key=lambda x: -x[1])[:10]

        total = len(visits_with_dwell)
        entry_count = sum(1 for v in visits if "entry" in v.get("zones_visited", []))
        browse_count = sum(1 for v in visits if "browse" in v.get("zones_visited", []))
        checkout_count = sum(1 for v in visits if "checkout" in v.get("zones_visited", []))
        purchase_count = len(converted)

        funnel = {
            "entry": entry_count or total,
            "browse": browse_count,
            "checkout": checkout_count,
            "purchase": purchase_count,
        }

        insights = []
        recommendations = []

        if converted_avg_dwell > not_converted_avg_dwell * 1.3:
            insights.append({
                "type": "dwell_conversion_correlation",
                "detail": (
                    f"Customers who buy spend {converted_avg_dwell:.0f}s vs "
                    f"{not_converted_avg_dwell:.0f}s for non-buyers. "
                    f"Longer dwell = higher conversion."
                ),
            })
            recommendations.append({
                "action": "Increase dwell time with sampling stations, displays, or seating areas",
                "impact_cents": 0,
            })

        if browse_count > 0 and checkout_count > 0:
            browse_to_checkout = checkout_count / browse_count
            if browse_to_checkout < 0.4:
                drop_count = browse_count - checkout_count
                insights.append({
                    "type": "browse_dropout",
                    "detail": (
                        f"{drop_count} visitors browse but don't reach checkout "
                        f"({browse_to_checkout:.0%} browse→checkout rate)"
                    ),
                })
                recommendations.append({
                    "action": "Review browse zone layout — improve sightlines to checkout, add wayfinding",
                    "impact_cents": 0,
                })

        if avg_dwell < 60:
            insights.append({
                "type": "low_dwell",
                "detail": f"Average dwell {avg_dwell:.0f}s is very low — customers may not be finding what they need",
            })

        score = min(100, 40 + int(avg_dwell / 5) + min(len(visits_with_dwell), 30))
        confidence = min(0.8, 0.35 + len(visits_with_dwell) / 300)

        return self._result(
            summary=f"Avg dwell {avg_dwell:.0f}s (buyers: {converted_avg_dwell:.0f}s vs non-buyers: {not_converted_avg_dwell:.0f}s)",
            score=score,
            insights=insights,
            recommendations=recommendations,
            data={
                "avg_dwell_seconds": round(avg_dwell, 1),
                "median_dwell_seconds": median_dwell,
                "max_dwell_seconds": max_dwell,
                "converted_avg_dwell": round(converted_avg_dwell, 1),
                "not_converted_avg_dwell": round(not_converted_avg_dwell, 1),
                "zone_stats": zone_stats,
                "top_zone_flows": [{"flow": k, "count": v} for k, v in top_flows],
                "funnel": funnel,
                "total_visits": len(visits_with_dwell),
            },
            confidence=confidence,
            calculation_path="full" if len(visits_with_dwell) >= 50 else "partial",
        )
