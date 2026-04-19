"""
Insight Generator — Produces actionable AI insights for merchants.

Takes raw analyses from all analyzers and generates prioritized,
human-readable insights with estimated impact.

Each insight has:
  • Type (money_left, product_recommendation, staffing, pricing, etc.)
  • Title + summary (human-readable, conversational)
  • Estimated monthly $ impact
  • Confidence score (0-1)
  • Related products/categories
  • Action status tracking
"""
import logging
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from typing import Any

logger = logging.getLogger("meridian.ai.generators.insights")


class InsightGenerator:
    """Generates prioritized, actionable insights."""

    MODEL_VERSION = "meridian-insight-v1"

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

        # Sort by estimated impact (highest first)
        insights.sort(
            key=lambda x: abs(x.get("estimated_monthly_impact_cents", 0)),
            reverse=True,
        )

        # Limit to top 20 insights per run
        insights = insights[:20]

        logger.info(f"Generated {len(insights)} insights for {ctx.org_id}")
        return insights

    # ─── Revenue Insights ─────────────────────────────────────

    def _revenue_insights(self, ctx, revenue: dict) -> list[dict]:
        """Generate insights from revenue analysis."""
        insights = []
        
        if revenue.get("error"):
            return insights

        kpis = revenue.get("kpis", {})
        trend = revenue.get("trend", {})
        comparison = revenue.get("comparison", {})

        # Insight: Revenue trend
        direction = trend.get("direction", "stable")
        wow_growth = trend.get("wow_growth_pct")
        
        if direction == "growing" and wow_growth and wow_growth > 5:
            insights.append(self._make_insight(
                ctx=ctx,
                type="general",
                title="📈 Revenue is growing strong",
                summary=(
                    f"Your revenue grew {wow_growth:+.1f}% week-over-week. "
                    f"You're averaging ${kpis.get('avg_daily_revenue_cents', 0)/100:,.0f}/day "
                    f"with {kpis.get('avg_transactions_per_day', 0):.0f} transactions. "
                    f"Keep the momentum going!"
                ),
                impact_cents=0,
                confidence=0.85,
                details={"trend": trend, "kpis": kpis},
            ))
        elif direction == "declining" and wow_growth and wow_growth < -5:
            daily_loss = int(abs(wow_growth) / 100 * kpis.get("avg_daily_revenue_cents", 0))
            insights.append(self._make_insight(
                ctx=ctx,
                type="general",
                title="📉 Revenue trending down",
                summary=(
                    f"Revenue dropped {wow_growth:+.1f}% week-over-week. "
                    f"That's roughly ${daily_loss/100:,.0f}/day less than last week. "
                    f"Check if traffic is down or average ticket size changed."
                ),
                impact_cents=daily_loss * 30,
                confidence=0.7,
                details={"trend": trend},
            ))

        # Insight: Avg ticket change
        ticket_change = comparison.get("avg_ticket_change_pct", 0)
        if abs(ticket_change) > 10:
            direction_word = "increased" if ticket_change > 0 else "decreased"
            insights.append(self._make_insight(
                ctx=ctx,
                type="pricing",
                title=f"🎫 Average ticket size {direction_word}",
                summary=(
                    f"Your average ticket {direction_word} by {abs(ticket_change):.1f}% "
                    f"compared to the previous period. "
                    f"Current average: ${kpis.get('avg_ticket_cents', 0)/100:,.2f}."
                ),
                impact_cents=0,
                confidence=0.8,
                details={"comparison": comparison},
            ))

        # Insight: Tip analysis
        tip_rate = kpis.get("tip_rate_pct", 0)
        if tip_rate > 0 and tip_rate < 10:
            insights.append(self._make_insight(
                ctx=ctx,
                type="general",
                title="💡 Tip rate below average",
                summary=(
                    f"Your tip rate is {tip_rate:.1f}% "
                    f"(industry average: 15-20%). "
                    f"Consider upgrading POS tip prompts or adding suggested amounts."
                ),
                impact_cents=int(kpis.get("total_revenue_cents", 0) * 0.05 / max(kpis.get("total_days", 1), 1) * 30),
                confidence=0.5,
                details={"tip_rate_pct": tip_rate},
            ))

        return insights

    # ─── Product Insights ─────────────────────────────────────

    def _product_insights(self, ctx, products: dict) -> list[dict]:
        """Generate insights from product analysis."""
        insights = []
        
        if products.get("error"):
            return insights

        # Insight: Star products
        tiers = products.get("tiers", {})
        stars = tiers.get("stars", [])
        if stars:
            star_names = ", ".join(s["name"] for s in stars[:3])
            insights.append(self._make_insight(
                ctx=ctx,
                type="product_recommendation",
                title="⭐ Your star products",
                summary=(
                    f"Your top performers: {star_names}. "
                    f"These drive the most revenue. "
                    f"Make sure they're always in stock and prominently featured."
                ),
                impact_cents=0,
                confidence=0.9,
                details={"stars": stars[:5]},
                related_products=[s.get("product_id") for s in stars[:5] if s.get("product_id")],
            ))

        # Insight: Dead stock warning
        dead = products.get("dead_stock", [])
        if len(dead) >= 3:
            dead_names = ", ".join(d["name"] for d in dead[:3])
            total_dead = len(dead)
            insights.append(self._make_insight(
                ctx=ctx,
                type="inventory",
                title=f"🚫 {total_dead} products with zero sales",
                summary=(
                    f"{total_dead} products haven't sold in {ctx.analysis_days} days: "
                    f"{dead_names}"
                    f"{' and more' if total_dead > 3 else ''}. "
                    f"Consider clearance pricing, bundling with popular items, "
                    f"or removing them to free up shelf space."
                ),
                impact_cents=total_dead * 10000,  # $100/product/month
                confidence=0.65,
                details={"dead_stock": dead[:10]},
            ))

        # Insight: Revenue concentration risk
        concentration = products.get("concentration_risk", {})
        if concentration.get("risk_level") == "high":
            insights.append(self._make_insight(
                ctx=ctx,
                type="general",
                title="⚠️ Revenue too concentrated",
                summary=(
                    f"'{concentration.get('top_product_name', 'Your top product')}' "
                    f"generates {concentration.get('top_product_share_pct', 0):.0f}% of revenue. "
                    f"Only {concentration.get('products_for_80_pct_revenue', 0)} products "
                    f"drive 80% of sales. Diversify to reduce risk."
                ),
                impact_cents=0,
                confidence=0.7,
                details={"concentration": concentration},
            ))

        # Insight: Pricing opportunities
        pricing_opps = products.get("pricing_opportunities", [])
        if pricing_opps:
            best_opp = pricing_opps[0]
            total_impact = sum(
                o.get("estimated_monthly_impact_cents", 0) for o in pricing_opps
            )
            insights.append(self._make_insight(
                ctx=ctx,
                type="pricing",
                title=f"💰 {len(pricing_opps)} pricing opportunities found",
                summary=(
                    f"We found {len(pricing_opps)} products with pricing optimization potential. "
                    f"Top opportunity: {best_opp.get('name', 'Unknown')} — "
                    f"{best_opp.get('reason', '')}. "
                    f"Total potential: ${total_impact/100:,.0f}/month."
                ),
                impact_cents=total_impact,
                confidence=0.6,
                details={"opportunities": pricing_opps[:5]},
            ))

        return insights

    # ─── Pattern Insights ─────────────────────────────────────

    def _pattern_insights(self, ctx, patterns: dict) -> list[dict]:
        """Generate insights from pattern analysis."""
        insights = []

        # Insight: Golden window
        peak_data = patterns.get("peak_hours", {})
        golden = peak_data.get("golden_window", {})
        if golden.get("label"):
            insights.append(self._make_insight(
                ctx=ctx,
                type="staffing",
                title=f"🔥 Golden hours: {golden['label']}",
                summary=(
                    f"Your most profitable window is {golden['label']}, "
                    f"generating {golden.get('total_revenue_share_pct', 0):.0f}% "
                    f"of daily revenue. "
                    f"Make sure you're fully staffed and stocked during this window."
                ),
                impact_cents=0,
                confidence=0.8,
                details={"golden_window": golden},
            ))

        # Insight: Best/worst day
        dow = patterns.get("day_of_week", {})
        best_day = dow.get("best_day")
        worst_day = dow.get("worst_day")
        if best_day and worst_day and best_day != worst_day:
            best_avg = dow.get("best_day_avg_cents", 0)
            worst_avg = dow.get("worst_day_avg_cents", 0)
            gap = best_avg - worst_avg
            
            if gap > 0 and worst_avg > 0:
                gap_pct = round(gap / worst_avg * 100, 0)
                if gap_pct > 30:
                    insights.append(self._make_insight(
                        ctx=ctx,
                        type="staffing",
                        title=f"📅 {worst_day}s need a boost",
                        summary=(
                            f"{best_day} averages ${best_avg/100:,.0f} but "
                            f"{worst_day} only ${worst_avg/100:,.0f} "
                            f"({gap_pct:.0f}% gap). "
                            f"Consider a {worst_day} promotion, happy hour, or "
                            f"special to drive traffic on your slowest day."
                        ),
                        impact_cents=int(gap * 4 * 0.2),  # 20% improvement on 4 slow days/month
                        confidence=0.5,
                        details={"day_analysis": dow},
                    ))

        # Insight: Payment mix
        payment = patterns.get("payment_patterns", {})
        cash_pct = payment.get("cash_pct", 0)
        if cash_pct > 50:
            insights.append(self._make_insight(
                ctx=ctx,
                type="general",
                title="💵 High cash transaction rate",
                summary=(
                    f"{cash_pct:.0f}% of transactions are cash. "
                    f"Promoting card/mobile payments can increase average ticket size "
                    f"(card customers typically spend 12-18% more) and reduce "
                    f"cash handling costs."
                ),
                impact_cents=0,
                confidence=0.55,
                details={"payment_mix": payment},
            ))

        return insights

    # ─── Money Left Insights ──────────────────────────────────

    def _money_left_insights(self, ctx, money_left: dict) -> list[dict]:
        """Generate the headline Money Left on Table insight."""
        insights = []
        
        total = money_left.get("total_score_cents", 0)
        if total <= 0:
            return insights
        
        summary_text = money_left.get("summary", "")
        top_actions = money_left.get("top_actions", [])
        
        # Build action list
        action_text = ""
        if top_actions:
            action_text = "\n\nTop actions:\n"
            for i, action in enumerate(top_actions[:3], 1):
                action_text += (
                    f"{i}. {action['description']} "
                    f"(~${action.get('impact_cents', 0)/100:,.0f}/mo)\n"
                )

        insights.append(self._make_insight(
            ctx=ctx,
            type="money_left",
            title=f"💸 ${total/100:,.0f}/month left on the table",
            summary=summary_text + action_text,
            impact_cents=total,
            confidence=0.6,
            details={
                "components": {
                    k: {"amount_cents": v.get("amount_cents", 0), "detail": v.get("detail", "")}
                    for k, v in money_left.get("components", {}).items()
                },
                "top_actions": top_actions[:5],
            },
        ))
        
        return insights

    # ─── Anomaly Insights ─────────────────────────────────────

    def _anomaly_insights(self, ctx, revenue: dict) -> list[dict]:
        """Generate alerts for recent anomalies."""
        insights = []
        
        anomalies = revenue.get("anomalies", [])
        # Only alert on recent anomalies (last 7 days)
        recent = [
            a for a in anomalies
            if a.get("severity") in ("high", "medium")
        ][:3]
        
        for anomaly in recent:
            atype = anomaly.get("type", "anomaly")
            emoji = "📈" if atype == "spike" else "📉"
            
            insights.append(self._make_insight(
                ctx=ctx,
                type="anomaly",
                title=f"{emoji} Unusual {atype} on {anomaly.get('date', 'recent day')}",
                summary=(
                    f"Revenue was ${anomaly.get('revenue_cents', 0)/100:,.0f} "
                    f"on {anomaly.get('date', 'this day')}, which is "
                    f"{abs(anomaly.get('deviation_pct', 0)):.0f}% "
                    f"{'above' if atype == 'spike' else 'below'} normal "
                    f"(expected: ~${anomaly.get('expected_cents', 0)/100:,.0f}). "
                    f"{'Great day! Understand what drove it.' if atype == 'spike' else 'Investigate: was it weather, a competitor, or an issue?'}"
                ),
                impact_cents=abs(
                    anomaly.get("revenue_cents", 0) - anomaly.get("expected_cents", 0)
                ),
                confidence=min(abs(anomaly.get("z_score", 0)) / 5, 0.95),
                details={"anomaly": anomaly},
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
        """Create a standardized insight dict."""
        return {
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
            "metadata": {},
        }
