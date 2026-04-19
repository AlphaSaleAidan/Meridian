"""
Money Left on Table Calculator — Meridian's headline metric.

This is THE number. "You're leaving $3,847/month on the table."

Computes a dollar score across 5 components:
  1. UNDERPRICED PRODUCTS — Products selling well below market/optimum
  2. DEAD STOCK — Products taking up shelf space with zero sales
  3. PEAK HOUR WASTE — Revenue lost from understaffing peak hours
  4. DISCOUNT LEAKAGE — Excessive discounting eroding margins
  5. SCHEDULING GAPS — Operating hours misaligned with demand

Each component provides actionable recommendations.
"""
import logging
import math
from datetime import datetime, timezone
from uuid import uuid4
from typing import Any

logger = logging.getLogger("meridian.ai.analyzers.money_left")


class MoneyLeftCalculator:
    """
    Calculates the total "money left on the table" score.
    
    This is the centerpiece of Meridian's value proposition.
    Business owners see this number and immediately understand
    how much revenue they're missing.
    """

    def calculate(
        self,
        ctx,
        revenue: dict,
        products: dict,
        patterns: dict,
    ) -> dict:
        """
        Calculate the Money Left on Table score.
        
        Returns:
            {
                "id": UUID,
                "org_id": str,
                "total_score_cents": int,
                "total_score_dollars": str,  # "$3,847"
                "components": {
                    "underpriced": {...},
                    "dead_stock": {...},
                    "peak_hour_waste": {...},
                    "discount_leakage": {...},
                    "scheduling_gaps": {...},
                },
                "summary": "You're leaving $3,847/mo on the table.",
                "top_actions": [top 3 things to fix],
                "scored_at": datetime,
            }
        """
        components = {}

        # ── Component 1: Underpriced Products ─────────────────
        components["underpriced"] = self._calc_underpriced(products)

        # ── Component 2: Dead Stock ───────────────────────────
        components["dead_stock"] = self._calc_dead_stock(products)

        # ── Component 3: Peak Hour Revenue Loss ───────────────
        components["peak_hour_waste"] = self._calc_peak_hour_waste(
            patterns, revenue
        )

        # ── Component 4: Discount Leakage ─────────────────────
        components["discount_leakage"] = self._calc_discount_leakage(revenue)

        # ── Component 5: Scheduling Gaps ──────────────────────
        components["scheduling_gaps"] = self._calc_scheduling_gaps(patterns)

        # ── Total Score ───────────────────────────────────────
        total_cents = sum(
            (c.get("amount_cents") or 0) for c in components.values()
        )

        # Build top actions (sorted by impact)
        all_actions = []
        for key, comp in components.items():
            for action in comp.get("actions", []):
                action["component"] = key
                all_actions.append(action)
        
        all_actions.sort(
            key=lambda x: (x.get("impact_cents") or 0), reverse=True
        )

        result = {
            "id": str(uuid4()),
            "org_id": ctx.org_id,
            "location_id": ctx.location_id,
            "total_score_cents": total_cents,
            "total_score_dollars": f"${total_cents / 100:,.0f}",
            "components": components,
            "top_actions": all_actions[:5],
            "summary": self._build_summary(total_cents, components),
            "scored_at": datetime.now(timezone.utc).isoformat(),
            "model_version": "meridian-mlt-v1",
        }

        logger.info(
            f"Money Left on Table for {ctx.org_id}: "
            f"${total_cents/100:,.0f}/month "
            f"({len(all_actions)} actionable items)"
        )
        return result

    # ─── Component Calculators ────────────────────────────────

    def _calc_underpriced(self, products: dict) -> dict:
        """
        Identify revenue lost from suboptimal pricing.
        
        Uses pricing opportunities from product analysis.
        Conservative estimate: assumes 50% adoption rate.
        """
        opportunities = products.get("pricing_opportunities", [])
        
        price_increase_opps = [
            o for o in opportunities if o.get("type") == "price_increase"
        ]
        
        total_potential = sum(
            (o.get("estimated_monthly_impact_cents") or 0) 
            for o in price_increase_opps
        )
        
        # Apply 50% adoption discount (not all changes will be made)
        amount = int(total_potential * 0.5)
        
        actions = []
        for opp in price_increase_opps[:5]:
            actions.append({
                "description": (
                    f"Raise '{opp['name']}' from "
                    f"${opp.get('current_price_cents', 0)/100:.2f} to "
                    f"${opp.get('suggested_price_cents', 0)/100:.2f}"
                ),
                "impact_cents": int(
                    (opp.get("estimated_monthly_impact_cents") or 0) * 0.5
                ),
                "confidence": opp.get("confidence", 0.5),
                "effort": "low",
            })
        
        return {
            "amount_cents": amount,
            "product_count": len(price_increase_opps),
            "actions": actions,
            "detail": f"{len(price_increase_opps)} products priced below optimal",
        }

    def _calc_dead_stock(self, products: dict) -> dict:
        """
        Estimate cost of dead stock (zero-sale products).
        
        Dead stock = shelf space, ordering cost, spoilage risk.
        Conservative estimate: $50-200/product/month in opportunity cost.
        """
        dead = products.get("dead_stock", [])
        
        # Estimate $100/product/month in opportunity cost
        per_product_cost = 10000  # $100 in cents
        amount = len(dead) * per_product_cost
        
        actions = []
        for item in dead[:5]:
            actions.append({
                "description": (
                    f"Review '{item['name']}' — zero sales in "
                    f"{item.get('days_without_sale', 30)} days. "
                    f"Consider clearance, bundling, or removal."
                ),
                "impact_cents": per_product_cost,
                "confidence": 0.6,
                "effort": "low",
            })
        
        return {
            "amount_cents": amount,
            "product_count": len(dead),
            "actions": actions,
            "detail": (
                f"{len(dead)} products with zero sales — "
                f"wasting shelf space and capital"
            ),
        }

    def _calc_peak_hour_waste(self, patterns: dict, revenue: dict) -> dict:
        """
        Revenue lost from not maximizing peak hours.
        
        If the best hour does 3x the average but you're not
        fully staffed, you're losing potential revenue.
        
        Compares actual peak performance to theoretical maximum.
        """
        peak_data = patterns.get("peak_hours", {})
        golden = peak_data.get("golden_window", {})
        
        if not golden:
            return {"amount_cents": 0, "actions": [], "detail": "Insufficient data"}
        
        # If golden window captures X% of revenue, estimate how much more
        # could be captured with optimal staffing
        revenue_share = (golden.get("total_revenue_share_pct") or 0)
        
        kpis = revenue.get("kpis", {})
        avg_daily_rev = (kpis.get("avg_daily_revenue_cents") or 0)
        
        # Estimate: with better peak optimization, capture 10-15% more
        # during golden window
        peak_revenue = avg_daily_rev * (revenue_share / 100)
        improvement_pct = 0.10  # 10% improvement potential
        daily_gain = int(peak_revenue * improvement_pct)
        monthly_gain = daily_gain * 30
        
        actions = []
        if monthly_gain > 0:
            actions.append({
                "description": (
                    f"Add staff during golden window "
                    f"({golden.get('label', 'peak hours')}). "
                    f"This window drives {revenue_share:.0f}% of daily revenue."
                ),
                "impact_cents": monthly_gain,
                "confidence": 0.55,
                "effort": "medium",
            })
        
        # Check for understaffed hours from staffing analysis
        staffing = patterns.get("staffing", {})
        busiest = staffing.get("busiest_hour", {})
        if busiest:
            actions.append({
                "description": (
                    f"Ensure full staffing at {busiest.get('hour_label', 'peak')} "
                    f"({busiest.get('avg_transactions', 0):.0f} avg transactions/hour)."
                ),
                "impact_cents": int(monthly_gain * 0.3),
                "confidence": 0.6,
                "effort": "low",
            })
        
        return {
            "amount_cents": monthly_gain,
            "golden_window": golden.get("label", ""),
            "actions": actions,
            "detail": (
                f"Peak hours ({golden.get('label', 'N/A')}) "
                f"could yield {improvement_pct*100:.0f}% more with optimal staffing"
            ),
        }

    def _calc_discount_leakage(self, revenue: dict) -> dict:
        """
        Revenue lost to excessive or unnecessary discounting.
        
        If discount rate > 3%, flag the excess as recoverable.
        """
        kpis = revenue.get("kpis", {})
        total_discounts = (kpis.get("total_discount_cents") or 0)
        total_revenue = (kpis.get("total_revenue_cents") or 0)
        discount_rate = (kpis.get("discount_rate_pct") or 0)
        
        # Benchmark: 2-3% discount rate is normal
        excess_rate = max(0, discount_rate - 3.0) / 100
        recoverable = int(total_revenue * excess_rate)
        
        # Normalize to monthly: score is per-month
        days = max(kpis.get("total_days", 30), 1)
        monthly_recoverable = int(recoverable * 30 / days)
        
        actions = []
        if monthly_recoverable > 0:
            actions.append({
                "description": (
                    f"Discount rate is {discount_rate:.1f}% "
                    f"(benchmark: ≤3%). Tighten discount policies."
                ),
                "impact_cents": monthly_recoverable,
                "confidence": 0.65,
                "effort": "low",
            })
        
        return {
            "amount_cents": monthly_recoverable,
            "current_discount_rate_pct": discount_rate,
            "benchmark_rate_pct": 3.0,
            "total_discounts_cents": total_discounts,
            "actions": actions,
            "detail": (
                f"{discount_rate:.1f}% discount rate "
                f"(${total_discounts/100:,.0f} total)"
            ),
        }

    def _calc_scheduling_gaps(self, patterns: dict) -> dict:
        """
        Revenue lost from operating hours misaligned with demand.
        
        Identifies days/hours where the business is open but
        generating minimal revenue (waste), or closed when
        demand exists (missed opportunity).
        """
        dow = patterns.get("day_of_week", {})
        breakdown = dow.get("breakdown", [])
        
        if not breakdown:
            return {"amount_cents": 0, "actions": [], "detail": "Insufficient data"}
        
        # Find the gap between best and worst days
        best_rev = (dow.get("best_day_avg_cents") or 0)
        worst_rev = (dow.get("worst_day_avg_cents") or 0)
        
        if best_rev == 0:
            return {"amount_cents": 0, "actions": [], "detail": "No revenue data"}
        
        # If worst day is <40% of best day, there's a scheduling opportunity
        worst_day = dow.get("worst_day", "N/A")
        best_day = dow.get("best_day", "N/A")
        
        gap_pct = (best_rev - worst_rev) / max(best_rev, 1)
        
        amount = 0
        actions = []
        
        if gap_pct > 0.6:
            # Worst day is <40% of best — consider different hours or promotion
            potential = int((best_rev * 0.5 - worst_rev) * 4)  # Monthly impact
            amount = max(0, potential)
            actions.append({
                "description": (
                    f"{worst_day} revenue is {(1-gap_pct)*100:.0f}% of {best_day}. "
                    f"Run a {worst_day} special or adjust hours."
                ),
                "impact_cents": amount,
                "confidence": 0.45,
                "effort": "medium",
            })
        
        # Check weekend vs weekday imbalance
        weekend_pct = (dow.get("weekend_vs_weekday_pct") or 0)
        if abs(weekend_pct) > 40:
            note = (
                f"Weekends are {'significantly stronger' if weekend_pct > 0 else 'much weaker'} "
                f"than weekdays ({weekend_pct:+.0f}%)."
            )
            actions.append({
                "description": f"{note} Adjust staffing and promotions accordingly.",
                "impact_cents": int(amount * 0.2),
                "confidence": 0.4,
                "effort": "medium",
            })
        
        return {
            "amount_cents": amount,
            "day_gap_pct": round(gap_pct * 100, 1),
            "best_day": best_day,
            "worst_day": worst_day,
            "actions": actions,
            "detail": (
                f"{worst_day} underperforms by {gap_pct*100:.0f}% vs {best_day}"
            ),
        }

    # ─── Summary Builder ──────────────────────────────────────

    def _build_summary(self, total_cents: int, components: dict) -> str:
        """Build human-readable summary."""
        total_dollars = total_cents / 100
        
        if total_dollars < 100:
            return (
                f"Your business is well-optimized! We found "
                f"${total_dollars:,.0f}/month in small improvements."
            )
        elif total_dollars < 1000:
            return (
                f"You're leaving ${total_dollars:,.0f}/month on the table. "
                f"A few targeted changes could recover most of it."
            )
        elif total_dollars < 5000:
            return (
                f"You're leaving ${total_dollars:,.0f}/month on the table — "
                f"that's ${total_dollars * 12:,.0f}/year. "
                f"Let's fix the biggest items first."
            )
        else:
            # Find biggest component
            biggest = max(components.items(), key=lambda x: x[1].get("amount_cents", 0))
            return (
                f"You're leaving ${total_dollars:,.0f}/month on the table "
                f"(${total_dollars * 12:,.0f}/year). "
                f"The biggest opportunity: {biggest[1].get('detail', biggest[0])}."
            )
