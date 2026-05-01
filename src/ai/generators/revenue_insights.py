"""Revenue insight generation with benchmark comparisons."""
from ._insight_helpers import fmt_cents, cite, make_insight


def generate(ctx, revenue: dict, bench, models) -> list[dict]:
    insights = []

    if revenue.get("error"):
        return insights

    kpis = revenue.get("kpis", {})
    trend = revenue.get("trend", {})
    comparison = revenue.get("comparison", {})

    avg_daily = kpis.get("avg_daily_revenue_cents", 0)
    avg_ticket = kpis.get("avg_ticket_cents", 0)
    wow_growth = trend.get("wow_growth_pct")
    direction = trend.get("direction", "stable")

    bench_context = ""
    if bench:
        daily_comp = bench.compare("avg_daily_revenue_cents", avg_daily)
        ticket_comp = bench.compare("avg_ticket_cents", avg_ticket)
        if daily_comp.get("status") != "no_benchmark":
            bench_context = (
                f" Relative to the {bench.data.label} industry benchmark, "
                f"your daily revenue places you in the {daily_comp.get('percentile_estimate', 'N/A')} "
                f"({daily_comp.get('gap_pct', 0):+.1f}% vs. industry median of "
                f"{fmt_cents(daily_comp.get('benchmark_value', 0))}/day)."
            )

    if direction == "growing" and wow_growth and wow_growth > 5:
        insights.append(make_insight(
            ctx=ctx,
            type="general",
            title="📈 Strong Revenue Momentum — Compounding Growth Detected",
            summary=(
                f"Week-over-week revenue grew {wow_growth:+.1f}%, reflecting sustained "
                f"demand acceleration. Your trailing average of {fmt_cents(avg_daily)}/day "
                f"across {kpis.get('avg_transactions_per_day', 0):.0f} daily transactions "
                f"indicates healthy throughput.{bench_context}"
                f"\n\n"
                f"At this trajectory, annualized revenue projects to "
                f"~{fmt_cents(int(avg_daily * 365))}, assuming no seasonal adjustment. "
                f"To sustain this growth curve, ensure staffing scales proportionally — "
                f"understaffed peak hours cost 8-15% of potential revenue "
                f"{cite('mit_sloan_scheduling')}."
                f"\n\n"
                f"*Recommended actions:*\n"
                f"1. Lock in supplier agreements at current volume to protect margins\n"
                f"2. Evaluate whether current peak-hour staffing can support continued growth\n"
                f"3. Consider modest price increases on top sellers while demand is strong "
                f"— a 1% price lift yields ~11% operating profit improvement {cite('hbr_pricing_power')}"
            ),
            impact_cents=0,
            confidence=0.88,
            details={
                "trend": trend,
                "kpis": kpis,
                "benchmark_comparison": daily_comp if bench else {},
                "citations": ["nra_2025_pricing", "mit_sloan_scheduling", "hbr_pricing_power"],
            },
        ))
    elif direction == "declining" and wow_growth and wow_growth < -5:
        daily_loss = int(abs(wow_growth) / 100 * avg_daily)
        monthly_loss = daily_loss * 30
        insights.append(make_insight(
            ctx=ctx,
            type="general",
            title="📉 Revenue Decline Requires Immediate Attention",
            summary=(
                f"Revenue contracted {wow_growth:+.1f}% week-over-week, translating to "
                f"approximately {fmt_cents(daily_loss)}/day in lost revenue "
                f"(~{fmt_cents(monthly_loss)}/month if sustained).{bench_context}"
                f"\n\n"
                f"Diagnostic framework — evaluate these factors in order:\n"
                f"1. *Traffic decline* — Are transaction counts down? If yes, the issue is "
                f"foot traffic / demand generation\n"
                f"2. *Ticket size decline* — If transactions are stable but revenue is down, "
                f"customers are spending less per visit (mix shift or price sensitivity)\n"
                f"3. *Product mix shift* — Are high-margin items being replaced by lower-margin ones?\n"
                f"4. *External factors* — Seasonal patterns, weather, competitor openings, "
                f"construction, or local events {cite('nra_seasonal_trends')}\n"
                f"\n"
                f"Per JPMorgan Chase research, the median small business holds only 27 days of "
                f"cash reserves {cite('jpmorgan_small_biz')}. Address revenue decline quickly "
                f"to maintain healthy cash flow buffers."
            ),
            impact_cents=monthly_loss,
            confidence=0.75,
            details={
                "trend": trend,
                "daily_loss_cents": daily_loss,
                "citations": ["nra_seasonal_trends", "jpmorgan_small_biz", "sba_cash_flow"],
            },
        ))

    ticket_change = comparison.get("avg_ticket_change_pct", 0)
    if abs(ticket_change) > 10:
        direction_word = "increased" if ticket_change > 0 else "decreased"
        ticket_bench = ""
        if bench:
            t_comp = bench.compare("avg_ticket_cents", avg_ticket)
            if t_comp.get("status") != "no_benchmark":
                ticket_bench = (
                    f" Industry benchmark for {bench.data.label}: "
                    f"{fmt_cents(t_comp.get('benchmark_value', 0))} "
                    f"(you are {t_comp.get('gap_pct', 0):+.1f}% vs. benchmark)."
                )
        insights.append(make_insight(
            ctx=ctx,
            type="pricing",
            title=f"🎫 Average Ticket {direction_word.title()} {abs(ticket_change):.1f}% — {'Opportunity' if ticket_change > 0 else 'Action Needed'}",
            summary=(
                f"Your average transaction value {direction_word} by {abs(ticket_change):.1f}% "
                f"to {fmt_cents(avg_ticket)}.{ticket_bench}"
                f"\n\n"
                + (
                    f"The upward movement signals either successful upselling, price increases "
                    f"absorbing well, or favorable product mix shifts. "
                    f"This is a strong indicator of pricing power — customers are accepting "
                    f"higher spend levels without volume decline. "
                    f"Per McKinsey research, businesses with rising average tickets can sustain "
                    f"further 2-3% increases with minimal demand impact {cite('mckinsey_pricing')}."
                    if ticket_change > 0 else
                    f"Declining ticket size may indicate: customer trade-down behavior, "
                    f"over-reliance on discounts, or a shift toward lower-margin items. "
                    f"Review your product mix and discount policy — excessive discounting "
                    f"trains customers to wait for deals and erodes perceived value "
                    f"{cite('hbr_discount_strategy')}."
                )
            ),
            impact_cents=0,
            confidence=0.8,
            details={
                "comparison": comparison,
                "citations": ["mckinsey_pricing", "hbr_discount_strategy"],
            },
        ))

    tip_rate = kpis.get("tip_rate_pct", 0)
    total_rev = kpis.get("total_revenue_cents", 0)
    total_days = kpis.get("total_days", 30)
    if models and tip_rate > 0 and tip_rate < 15:
        tip_analysis = models.tip_optimization_potential(
            current_tip_rate=tip_rate,
            total_revenue_cents=total_rev,
            days=total_days,
        )
        if tip_analysis.get("status") == "below_optimal":
            insights.append(make_insight(
                ctx=ctx,
                type="general",
                title="💡 Tip Rate Below Industry Optimal — Easy Revenue for Staff",
                summary=(
                    f"{tip_analysis['guidance']}"
                    f"\n\n"
                    f"Higher tips don't just help your staff — they directly reduce turnover. "
                    f"With labor costs averaging {bench.get('labor_cost_pct', 30)}% of revenue "
                    f"in {bench.data.label if bench else 'food service'} "
                    f"{cite('bls_labor_costs')}, "
                    f"reducing turnover through better tip income is one of the highest-ROI "
                    f"operational changes available."
                    f"\n\n"
                    f"*Implementation:* Update your POS tip screen to show preset buttons "
                    f"at 18%, 20%, and 25% (plus custom). Cornell research shows this single "
                    f"change increases tip probability by 27% {cite('cornell_tipping')}."
                ),
                impact_cents=tip_analysis.get("monthly_potential_cents", 0),
                confidence=0.65,
                details={
                    "tip_analysis": tip_analysis,
                    "citations": ["cornell_tipping", "bls_labor_costs", "square_payments_report"],
                },
            ))

    discount_cents = kpis.get("total_discount_cents", 0)
    if models and total_rev > 0 and discount_cents > 0:
        bench_rate = bench.get("healthy_discount_rate_pct", 3.0) if bench else 3.0
        disc_analysis = models.discount_roi_analysis(
            total_revenue_cents=total_rev,
            total_discount_cents=discount_cents,
            total_transactions=kpis.get("total_transactions", 1),
            benchmark_discount_rate=bench_rate,
        )
        if disc_analysis.get("status") in ("elevated", "excessive"):
            insights.append(make_insight(
                ctx=ctx,
                type="pricing",
                title=f"🏷️ Discount Rate at {disc_analysis['actual_rate_pct']}% — Margin Erosion Risk",
                summary=(
                    f"{disc_analysis['guidance']}"
                    f"\n\n"
                    f"Research from Harvard Business Review shows that targeted, time-limited "
                    f"promotions outperform blanket discounts by a 3:1 margin in terms of "
                    f"incremental revenue generated {cite('hbr_discount_strategy')}."
                    f"\n\n"
                    f"*Recommended strategy:*\n"
                    f"1. Audit current discount triggers — identify which are driving new "
                    f"customers vs. subsidizing existing ones\n"
                    f"2. Cap blanket discounts at {bench_rate}% of revenue\n"
                    f"3. Shift budget to targeted offers: loyalty rewards, "
                    f"slow-day promotions, and new customer incentives"
                ),
                impact_cents=disc_analysis.get("excess_cents", 0),
                confidence=0.7,
                details={
                    "discount_analysis": disc_analysis,
                    "citations": ["hbr_discount_strategy", "mckinsey_pricing"],
                },
            ))

    return insights
