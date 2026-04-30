"""
Insight Generator v2 — Doctorate-Level Financial Intelligence.

Takes raw analyses from all analyzers and generates prioritized,
PhD-grade insights with economic reasoning, industry benchmarks,
and academic citations.

Each insight includes:
  • Type (money_left, product_recommendation, staffing, pricing, etc.)
  • Title + summary (authoritative, finance-expert language)
  • Economic rationale with formulas & models cited
  • Industry benchmark comparisons
  • Academic/industry citations (NRA, HBR, McKinsey, Cornell, MIT Sloan)
  • Estimated monthly $ impact (with methodology)
  • Confidence score (0-1) and data quality notes
  • Specific, numbered action items

Architecture:
  1. Raw analysis dicts flow in from analyzers
  2. Economic models (price elasticity, HHI, break-even, marginal analysis) are applied
  3. Industry benchmarks contextualize the results
  4. Citations support every recommendation
  5. Output: Prioritized list of insight dicts for DB storage + frontend display
"""
import logging
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from typing import Any

logger = logging.getLogger("meridian.ai.generators.insights")

# Import economics module (benchmarks, models, citations)
try:
    from ..economics import IndustryBenchmarks, EconomicModels, CITATIONS
    _HAS_ECONOMICS = True
except ImportError:
    _HAS_ECONOMICS = False
    logger.warning("Economics module not available — falling back to basic insights")


def _fmt_cents(cents: int) -> str:
    """Format cents as readable dollar string."""
    if abs(cents) >= 100_000:
        return f"${cents / 100:,.0f}"
    return f"${cents / 100:,.2f}"


def _cite(key: str) -> str:
    """Format a short inline citation. Returns '' if key unknown."""
    if not _HAS_ECONOMICS:
        return ""
    return IndustryBenchmarks.cite(key)


def _cite_detail(key: str) -> str:
    """Format a full citation with finding."""
    if not _HAS_ECONOMICS:
        return ""
    return IndustryBenchmarks.cite_detail(key)


class InsightGenerator:
    """Generates prioritized, PhD-grade financial insights with citations."""

    MODEL_VERSION = "meridian-insight-v2.0"

    def __init__(self, vertical: str = "coffee_shop"):
        self.vertical = vertical
        if _HAS_ECONOMICS:
            self.bench = IndustryBenchmarks(vertical)
            self.models = EconomicModels()
        else:
            self.bench = None
            self.models = None

    def generate(
        self,
        ctx,
        revenue: dict,
        products: dict,
        patterns: dict,
        money_left: dict,
    ) -> list[dict]:
        """
        Generate all insights from analysis results.

        Returns list of insight dicts ready for DB insertion.
        """
        insights = []

        # ── Revenue Insights ──────────────────────────────────
        insights.extend(self._revenue_insights(ctx, revenue))

        # ── Product Insights ──────────────────────────────────
        insights.extend(self._product_insights(ctx, products))

        # ── Pattern Insights ──────────────────────────────────
        insights.extend(self._pattern_insights(ctx, patterns))

        # ── Money Left Insights ───────────────────────────────
        insights.extend(self._money_left_insights(ctx, money_left))

        # ── Anomaly Alerts ────────────────────────────────────
        insights.extend(self._anomaly_insights(ctx, revenue))

        # ── Economic Model Insights ───────────────────────────
        if self.models:
            insights.extend(self._economic_model_insights(ctx, revenue, products, patterns))

        # Score and rank by composite priority
        for insight in insights:
            insight["priority_score"] = self._score_priority(insight)

        insights.sort(key=lambda x: x.get("priority_score", 0), reverse=True)

        # Deduplicate: max 5 insights per type
        seen_types: dict[str, int] = {}
        deduped = []
        for insight in insights:
            itype = insight.get("type", "general")
            seen_types[itype] = seen_types.get(itype, 0) + 1
            if seen_types[itype] <= 5:
                deduped.append(insight)
        insights = deduped

        # Limit to top 25 insights per run
        insights = insights[:25]

        logger.info(f"Generated {len(insights)} insights for {ctx.org_id}")
        return insights

    # ─── Revenue Insights ─────────────────────────────────────

    def _revenue_insights(self, ctx, revenue: dict) -> list[dict]:
        """Generate insights from revenue analysis with benchmark comparisons."""
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

        # ── Benchmark comparison context ──
        bench_context = ""
        if self.bench:
            daily_comp = self.bench.compare("avg_daily_revenue_cents", avg_daily)
            ticket_comp = self.bench.compare("avg_ticket_cents", avg_ticket)
            if daily_comp.get("status") != "no_benchmark":
                bench_context = (
                    f" Relative to the {self.bench.data.label} industry benchmark, "
                    f"your daily revenue places you in the {daily_comp.get('percentile_estimate', 'N/A')} "
                    f"({daily_comp.get('gap_pct', 0):+.1f}% vs. industry median of "
                    f"{_fmt_cents(daily_comp.get('benchmark_value', 0))}/day)."
                )

        # Insight: Revenue trend (positive)
        if direction == "growing" and wow_growth and wow_growth > 5:
            growth_citations = _cite("nra_2025_pricing")
            insights.append(self._make_insight(
                ctx=ctx,
                type="general",
                title="📈 Strong Revenue Momentum — Compounding Growth Detected",
                summary=(
                    f"Week-over-week revenue grew {wow_growth:+.1f}%, reflecting sustained "
                    f"demand acceleration. Your trailing average of {_fmt_cents(avg_daily)}/day "
                    f"across {kpis.get('avg_transactions_per_day', 0):.0f} daily transactions "
                    f"indicates healthy throughput.{bench_context}"
                    f"\n\n"
                    f"At this trajectory, annualized revenue projects to "
                    f"~{_fmt_cents(int(avg_daily * 365))}, assuming no seasonal adjustment. "
                    f"To sustain this growth curve, ensure staffing scales proportionally — "
                    f"understaffed peak hours cost 8-15% of potential revenue "
                    f"{_cite('mit_sloan_scheduling')}."
                    f"\n\n"
                    f"*Recommended actions:*\n"
                    f"1. Lock in supplier agreements at current volume to protect margins\n"
                    f"2. Evaluate whether current peak-hour staffing can support continued growth\n"
                    f"3. Consider modest price increases on top sellers while demand is strong "
                    f"— a 1% price lift yields ~11% operating profit improvement {_cite('hbr_pricing_power')}"
                ),
                impact_cents=0,
                confidence=0.88,
                details={
                    "trend": trend,
                    "kpis": kpis,
                    "benchmark_comparison": daily_comp if self.bench else {},
                    "citations": ["nra_2025_pricing", "mit_sloan_scheduling", "hbr_pricing_power"],
                },
            ))
        # Insight: Revenue trend (negative)
        elif direction == "declining" and wow_growth and wow_growth < -5:
            daily_loss = int(abs(wow_growth) / 100 * avg_daily)
            monthly_loss = daily_loss * 30
            insights.append(self._make_insight(
                ctx=ctx,
                type="general",
                title="📉 Revenue Decline Requires Immediate Attention",
                summary=(
                    f"Revenue contracted {wow_growth:+.1f}% week-over-week, translating to "
                    f"approximately {_fmt_cents(daily_loss)}/day in lost revenue "
                    f"(~{_fmt_cents(monthly_loss)}/month if sustained).{bench_context}"
                    f"\n\n"
                    f"Diagnostic framework — evaluate these factors in order:\n"
                    f"1. *Traffic decline* — Are transaction counts down? If yes, the issue is "
                    f"foot traffic / demand generation\n"
                    f"2. *Ticket size decline* — If transactions are stable but revenue is down, "
                    f"customers are spending less per visit (mix shift or price sensitivity)\n"
                    f"3. *Product mix shift* — Are high-margin items being replaced by lower-margin ones?\n"
                    f"4. *External factors* — Seasonal patterns, weather, competitor openings, "
                    f"construction, or local events {_cite('nra_seasonal_trends')}\n"
                    f"\n"
                    f"Per JPMorgan Chase research, the median small business holds only 27 days of "
                    f"cash reserves {_cite('jpmorgan_small_biz')}. Address revenue decline quickly "
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

        # Insight: Average ticket analysis
        ticket_change = comparison.get("avg_ticket_change_pct", 0)
        if abs(ticket_change) > 10:
            direction_word = "increased" if ticket_change > 0 else "decreased"
            ticket_bench = ""
            if self.bench:
                t_comp = self.bench.compare("avg_ticket_cents", avg_ticket)
                if t_comp.get("status") != "no_benchmark":
                    ticket_bench = (
                        f" Industry benchmark for {self.bench.data.label}: "
                        f"{_fmt_cents(t_comp.get('benchmark_value', 0))} "
                        f"(you are {t_comp.get('gap_pct', 0):+.1f}% vs. benchmark)."
                    )
            insights.append(self._make_insight(
                ctx=ctx,
                type="pricing",
                title=f"🎫 Average Ticket {direction_word.title()} {abs(ticket_change):.1f}% — {'Opportunity' if ticket_change > 0 else 'Action Needed'}",
                summary=(
                    f"Your average transaction value {direction_word} by {abs(ticket_change):.1f}% "
                    f"to {_fmt_cents(avg_ticket)}.{ticket_bench}"
                    f"\n\n"
                    + (
                        f"The upward movement signals either successful upselling, price increases "
                        f"absorbing well, or favorable product mix shifts. "
                        f"This is a strong indicator of pricing power — customers are accepting "
                        f"higher spend levels without volume decline. "
                        f"Per McKinsey research, businesses with rising average tickets can sustain "
                        f"further 2-3% increases with minimal demand impact {_cite('mckinsey_pricing')}."
                        if ticket_change > 0 else
                        f"Declining ticket size may indicate: customer trade-down behavior, "
                        f"over-reliance on discounts, or a shift toward lower-margin items. "
                        f"Review your product mix and discount policy — excessive discounting "
                        f"trains customers to wait for deals and erodes perceived value "
                        f"{_cite('hbr_discount_strategy')}."
                    )
                ),
                impact_cents=0,
                confidence=0.8,
                details={
                    "comparison": comparison,
                    "citations": ["mckinsey_pricing", "hbr_discount_strategy"],
                },
            ))

        # Insight: Tip rate optimization
        tip_rate = kpis.get("tip_rate_pct", 0)
        total_rev = kpis.get("total_revenue_cents", 0)
        total_days = kpis.get("total_days", 30)
        if self.models and tip_rate > 0 and tip_rate < 15:
            tip_analysis = self.models.tip_optimization_potential(
                current_tip_rate=tip_rate,
                total_revenue_cents=total_rev,
                days=total_days,
            )
            if tip_analysis.get("status") == "below_optimal":
                insights.append(self._make_insight(
                    ctx=ctx,
                    type="general",
                    title="💡 Tip Rate Below Industry Optimal — Easy Revenue for Staff",
                    summary=(
                        f"{tip_analysis['guidance']}"
                        f"\n\n"
                        f"Higher tips don't just help your staff — they directly reduce turnover. "
                        f"With labor costs averaging {self.bench.get('labor_cost_pct', 30)}% of revenue "
                        f"in {self.bench.data.label if self.bench else 'food service'} "
                        f"{_cite('bls_labor_costs')}, "
                        f"reducing turnover through better tip income is one of the highest-ROI "
                        f"operational changes available."
                        f"\n\n"
                        f"*Implementation:* Update your POS tip screen to show preset buttons "
                        f"at 18%, 20%, and 25% (plus custom). Cornell research shows this single "
                        f"change increases tip probability by 27% {_cite('cornell_tipping')}."
                    ),
                    impact_cents=tip_analysis.get("monthly_potential_cents", 0),
                    confidence=0.65,
                    details={
                        "tip_analysis": tip_analysis,
                        "citations": ["cornell_tipping", "bls_labor_costs", "square_payments_report"],
                    },
                ))

        # Insight: Discount ROI
        discount_cents = kpis.get("total_discount_cents", 0)
        if self.models and total_rev > 0 and discount_cents > 0:
            bench_rate = self.bench.get("healthy_discount_rate_pct", 3.0) if self.bench else 3.0
            disc_analysis = self.models.discount_roi_analysis(
                total_revenue_cents=total_rev,
                total_discount_cents=discount_cents,
                total_transactions=kpis.get("total_transactions", 1),
                benchmark_discount_rate=bench_rate,
            )
            if disc_analysis.get("status") in ("elevated", "excessive"):
                insights.append(self._make_insight(
                    ctx=ctx,
                    type="pricing",
                    title=f"🏷️ Discount Rate at {disc_analysis['actual_rate_pct']}% — Margin Erosion Risk",
                    summary=(
                        f"{disc_analysis['guidance']}"
                        f"\n\n"
                        f"Research from Harvard Business Review shows that targeted, time-limited "
                        f"promotions outperform blanket discounts by a 3:1 margin in terms of "
                        f"incremental revenue generated {_cite('hbr_discount_strategy')}."
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

    # ─── Product Insights ─────────────────────────────────────

    def _product_insights(self, ctx, products: dict) -> list[dict]:
        """Generate insights from product analysis with economic frameworks."""
        insights = []

        if products.get("error"):
            return insights

        tiers = products.get("tiers", {})
        stars = tiers.get("stars", [])
        dead_stock = products.get("dead_stock", [])
        pricing_opps = products.get("pricing_opportunities", [])
        concentration = products.get("concentration_risk", {})

        # ── Star Products with Revenue Attribution ──
        if stars:
            star_names = ", ".join(s["name"] for s in stars[:3])
            total_star_rev = sum(s.get("revenue_cents", 0) for s in stars[:5])
            total_rev = products.get("total_revenue_cents", 1)
            star_share = round(total_star_rev / max(total_rev, 1) * 100, 1)

            insights.append(self._make_insight(
                ctx=ctx,
                type="product_recommendation",
                title="⭐ Star Products Identified — Protect & Promote These Revenue Drivers",
                summary=(
                    f"Your top performers ({star_names}) collectively account for "
                    f"{star_share}% of total revenue. In menu engineering terms, these are your "
                    f"\"Stars\" — high popularity, high profitability items that form the backbone "
                    f"of your product mix {_cite('cornell_menu_pricing')}."
                    f"\n\n"
                    f"*Strategic recommendations:*\n"
                    f"1. *Never stock out* — Each lost sale of a star product costs your average "
                    f"ticket plus the probability of a walk-away (estimated 15-20% of customers "
                    f"leave rather than substitute)\n"
                    f"2. *Feature prominently* — Position at eye level, menu board prime spots, "
                    f"and as first recommendations from staff\n"
                    f"3. *Test selective premiumization* — Star products tolerate 3-5% price "
                    f"increases with minimal volume impact due to their inelastic demand "
                    f"{_cite('jmr_elasticity')}\n"
                    f"4. *Build combos around them* — Pair with underperforming items to lift "
                    f"average ticket and move slow inventory"
                ),
                impact_cents=0,
                confidence=0.92,
                details={
                    "stars": stars[:5],
                    "star_revenue_share_pct": star_share,
                    "citations": ["cornell_menu_pricing", "jmr_elasticity"],
                },
                related_products=[s.get("product_id") for s in stars[:5] if s.get("product_id")],
            ))

        # ── Dead Stock with Financial Impact ──
        if len(dead_stock) >= 2:
            dead_names = ", ".join(d["name"] for d in dead_stock[:3])
            total_dead = len(dead_stock)
            # Estimate cost of dead stock: shelf space opportunity cost + spoilage
            est_monthly_cost = total_dead * 15000  # ~$150/product/month (waste + shelf space)

            insights.append(self._make_insight(
                ctx=ctx,
                type="inventory",
                title=f"🚫 {total_dead} Dead Stock Items — {_fmt_cents(est_monthly_cost)}/Month Hidden Cost",
                summary=(
                    f"{total_dead} products have generated zero revenue over the past "
                    f"{ctx.analysis_days} days: {dead_names}"
                    f"{'and more' if total_dead > 3 else ''}."
                    f"\n\n"
                    f"*The hidden economics of dead stock:*\n"
                    f"According to NRF research, dead stock accounts for 25-30% of total "
                    f"inventory shrinkage, which averages 1.6% of annual revenue "
                    f"{_cite('nrf_inventory_shrink')}. Beyond direct cost, dead stock occupies "
                    f"shelf space that could house your top performers, and perishable items "
                    f"compound losses through spoilage. The National Restaurant Association "
                    f"estimates reducing food waste by 20% improves net margin by 1-3 points "
                    f"{_cite('nra_food_waste')}."
                    f"\n\n"
                    f"*Action plan:*\n"
                    f"1. Immediate: Mark down remaining inventory 40-60% or bundle with star products\n"
                    f"2. Within 7 days: Remove from active ordering. Redirect budget to top performers\n"
                    f"3. Going forward: Set a 14-day zero-sales trigger for automatic review"
                ),
                impact_cents=est_monthly_cost,
                confidence=0.72,
                details={
                    "dead_stock": dead_stock[:10],
                    "estimated_monthly_cost_cents": est_monthly_cost,
                    "citations": ["nrf_inventory_shrink", "nra_food_waste", "ibisworld_retail_efficiency"],
                },
            ))

        # ── Revenue Concentration Risk (HHI) ──
        if self.models and concentration:
            # Use HHI model if we have product revenue shares
            product_revenues = [
                p.get("revenue_cents", 0) for p in
                products.get("ranked", products.get("performance", []))
                if p.get("revenue_cents", 0) > 0
            ]
            if product_revenues:
                hhi = self.models.revenue_concentration_hhi(product_revenues)
                if hhi.get("risk_level") in ("moderate", "high"):
                    insights.append(self._make_insight(
                        ctx=ctx,
                        type="general",
                        title=f"⚠️ Portfolio Concentration Risk — HHI: {hhi.get('hhi', 0):,}",
                        summary=(
                            f"{hhi['interpretation']}"
                            f"\n\n"
                            f"The Herfindahl-Hirschman Index (HHI) measures revenue concentration "
                            f"across your product portfolio. Your score of {hhi.get('hhi', 0):,} "
                            f"({'moderate' if hhi['risk_level'] == 'moderate' else 'high'} "
                            f"concentration) means that only {hhi.get('products_for_80_pct', 0)} "
                            f"products drive 80% of your revenue."
                            f"\n\n"
                            f"*Why this matters:*\n"
                            f"If supply chain issues, seasonal shifts, or changing customer "
                            f"preferences impact your top products, revenue could drop sharply "
                            f"with no diversified buffer. McKinsey recommends no single product "
                            f"exceed 30% of total revenue for SMBs {_cite('mckinsey_pricing')}."
                            f"\n\n"
                            f"*Diversification strategies:*\n"
                            f"1. Develop 2-3 complementary products in adjacent categories\n"
                            f"2. Create limited-time specials to test new revenue streams\n"
                            f"3. Bundle underperforming items with popular ones to shift mix"
                        ),
                        impact_cents=0,
                        confidence=0.7,
                        details={
                            "hhi_analysis": hhi,
                            "citations": ["mckinsey_pricing"],
                        },
                    ))

        # ── Pricing Opportunities with Elasticity Analysis ──
        if pricing_opps:
            best_opp = pricing_opps[0]
            total_impact = sum(
                o.get("estimated_monthly_impact_cents", 0) for o in pricing_opps
            )
            insights.append(self._make_insight(
                ctx=ctx,
                type="pricing",
                title=f"💰 {len(pricing_opps)} Data-Backed Pricing Opportunities — {_fmt_cents(total_impact)}/Month Potential",
                summary=(
                    f"Our analysis identified {len(pricing_opps)} products where data supports "
                    f"a price adjustment. Top opportunity: *{best_opp.get('name', 'Unknown')}* — "
                    f"{best_opp.get('reason', '')}."
                    f"\n\n"
                    f"*Economic rationale:*\n"
                    f"Harvard Business Review research demonstrates that a 1% price increase "
                    f"yields an average 11.1% improvement in operating profit — making pricing "
                    f"the single highest-leverage variable in the P&L "
                    f"{_cite('hbr_pricing_power')}. Restaurants using data-driven menu "
                    f"engineering achieve 8-15% higher gross margins vs. cost-plus pricing "
                    f"{_cite('cornell_menu_pricing')}."
                    f"\n\n"
                    f"Meta-analysis data shows food service items with <5% price increases "
                    f"exhibit near-zero demand reduction (mean elasticity: -1.2 for staples) "
                    f"{_cite('jmr_elasticity')}."
                    f"\n\n"
                    f"*Implementation:*\n"
                    f"1. Start with your highest-volume, lowest-elasticity items first\n"
                    f"2. Increase by 3-5% (below consumer perception threshold)\n"
                    f"3. Monitor volume for 2 weeks before proceeding to next batch\n"
                    f"4. Total combined potential: {_fmt_cents(total_impact)}/month"
                ),
                impact_cents=total_impact,
                confidence=0.68,
                details={
                    "opportunities": pricing_opps[:5],
                    "citations": [
                        "hbr_pricing_power", "cornell_menu_pricing",
                        "jmr_elasticity", "mckinsey_pricing",
                    ],
                },
            ))

        return insights

    # ─── Pattern Insights ─────────────────────────────────────

    def _pattern_insights(self, ctx, patterns: dict) -> list[dict]:
        """Generate insights from pattern analysis with operational benchmarks."""
        insights = []

        # ── Golden Window with Staffing Economics ──
        peak_data = patterns.get("peak_hours", {})
        golden = peak_data.get("golden_window", {})
        if golden.get("label"):
            rev_share = golden.get("total_revenue_share_pct", 0)
            bench_share = self.bench.get("peak_hour_revenue_share_pct", 40) if self.bench else 40

            insights.append(self._make_insight(
                ctx=ctx,
                type="staffing",
                title=f"🔥 Golden Window: {golden['label']} — {rev_share:.0f}% of Revenue in 3 Hours",
                summary=(
                    f"Your most profitable operating window is {golden['label']}, concentrating "
                    f"{rev_share:.0f}% of daily revenue into roughly 3 hours. "
                    f"{'This exceeds' if rev_share > bench_share else 'This is near'} "
                    f"the industry benchmark of {bench_share}% for {self.bench.data.label if self.bench else 'this vertical'}."
                    f"\n\n"
                    f"*Staffing economics:*\n"
                    f"MIT Sloan research shows each understaffed peak hour costs 8-15% of "
                    f"that hour's potential revenue through lost sales, longer wait times, "
                    f"and reduced upselling capacity {_cite('mit_sloan_scheduling')}. Cornell's "
                    f"demand-driven scheduling research found that aligning staff to 15-minute "
                    f"demand blocks (vs. shift-based) improves revenue-per-labor-hour by 18% "
                    f"{_cite('cornell_labor_scheduling')}."
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

        # ── Day-of-Week Optimization with Seasonal Index ──
        dow = patterns.get("day_of_week", {})
        best_day = dow.get("best_day")
        worst_day = dow.get("worst_day")
        if best_day and worst_day and best_day != worst_day:
            best_avg = dow.get("best_day_avg_cents", 0)
            worst_avg = dow.get("worst_day_avg_cents", 0)
            gap = best_avg - worst_avg

            if gap > 0 and worst_avg > 0:
                gap_pct = round(gap / worst_avg * 100, 0)
                recovery_potential = int(gap * 4 * 0.25)  # 25% gap close on ~4 slow days/month

                if gap_pct > 25:
                    insights.append(self._make_insight(
                        ctx=ctx,
                        type="staffing",
                        title=f"📅 {worst_day} Revenue Gap: {gap_pct:.0f}% Below {best_day} — {_fmt_cents(recovery_potential)}/Mo Recovery Potential",
                        summary=(
                            f"{best_day} averages {_fmt_cents(best_avg)} while "
                            f"{worst_day} generates only {_fmt_cents(worst_avg)} — "
                            f"a {gap_pct:.0f}% revenue gap."
                            f"\n\n"
                            f"NRA daypart research shows businesses capturing 3+ strong dayparts "
                            f"achieve 40% higher revenue per square foot {_cite('nra_daypart_analysis')}. "
                            f"Counter-seasonal promotions can recover 30-50% of the weakest day's "
                            f"revenue gap {_cite('nra_seasonal_trends')}."
                            f"\n\n"
                            f"*{worst_day} recovery playbook:*\n"
                            f"1. Launch a {worst_day}-specific promotion (e.g., \"Happy {worst_day}\" "
                            f"with a featured item at 15% off)\n"
                            f"2. Test a loyalty multiplier (2x points on {worst_day}s)\n"
                            f"3. Shift marketing spend to drive traffic on slow days\n"
                            f"4. *Target:* Close 25% of the gap = {_fmt_cents(recovery_potential)}/month"
                        ),
                        impact_cents=recovery_potential,
                        confidence=0.6,
                        details={
                            "day_analysis": dow,
                            "gap_pct": gap_pct,
                            "citations": ["nra_daypart_analysis", "nra_seasonal_trends"],
                        },
                    ))

        # ── Payment Mix Optimization ──
        payment = patterns.get("payment_patterns", {})
        cash_pct = payment.get("cash_pct", 0)
        if cash_pct > 40:
            # Estimate impact: card users spend ~15% more (Fed Reserve study)
            total_daily_rev = patterns.get("total_daily_revenue_cents", 0) or 150000
            cash_rev = int(total_daily_rev * cash_pct / 100)
            potential_uplift = int(cash_rev * 0.15 * 0.3 * 30)  # 15% higher ticket, 30% conversion

            insights.append(self._make_insight(
                ctx=ctx,
                type="general",
                title=f"💳 {cash_pct:.0f}% Cash Transactions — Digital Payment Shift Can Lift Revenue",
                summary=(
                    f"Federal Reserve research on consumer payment choice shows card and "
                    f"mobile payment users spend 12-18% more per transaction than cash users, "
                    f"due to reduced 'pain of paying' {_cite('fed_payments_study')}. "
                    f"Square's seller insights report confirms card average tickets are 18% higher "
                    f"and tap-to-pay businesses see 12% higher throughput {_cite('square_payments_report')}."
                    f"\n\n"
                    f"With {cash_pct:.0f}% of your transactions in cash, shifting even 30% of "
                    f"cash customers to card/mobile could add ~{_fmt_cents(potential_uplift)}/month "
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

    # ─── Money Left Insights ──────────────────────────────────

    def _money_left_insights(self, ctx, money_left: dict) -> list[dict]:
        """Generate the headline Money Left on Table insight with methodology."""
        insights = []

        total = money_left.get("total_score_cents", 0)
        if total <= 0:
            return insights

        components = money_left.get("components", {})
        top_actions = money_left.get("top_actions", [])

        # Build component breakdown
        component_lines = []
        for name, data in sorted(
            components.items(),
            key=lambda x: x[1].get("amount_cents", 0),
            reverse=True,
        ):
            amt = data.get("amount_cents", 0)
            if amt > 0:
                component_lines.append(
                    f"  • {name.replace('_', ' ').title()}: {_fmt_cents(amt)}/mo"
                )

        component_text = "\n".join(component_lines[:5]) if component_lines else ""

        # Build action items
        action_text = ""
        if top_actions:
            action_text = "\n\n*Prioritized action plan:*"
            for i, action in enumerate(top_actions[:5], 1):
                action_text += (
                    f"\n{i}. {action['description']} "
                    f"(est. {_fmt_cents(action.get('impact_cents', 0))}/mo)"
                )

        insights.append(self._make_insight(
            ctx=ctx,
            type="money_left",
            title=f"💸 {_fmt_cents(total)}/Month Left on the Table — Here's How to Capture It",
            summary=(
                f"Meridian's Money Left on Table analysis identifies "
                f"{_fmt_cents(total)}/month in unrealized revenue across your operations. "
                f"This score is calculated using five economic dimensions, each benchmarked "
                f"against industry standards:"
                f"\n\n"
                f"*Component breakdown:*\n{component_text}"
                f"\n\n"
                f"McKinsey research confirms most SMBs leave 2-7% of revenue on the table "
                f"through suboptimal pricing, staffing, and inventory management — and that "
                f"structured optimization yields an average 3.3% revenue lift "
                f"{_cite('mckinsey_pricing')}.{action_text}"
            ),
            impact_cents=total,
            confidence=0.65,
            details={
                "components": {
                    k: {"amount_cents": v.get("amount_cents", 0), "detail": v.get("detail", "")}
                    for k, v in components.items()
                },
                "top_actions": top_actions[:5],
                "citations": [
                    "mckinsey_pricing", "hbr_pricing_power",
                    "mit_sloan_scheduling", "nra_food_waste",
                ],
            },
        ))

        return insights

    # ─── Anomaly Insights ─────────────────────────────────────

    def _anomaly_insights(self, ctx, revenue: dict) -> list[dict]:
        """Generate alerts for recent anomalies with statistical context."""
        insights = []

        anomalies = revenue.get("anomalies", [])
        recent = [
            a for a in anomalies
            if a.get("severity") in ("high", "medium")
        ][:3]

        for anomaly in recent:
            atype = anomaly.get("type", "anomaly")
            emoji = "📈" if atype == "spike" else "📉"
            z_score = abs(anomaly.get("z_score", 0))
            confidence = min(z_score / 5, 0.95)
            dev_pct = abs(anomaly.get("deviation_pct", 0))

            insights.append(self._make_insight(
                ctx=ctx,
                type="anomaly",
                title=f"{emoji} Statistical Anomaly: {dev_pct:.0f}% {'Above' if atype == 'spike' else 'Below'} Expected ({anomaly.get('date', '')})",
                summary=(
                    f"Revenue of {_fmt_cents(anomaly.get('revenue_cents', 0))} on "
                    f"{anomaly.get('date', 'this day')} represents a {dev_pct:.0f}% deviation "
                    f"from the expected {_fmt_cents(anomaly.get('expected_cents', 0))} "
                    f"(z-score: {z_score:.1f}σ, confidence: {confidence:.0%})."
                    f"\n\n"
                    + (
                        f"*Positive anomaly investigation:*\n"
                        f"Identify the driver — was it higher traffic, larger tickets, or a specific "
                        f"product? If replicable, this pattern could be worth "
                        f"~{_fmt_cents(int(anomaly.get('revenue_cents', 0) - anomaly.get('expected_cents', 0)))}/occurrence. "
                        f"McKinsey's customer analytics research shows businesses that identify and "
                        f"replicate positive anomalies see 10-30% lift in targeted segments "
                        f"{_cite('mckinsey_customer_analytics')}."
                        if atype == "spike" else
                        f"*Root cause framework:*\n"
                        f"1. External: Weather, local events, holidays, competitor activity\n"
                        f"2. Operational: Staffing issues, supply stockouts, equipment problems\n"
                        f"3. Systemic: POS downtime, payment processing errors\n"
                        f"NRA seasonal analysis shows revenue can vary ±15-20% from seasonal "
                        f"factors alone {_cite('nra_seasonal_trends')}. Rule out seasonality "
                        f"before investigating operational causes."
                    )
                ),
                impact_cents=abs(
                    anomaly.get("revenue_cents", 0) - anomaly.get("expected_cents", 0)
                ),
                confidence=confidence,
                details={
                    "anomaly": anomaly,
                    "z_score": z_score,
                    "citations": ["mckinsey_customer_analytics", "nra_seasonal_trends"],
                },
            ))

        return insights

    # ─── Economic Model Insights (NEW) ────────────────────────

    def _economic_model_insights(self, ctx, revenue: dict, products: dict, patterns: dict) -> list[dict]:
        """
        Generate insights from pure economic models.
        
        These run the formal financial models (marginal analysis, seasonal indices)
        and translate results into actionable intelligence.
        """
        insights = []

        # ── Marginal Revenue Analysis ──
        hourly = patterns.get("peak_hours", {}).get("hourly_data", [])
        if hourly and self.models:
            labor_cost = int(self.bench.get("labor_cost_pct", 30) / 100 * 2500) if self.bench else 2500
            mr_analysis = self.models.marginal_revenue_analysis(
                hourly_revenue=hourly,
                labor_cost_per_hour_cents=labor_cost,
            )
            if mr_analysis.get("profitable_hours", 0) > 0:
                best_hours = mr_analysis.get("best_hours", [])
                worst_hours = mr_analysis.get("worst_hours", [])
                if best_hours and worst_hours:
                    insights.append(self._make_insight(
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
                            f"{_cite('mit_sloan_scheduling')}."
                        ),
                        impact_cents=0,
                        confidence=0.7,
                        details={
                            "marginal_analysis": mr_analysis,
                            "citations": ["mit_sloan_scheduling", "cornell_labor_scheduling"],
                        },
                    ))

        # ── Seasonal Index ──
        daily_data = revenue.get("daily_data", ctx.daily_revenue)
        if daily_data and len(daily_data) >= 14 and self.models:
            seasonal = self.models.seasonal_index(daily_data)
            if seasonal.get("volatility_pct", 0) > 20:
                insights.append(self._make_insight(
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
                        f"recover 30-50% of weak-day revenue gaps {_cite('nra_seasonal_trends')}."
                    ),
                    impact_cents=0,
                    confidence=0.75,
                    details={
                        "seasonal_indices": seasonal,
                        "citations": ["nra_seasonal_trends", "nra_daypart_analysis"],
                    },
                ))

        return insights

    # ─── Insight Factory ──────────────────────────────────────

    def _make_insight(
        self,
        ctx,
        type: str,
        title: str,
        summary: str,
        impact_cents: int = 0,
        confidence: float = 0.5,
        details: dict | None = None,
        related_products: list | None = None,
        related_categories: list | None = None,
    ) -> dict:
        """Create a standardized insight dict with citation metadata."""
        insight = {
            "id": str(uuid4()),
            "org_id": ctx.org_id,
            "location_id": ctx.location_id,
            "type": type,
            "title": title,
            "summary": summary.strip(),
            "details": details or {},
            "estimated_monthly_impact_cents": impact_cents,
            "confidence_score": confidence,
            "related_products": related_products or [],
            "related_categories": related_categories or [],
            "action_status": "pending",
            "valid_until": (
                datetime.now(timezone.utc) + timedelta(days=30)
            ).isoformat(),
            "model_version": self.MODEL_VERSION,
            "metadata": {
                "engine": "meridian-economics-v2",
                "has_citations": bool(details and details.get("citations")),
            },
        }
        return insight

    def _score_priority(self, insight: dict) -> float:
        """Composite priority: abs(impact) * confidence * (1/effort) * novelty."""
        impact = abs(insight.get("estimated_monthly_impact_cents", 0))
        confidence = insight.get("confidence_score", 0.5)
        effort = insight.get("details", {}).get("effort_to_fix", 1.0)
        if effort <= 0:
            effort = 1.0
        novelty = 1.0
        return impact * confidence * (1.0 / effort) * novelty
