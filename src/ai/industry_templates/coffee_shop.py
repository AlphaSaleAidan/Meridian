from .base import IndustryAnalyzer, register


@register
class CoffeeShopAnalyzer(IndustryAnalyzer):
    vertical = "coffee_shop"
    label = "Coffee Shop / Café"

    def get_kpis(self) -> list[str]:
        return [
            "revenue", "avg_ticket", "cost_per_cup", "food_attach_rate",
            "cups_per_labor_hour", "tip_rate", "avg_wait_time_proxy",
        ]

    def get_peak_hours(self) -> list[int]:
        return [7, 8, 9, 12, 13]

    def analyze_revenue(self, data: dict) -> dict:
        adjustments = []
        avg_ticket = data.get("avg_ticket_cents", 0)
        benchmark = self.benchmarks.get("avg_ticket_cents")
        if benchmark and avg_ticket < benchmark * 0.8:
            adjustments.append({
                "type": "upsell_opportunity",
                "detail": f"Avg ticket ${avg_ticket/100:.2f} below café benchmark ${benchmark/100:.2f}",
                "recommendation": "Train baristas on food pairing and drink size upsells",
            })

        morning_share = data.get("morning_revenue_share_pct", 0)
        if morning_share and morning_share < 55:
            adjustments.append({
                "type": "daypart_imbalance",
                "detail": f"Morning only {morning_share:.0f}% of revenue (benchmark: 65%)",
                "recommendation": "Strengthen morning marketing — loyalty app push for AM specials",
            })

        return {"industry_context": self.vertical, "adjustments": adjustments}

    def analyze_products(self, data: dict) -> dict:
        adjustments = []
        products = data.get("products", [])

        food_items = [p for p in products if p.get("category", "").lower() in ("food", "pastry", "bakery", "sandwich")]
        coffee_items = [p for p in products if p.get("category", "").lower() in ("coffee", "espresso", "beverage", "drink")]

        if coffee_items and food_items:
            coffee_txns = sum(p.get("quantity_sold", 0) for p in coffee_items)
            food_txns = sum(p.get("quantity_sold", 0) for p in food_items)
            if coffee_txns > 0:
                attach_rate = food_txns / coffee_txns
                if attach_rate < 0.25:
                    adjustments.append({
                        "type": "food_attach",
                        "detail": f"Food attach rate {attach_rate:.0%} (target: 30%+)",
                        "recommendation": "Display pastries at register, offer combo pricing",
                        "metric_value": round(attach_rate, 3),
                    })

        for p in coffee_items[:5]:
            cogs = p.get("cogs_cents", 0)
            price = p.get("avg_price_cents", 0)
            if cogs > 0 and price > 0:
                margin = (price - cogs) / price
                if margin < 0.70:
                    adjustments.append({
                        "type": "cost_per_cup",
                        "detail": f"{p.get('name', '?')}: {margin:.0%} margin (target: 75%+)",
                        "recommendation": "Review bean cost or portion size — coffee should be 75%+ margin",
                    })

        return {"industry_context": self.vertical, "adjustments": adjustments}

    def analyze_patterns(self, data: dict) -> dict:
        adjustments = []

        peak_share = data.get("peak_hour_revenue_share_pct", 0)
        if peak_share and peak_share < 35:
            adjustments.append({
                "type": "peak_underperformance",
                "detail": f"Peak hours only {peak_share:.0f}% of revenue (café benchmark: 45%)",
                "recommendation": "Speed up morning service — every minute saved adds throughput",
            })

        peak_txns = data.get("peak_hour_txns", 0)
        if peak_txns and peak_txns > 40:
            adjustments.append({
                "type": "throughput_constraint",
                "detail": f"Peak hour hits {peak_txns} transactions — likely causing wait times",
                "recommendation": "Add mobile ordering or batch prep for top 5 drinks",
            })

        return {"industry_context": self.vertical, "adjustments": adjustments}

    def calculate_money_left(self, data: dict) -> dict:
        adjustments = []

        attach_rate = data.get("food_attach_rate", 0)
        daily_rev = data.get("avg_daily_revenue_cents", 0)
        if 0 < attach_rate < 0.3 and daily_rev > 0:
            potential = int(daily_rev * (0.30 - attach_rate) * 0.5 * 30)
            adjustments.append({
                "type": "food_attach_opportunity",
                "detail": f"Raising food attach from {attach_rate:.0%} to 30% = ${potential/100:.0f}/month",
                "potential_monthly_cents": potential,
            })

        avg_ticket = data.get("avg_ticket_cents", 0)
        if avg_ticket > 0 and avg_ticket < 600:
            upsell_potential = int((600 - avg_ticket) * 0.2 * data.get("avg_daily_transactions", 50) * 30)
            adjustments.append({
                "type": "size_upsell",
                "detail": f"Size upsell on 20% of orders = ${upsell_potential/100:.0f}/month",
                "potential_monthly_cents": upsell_potential,
            })

        return {"industry_context": self.vertical, "adjustments": adjustments}
