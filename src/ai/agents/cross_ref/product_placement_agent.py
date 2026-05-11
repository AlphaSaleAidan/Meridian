"""
Product Placement Agent — Optimizes product position based on zone traffic and sales.

Cross-references which zones get the most dwell time with which products
sell best, identifying placement mismatches (high-traffic zone has
low-margin products, or hero products are in low-traffic areas).
"""
from collections import defaultdict
from .base import BaseCrossRefAgent


class ProductPlacementAgent(BaseCrossRefAgent):
    name = "product_placement"
    description = "Optimizes product positioning by cross-referencing zone traffic with sales data"
    tier = 4

    async def analyze(self) -> dict:
        converted = self.converted_journeys
        transactions = self.ctx.transactions

        if not converted or not transactions:
            return self._insufficient_data("Converted journeys with transaction data")

        zone_traffic = defaultdict(int)
        zone_dwell = defaultdict(float)
        for j in self.journeys:
            for stop in j.get("zone_stops", []):
                zn = stop.get("zone_name", "")
                if zn:
                    zone_traffic[zn] += 1
                    zone_dwell[zn] += stop.get("dwell_seconds", 0)

        zone_avg_dwell = {
            z: round(zone_dwell[z] / max(zone_traffic[z], 1), 1)
            for z in zone_traffic
        }

        top_products = defaultdict(lambda: {"sold": 0, "revenue_cents": 0})
        for txn in transactions[:500]:
            for item in txn.get("items", []) or txn.get("line_items", []):
                name = item.get("name", item.get("product_name", "Unknown"))
                qty = item.get("quantity", 1)
                amount = item.get("total_money_cents", item.get("amount_cents", 0))
                top_products[name]["sold"] += qty
                top_products[name]["revenue_cents"] += amount

        hero_products = sorted(
            top_products.items(),
            key=lambda x: x[1]["revenue_cents"],
            reverse=True,
        )[:10]

        traffic_ranked = sorted(zone_traffic.items(), key=lambda x: -x[1])
        dwell_ranked = sorted(zone_avg_dwell.items(), key=lambda x: -x[1])

        insights = []
        recommendations = []

        if traffic_ranked and dwell_ranked:
            high_traffic_zone = traffic_ranked[0][0]
            high_dwell_zone = dwell_ranked[0][0]

            if high_traffic_zone != high_dwell_zone:
                insights.append({
                    "type": "traffic_dwell_mismatch",
                    "detail": (
                        f"Highest traffic zone '{high_traffic_zone}' ({traffic_ranked[0][1]} visits) "
                        f"differs from highest dwell zone '{high_dwell_zone}' ({dwell_ranked[0][1]}s avg dwell). "
                        f"Place impulse items in traffic zones, considered purchases in dwell zones."
                    ),
                })

            if hero_products:
                recommendations.append({
                    "action": (
                        f"Place top seller '{hero_products[0][0]}' in '{high_traffic_zone}' zone "
                        f"(highest foot traffic) for maximum visibility"
                    ),
                    "impact_cents": 0,
                })

        if len(traffic_ranked) >= 3:
            low_traffic_zone = traffic_ranked[-1][0]
            insights.append({
                "type": "low_traffic_zone",
                "detail": (
                    f"'{low_traffic_zone}' gets least traffic ({traffic_ranked[-1][1]} visits). "
                    f"Consider wayfinding improvements or relocating anchor products here."
                ),
            })

        zone_engagement = {}
        for z in zone_traffic:
            engagement = zone_traffic[z] * zone_avg_dwell.get(z, 0)
            zone_engagement[z] = {
                "traffic": zone_traffic[z],
                "avg_dwell_seconds": zone_avg_dwell.get(z, 0),
                "engagement_score": round(engagement / 100, 1),
            }

        self.emit_finding(
            "placement_analysis",
            f"{len(zone_traffic)} zones analyzed, {len(hero_products)} hero products identified",
            {"top_zones": dict(traffic_ranked[:5]), "hero_products": [h[0] for h in hero_products[:5]]},
        )

        score = min(100, 40 + min(len(zone_traffic), 5) * 8 + min(len(converted), 20))

        return self._result(
            summary=f"{len(zone_traffic)} zones, top traffic: {traffic_ranked[0][0] if traffic_ranked else 'N/A'}, {len(hero_products)} hero products",
            score=score,
            insights=insights,
            recommendations=recommendations,
            data={
                "zone_engagement": zone_engagement,
                "hero_products": [
                    {"name": name, "sold": data["sold"], "revenue_cents": data["revenue_cents"]}
                    for name, data in hero_products
                ],
                "traffic_ranking": dict(traffic_ranked),
                "dwell_ranking": dict(dwell_ranked),
            },
            confidence=min(0.7, 0.25 + len(converted) / 100),
        )
