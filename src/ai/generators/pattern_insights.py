"""Pattern insight generation with operational benchmarks."""
from ._insight_helpers import fmt_cents, cite, make_insight


def generate(ctx, patterns: dict, bench, models) -> list[dict]:
    insights = []

    peak_data = patterns.get("peak_hours", {})
    golden = peak_data.get("golden_window", {})
    if golden.get("label"):
        rev_share = golden.get("total_revenue_share_pct", 0)
        bench_share = bench.get("peak_hour_revenue_share_pct", 40) if bench else 40

        insights.append(make_insight(
            ctx=ctx,
            type="staffing",
            title=f"🔥 Golden Window: {golden['label']} — {rev_share:.0f}% of Revenue in 3 Hours",
            summary=(
                f"Your most profitable operating window is {golden['label']}, concentrating "
                f"{rev_share:.0f}% of daily revenue into roughly 3 hours. "
                f"{'This exceeds' if rev_share > bench_share else 'This is near'} "
                f"the industry benchmark of {bench_share}% for {bench.data.label if bench else 'this vertical'}."
                f"\n\n"
                f"*Staffing economics:*\n"
                f"MIT Sloan research shows each understaffed peak hour costs 8-15% of "
                f"that hour's potential revenue through lost sales, longer wait times, "
                f"and reduced upselling capacity {cite('mit_sloan_scheduling')}. Cornell's "
                f"demand-driven scheduling research found that aligning staff to 15-minute "
                f"demand blocks (vs. shift-based) improves revenue-per-labor-hour by 18% "
                f"{cite('cornell_labor_scheduling')}."
                f"\n\n"
                f"*Action items:*\n"
                f"1. Ensure maximum staffing during {golden['label']} — every position filled\n"
                f"2. Pre-prep high-volume items 30 min before peak to maximize throughput\n"
                f"3. Schedule breaks and training during off-peak hours only\n"
                f"4. Track revenue-per-labor-hour weekly to optimize scheduling"
            ),
            impact_cents=0,
            confidence=0.85,
            details={
                "golden_window": golden,
                "benchmark_share_pct": bench_share,
                "citations": ["mit_sloan_scheduling", "cornell_labor_scheduling", "bls_labor_costs"],
            },
        ))

    dow = patterns.get("day_of_week", {})
    best_day = dow.get("best_day")
    worst_day = dow.get("worst_day")
    if best_day and worst_day and best_day != worst_day:
        best_avg = dow.get("best_day_avg_cents", 0)
        worst_avg = dow.get("worst_day_avg_cents", 0)
        gap = best_avg - worst_avg

        if gap > 0 and worst_avg > 0:
            gap_pct = round(gap / worst_avg * 100, 0)
            recovery_potential = int(gap * 4 * 0.25)

            if gap_pct > 25:
                insights.append(make_insight(
                    ctx=ctx,
                    type="staffing",
                    title=f"📅 {worst_day} Revenue Gap: {gap_pct:.0f}% Below {best_day} — {fmt_cents(recovery_potential)}/Mo Recovery Potential",
                    summary=(
                        f"{best_day} averages {fmt_cents(best_avg)} while "
                        f"{worst_day} generates only {fmt_cents(worst_avg)} — "
                        f"a {gap_pct:.0f}% revenue gap."
                        f"\n\n"
                        f"NRA daypart research shows businesses capturing 3+ strong dayparts "
                        f"achieve 40% higher revenue per square foot {cite('nra_daypart_analysis')}. "
                        f"Counter-seasonal promotions can recover 30-50% of the weakest day's "
                        f"revenue gap {cite('nra_seasonal_trends')}."
                        f"\n\n"
                        f"*{worst_day} recovery playbook:*\n"
                        f"1. Launch a {worst_day}-specific promotion (e.g., \"Happy {worst_day}\" "
                        f"with a featured item at 15% off)\n"
                        f"2. Test a loyalty multiplier (2x points on {worst_day}s)\n"
                        f"3. Shift marketing spend to drive traffic on slow days\n"
                        f"4. *Target:* Close 25% of the gap = {fmt_cents(recovery_potential)}/month"
                    ),
                    impact_cents=recovery_potential,
                    confidence=0.6,
                    details={
                        "day_analysis": dow,
                        "gap_pct": gap_pct,
                        "citations": ["nra_daypart_analysis", "nra_seasonal_trends"],
                    },
                ))

    payment = patterns.get("payment_patterns", {})
    cash_pct = payment.get("cash_pct", 0)
    if cash_pct > 40:
        total_daily_rev = patterns.get("total_daily_revenue_cents", 0) or 150000
        cash_rev = int(total_daily_rev * cash_pct / 100)
        potential_uplift = int(cash_rev * 0.15 * 0.3 * 30)

        insights.append(make_insight(
            ctx=ctx,
            type="general",
            title=f"💳 {cash_pct:.0f}% Cash Transactions — Digital Payment Shift Can Lift Revenue",
            summary=(
                f"Federal Reserve research on consumer payment choice shows card and "
                f"mobile payment users spend 12-18% more per transaction than cash users, "
                f"due to reduced 'pain of paying' {cite('fed_payments_study')}. "
                f"Square's seller insights report confirms card average tickets are 18% higher "
                f"and tap-to-pay businesses see 12% higher throughput {cite('square_payments_report')}."
                f"\n\n"
                f"With {cash_pct:.0f}% of your transactions in cash, shifting even 30% of "
                f"cash customers to card/mobile could add ~{fmt_cents(potential_uplift)}/month "
                f"from higher average tickets alone, plus reduced cash handling costs."
                f"\n\n"
                f"*Strategies:*\n"
                f"1. Prominently display card/mobile payment options at point of sale\n"
                f"2. Offer small incentive for digital payments (loyalty points, faster checkout)\n"
                f"3. Ensure tap-to-pay is enabled and working"
            ),
            impact_cents=potential_uplift,
            confidence=0.55,
            details={
                "payment_mix": payment,
                "citations": ["fed_payments_study", "square_payments_report"],
            },
        ))

    return insights
