from .base import BaseAgent
from collections import defaultdict


class DemographicProfilerAgent(BaseAgent):
    name = "demographic_profiler"
    description = "Age/gender distribution, segment-specific conversion, daypart demographics"
    tier = 3

    async def analyze(self) -> dict:
        visitors = getattr(self.ctx, "vision_visitors", [])
        visits = getattr(self.ctx, "vision_visits", [])
        traffic = getattr(self.ctx, "vision_traffic", [])

        visitors_with_demo = [
            v for v in visitors
            if v.get("demographic") and v["demographic"] != {}
        ]

        if not visitors_with_demo:
            return self._insufficient_data(
                "Demographic data (requires opt_in_identity mode with demographic detection enabled)"
            )

        age_dist = defaultdict(int)
        gender_dist = defaultdict(int)
        for v in visitors_with_demo:
            demo = v["demographic"]
            age = demo.get("age_range", "unknown")
            gender = demo.get("gender_est", "unknown")
            age_dist[age] += 1
            gender_dist[gender] += 1

        total = len(visitors_with_demo)
        age_pct = {k: round(v / total * 100, 1) for k, v in sorted(age_dist.items())}
        gender_pct = {k: round(v / total * 100, 1) for k, v in sorted(gender_dist.items())}

        dominant_age = max(age_dist, key=age_dist.get) if age_dist else "unknown"
        dominant_gender = max(gender_dist, key=gender_dist.get) if gender_dist else "unknown"

        visitor_ids_by_age = defaultdict(set)
        for v in visitors_with_demo:
            age = v["demographic"].get("age_range", "unknown")
            visitor_ids_by_age[age].add(v["id"])

        segment_conversion = {}
        for age_range, vid_set in visitor_ids_by_age.items():
            segment_visits = [v for v in visits if v.get("visitor_id") in vid_set]
            segment_converted = [v for v in segment_visits if v.get("converted")]
            conv_rate = len(segment_converted) / max(len(segment_visits), 1)
            segment_conversion[age_range] = {
                "visits": len(segment_visits),
                "conversions": len(segment_converted),
                "conversion_rate": round(conv_rate, 3),
            }

        daypart_demo = defaultdict(lambda: defaultdict(int))
        for r in traffic:
            demo_breakdown = r.get("demographic_breakdown", {})
            bucket = r.get("bucket", "")
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(bucket.replace("Z", "+00:00"))
                if dt.hour < 11:
                    daypart = "morning"
                elif dt.hour < 14:
                    daypart = "lunch"
                elif dt.hour < 17:
                    daypart = "afternoon"
                else:
                    daypart = "evening"
                for age_range, count in demo_breakdown.items():
                    daypart_demo[daypart][age_range] += count
            except (ValueError, AttributeError):
                pass

        insights = []
        recommendations = []

        insights.append({
            "type": "demographic_profile",
            "detail": (
                f"Primary customer: {dominant_age}, {dominant_gender} "
                f"({age_pct.get(dominant_age, 0)}% of visitors)"
            ),
        })

        best_segment = None
        best_conv = 0
        worst_segment = None
        worst_conv = 1.0
        for age, data in segment_conversion.items():
            if data["visits"] >= 10:
                if data["conversion_rate"] > best_conv:
                    best_conv = data["conversion_rate"]
                    best_segment = age
                if data["conversion_rate"] < worst_conv:
                    worst_conv = data["conversion_rate"]
                    worst_segment = age

        if best_segment and worst_segment and best_segment != worst_segment:
            insights.append({
                "type": "segment_conversion_gap",
                "detail": (
                    f"{best_segment} converts at {best_conv:.0%} vs "
                    f"{worst_segment} at {worst_conv:.0%}. "
                    f"Tailor experience for underperforming segments."
                ),
            })
            recommendations.append({
                "action": (
                    f"Analyze why {worst_segment} has low conversion — "
                    f"product mix, pricing, or store layout may not match their preferences"
                ),
                "impact_cents": 0,
            })

        if dominant_age != "unknown":
            recommendations.append({
                "action": (
                    f"Your core demographic is {dominant_age} — "
                    f"ensure marketing, product selection, and store ambiance match this segment"
                ),
                "impact_cents": 0,
            })

        score = min(100, 40 + min(total, 40) + len(segment_conversion) * 5)
        confidence = min(0.7, 0.3 + total / 200)

        return self._result(
            summary=f"Core: {dominant_age} {dominant_gender} ({total} profiled visitors)",
            score=score,
            insights=insights,
            recommendations=recommendations,
            data={
                "total_profiled": total,
                "age_distribution": age_pct,
                "gender_distribution": gender_pct,
                "dominant_age": dominant_age,
                "dominant_gender": dominant_gender,
                "segment_conversion": segment_conversion,
                "daypart_demographics": dict(daypart_demo),
            },
            confidence=confidence,
            calculation_path="full" if total >= 50 else "partial",
        )
