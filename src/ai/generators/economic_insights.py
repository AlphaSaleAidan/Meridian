"""Economic model insights — marginal analysis and seasonal indices."""
from ._insight_helpers import cite, make_insight


def generate(ctx, revenue: dict, products: dict, patterns: dict, bench, models) -> list[dict]:
    insights = []

    hourly = patterns.get("peak_hours", {}).get("hourly_data", [])
    if hourly and models:
        labor_cost = int(bench.get("labor_cost_pct", 30) / 100 * 2500) if bench else 2500
        mr_analysis = models.marginal_revenue_analysis(
            hourly_revenue=hourly,
            labor_cost_per_hour_cents=labor_cost,
        )
        if mr_analysis.get("profitable_hours", 0) > 0:
            best_hours = mr_analysis.get("best_hours", [])
            worst_hours = mr_analysis.get("worst_hours", [])
            if best_hours and worst_hours:
                insights.append(make_insight(
                    ctx=ctx,
                    type="staffing",
                    title="📊 Marginal Revenue Analysis — Staffing ROI by Hour",
                    summary=(
                        f"{mr_analysis['interpretation']}"
                        f"\n\n"
                        f"*Highest-ROI hours* (revenue-to-labor-cost ratio):\n"
                        + "\n".join(
                            f"  • {h['hour']}: {h['revenue_to_cost_ratio']}:1 ratio"
                            for h in best_hours[:3]
                        )
                        + f"\n\n*Lowest-ROI hours:*\n"
                        + "\n".join(
                            f"  • {h['hour']}: {h['revenue_to_cost_ratio']}:1 ratio"
                            for h in worst_hours[:3]
                        )
                        + f"\n\n"
                        f"The standard economic rule: keep adding labor where marginal revenue "
                        f"exceeds marginal cost (MR > MC). For service businesses, the practical "
                        f"threshold is a 3:1 revenue-to-labor-cost ratio "
                        f"{cite('mit_sloan_scheduling')}."
                    ),
                    impact_cents=0,
                    confidence=0.7,
                    details={
                        "marginal_analysis": mr_analysis,
                        "citations": ["mit_sloan_scheduling", "cornell_labor_scheduling"],
                    },
                ))

    daily_data = revenue.get("daily_data", ctx.daily_revenue)
    if daily_data and len(daily_data) >= 14 and models:
        seasonal = models.seasonal_index(daily_data)
        if seasonal.get("volatility_pct", 0) > 20:
            insights.append(make_insight(
                ctx=ctx,
                type="general",
                title=f"📅 Weekly Demand Pattern: {seasonal.get('volatility_pct', 0):.0f}% Volatility — Optimization Possible",
                summary=(
                    f"{seasonal['interpretation']}"
                    f"\n\n"
                    f"*Day-of-week demand indices:*\n"
                    + "\n".join(
                        f"  • {day}: {idx}x average"
                        + (" ← peak" if idx == max(seasonal.get("indices", {}).values()) else "")
                        + (" ← trough" if idx == min(seasonal.get("indices", {}).values()) else "")
                        for day, idx in seasonal.get("indices", {}).items()
                    )
                    + f"\n\n"
                    f"Use these indices for demand forecasting, staff scheduling, and "
                    f"inventory ordering. NRA research shows counter-seasonal promotions "
                    f"recover 30-50% of weak-day revenue gaps {cite('nra_seasonal_trends')}."
                ),
                impact_cents=0,
                confidence=0.75,
                details={
                    "seasonal_indices": seasonal,
                    "citations": ["nra_seasonal_trends", "nra_daypart_analysis"],
                },
            ))

    return insights
