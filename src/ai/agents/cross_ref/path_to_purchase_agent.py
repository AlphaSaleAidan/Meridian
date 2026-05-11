"""
Path to Purchase Agent — Maps the physical journey customers take before buying.

Finds the most common zone sequences that lead to a purchase vs. those
that lead to walkaway. Identifies "golden paths" and "dead-end" routes.
"""
from collections import Counter
from .base import BaseCrossRefAgent


class PathToPurchaseAgent(BaseCrossRefAgent):
    name = "path_to_purchase"
    description = "Maps zone sequences leading to purchase vs walkaway"
    tier = 3

    async def analyze(self) -> dict:
        if not self.journeys:
            return self._insufficient_data("Customer journey data (connect cameras + POS)")

        converted = self.converted_journeys
        unconverted = self.unconverted_journeys

        buy_paths = Counter()
        for j in converted:
            path = tuple(j.get("zones_visited", []))
            if path:
                buy_paths[path] += 1

        walk_paths = Counter()
        for j in unconverted:
            path = tuple(j.get("zones_visited", []))
            if path:
                walk_paths[path] += 1

        golden_paths = buy_paths.most_common(5)
        dead_ends = walk_paths.most_common(5)

        avg_stops_buy = 0
        avg_stops_walk = 0
        if converted:
            avg_stops_buy = sum(len(j.get("zones_visited", [])) for j in converted) / len(converted)
        if unconverted:
            avg_stops_walk = sum(len(j.get("zones_visited", [])) for j in unconverted) / len(unconverted)

        avg_dwell_buy = 0
        avg_dwell_walk = 0
        if converted:
            avg_dwell_buy = sum(j.get("total_dwell_seconds", 0) for j in converted) / len(converted)
        if unconverted:
            avg_dwell_walk = sum(j.get("total_dwell_seconds", 0) for j in unconverted) / len(unconverted)

        insights = []
        recommendations = []

        if golden_paths:
            top_path = " → ".join(golden_paths[0][0])
            insights.append({
                "type": "golden_path",
                "detail": f"Top purchase path: {top_path} ({golden_paths[0][1]} buyers took this route)",
            })

        if dead_ends:
            top_dead = " → ".join(dead_ends[0][0])
            insights.append({
                "type": "dead_end_path",
                "detail": f"Top walkaway path: {top_dead} ({dead_ends[0][1]} left without buying)",
            })
            recommendations.append({
                "action": f"Add wayfinding or product callouts along the '{top_dead}' route to guide walkers toward checkout",
                "impact_cents": 0,
            })

        if avg_stops_buy > avg_stops_walk * 1.3:
            insights.append({
                "type": "engagement_depth",
                "detail": (
                    f"Buyers visit {avg_stops_buy:.1f} zones vs {avg_stops_walk:.1f} for non-buyers. "
                    f"More zone exposure correlates with purchase."
                ),
            })
            recommendations.append({
                "action": "Design store layout to encourage visiting more zones before checkout",
                "impact_cents": 0,
            })

        self.emit_finding(
            "golden_paths",
            f"Top {len(golden_paths)} purchase paths identified",
            {"paths": [{"path": list(p), "count": c} for p, c in golden_paths]},
        )

        conversion = self._conversion_rate()
        score = min(100, 30 + int(conversion * 100) + min(len(self.journeys), 30))

        return self._result(
            summary=f"{len(converted)} purchases from {len(self.journeys)} journeys, {len(golden_paths)} golden paths found",
            score=score,
            insights=insights,
            recommendations=recommendations,
            data={
                "total_journeys": len(self.journeys),
                "converted": len(converted),
                "conversion_rate": round(conversion, 3),
                "avg_zones_buyers": round(avg_stops_buy, 1),
                "avg_zones_walkers": round(avg_stops_walk, 1),
                "avg_dwell_buyers": round(avg_dwell_buy, 1),
                "avg_dwell_walkers": round(avg_dwell_walk, 1),
                "golden_paths": [{"path": list(p), "count": c} for p, c in golden_paths],
                "dead_end_paths": [{"path": list(p), "count": c} for p, c in dead_ends],
            },
            confidence=min(0.8, 0.3 + len(self.journeys) / 200),
        )
