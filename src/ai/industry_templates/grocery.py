from .base import IndustryAnalyzer, register


@register
class GroceryAnalyzer(IndustryAnalyzer):
    vertical = "grocery"
    label = "Grocery / Market"

    def get_kpis(self) -> list[str]:
        return [
            "avg_basket_cents", "items_per_transaction", "perishable_waste_pct",
            "private_label_mix_pct", "sales_per_sqft", "inventory_turnover",
            "shrinkage_pct", "checkout_speed_items_per_min",
        ]

    def get_peak_hours(self) -> list[int]:
        return [10, 11, 12, 16, 17, 18]

    def analyze_revenue(self, data: dict) -> dict:
        adjustments = []
        basket = data.get("avg_ticket_cents", 0)
        benchmark = self.benchmarks.get("avg_ticket_cents")
        if benchmark and basket < benchmark * 0.85:
            adjustments.append({
                "type": "basket_size",
                "detail": f"Avg basket ${basket/100:.2f} below grocery benchmark ${benchmark/100:.2f}",
                "recommendation": "Add impulse displays at endcaps and checkout — target $2-5 add-ons per visit",
            })

        items_per_txn = data.get("items_per_transaction", 0)
        if items_per_txn and items_per_txn < 12:
            adjustments.append({
                "type": "trip_depth",
                "detail": f"Avg {items_per_txn:.1f} items per trip (target: 15+)",
                "recommendation": "Cross-merchandise complementary items — pasta near sauce, chips near salsa",
            })

        return {"industry_context": self.vertical, "adjustments": adjustments}

    def analyze_products(self, data: dict) -> dict:
        adjustments = []
        products = data.get("products", [])

        private_label = [p for p in products if p.get("is_private_label", False)]
        total_rev = sum(p.get("revenue_cents", 0) for p in products) or 1
        pl_rev = sum(p.get("revenue_cents", 0) for p in private_label)
        pl_share = pl_rev / total_rev

        if pl_share < 0.20:
            adjustments.append({
                "type": "private_label_mix",
                "detail": f"Private label is {pl_share:.0%} of revenue (target: 25%+)",
                "recommendation": "Expand store-brand offerings in top categories — 10-15pt higher margin than national brands",
            })

        perishable = [p for p in products if p.get("category", "").lower() in ("produce", "dairy", "meat", "bakery", "deli")]
        perishable_waste = data.get("perishable_waste_pct", 0)
        if perishable_waste > 5:
            adjustments.append({
                "type": "perishable_waste",
                "detail": f"Perishable waste at {perishable_waste:.1f}% (target: 3-4%)",
                "recommendation": "Implement markdown schedule: 30% off at day-2, 50% off at day-3, donate at day-4",
            })

        return {"industry_context": self.vertical, "adjustments": adjustments}

    def analyze_patterns(self, data: dict) -> dict:
        adjustments = []

        weekend_share = data.get("weekend_revenue_share_pct", 0)
        if weekend_share and weekend_share > 45:
            adjustments.append({
                "type": "weekend_heavy",
                "detail": f"Weekend drives {weekend_share:.0f}% of revenue — midweek is underperforming",
                "recommendation": "Run midweek specials (Wed double-points, Tue senior discount) to flatten traffic",
            })

        checkout_speed = data.get("checkout_speed_items_per_min", 0)
        if checkout_speed and checkout_speed < 18:
            adjustments.append({
                "type": "checkout_throughput",
                "detail": f"Checkout speed {checkout_speed:.0f} items/min (target: 20+)",
                "recommendation": "Train cashiers on scan technique, add self-checkout for small baskets (<15 items)",
            })

        evening_share = data.get("evening_revenue_share_pct", 0)
        if evening_share and evening_share > 35:
            adjustments.append({
                "type": "evening_opportunity",
                "detail": f"Evening shoppers drive {evening_share:.0f}% — likely meal-prep focused",
                "recommendation": "Expand prepared meals and meal-kit sections for dinner convenience shoppers",
            })

        return {"industry_context": self.vertical, "adjustments": adjustments}

    def calculate_money_left(self, data: dict) -> dict:
        adjustments = []

        # Markdown optimization
        waste_pct = data.get("perishable_waste_pct", 0)
        daily_rev = data.get("avg_daily_revenue_cents", 0)
        if waste_pct > 4 and daily_rev > 0:
            perishable_share = data.get("perishable_revenue_share_pct", 40) / 100
            savings = int(daily_rev * perishable_share * (waste_pct - 3) / 100 * 30)
            adjustments.append({
                "type": "markdown_optimization",
                "detail": f"Reducing waste from {waste_pct:.1f}% to 3% saves ${savings/100:.0f}/month",
                "potential_monthly_cents": savings,
                "recommendation": "Dynamic markdown pricing on perishables — use sell-by date to auto-discount",
            })

        # Shelf space ROI
        low_turn_skus = data.get("low_turnover_sku_count", 0)
        total_skus = data.get("total_sku_count", 1) or 1
        if low_turn_skus / total_skus > 0.20:
            adjustments.append({
                "type": "shelf_space_roi",
                "detail": f"{low_turn_skus} SKUs ({low_turn_skus/total_skus:.0%}) below minimum turnover threshold",
                "recommendation": "Replace bottom-turning SKUs with proven sellers or new private-label — each foot of shelf earns rent",
            })

        # Checkout speed improvement
        avg_wait = data.get("avg_checkout_wait_seconds", 0)
        if avg_wait > 180:
            adjustments.append({
                "type": "checkout_speed",
                "detail": f"Avg checkout wait {avg_wait/60:.1f} minutes (target: <2 min)",
                "recommendation": "Add express lane or self-checkout — long waits cause cart abandonment and lost trips",
            })

        return {"industry_context": self.vertical, "adjustments": adjustments}
