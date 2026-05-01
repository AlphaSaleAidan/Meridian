"""
Demand Forecasting per Product — Predictive 5.

Unlike the total revenue forecaster (Agent 24), this forecasts
EACH product individually for prep guides and inventory ordering.
"""
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("meridian.ai.predictive.demand")


class DemandForecastAgent:
    """Per-product demand forecasting for prep and inventory."""

    name = "demand_forecast"
    tier = 6

    DOW_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    def __init__(self, ctx, agent_outputs: dict | None = None):
        self.ctx = ctx
        self.outputs = agent_outputs or getattr(ctx, "agent_outputs", {})

    async def analyze(self) -> dict:
        velocity = self.outputs.get("product_velocity", {})
        seasonal = self.outputs.get("seasonality", {})
        dow_agent = self.outputs.get("day_of_week", {})

        products = velocity.get("data", {}).get("ranked", [])
        if not products:
            products = self.ctx.product_performance or []

        if not products:
            return {
                "agent_name": self.name,
                "status": "insufficient_data",
                "summary": "Need product velocity data",
            }

        analysis_days = max(self.ctx.analysis_days, 1)
        seasonal_idx = seasonal.get("data", {}).get("current_seasonal_index", 1.0)

        # Build day-of-week indices
        dow_indices = {}
        dow_data = dow_agent.get("data", {}).get("day_performance", {})
        if dow_data:
            values = [dow_data.get(d, {}).get("avg_revenue_cents", 0) for d in self.DOW_NAMES]
            avg_val = sum(values) / max(len([v for v in values if v > 0]), 1)
            for i, d in enumerate(self.DOW_NAMES):
                dow_indices[i] = values[i] / max(avg_val, 1) if avg_val > 0 else 1.0
        else:
            dow_indices = {i: 1.0 for i in range(7)}

        # Forecast each product
        product_forecasts = []
        prep_guides = []
        inventory_orders = []
        today = datetime.now(timezone.utc)

        for p in products[:30]:
            name = p.get("name", "Unknown")
            qty_sold = p.get("quantity_sold", 0)
            velocity_30d = qty_sold / max(analysis_days, 1)

            # Recent trend: velocity_7d vs velocity_30d
            velocity_7d = p.get("velocity_7d", velocity_30d)
            if velocity_30d > 0:
                trend_multiplier = 1 + (velocity_7d - velocity_30d) / velocity_30d
            else:
                trend_multiplier = 1.0
            trend_multiplier = max(0.5, min(2.0, trend_multiplier))

            # Forecast next 7 days
            daily_forecasts = []
            for day_offset in range(1, 8):
                forecast_date = today + timedelta(days=day_offset)
                dow = forecast_date.weekday()
                dow_idx = dow_indices.get(dow, 1.0)

                predicted = velocity_30d * dow_idx * seasonal_idx * trend_multiplier
                daily_forecasts.append({
                    "date": forecast_date.strftime("%Y-%m-%d"),
                    "day": self.DOW_NAMES[dow],
                    "predicted_qty": round(max(0, predicted), 1),
                })

            product_forecasts.append({
                "product": name,
                "velocity_30d": round(velocity_30d, 2),
                "velocity_7d": round(velocity_7d, 2),
                "trend_multiplier": round(trend_multiplier, 2),
                "daily_forecasts": daily_forecasts,
            })

            # Prep guide
            avg_forecast = sum(f["predicted_qty"] for f in daily_forecasts) / 7
            waste_buffer = 1.1
            current_prep = p.get("avg_daily_prep", avg_forecast * 1.3)
            prep_qty = round(avg_forecast * waste_buffer, 0)
            waste_savings = 0
            if current_prep > prep_qty:
                avg_price = p.get("avg_price_cents", 500)
                waste_per_day = current_prep - prep_qty
                waste_savings = int(waste_per_day * avg_price * 0.4 * 7)  # 40% COGS

            if avg_forecast > 0.5:
                prep_guides.append({
                    "product": name,
                    "recommended_prep": int(prep_qty),
                    "current_avg_sold": round(avg_forecast, 1),
                    "waste_savings_weekly_cents": waste_savings,
                    "note": (
                        f"Prep {int(prep_qty)} (avg sold: {avg_forecast:.0f}, +10% buffer)"
                        + (f". Save ${waste_savings/100:.0f}/week by matching prep to demand."
                           if waste_savings > 100 else "")
                    ),
                })

            # Inventory order suggestion
            on_hand = p.get("quantity_on_hand", 0)
            lead_time = p.get("lead_time_days", 3)
            if on_hand > 0 and velocity_30d > 0:
                weekly_need = sum(f["predicted_qty"] for f in daily_forecasts)
                safety_stock = velocity_30d * lead_time * 1.5
                reorder_point = velocity_30d * lead_time + safety_stock
                days_until_stockout = on_hand / max(velocity_30d, 0.1)

                if on_hand <= reorder_point:
                    order_qty = max(0, int(weekly_need * 2 - on_hand + safety_stock))
                    inventory_orders.append({
                        "product": name,
                        "on_hand": on_hand,
                        "order_qty": order_qty,
                        "days_until_stockout": round(days_until_stockout, 1),
                        "urgency": "urgent" if days_until_stockout < lead_time else "soon",
                    })

        prep_guides.sort(key=lambda x: x["waste_savings_weekly_cents"], reverse=True)
        total_waste_savings = sum(p["waste_savings_weekly_cents"] for p in prep_guides)

        return {
            "agent_name": self.name,
            "status": "complete",
            "summary": (
                f"Forecasted {len(product_forecasts)} products. "
                f"Prep optimization saves ${total_waste_savings/100:.0f}/week."
            ),
            "product_forecasts": product_forecasts[:20],
            "prep_guides": prep_guides[:15],
            "inventory_orders": inventory_orders,
            "total_waste_savings_weekly_cents": total_waste_savings,
            "forecast_parameters": {
                "seasonal_index": round(seasonal_idx, 2),
                "horizon_days": 7,
            },
            "confidence": 0.6 if len(products) >= 10 else 0.4,
            "data_quality": 0.6,
            "insights": [
                {
                    "type": "inventory",
                    "title": f"Prep optimization: save ${total_waste_savings/100:.0f}/week",
                    "detail": f"Match prep quantities to demand across {len(prep_guides)} products",
                    "data_quality": 0.6,
                }
            ],
            "recommendations": [
                {
                    "action": "Implement daily prep guides based on per-product forecasts",
                    "impact_cents": total_waste_savings * 4,
                    "effort": "low",
                },
            ] + ([{
                "action": f"Order {inventory_orders[0]['product']} ({inventory_orders[0]['order_qty']} units) — {inventory_orders[0]['days_until_stockout']:.0f} days to stockout",
                "impact_cents": 0,
                "effort": "low",
            }] if inventory_orders else []),
        }
