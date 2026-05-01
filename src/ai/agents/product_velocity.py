from .base import BaseAgent
from collections import defaultdict

class ProductVelocityAgent(BaseAgent):
    name = "product_velocity"
    description = "Product velocity ranking, rising stars, dead stock"
    tier = 2

    async def analyze(self) -> dict:
        path, confidence = self._select_path()
        products = self.ctx.product_performance

        # MINIMAL: skip — not enough product data for meaningful velocity
        if path == "minimal" or len(products) < 3:
            if len(products) < 3 and path != "minimal":
                return self._insufficient_data("At least 3 products with sales data")
            return self._result(
                summary="Insufficient product data for velocity analysis",
                score=50,
                insights=[{"type": "no_product_data", "detail": "Product velocity requires product-level sales data", "estimated": True}],
                recommendations=[{
                    "action": "Connect POS line-item data for precise analysis",
                    "impact": "Improves accuracy from estimated to actual values",
                    "effort": "low",
                }],
                data={"source": "minimal", "product_count": len(products)},
                confidence=confidence,
                calculation_path=path,
            )

        days = max(self.ctx.analysis_days, 1)
        velocity_data = []
        dead_stock = []
        total_revenue = sum(p.get("total_revenue_cents", 0) for p in products)

        for p in products:
            name = p.get("name", "Unknown")
            qty = p.get("quantity_sold", 0)
            rev = p.get("total_revenue_cents", 0)
            daily_velocity = round(qty / days, 2)

            entry = {
                "product": name,
                "quantity_sold": qty,
                "daily_velocity": daily_velocity,
                "revenue_cents": rev,
                "revenue_share_pct": round(rev / max(total_revenue, 1) * 100, 1),
            }

            if qty == 0:
                dead_stock.append({**entry, "days_since_last_sale": days})
            else:
                velocity_data.append(entry)

        velocity_data.sort(key=lambda x: x["daily_velocity"], reverse=True)

        # Rising stars (top 20% by velocity) and fading (bottom 20%)
        n = len(velocity_data)
        top_cut = max(1, n // 5)
        rising_stars = velocity_data[:top_cut]
        fading = [v for v in velocity_data[-top_cut:] if v["daily_velocity"] < 1]

        # Dead stock value: only available with inventory data (FULL path)
        inventory = self.ctx.inventory if path == "full" else []
        dead_stock_value = sum(
            p.get("price_cents", 0) * i.get("quantity_on_hand", 0)
            for p in products for i in inventory
            if p.get("name") == i.get("product_name") and p.get("quantity_sold", 0) == 0
        )

        score = max(0, 100 - len(dead_stock) * 5 - len(fading) * 3)

        insights = []
        if dead_stock:
            insights.append({"type": "dead_stock", "detail": f"{len(dead_stock)} products with zero sales in {days} days", "estimated": path != "full"})
        if rising_stars:
            insights.append({"type": "rising_stars", "detail": f"Top movers: {', '.join(r['product'] for r in rising_stars[:3])}", "estimated": path != "full"})

        recommendations = []
        if dead_stock:
            recommendations.append({"action": f"Clear {len(dead_stock)} dead-stock items — mark down or bundle", "impact_cents": dead_stock_value // 2})
        if fading:
            recommendations.append({"action": f"Investigate {len(fading)} fading products for repositioning", "impact_cents": 0})

        if path == "partial":
            recommendations.append({"action": "Connect POS line-item data for precise analysis", "impact": "Improves accuracy from estimated to actual values", "effort": "low"})

        return self._result(
            summary=f"{len(velocity_data)} active products, {len(dead_stock)} dead stock, top mover: {velocity_data[0]['product'] if velocity_data else 'N/A'}",
            score=score,
            insights=insights,
            recommendations=recommendations,
            data={
                "velocity_ranking": velocity_data[:20],
                "rising_stars": rising_stars,
                "fading_products": fading,
                "dead_stock": dead_stock,
                "dead_stock_value_cents": dead_stock_value,
            },
            confidence=confidence,
            calculation_path=path,
        )
