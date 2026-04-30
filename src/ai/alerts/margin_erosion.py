from .base import BaseAlert, AlertSeverity

class MarginErosionAlert(BaseAlert):
    name = "margin_erosion"
    description = "Warns when margins drop vs 30-day average"
    cooldown_hours = 48

    async def evaluate(self) -> list[dict]:
        pricing_output = self.agent_outputs.get("pricing_power", {})
        products = getattr(self.ctx, "product_performance", []) or []
        txns = getattr(self.ctx, "transactions", []) or []

        if not products and not txns:
            return self.no_alerts()

        alerts = []

        # Check overall margin drift from pricing agent
        pricing_data = pricing_output.get("data", {})
        if pricing_data:
            # Look for margin metrics in the output
            margin_drift = pricing_data.get("margin_drift_pct", None)
            if margin_drift is not None and margin_drift < -5.0:
                alerts.append(self.fire(
                    AlertSeverity.WARNING,
                    f"Margins dropped {abs(margin_drift):.1f}% this week",
                    f"7-day avg margin is {abs(margin_drift):.1f}% below your 30-day average. "
                    f"Check: supplier price increases, more discounting, or product mix "
                    f"shifting to low-margin items.",
                    metric_value=margin_drift,
                    threshold=-5.0,
                ))

        # Check individual top-volume products for margin drops
        if products:
            sorted_prods = sorted(products, key=lambda p: p.get("quantity_sold", 0), reverse=True)
            for p in sorted_prods[:20]:
                cost = p.get("cost_cents", 0)
                price = p.get("price_cents", 0)
                if cost and price and cost > 0:
                    current_margin = (price - cost) / price * 100
                    prev_margin = p.get("prev_margin_pct")
                    if prev_margin and current_margin < prev_margin * 0.9:
                        alerts.append(self.fire(
                            AlertSeverity.WARNING,
                            f"{p.get('name', 'Item')} margin dropped to {current_margin:.0f}%",
                            f"Was {prev_margin:.0f}%, now {current_margin:.0f}%. "
                            f"Check supplier costs or pricing for this item.",
                            metric_value=current_margin,
                            threshold=prev_margin * 0.9,
                            metadata={"product_name": p.get("name"), "product_id": p.get("id")},
                        ))

        return alerts
