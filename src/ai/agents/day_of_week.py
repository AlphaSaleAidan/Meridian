from .base import BaseAgent
from collections import defaultdict
from datetime import datetime


class DayOfWeekAgent(BaseAgent):
    name = "day_of_week"
    description = "Best/worst days and day-specific patterns"
    tier = 3

    async def analyze(self) -> dict:
        avail = self.get_data_availability()

        if avail.is_full:
            confidence = avail.quality_score
            path = "full"
        elif avail.is_partial:
            confidence = avail.quality_score
            path = "partial"
        else:
            confidence = min(0.4, avail.quality_score)
            path = "minimal"

        # Adjust confidence based on weeks of data
        if avail.date_range_days >= 28:
            confidence = max(confidence, 0.9)
        elif avail.date_range_days < 14:
            confidence = min(confidence, 0.5)

        daily = self.ctx.daily_revenue

        # --- MINIMAL path: industry DOW pattern ---
        if path == "minimal" or len(daily) < 7:
            bench = self.get_benchmark_range("day_of_week_spread_pct")
            source = bench.source if bench else "industry default"
            day_names = [
                "Monday", "Tuesday", "Wednesday", "Thursday",
                "Friday", "Saturday", "Sunday",
            ]
            default_stats = [
                {"day": "Monday", "day_index": 0, "avg_revenue_cents": 8000, "relative_pct": 85},
                {"day": "Tuesday", "day_index": 1, "avg_revenue_cents": 8500, "relative_pct": 90},
                {"day": "Wednesday", "day_index": 2, "avg_revenue_cents": 9000, "relative_pct": 95},
                {"day": "Thursday", "day_index": 3, "avg_revenue_cents": 9500, "relative_pct": 100},
                {"day": "Friday", "day_index": 4, "avg_revenue_cents": 11000, "relative_pct": 116},
                {"day": "Saturday", "day_index": 5, "avg_revenue_cents": 12000, "relative_pct": 127},
                {"day": "Sunday", "day_index": 6, "avg_revenue_cents": 7500, "relative_pct": 79},
            ]
            return self._result(
                summary=f"Day-of-week pattern estimated from industry benchmarks (source: {source})",
                score=50,
                insights=[{
                    "type": "estimated_dow",
                    "detail": f"Using industry day-of-week pattern — need 14+ days for real analysis (source: {source})",
                }],
                recommendations=[{
                    "action": "Connect more data sources for precise analysis",
                    "impact": "Improves accuracy from estimated to actual",
                    "effort": "low",
                }],
                data={
                    "day_stats": default_stats,
                    "benchmark_source": source,
                },
                confidence=confidence,
                calculation_path=path,
            )

        if len(daily) < 14:
            return self._insufficient_data("At least 14 days of daily revenue")

        day_names = [
            "Monday", "Tuesday", "Wednesday", "Thursday",
            "Friday", "Saturday", "Sunday",
        ]
        dow_rev = defaultdict(list)
        for d in daily:
            try:
                dt = datetime.fromisoformat(
                    d.get("date", "").replace("Z", "+00:00")
                )
                dow_rev[dt.weekday()].append(d.get("revenue_cents", 0))
            except (ValueError, AttributeError):
                pass

        day_stats = []
        for i in range(7):
            revs = dow_rev.get(i, [])
            if not revs:
                continue
            avg = sum(revs) // len(revs)
            variance = sum((r - avg) ** 2 for r in revs) / max(len(revs) - 1, 1)
            std = int(variance ** 0.5)
            day_stats.append({
                "day": day_names[i],
                "day_index": i,
                "avg_revenue_cents": avg,
                "std_dev_cents": std,
                "sample_count": len(revs),
                "consistency_score": round(
                    100 - (std / max(avg, 1) * 100), 1
                ),
            })

        if not day_stats:
            return self._insufficient_data("Revenue data with valid dates")

        day_stats.sort(key=lambda x: x["avg_revenue_cents"], reverse=True)
        best = day_stats[0]
        worst = day_stats[-1]

        overall_avg = (
            sum(d["avg_revenue_cents"] for d in day_stats) // len(day_stats)
        )
        gap = best["avg_revenue_cents"] - worst["avg_revenue_cents"]
        gap_pct = round(gap / max(overall_avg, 1) * 100, 1)

        weak_days = [
            d for d in day_stats
            if d["avg_revenue_cents"] < overall_avg * 0.8
        ]
        score = max(0, 100 - len(weak_days) * 15)

        insights = [
            {
                "type": "day_ranking",
                "detail": (
                    f"Best: {best['day']}"
                    f" (${best['avg_revenue_cents'] / 100:,.0f}),"
                    f" Worst: {worst['day']}"
                    f" (${worst['avg_revenue_cents'] / 100:,.0f}),"
                    f" gap: {gap_pct}%"
                ),
            }
        ]
        if weak_days:
            weak_names = ", ".join(d["day"] for d in weak_days)
            insights.append({
                "type": "weak_days",
                "detail": f"Consistently weak: {weak_names}",
            })

        # Recovery target: weakest day revenue * 1.3, annualized
        recovery_target_daily = int(worst["avg_revenue_cents"] * 1.3)
        recovery_uplift_daily = recovery_target_daily - worst["avg_revenue_cents"]
        recovery_target_annual = recovery_uplift_daily * 52  # 52 weeks

        recommendations = []
        for wd in weak_days:
            recommendations.append({
                "action": (
                    f"Run {wd['day']}-specific promotion"
                    f" to close ${gap / 100:,.0f} gap"
                ),
                "impact_cents": gap // 3,
            })
        if path != "full":
            recommendations.append({
                "action": "Connect more data sources for precise analysis",
                "impact": "Improves accuracy from estimated to actual",
                "effort": "low",
            })

        return self._result(
            summary=(
                f"Best day: {best['day']}, worst: {worst['day']},"
                f" {gap_pct}% spread"
            ),
            score=score,
            insights=insights,
            recommendations=recommendations,
            data={
                "day_stats": day_stats,
                "best_day": best,
                "worst_day": worst,
                "gap_pct": gap_pct,
                "weak_days": weak_days,
                "recovery_target": {
                    "weakest_day": worst["day"],
                    "current_avg_cents": worst["avg_revenue_cents"],
                    "target_avg_cents": recovery_target_daily,
                    "annual_uplift_cents": recovery_target_annual,
                },
            },
            confidence=confidence,
            calculation_path=path,
        )
