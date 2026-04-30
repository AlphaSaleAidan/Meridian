from .base import BaseAlert, AlertSeverity

class StockoutAlert(BaseAlert):
    name = "stockout_predictor"
    description = "Predicts imminent stockouts based on burn rate"
    cooldown_hours = 12

    async def evaluate(self) -> list[dict]:
        inventory = getattr(self.ctx, "inventory", []) or []
        inv_output = self.agent_outputs.get("inventory_intel", {})

        if not inventory:
            return self.no_alerts()

        inv_data = inv_output.get("data", {})
        reorder_alerts = inv_data.get("reorder_alerts", [])

        alerts = []
        for item in inventory:
            on_hand = item.get("quantity_on_hand", 0)
            name = item.get("product_name", "Unknown item")

            # Calculate burn rate from sold quantity and days
            qty_sold = item.get("quantity_sold", 0)
            days = getattr(self.ctx, "analysis_days", 30)
            burn_rate = qty_sold / max(days, 1)

            if burn_rate <= 0:
                continue

            days_to_stockout = on_hand / burn_rate
            lead_time = item.get("lead_time_days", 3)
            price = item.get("price_cents", 0) or item.get("avg_selling_price_cents", 0)

            if days_to_stockout < 2:
                lost_rev = int(burn_rate * price * 3)
                alerts.append(self.fire(
                    AlertSeverity.URGENT,
                    f"{name} runs out TOMORROW at current sell rate",
                    f"Only {on_hand} units left, selling ~{burn_rate:.1f}/day. "
                    f"Estimated lost revenue if stockout: ${lost_rev / 100:.0f}.",
                    metric_value=days_to_stockout,
                    threshold=2.0,
                    impact_cents=lost_rev,
                    metadata={"product_name": name, "on_hand": on_hand, "burn_rate": round(burn_rate, 2)},
                ))
            elif days_to_stockout < lead_time * 1.5:
                lost_rev = int(burn_rate * price * max(lead_time - days_to_stockout + 1, 1))
                alerts.append(self.fire(
                    AlertSeverity.WARNING,
                    f"Reorder {name} now — runs out in {days_to_stockout:.0f} days",
                    f"{on_hand} units left, selling ~{burn_rate:.1f}/day. "
                    f"Restocking takes ~{lead_time} days. Order today to avoid stockout.",
                    metric_value=days_to_stockout,
                    threshold=lead_time * 1.5,
                    impact_cents=lost_rev,
                    metadata={"product_name": name, "on_hand": on_hand, "lead_time": lead_time},
                ))

        return alerts
