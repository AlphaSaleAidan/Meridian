from .base import BaseAgent
import math

class InventoryIntelAgent(BaseAgent):
    name = "inventory_intel"
    description = "Days-of-stock, reorder alerts, EOQ model"
    tier = 2

    async def analyze(self) -> dict:
        path, confidence = self._select_path()
        inventory = self.ctx.inventory
        products = self.ctx.product_performance

        # MINIMAL: no inventory data at all
        if path == "minimal" or not inventory:
            if not inventory and path != "minimal":
                return self._insufficient_data("Inventory snapshot data")
            return self._result(
                summary="Insufficient data for inventory analysis",
                score=50,
                insights=[{"type": "no_inventory_data", "detail": "Inventory intelligence requires inventory snapshot data (on-hand quantities)", "estimated": True}],
                recommendations=[{
                    "action": "Connect POS line-item data for precise analysis",
                    "impact": "Improves accuracy from estimated to actual values",
                    "effort": "low",
                }],
                data={"source": "minimal", "inventory_items_available": len(inventory)},
                confidence=confidence,
                calculation_path=path,
            )

        days = max(self.ctx.analysis_days, 1)
        prod_velocity = {p.get("name", ""): p.get("quantity_sold", 0) / days for p in products}

        reorder_alerts = []
        overstock_alerts = []
        dead_inventory = []
        total_dead_value = 0

        items = []
        for inv in inventory:
            name = inv.get("product_name", "")
            on_hand = inv.get("quantity_on_hand", 0)
            velocity = prod_velocity.get(name, 0)

            if velocity > 0:
                days_of_stock = round(on_hand / velocity, 1)
            elif on_hand > 0:
                days_of_stock = 999
            else:
                days_of_stock = 0

            # EOQ: sqrt(2 * annual_demand * order_cost / holding_cost_per_unit)
            annual_demand = velocity * 365
            # Assume $5 order cost and $1/unit/year holding
            eoq = round(math.sqrt(2 * annual_demand * 500 / max(100, 1))) if annual_demand > 0 else 0

            entry = {
                "product": name,
                "quantity_on_hand": on_hand,
                "daily_velocity": round(velocity, 2),
                "days_of_stock": days_of_stock,
                "optimal_reorder_qty": eoq,
            }
            items.append(entry)

            if 0 < days_of_stock <= 7:
                reorder_alerts.append(entry)
            elif days_of_stock > 90:
                overstock_alerts.append(entry)

            if velocity == 0 and on_hand > 0:
                # Estimate value from products list
                price = next((p.get("price_cents", 0) for p in products if p.get("name") == name), 0)
                value = price * on_hand
                total_dead_value += value
                dead_inventory.append({**entry, "estimated_value_cents": value})

        items.sort(key=lambda x: x["days_of_stock"])
        score = max(0, 100 - len(reorder_alerts) * 10 - len(dead_inventory) * 5)

        insights = []
        if reorder_alerts:
            insights.append({"type": "low_stock", "detail": f"{len(reorder_alerts)} products at risk of stockout within 7 days", "estimated": path != "full"})
        if dead_inventory:
            insights.append({"type": "dead_inventory", "detail": f"{len(dead_inventory)} products with zero velocity — ${total_dead_value/100:,.0f} tied up", "estimated": path != "full"})

        recommendations = []
        if reorder_alerts:
            recommendations.append({"action": f"Reorder {len(reorder_alerts)} products immediately: {', '.join(r['product'] for r in reorder_alerts[:3])}", "impact_cents": 0})
        if dead_inventory:
            recommendations.append({"action": f"Liquidate ${total_dead_value/100:,.0f} of dead inventory through markdowns or bundles", "impact_cents": total_dead_value // 2})

        if path == "partial":
            recommendations.append({"action": "Connect POS line-item data for precise analysis", "impact": "Improves accuracy from estimated to actual values", "effort": "low"})

        return self._result(
            summary=f"{len(reorder_alerts)} reorder alerts, {len(overstock_alerts)} overstock, ${total_dead_value/100:,.0f} dead inventory",
            score=score,
            insights=insights,
            recommendations=recommendations,
            data={
                "inventory_items": items[:30],
                "reorder_alerts": reorder_alerts,
                "overstock_alerts": overstock_alerts,
                "dead_inventory": dead_inventory,
                "dead_inventory_value_cents": total_dead_value,
            },
            confidence=confidence,
            calculation_path=path,
        )
