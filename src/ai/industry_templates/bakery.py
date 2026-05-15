from .base import IndustryAnalyzer, register


@register
class BakeryAnalyzer(IndustryAnalyzer):
    vertical = "bakery"
    label = "Bakery"

    def get_kpis(self) -> list[str]:
        return [
            "morning_rush_capture_pct", "waste_pct", "pre_order_rate",
            "custom_order_margin_pct", "avg_ticket", "items_per_transaction",
            "wholesale_revenue_pct", "repeat_customer_rate",
        ]

    def get_peak_hours(self) -> list[int]:
        return [6, 7, 8, 9]

    def analyze_revenue(self, data: dict) -> dict:
        adjustments = []
        avg_ticket = data.get("avg_ticket_cents", 0)
        benchmark = self.benchmarks.get("avg_ticket_cents")
        if benchmark and avg_ticket < benchmark * 0.85:
            adjustments.append({
                "type": "ticket_building",
                "detail": f"Avg ticket ${avg_ticket/100:.2f} below bakery benchmark ${benchmark/100:.2f}",
                "recommendation": "Bundle coffee + pastry combos at $1 discount — drives ticket up while feeling like a deal",
            })

        morning_share = data.get("morning_revenue_share_pct", 0)
        if morning_share and morning_share < 55:
            adjustments.append({
                "type": "morning_capture",
                "detail": f"Morning (6-10am) is only {morning_share:.0f}% of revenue (target: 60%+)",
                "recommendation": "Bakeries win or lose before 10am — focus on speed, pre-orders, and grab-and-go display",
            })

        return {"industry_context": self.vertical, "adjustments": adjustments}

    def analyze_products(self, data: dict) -> dict:
        adjustments = []
        products = data.get("products", [])

        custom_orders = [p for p in products if p.get("is_custom", False) or "custom" in p.get("name", "").lower() or "cake" in p.get("category", "").lower()]
        total_rev = sum(p.get("revenue_cents", 0) for p in products) or 1
        custom_rev = sum(p.get("revenue_cents", 0) for p in custom_orders)
        custom_share = custom_rev / total_rev

        if custom_share < 0.20:
            adjustments.append({
                "type": "custom_order_mix",
                "detail": f"Custom/special orders are {custom_share:.0%} of revenue (target: 25%+)",
                "recommendation": "Promote custom cakes and event catering — highest margin line at 60-70%",
            })

        daily_items = [p for p in products if p.get("category", "").lower() in ("bread", "pastry", "muffin", "croissant", "danish")]
        for p in daily_items[:5]:
            margin = p.get("margin_pct", 100)
            if margin < 55:
                adjustments.append({
                    "type": "daily_item_margin",
                    "detail": f"{p.get('name', '?')}: {margin:.0f}% margin (target: 60%+)",
                    "recommendation": "Review ingredient costs and portion — small reductions in butter/filling compound across volume",
                })

        return {"industry_context": self.vertical, "adjustments": adjustments}

    def analyze_patterns(self, data: dict) -> dict:
        adjustments = []

        afternoon_share = data.get("afternoon_revenue_share_pct", 0)
        if afternoon_share and afternoon_share < 15:
            adjustments.append({
                "type": "afternoon_dead_zone",
                "detail": f"Afternoon (1-5pm) is only {afternoon_share:.0f}% of revenue",
                "recommendation": "Add lunch sandwiches on fresh bread, or afternoon tea/coffee specials to drive 2nd daypart",
            })

        weekend_share = data.get("weekend_revenue_share_pct", 0)
        if weekend_share and weekend_share > 50:
            adjustments.append({
                "type": "weekend_dependent",
                "detail": f"Weekends are {weekend_share:.0f}% of revenue — weekday traffic needs work",
                "recommendation": "Start a weekday bread subscription or office delivery program for consistent midweek volume",
            })

        return {"industry_context": self.vertical, "adjustments": adjustments}

    def calculate_money_left(self, data: dict) -> dict:
        adjustments = []

        # Day-old markdown strategy
        waste_pct = data.get("waste_pct", 0)
        daily_production_cost = data.get("daily_production_cost_cents", 0)
        if waste_pct > 8 and daily_production_cost > 0:
            recoverable = int(daily_production_cost * (waste_pct - 5) / 100 * 0.5 * 30)
            adjustments.append({
                "type": "dayold_markdown",
                "detail": f"Waste at {waste_pct:.0f}% (target: 5%) — recovering half via day-old sales = ${recoverable/100:.0f}/mo",
                "potential_monthly_cents": recoverable,
                "recommendation": "Sell day-old at 50% off in a dedicated bin — partner with Too Good To Go app",
            })

        # Custom order pricing
        custom_margin = data.get("custom_order_margin_pct", 0)
        if custom_margin and custom_margin < 55:
            adjustments.append({
                "type": "custom_pricing",
                "detail": f"Custom order margin {custom_margin:.0f}% (target: 60%+)",
                "recommendation": "Price custom cakes by tier (simple/moderate/elaborate) — customers anchor to middle tier",
            })

        # Wholesale channel
        wholesale_pct = data.get("wholesale_revenue_pct", 0)
        if wholesale_pct < 10:
            adjustments.append({
                "type": "wholesale_channel",
                "detail": f"Wholesale is only {wholesale_pct:.0f}% of revenue (opportunity: 15-20%)",
                "recommendation": "Supply local cafes and restaurants with bread/pastries — fills production capacity at lower margin but consistent volume",
            })

        # Pre-order rate
        preorder_rate = data.get("pre_order_rate_pct", 0)
        if preorder_rate < 15:
            adjustments.append({
                "type": "preorder_growth",
                "detail": f"Pre-orders are {preorder_rate:.0f}% of sales (target: 20%+)",
                "recommendation": "Enable online pre-ordering with pickup time slots — reduces waste and guarantees morning sales",
            })

        return {"industry_context": self.vertical, "adjustments": adjustments}
