"""
Staff Effect Agent — Correlates staff proximity with conversion.

Measures how staff presence in zones affects customer conversion rates
and basket sizes. Identifies zones that benefit most from staff attention.
"""
from collections import defaultdict
from .base import BaseCrossRefAgent


class StaffEffectAgent(BaseCrossRefAgent):
    name = "staff_effect"
    description = "Correlates staff zone presence with customer conversion and basket size"
    tier = 3

    async def analyze(self) -> dict:
        if not self.journeys:
            return self._insufficient_data("Customer journey data")

        staff_positions = self.ctx.staff_positions
        if not staff_positions:
            return self._result(
                summary="No staff position data — connect cameras with staff tracking to enable this analysis",
                score=50,
                insights=[{
                    "type": "no_staff_data",
                    "detail": "Staff position tracking not yet enabled. Enable camera-based staff detection for correlation analysis.",
                }],
                recommendations=[{
                    "action": "Enable staff position tracking in camera pipeline settings",
                    "impact_cents": 0,
                }],
                data={"staff_data_available": False},
                confidence=0.2,
                calculation_path="minimal",
            )

        staff_zone_times: dict[str, float] = defaultdict(float)
        for sp in staff_positions:
            zone = sp.get("zone", "")
            duration = sp.get("duration_seconds", 0)
            if zone:
                staff_zone_times[zone] += duration

        zone_with_staff: dict[str, dict] = defaultdict(lambda: {"converted": 0, "total": 0, "baskets": []})
        zone_without_staff: dict[str, dict] = defaultdict(lambda: {"converted": 0, "total": 0, "baskets": []})

        staffed_zones = set(z for z, t in staff_zone_times.items() if t > 60)

        for j in self.journeys:
            for stop in j.get("zone_stops", []):
                zn = stop.get("zone_name", "")
                if not zn:
                    continue
                bucket = zone_with_staff[zn] if zn in staffed_zones else zone_without_staff[zn]
                bucket["total"] += 1
                if j.get("converted"):
                    bucket["converted"] += 1
                    if j.get("transaction_total_cents"):
                        bucket["baskets"].append(j["transaction_total_cents"])

        insights = []
        recommendations = []

        for zn in set(list(zone_with_staff.keys()) + list(zone_without_staff.keys())):
            ws = zone_with_staff.get(zn, {"converted": 0, "total": 0, "baskets": []})
            wos = zone_without_staff.get(zn, {"converted": 0, "total": 0, "baskets": []})

            if ws["total"] < 5 or wos["total"] < 5:
                continue

            rate_staffed = ws["converted"] / max(ws["total"], 1)
            rate_unstaffed = wos["converted"] / max(wos["total"], 1)

            if rate_staffed > rate_unstaffed * 1.25:
                lift = rate_staffed / max(rate_unstaffed, 0.01) - 1
                insights.append({
                    "type": "staff_conversion_lift",
                    "detail": (
                        f"Staff presence in '{zn}' lifts conversion by {lift:.0%} "
                        f"({rate_staffed:.0%} vs {rate_unstaffed:.0%} without staff)"
                    ),
                })
                recommendations.append({
                    "action": f"Prioritize staffing '{zn}' zone during peak hours for {lift:.0%} conversion lift",
                    "impact_cents": 0,
                })

        score = min(100, 40 + len(insights) * 15 + min(len(self.journeys), 25))

        return self._result(
            summary=f"Staff effect analyzed across {len(staffed_zones)} staffed zones",
            score=score,
            insights=insights,
            recommendations=recommendations,
            data={
                "staffed_zones": list(staffed_zones),
                "staff_zone_hours": {z: round(t / 3600, 1) for z, t in staff_zone_times.items()},
                "total_journeys": len(self.journeys),
            },
            confidence=min(0.7, 0.25 + len(self.journeys) / 200),
        )
