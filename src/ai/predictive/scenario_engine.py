"""
What-If Scenario Engine — Predictive 1.

Supports these scenario types:
  - price_change: "What if I raise Latte price $0.50?"
  - add_shift: "What if I add a night shift?"
  - drop_products: "What if I drop my worst 3 products?"
"""
import logging

logger = logging.getLogger("meridian.ai.predictive.scenario")


class ScenarioEngine:
    """Run what-if scenarios using agent outputs as the foundation."""

    def __init__(self, ctx, agent_outputs: dict | None = None):
        self.ctx = ctx
        self.outputs = agent_outputs or getattr(ctx, "agent_outputs", {})

    async def run(self, scenario_type: str, params: dict) -> dict:
        """Dispatch to the right scenario handler."""
        handlers = {
            "price_change": self._price_change,
            "add_shift": self._add_shift,
            "drop_products": self._drop_products,
        }
        handler = handlers.get(scenario_type)
        if not handler:
            return {
                "status": "error",
                "error": f"Unknown scenario type: {scenario_type}",
                "supported": list(handlers.keys()),
            }
        try:
            return await handler(params)
        except Exception as e:
            logger.error(f"Scenario {scenario_type} failed: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}

    async def _price_change(self, params: dict) -> dict:
        """What if I change price of product X by Y?"""
        product_name = params.get("product_name", "")
        price_change_cents = params.get("price_change_cents", 50)

        pricing = self.outputs.get("pricing_power", {})
        products = self.outputs.get("product_velocity", {})

        # Find current product data
        product_data = None
        for p in products.get("data", {}).get("ranked", []):
            if p.get("name", "").lower() == product_name.lower():
                product_data = p
                break

        if not product_data:
            # Fallback: use aggregate data
            avg_price = pricing.get("data", {}).get("avg_price_cents", 500)
            avg_volume = 20  # daily default
            elasticity = pricing.get("data", {}).get("price_elasticity", -1.2)
        else:
            avg_price = product_data.get("avg_price_cents", 500)
            avg_volume = product_data.get("daily_velocity", 20)
            elasticity = pricing.get("data", {}).get("price_elasticity", -1.2)

        price_change_pct = price_change_cents / max(avg_price, 1)
        predicted_volume_change = elasticity * price_change_pct
        new_volume = avg_volume * (1 + predicted_volume_change)
        new_price = avg_price + price_change_cents
        new_daily_rev = new_volume * new_price
        old_daily_rev = avg_volume * avg_price
        net_impact_daily = new_daily_rev - old_daily_rev
        net_impact_monthly = int(net_impact_daily * 30)

        confidence = 0.7
        # Lower confidence if elasticity is estimated
        if not product_data:
            confidence = 0.4

        return {
            "status": "complete",
            "scenario_type": "price_change",
            "params": params,
            "current": {
                "price_cents": avg_price,
                "daily_volume": round(avg_volume, 1),
                "daily_revenue_cents": int(old_daily_rev),
            },
            "predicted": {
                "price_cents": new_price,
                "daily_volume": round(max(0, new_volume), 1),
                "daily_revenue_cents": int(new_daily_rev),
            },
            "net_impact_monthly_cents": net_impact_monthly,
            "elasticity_used": round(elasticity, 2),
            "confidence": confidence,
            "assumptions": [
                f"Price elasticity of {elasticity:.2f} (constant)",
                "No competitor response",
                "No substitution effects within menu",
            ],
            "risks": [
                "Elasticity may vary by time of day and customer segment",
                "Price increases above 10% trigger higher customer awareness",
            ],
            "recommendation": (
                f"{'Increase' if net_impact_monthly > 0 else 'Avoid'}: "
                f"net {'gain' if net_impact_monthly > 0 else 'loss'} of "
                f"${abs(net_impact_monthly)/100:.0f}/month predicted"
            ),
        }

    async def _add_shift(self, params: dict) -> dict:
        """What if I add a shift (e.g., night shift)?"""
        hours = params.get("hours", 4)
        hourly_wage_cents = params.get("hourly_wage_cents", 1800)
        staff_count = params.get("staff_count", 2)

        peak_hours_data = self.outputs.get("peak_hours", {})
        benchmark_data = self.outputs.get("benchmark", {})

        # Get dead hours revenue from peak hours agent
        hourly_rev = peak_hours_data.get("data", {}).get("hourly_avg", {})
        dead_hours = peak_hours_data.get("data", {}).get("dead_hours", [])

        # Calculate labor cost
        labor_cost_daily = hours * hourly_wage_cents * staff_count
        labor_cost_monthly = labor_cost_daily * 30

        # Estimate revenue from similar businesses' off-peak
        avg_ticket = 0
        for p in self.ctx.product_performance[:10]:
            if p.get("avg_price_cents"):
                avg_ticket = p["avg_price_cents"]
                break
        if not avg_ticket:
            avg_ticket = 700

        break_even_txns = labor_cost_daily / max(avg_ticket, 1)

        # Predicted transactions based on dead hour benchmarks
        dead_hour_avg_rev = 0
        if dead_hours:
            dead_hour_avg_rev = sum(
                hourly_rev.get(str(h), {}).get("avg_cents", 0) for h in dead_hours[:hours]
            ) or int(avg_ticket * 3 * hours)  # fallback: 3 txns/hr
        else:
            dead_hour_avg_rev = int(avg_ticket * 3 * hours)

        predicted_daily_rev = int(dead_hour_avg_rev * 1.5)  # new shift lifts
        roi_daily = predicted_daily_rev - labor_cost_daily
        roi_monthly = roi_daily * 30

        return {
            "status": "complete",
            "scenario_type": "add_shift",
            "params": params,
            "labor_cost_monthly_cents": labor_cost_monthly,
            "break_even_txns_per_day": round(break_even_txns, 1),
            "predicted_daily_revenue_cents": predicted_daily_rev,
            "predicted_monthly_revenue_cents": predicted_daily_rev * 30,
            "roi_monthly_cents": roi_monthly,
            "confidence": 0.45,
            "assumptions": [
                f"Staff: {staff_count} at ${hourly_wage_cents/100:.2f}/hr for {hours}hrs",
                "Assumes 50% revenue lift from extended hours awareness",
                "Based on current dead-hour traffic patterns",
            ],
            "risks": [
                "New shift may take 4-8 weeks to build traffic",
                "Startup costs not included (marketing, training)",
                "Security and insurance costs may increase",
            ],
            "recommendation": (
                f"{'Viable' if roi_monthly > 0 else 'Not recommended'}: "
                f"predicted {'profit' if roi_monthly > 0 else 'loss'} of "
                f"${abs(roi_monthly)/100:.0f}/month. "
                f"Need {break_even_txns:.0f} transactions/day to break even."
            ),
        }

    async def _drop_products(self, params: dict) -> dict:
        """What if I drop my worst N products?"""
        n = params.get("count", 3)

        velocity = self.outputs.get("product_velocity", {})
        basket = self.outputs.get("basket_analysis", {})

        ranked = velocity.get("data", {}).get("ranked", [])
        if not ranked:
            return {
                "status": "insufficient_data",
                "error": "No product velocity data available",
            }

        # Get worst products
        worst = sorted(ranked, key=lambda p: p.get("revenue_cents", 0))[:n]

        lost_revenue_monthly = sum(p.get("revenue_cents", 0) for p in worst)

        # Check basket impact
        basket_items = basket.get("data", {}).get("frequent_pairs", [])
        worst_names = {p.get("name", "").lower() for p in worst}
        at_risk_baskets = 0
        for pair in basket_items:
            items = [i.lower() for i in pair.get("items", [])]
            if any(w in items for w in worst_names if w):
                at_risk_baskets += pair.get("frequency", 0)

        # Estimate substitution
        substitution_rate = 0.3  # 30% of customers substitute
        cannibalization_risk = at_risk_baskets > 0
        substitution_gain = int(lost_revenue_monthly * substitution_rate)

        # Labor savings estimate (fewer items to prep/stock)
        labor_savings_monthly = n * 5000  # ~$50/month per dropped item

        net_impact = -lost_revenue_monthly + substitution_gain + labor_savings_monthly

        return {
            "status": "complete",
            "scenario_type": "drop_products",
            "params": {"count": n},
            "products_to_drop": [
                {"name": p.get("name", "?"), "monthly_revenue_cents": p.get("revenue_cents", 0)}
                for p in worst
            ],
            "lost_revenue_monthly_cents": lost_revenue_monthly,
            "substitution_gain_cents": substitution_gain,
            "labor_savings_monthly_cents": labor_savings_monthly,
            "basket_impact": {
                "at_risk_basket_count": at_risk_baskets,
                "cannibalization_risk": cannibalization_risk,
            },
            "net_impact_monthly_cents": net_impact,
            "confidence": 0.55,
            "assumptions": [
                f"30% substitution rate to remaining products",
                f"${labor_savings_monthly/100:.0f}/month labor savings from simplification",
                "No menu redesign costs included",
            ],
            "risks": [
                "Some customers may leave if their preferred item is removed",
                f"{'Basket disruption: worst items appear in multi-item orders' if cannibalization_risk else 'Low basket disruption risk'}",
            ],
            "recommendation": (
                f"{'Proceed' if net_impact > 0 else 'Caution'}: "
                f"net {'gain' if net_impact > 0 else 'loss'} of "
                f"${abs(net_impact)/100:.0f}/month. "
                + ("Consider phased removal." if cannibalization_risk else "Low risk of customer impact.")
            ),
        }
