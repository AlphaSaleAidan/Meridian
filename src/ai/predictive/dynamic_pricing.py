"""
Dynamic Pricing Optimizer — Predictive 4.

Calculates optimal price per product per context (hour/day/season)
using elasticity data from agents.

IMPORTANT: caps adjustments at +/-15% from menu price.
Implement via "happy hour specials" not surge pricing.
"""
import logging

logger = logging.getLogger("meridian.ai.predictive.pricing")

# Optional: SHAP for explainable pricing recommendations
try:
    import shap
    HAS_SHAP = True
except ImportError:
    HAS_SHAP = False


class DynamicPricingOptimizer:
    """Calculate context-dependent optimal prices."""

    name = "dynamic_pricing"
    tier = 6

    MAX_ADJUSTMENT_PCT = 15

    def __init__(self, ctx, agent_outputs: dict | None = None):
        self.ctx = ctx
        self.outputs = agent_outputs or getattr(ctx, "agent_outputs", {})

    async def analyze(self) -> dict:
        pricing = self.outputs.get("pricing_power", {})
        peak = self.outputs.get("peak_hours", {})
        seasonal = self.outputs.get("seasonality", {})
        dow = self.outputs.get("day_of_week", {})
        velocity = self.outputs.get("product_velocity", {})

        if pricing.get("status") != "complete":
            return {
                "agent_name": self.name,
                "status": "insufficient_data",
                "summary": "Need pricing power agent data for dynamic pricing",
            }

        elasticity = pricing.get("data", {}).get("price_elasticity", -1.2)
        products = velocity.get("data", {}).get("ranked", [])
        if not products:
            products = self.ctx.product_performance or []

        peak_data = peak.get("data", {})
        golden_hours = peak_data.get("golden_hours", [])
        dead_hours = peak_data.get("dead_hours", [])

        seasonal_data = seasonal.get("data", {})
        current_season_idx = seasonal_data.get("current_seasonal_index", 1.0)
        is_peak_season = current_season_idx > 1.1
        is_slow_season = current_season_idx < 0.9

        dow_data = dow.get("data", {})
        worst_day = dow_data.get("worst_day")
        best_day = dow_data.get("best_day")

        # Calculate per-product pricing
        price_matrix = []
        total_revenue_lift = 0

        for p in products[:20]:
            name = p.get("name", "Unknown")
            current_price = p.get("avg_price_cents", 0)
            daily_volume = p.get("daily_velocity", 0) or p.get("quantity_sold", 0) / max(self.ctx.analysis_days, 1)

            if current_price <= 0 or daily_volume <= 0:
                continue

            # Base optimal: price * (1 + 1/elasticity)
            # Only meaningful if elasticity is negative
            if elasticity < -0.1:
                base_optimal = int(current_price * (1 + 1 / elasticity))
            else:
                base_optimal = current_price

            # Context adjustments
            peak_adj = 0.0
            if golden_hours and abs(elasticity) < 0.7:
                peak_adj = 0.07  # +7% during golden hours

            slow_day_adj = 0.0
            if worst_day and abs(elasticity) > 1.2:
                slow_day_adj = -0.12  # -12% on weakest day

            season_adj = 0.0
            if is_peak_season:
                season_adj = 0.05
            elif is_slow_season:
                season_adj = -0.10

            # Cap adjustments
            total_adj = peak_adj + slow_day_adj + season_adj
            total_adj = max(-self.MAX_ADJUSTMENT_PCT / 100, min(self.MAX_ADJUSTMENT_PCT / 100, total_adj))

            dynamic_price = int(base_optimal * (1 + total_adj))

            # Ensure within +/-15% of current
            dynamic_price = max(
                int(current_price * 0.85),
                min(int(current_price * 1.15), dynamic_price)
            )

            price_change = dynamic_price - current_price
            volume_impact = elasticity * (price_change / max(current_price, 1))
            new_volume = daily_volume * (1 + volume_impact)
            daily_lift = (new_volume * dynamic_price) - (daily_volume * current_price)
            monthly_lift = int(daily_lift * 30)
            total_revenue_lift += monthly_lift

            entry = {
                "product": name,
                "current_price_cents": current_price,
                "optimal_price_cents": dynamic_price,
                "change_cents": price_change,
                "change_pct": round(price_change / max(current_price, 1) * 100, 1),
                "contexts": {
                    "peak_hour_premium_pct": round(peak_adj * 100, 1),
                    "slow_day_discount_pct": round(slow_day_adj * 100, 1),
                    "seasonal_adj_pct": round(season_adj * 100, 1),
                },
                "predicted_monthly_lift_cents": monthly_lift,
            }

            # SHAP: explain why this price was recommended
            why = self._explain_pricing(
                peak_adj, slow_day_adj, season_adj,
                elasticity, price_change, current_price,
            )
            if why:
                entry["why"] = why

            price_matrix.append(entry)

        price_matrix.sort(key=lambda x: x["predicted_monthly_lift_cents"], reverse=True)

        return {
            "agent_name": self.name,
            "status": "complete",
            "summary": (
                f"Dynamic pricing across {len(price_matrix)} products could add "
                f"${total_revenue_lift/100:.0f}/month"
            ),
            "total_revenue_lift_monthly_cents": total_revenue_lift,
            "products_analyzed": len(price_matrix),
            "price_matrix": price_matrix[:15],
            "elasticity_used": round(elasticity, 2),
            "max_adjustment_pct": self.MAX_ADJUSTMENT_PCT,
            "context": {
                "is_peak_season": is_peak_season,
                "is_slow_season": is_slow_season,
                "golden_hours": golden_hours[:3] if golden_hours else [],
                "worst_day": worst_day,
            },
            "confidence": 0.55 if len(products) >= 10 else 0.35,
            "data_quality": 0.6,
            "insights": [
                {
                    "type": "pricing",
                    "title": f"Dynamic pricing opportunity: ${total_revenue_lift/100:.0f}/month",
                    "detail": (
                        f"Top opportunity: {price_matrix[0]['product']} "
                        f"({price_matrix[0]['change_pct']:+.1f}%)"
                        if price_matrix else "No actionable pricing changes"
                    ),
                    "data_quality": 0.6,
                }
            ],
            "recommendations": [
                {
                    "action": "Implement peak-hour premiums via 'specials' framing, not surge pricing",
                    "impact_cents": total_revenue_lift,
                    "effort": "medium",
                },
                {
                    "action": f"Launch {worst_day} happy hour with {abs(slow_day_adj)*100:.0f}% discounts on elastic items" if worst_day else "Test slow-day discounts",
                    "impact_cents": int(total_revenue_lift * 0.3),
                    "effort": "low",
                },
            ],
        }

    def _explain_pricing(
        self,
        peak_adj: float,
        slow_day_adj: float,
        season_adj: float,
        elasticity: float,
        price_change: int,
        current_price: int,
    ) -> list[str]:
        """Explain top 3 factors driving a pricing recommendation.

        Uses SHAP with a simple linear model when available, otherwise
        returns a heuristic explanation based on adjustment magnitudes.
        """
        feature_names = [
            "peak_hour_demand",
            "slow_day_discount",
            "seasonal_adjustment",
            "price_elasticity",
        ]
        feature_values = [peak_adj, slow_day_adj, season_adj, elasticity]

        if HAS_SHAP:
            try:
                import numpy as np

                # Use KernelExplainer on a simple linear prediction function
                X_bg = np.array([[0.0, 0.0, 0.0, -1.0]])
                X_instance = np.array([feature_values])

                def pricing_model(X):
                    """Simplified pricing impact model for SHAP."""
                    return np.array([
                        row[0] * 100 + row[1] * 100 + row[2] * 100 + (1 + 1/min(row[3], -0.1)) * 100
                        if row[3] < -0.1 else row[0] * 100 + row[1] * 100 + row[2] * 100
                        for row in X
                    ])

                explainer = shap.KernelExplainer(pricing_model, X_bg)
                sv = explainer.shap_values(X_instance, nsamples=50)[0]
                top_indices = np.argsort(np.abs(sv))[::-1][:3]

                factors = []
                for idx in top_indices:
                    val = feature_values[idx]
                    if abs(sv[idx]) < 0.01:
                        continue
                    name = feature_names[idx]
                    if name == "peak_hour_demand" and val > 0:
                        factors.append(f"High peak-hour demand supports +{val*100:.0f}% premium")
                    elif name == "slow_day_discount" and val < 0:
                        factors.append(f"Weak slow-day traffic warrants {val*100:.0f}% discount")
                    elif name == "seasonal_adjustment" and val != 0:
                        direction = "peak" if val > 0 else "slow"
                        factors.append(f"Seasonal {direction} factor: {val*100:+.0f}%")
                    elif name == "price_elasticity":
                        if abs(elasticity) > 1.2:
                            factors.append(f"Elastic demand (e={elasticity:.1f}) favors competitive pricing")
                        else:
                            factors.append(f"Inelastic demand (e={elasticity:.1f}) supports premium pricing")
                return factors[:3] if factors else None
            except Exception as e:
                logger.debug(f"SHAP pricing explanation failed: {e}")

        # Heuristic fallback: rank by absolute magnitude
        factors = []
        adjustments = sorted(
            zip(
                ["Peak-hour premium", "Slow-day discount", "Seasonal adjustment"],
                [peak_adj, slow_day_adj, season_adj],
            ),
            key=lambda x: abs(x[1]),
            reverse=True,
        )
        for label, val in adjustments:
            if abs(val) > 0.01:
                factors.append(f"{label}: {val*100:+.1f}%")
        if abs(elasticity) > 1.2:
            factors.append(f"Elastic demand (e={elasticity:.1f}) favors lower prices")
        elif abs(elasticity) < 0.7:
            factors.append(f"Inelastic demand (e={elasticity:.1f}) supports premiums")
        return factors[:3] if factors else None
