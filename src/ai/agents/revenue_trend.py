from .base import BaseAgent
from collections import defaultdict
from datetime import datetime

class RevenueTrendAgent(BaseAgent):
    name = "revenue_trend"
    description = "Daily/weekly/monthly growth rates and trend signals"
    tier = 1

    async def analyze(self) -> dict:
        avail = self.get_data_availability()
        daily = self.ctx.daily_revenue

        # Choose calculation path
        if avail.is_full:
            confidence = avail.quality_score
            path = "full"
        elif avail.is_partial:
            confidence = avail.quality_score
            path = "partial"
        else:
            confidence = min(0.4, avail.quality_score)
            path = "minimal"

        # MINIMAL: use benchmark growth rates when no daily data
        if path == "minimal" or len(daily) < 7:
            if len(daily) < 7 and path != "minimal":
                return self._insufficient_data("At least 7 days of revenue data")
            growth_range = self.get_benchmark_range("healthy_wow_growth_pct")
            bench_growth = growth_range.mid if growth_range else 2.0
            insights = [{"type": "benchmark_estimate", "detail": f"Using industry benchmark WoW growth of {bench_growth}% (no sufficient daily data)"}]
            if growth_range:
                insights[0]["benchmark"] = {"low": growth_range.low, "mid": growth_range.mid, "high": growth_range.high, "source": growth_range.source}
                insights[0]["estimated"] = True
            recommendations = [{
                "action": "Connect POS line-item data for precise analysis",
                "impact": "Improves accuracy from estimated to actual values",
                "effort": "low",
            }]
            return self._result(
                summary=f"Estimated WoW growth ~{bench_growth}% (industry benchmark)",
                score=50,
                insights=insights,
                recommendations=recommendations,
                data={"wow_growth_pct": bench_growth, "source": "benchmark", "days_analyzed": len(daily)},
                confidence=confidence,
                calculation_path=path,
            )

        sorted_days = sorted(daily, key=lambda d: d.get("date", ""))

        # Daily totals
        revenues = [d.get("revenue_cents", 0) for d in sorted_days]
        total = sum(revenues)
        avg_daily = total // len(revenues)

        # Week-over-week
        if len(revenues) >= 14:
            recent_week = sum(revenues[-7:])
            prior_week = sum(revenues[-14:-7])
            wow_growth = round((recent_week - prior_week) / max(prior_week, 1) * 100, 1)
        else:
            wow_growth = 0.0

        # Month-over-month
        if len(revenues) >= 60:
            recent_month = sum(revenues[-30:])
            prior_month = sum(revenues[-60:-30])
            mom_growth = round((recent_month - prior_month) / max(prior_month, 1) * 100, 1)
        else:
            mom_growth = None

        # Trend direction (simple linear regression slope)
        n = len(revenues)
        x_mean = (n - 1) / 2
        y_mean = sum(revenues) / n
        numerator = sum((i - x_mean) * (r - y_mean) for i, r in enumerate(revenues))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        slope = numerator / max(denominator, 1)
        trend = "accelerating" if slope > avg_daily * 0.01 else "decelerating" if slope < -avg_daily * 0.01 else "stable"

        # Compare to benchmark
        growth_range = self.get_benchmark_range("healthy_wow_growth_pct")
        benchmark_growth = growth_range.mid if growth_range else (self.get_benchmark("healthy_wow_growth_pct") or 2.0)
        score = min(100, max(0, 50 + (wow_growth - benchmark_growth) * 10))

        insights = []
        trend_insight = {}
        if wow_growth > benchmark_growth:
            trend_insight = {"type": "positive_trend", "detail": f"WoW growth {wow_growth}% exceeds benchmark {benchmark_growth}%"}
        elif wow_growth < 0:
            trend_insight = {"type": "declining_revenue", "detail": f"Revenue declined {wow_growth}% week-over-week", "severity": "high"}
        if trend_insight:
            if growth_range:
                trend_insight["benchmark"] = {"low": growth_range.low, "mid": growth_range.mid, "high": growth_range.high, "source": growth_range.source}
            trend_insight["estimated"] = path != "full"
            insights.append(trend_insight)

        recommendations = []
        if wow_growth < 0:
            recommendations.append({"action": "Investigate revenue decline — check traffic, pricing, and competitor activity", "impact_estimate": "Stabilize before optimizing"})
        if trend == "decelerating":
            recommendations.append({"action": "Growth is slowing — consider new promotions or menu updates", "impact_estimate": "Prevent further deceleration"})
        if path == "partial":
            recommendations.append({"action": "Connect POS line-item data for precise analysis", "impact": "Improves accuracy from estimated to actual values", "effort": "low"})

        return self._result(
            summary=f"Revenue {'growing' if wow_growth > 0 else 'declining'} at {wow_growth}% WoW, trend {trend}",
            score=score,
            insights=insights,
            recommendations=recommendations,
            data={
                "total_revenue_cents": total,
                "avg_daily_cents": avg_daily,
                "wow_growth_pct": wow_growth,
                "mom_growth_pct": mom_growth,
                "trend_direction": trend,
                "slope_cents_per_day": round(slope),
                "days_analyzed": n,
            },
            confidence=confidence,
            calculation_path=path,
        )
