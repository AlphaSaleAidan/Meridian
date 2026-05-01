"""Product insight generation with economic frameworks."""
from ._insight_helpers import fmt_cents, cite, make_insight


def generate(ctx, products: dict, bench, models) -> list[dict]:
    insights = []

    if products.get("error"):
        return insights

    tiers = products.get("tiers", {})
    stars = tiers.get("stars", [])
    dead_stock = products.get("dead_stock", [])
    pricing_opps = products.get("pricing_opportunities", [])
    concentration = products.get("concentration_risk", {})

    if stars:
        star_names = ", ".join(s["name"] for s in stars[:3])
        total_star_rev = sum(s.get("revenue_cents", 0) for s in stars[:5])
        total_rev = products.get("total_revenue_cents", 1)
        star_share = round(total_star_rev / max(total_rev, 1) * 100, 1)

        insights.append(make_insight(
            ctx=ctx,
            type="product_recommendation",
            title="⭐ Star Products Identified — Protect & Promote These Revenue Drivers",
            summary=(
                f"Your top performers ({star_names}) collectively account for "
                f"{star_share}% of total revenue. In menu engineering terms, these are your "
                f"\"Stars\" — high popularity, high profitability items that form the backbone "
                f"of your product mix {cite('cornell_menu_pricing')}."
                f"\n\n"
                f"*Strategic recommendations:*\n"
                f"1. *Never stock out* — Each lost sale of a star product costs your average "
                f"ticket plus the probability of a walk-away (estimated 15-20% of customers "
                f"leave rather than substitute)\n"
                f"2. *Feature prominently* — Position at eye level, menu board prime spots, "
                f"and as first recommendations from staff\n"
                f"3. *Test selective premiumization* — Star products tolerate 3-5% price "
                f"increases with minimal volume impact due to their inelastic demand "
                f"{cite('jmr_elasticity')}\n"
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

    if len(dead_stock) >= 2:
        dead_names = ", ".join(d["name"] for d in dead_stock[:3])
        total_dead = len(dead_stock)
        est_monthly_cost = total_dead * 15000

        insights.append(make_insight(
            ctx=ctx,
            type="inventory",
            title=f"🚫 {total_dead} Dead Stock Items — {fmt_cents(est_monthly_cost)}/Month Hidden Cost",
            summary=(
                f"{total_dead} products have generated zero revenue over the past "
                f"{ctx.analysis_days} days: {dead_names}"
                f"{'and more' if total_dead > 3 else ''}."
                f"\n\n"
                f"*The hidden economics of dead stock:*\n"
                f"According to NRF research, dead stock accounts for 25-30% of total "
                f"inventory shrinkage, which averages 1.6% of annual revenue "
                f"{cite('nrf_inventory_shrink')}. Beyond direct cost, dead stock occupies "
                f"shelf space that could house your top performers, and perishable items "
                f"compound losses through spoilage. The National Restaurant Association "
                f"estimates reducing food waste by 20% improves net margin by 1-3 points "
                f"{cite('nra_food_waste')}."
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

    if models and concentration:
        product_revenues = [
            p.get("revenue_cents", 0) for p in
            products.get("ranked", products.get("performance", []))
            if p.get("revenue_cents", 0) > 0
        ]
        if product_revenues:
            hhi = models.revenue_concentration_hhi(product_revenues)
            if hhi.get("risk_level") in ("moderate", "high"):
                insights.append(make_insight(
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
                        f"exceed 30% of total revenue for SMBs {cite('mckinsey_pricing')}."
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

    if pricing_opps:
        best_opp = pricing_opps[0]
        total_impact = sum(
            o.get("estimated_monthly_impact_cents", 0) for o in pricing_opps
        )
        insights.append(make_insight(
            ctx=ctx,
            type="pricing",
            title=f"💰 {len(pricing_opps)} Data-Backed Pricing Opportunities — {fmt_cents(total_impact)}/Month Potential",
            summary=(
                f"Our analysis identified {len(pricing_opps)} products where data supports "
                f"a price adjustment. Top opportunity: *{best_opp.get('name', 'Unknown')}* — "
                f"{best_opp.get('reason', '')}."
                f"\n\n"
                f"*Economic rationale:*\n"
                f"Harvard Business Review research demonstrates that a 1% price increase "
                f"yields an average 11.1% improvement in operating profit — making pricing "
                f"the single highest-leverage variable in the P&L "
                f"{cite('hbr_pricing_power')}. Restaurants using data-driven menu "
                f"engineering achieve 8-15% higher gross margins vs. cost-plus pricing "
                f"{cite('cornell_menu_pricing')}."
                f"\n\n"
                f"Meta-analysis data shows food service items with <5% price increases "
                f"exhibit near-zero demand reduction (mean elasticity: -1.2 for staples) "
                f"{cite('jmr_elasticity')}."
                f"\n\n"
                f"*Implementation:*\n"
                f"1. Start with your highest-volume, lowest-elasticity items first\n"
                f"2. Increase by 3-5% (below consumer perception threshold)\n"
                f"3. Monitor volume for 2 weeks before proceeding to next batch\n"
                f"4. Total combined potential: {fmt_cents(total_impact)}/month"
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
