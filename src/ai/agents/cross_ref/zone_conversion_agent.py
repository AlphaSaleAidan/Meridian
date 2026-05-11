"""
Zone Conversion Agent — Measures per-zone conversion rates.

Identifies which zones act as purchase accelerators vs. dead zones.
Calculates the "conversion lift" of visiting a specific zone.
"""
from collections import defaultdict
from .base import BaseCrossRefAgent


class ZoneConversionAgent(BaseCrossRefAgent):
    name = "zone_conversion"
    description = "Per-zone conversion rates and purchase acceleration analysis"
    tier = 3

    async def analyze(self) -> dict:
        if not self.journeys:
            return self._insufficient_data("Customer journey data with zone tracking")

        zone_visits: dict[str, int] = defaultdict(int)
        zone_conversions: dict[str, int] = defaultdict(int)
        zone_revenue: dict[str, int] = defaultdict(int)
        zone_dwell_total: dict[str, float] = defaultdict(float)
        zone_dwell_count: dict[str, int] = defaultdict(int)

        for j in self.journeys:
            zones_seen = set()
            for stop in j.get("zone_stops", []):
                zn = stop.get("zone_name", "")
                if not zn or zn in zones_seen:
                    continue
                zones_seen.add(zn)
                zone_visits[zn] += 1
                zone_dwell_total[zn] += stop.get("dwell_seconds", 0)
                zone_dwell_count[zn] += 1

                if j.get("converted"):
                    zone_conversions[zn] += 1
                    zone_revenue[zn] += j.get("transaction_total_cents", 0)

        overall_conv = self._conversion_rate()

        zone_stats = {}
        accelerators = []
        dead_zones = []

        for zn in zone_visits:
            visits = zone_visits[zn]
            convs = zone_conversions[zn]
            rate = convs / max(visits, 1)
            avg_dwell = zone_dwell_total[zn] / max(zone_dwell_count[zn], 1)
            lift = (rate / overall_conv - 1) if overall_conv > 0 else 0

            stats = {
                "visits": visits,
                "conversions": convs,
                "conversion_rate": round(rate, 3),
                "lift_vs_baseline": round(lift, 3),
                "avg_dwell_seconds": round(avg_dwell, 1),
                "total_revenue_cents": zone_revenue[zn],
                "revenue_per_visit_cents": int(zone_revenue[zn] / max(visits, 1)),
            }
            zone_stats[zn] = stats

            if lift > 0.15 and visits >= 5:
                accelerators.append((zn, stats))
            elif lift < -0.15 and visits >= 5:
                dead_zones.append((zn, stats))

        insights = []
        recommendations = []

        for zn, stats in sorted(accelerators, key=lambda x: -x[1]["lift_vs_baseline"])[:3]:
            insights.append({
                "type": "zone_accelerator",
                "detail": (
                    f"'{zn}' zone boosts conversion by {stats['lift_vs_baseline']:.0%} "
                    f"({stats['conversion_rate']:.0%} vs {overall_conv:.0%} baseline)"
                ),
            })

        for zn, stats in sorted(dead_zones, key=lambda x: x[1]["lift_vs_baseline"])[:3]:
            insights.append({
                "type": "dead_zone",
                "detail": (
                    f"'{zn}' zone hurts conversion by {abs(stats['lift_vs_baseline']):.0%} — "
                    f"visitors who enter convert at only {stats['conversion_rate']:.0%}"
                ),
            })
            recommendations.append({
                "action": f"Redesign '{zn}' zone — add product highlights or redirect traffic toward accelerator zones",
                "impact_cents": 0,
            })

        self.emit_finding(
            "zone_conversion_rates",
            f"{len(accelerators)} accelerator zones, {len(dead_zones)} dead zones",
            {"zone_stats": zone_stats},
        )

        score = min(100, 40 + len(accelerators) * 10 + min(len(self.journeys), 30))

        return self._result(
            summary=f"{len(zone_stats)} zones analyzed, {len(accelerators)} accelerators, {len(dead_zones)} dead zones",
            score=score,
            insights=insights,
            recommendations=recommendations,
            data={
                "zone_stats": zone_stats,
                "overall_conversion": round(overall_conv, 3),
                "accelerator_zones": [z[0] for z in accelerators],
                "dead_zones": [z[0] for z in dead_zones],
            },
            confidence=min(0.8, 0.3 + len(self.journeys) / 200),
        )
