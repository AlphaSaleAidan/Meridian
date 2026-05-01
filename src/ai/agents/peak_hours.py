from .base import BaseAgent
from collections import defaultdict


class PeakHoursAgent(BaseAgent):
    name = "peak_hours"
    description = "Revenue heatmap and peak hour optimization"
    tier = 3

    async def analyze(self) -> dict:
        path, confidence = self._select_path()
        hourly = self.ctx.hourly_revenue

        # --- MINIMAL path: use industry benchmarks ---
        if path == "minimal" or len(hourly) < 24:
            bench = self.get_benchmark_range("peak_hours")
            peak_hours_default = [11, 12, 13, 17, 18, 19]
            source = bench.source if bench else "industry default"
            return self._result(
                summary="Peak hours estimated from industry benchmarks (no hourly data)",
                score=50,
                insights=[{
                    "type": "estimated_peak",
                    "detail": f"Estimated peak hours: 11-13, 17-19 (source: {source})",
                }],
                recommendations=[{
                    "action": "Connect more data sources for precise analysis",
                    "impact": "Improves accuracy from estimated to actual",
                    "effort": "low",
                }],
                data={
                    "estimated_peak_hours": peak_hours_default,
                    "benchmark_source": source,
                },
                confidence=confidence,
                calculation_path=path,
            )

        # --- PARTIAL path: estimate from transaction timestamps ---
        if path == "partial":
            # We have hourly data but may lack items/products/inventory depth
            confidence = min(0.9, confidence) if len(hourly) >= 168 else confidence

        # --- FULL path: real heatmap ---
        if path == "full":
            confidence = 0.9 if len(hourly) >= 168 else min(0.9, confidence)

        # Build 7x24 heatmap
        heatmap = defaultdict(lambda: defaultdict(lambda: {"revenue": 0, "count": 0, "txns": 0}))
        for h in hourly:
            dow = h.get("day_of_week", 0)
            hour = h.get("hour", 0)
            heatmap[dow][hour]["revenue"] += h.get("revenue_cents", 0)
            heatmap[dow][hour]["count"] += 1
            heatmap[dow][hour]["txns"] += h.get("transaction_count", 0)

        # Avg revenue per hour slot
        hour_avgs = {}
        for dow in range(7):
            for hour in range(24):
                cell = heatmap[dow][hour]
                avg = cell["revenue"] // max(cell["count"], 1)
                hour_avgs[(dow, hour)] = avg

        # Find top and bottom windows
        sorted_windows = sorted(hour_avgs.items(), key=lambda x: -x[1])
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        top_5 = [
            {"day": day_names[k[0]], "hour": k[1], "avg_revenue_cents": v}
            for k, v in sorted_windows[:5]
        ]
        bottom_5 = [
            {"day": day_names[k[0]], "hour": k[1], "avg_revenue_cents": v}
            for k, v in sorted_windows[-5:]
            if v > 0
        ]

        # Golden hour
        golden = top_5[0] if top_5 else None

        # Hourly totals for staffing
        hour_totals = defaultdict(int)
        hour_counts = defaultdict(int)
        hour_txn_totals = defaultdict(int)
        hour_txn_counts = defaultdict(int)
        for (dow, hour), avg in hour_avgs.items():
            hour_totals[hour] += avg
            hour_counts[hour] += 1
        for dow in range(7):
            for hour in range(24):
                cell = heatmap[dow][hour]
                if cell["count"] > 0:
                    hour_txn_totals[hour] += cell["txns"] // cell["count"]
                    hour_txn_counts[hour] += 1

        hourly_profile = []
        for hour in range(24):
            avg = hour_totals[hour] // max(hour_counts[hour], 1)
            avg_txns = hour_txn_totals[hour] // max(hour_txn_counts[hour], 1)
            hourly_profile.append({
                "hour": hour,
                "avg_revenue_cents": avg,
                "avg_txn_count": avg_txns,
            })

        total_daily = sum(h["avg_revenue_cents"] for h in hourly_profile)
        peak_share = sum(
            h["avg_revenue_cents"]
            for h in sorted(hourly_profile, key=lambda x: -x["avg_revenue_cents"])[:3]
        )
        peak_share_pct = round(peak_share / max(total_daily, 1) * 100, 1)

        benchmark = self.get_benchmark("peak_hour_revenue_share_pct") or 40
        score = (
            min(100, 50 + (peak_share_pct - benchmark) * 2)
            if peak_share_pct > 0
            else 50
        )

        # Staffing mismatch: hours where txn_count > median but avg_ticket < overall_avg
        all_txn_counts = [h["avg_txn_count"] for h in hourly_profile if h["avg_txn_count"] > 0]
        median_txns = sorted(all_txn_counts)[len(all_txn_counts) // 2] if all_txn_counts else 0
        overall_avg_ticket = total_daily // max(sum(h["avg_txn_count"] for h in hourly_profile), 1)
        staffing_mismatch = []
        for h in hourly_profile:
            if h["avg_txn_count"] > median_txns and h["avg_revenue_cents"] > 0:
                hour_avg_ticket = h["avg_revenue_cents"] // max(h["avg_txn_count"], 1)
                if hour_avg_ticket < overall_avg_ticket:
                    staffing_mismatch.append({
                        "hour": h["hour"],
                        "txn_count": h["avg_txn_count"],
                        "avg_ticket_cents": hour_avg_ticket,
                        "overall_avg_ticket_cents": overall_avg_ticket,
                    })

        insights = []
        if golden:
            insights.append({
                "type": "golden_hour",
                "detail": (
                    f"Most profitable window: {golden['day']} {golden['hour']}:00"
                    f" (${golden['avg_revenue_cents'] / 100:,.0f} avg)"
                ),
            })
        if staffing_mismatch:
            mismatch_hours = ", ".join(f"{m['hour']}:00" for m in staffing_mismatch[:3])
            insights.append({
                "type": "staffing_mismatch",
                "detail": (
                    f"{len(staffing_mismatch)} hours with high traffic but below-avg ticket"
                    f" — consider upsell training at {mismatch_hours}"
                ),
            })

        recommendations = []
        if bottom_5:
            dead = bottom_5[0]
            recommendations.append({
                "action": (
                    f"Consider promotions during {dead['day']} {dead['hour']}:00"
                    " — lowest revenue window"
                ),
                "impact_cents": 0,
            })
        if path != "full":
            recommendations.append({
                "action": "Connect more data sources for precise analysis",
                "impact": "Improves accuracy from estimated to actual",
                "effort": "low",
            })

        # Heatmap grid for frontend
        grid = []
        for dow in range(7):
            for hour in range(24):
                grid.append({
                    "day_of_week": dow,
                    "hour": hour,
                    "avg_revenue_cents": hour_avgs.get((dow, hour), 0),
                })

        summary = (
            f"Peak 3 hours drive {peak_share_pct}% of daily revenue."
            f" Golden hour: {golden['day']} {golden['hour']}:00"
            if golden
            else "Insufficient hourly data"
        )

        return self._result(
            summary=summary,
            score=score,
            insights=insights,
            recommendations=recommendations,
            data={
                "heatmap": grid,
                "top_5_windows": top_5,
                "bottom_5_windows": bottom_5,
                "golden_hour": golden,
                "hourly_profile": hourly_profile,
                "peak_share_pct": peak_share_pct,
                "staffing_mismatch": staffing_mismatch,
            },
            confidence=confidence,
            calculation_path=path,
        )
