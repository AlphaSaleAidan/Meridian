"""
Influence Zone Agent — Identifies zones that influence basket size.

Measures how visiting certain zones correlates with larger or smaller
transaction amounts. Finds "upsell zones" that increase ticket size.
"""
from collections import defaultdict
from .base import BaseCrossRefAgent


class InfluenceZoneAgent(BaseCrossRefAgent):
    name = "influence_zone"
    description = "Identifies zones that correlate with higher basket size"
    tier = 3

    async def analyze(self) -> dict:
        converted = self.converted_journeys
        if not converted or len(converted) < 5:
            return self._insufficient_data("At least 5 converted journeys with transaction data")

        avg_basket = self._avg_basket_cents()

        zone_baskets: dict[str, list[int]] = defaultdict(list)

        for j in converted:
            total = j.get("transaction_total_cents", 0)
            if not total:
                continue
            zones_seen = set()
            for stop in j.get("zone_stops", []):
                zn = stop.get("zone_name", "")
                if zn and zn not in zones_seen:
                    zones_seen.add(zn)
                    zone_baskets[zn].append(total)

        zone_influence = {}
        upsell_zones = []

        for zn, baskets in zone_baskets.items():
            if len(baskets) < 3:
                continue
            avg = sum(baskets) / len(baskets)
            lift_cents = avg - avg_basket
            lift_pct = (avg / avg_basket - 1) if avg_basket > 0 else 0

            zone_influence[zn] = {
                "avg_basket_cents": int(avg),
                "lift_cents": int(lift_cents),
                "lift_pct": round(lift_pct, 3),
                "sample_size": len(baskets),
            }

            if lift_pct > 0.1 and len(baskets) >= 5:
                upsell_zones.append((zn, zone_influence[zn]))

        upsell_zones.sort(key=lambda x: -x[1]["lift_pct"])

        insights = []
        recommendations = []

        for zn, stats in upsell_zones[:3]:
            insights.append({
                "type": "upsell_zone",
                "detail": (
                    f"Visitors to '{zn}' zone spend {stats['lift_pct']:.0%} more "
                    f"(${stats['avg_basket_cents'] / 100:.2f} vs ${avg_basket / 100:.2f} avg)"
                ),
            })

        if upsell_zones:
            top = upsell_zones[0]
            recommendations.append({
                "action": f"Route more traffic through '{top[0]}' zone — it lifts basket size by ${top[1]['lift_cents'] / 100:.2f}",
                "impact_cents": top[1]["lift_cents"] * len(converted) // 10,
            })

        self.emit_finding(
            "influence_zones",
            f"{len(upsell_zones)} upsell zones found",
            {"zones": {z: s for z, s in upsell_zones}},
        )

        score = min(100, 40 + len(upsell_zones) * 15 + min(len(converted), 25))

        return self._result(
            summary=f"{len(upsell_zones)} upsell zones identified, avg basket ${avg_basket / 100:.2f}",
            score=score,
            insights=insights,
            recommendations=recommendations,
            data={
                "zone_influence": zone_influence,
                "upsell_zones": [z[0] for z in upsell_zones],
                "avg_basket_cents": avg_basket,
                "total_converted": len(converted),
            },
            confidence=min(0.75, 0.3 + len(converted) / 100),
        )
