from .base import IndustryAnalyzer, register


@register
class RestaurantAnalyzer(IndustryAnalyzer):
    vertical = "restaurant"
    label = "Full-Service Restaurant"

    def get_kpis(self) -> list[str]:
        return ["revenue", "avg_ticket", "food_cost_pct", "table_turnover", "tip_rate", "labor_cost_pct"]

    def get_peak_hours(self) -> list[int]:
        return [12, 13, 18, 19, 20]

    def analyze_revenue(self, data: dict) -> dict:
        adjustments = []
        avg_ticket = data.get("avg_ticket_cents", 0)
        benchmark = self.benchmarks.get("avg_ticket_cents")
        if benchmark and avg_ticket < benchmark * 0.8:
            adjustments.append({
                "type": "upsell_opportunity",
                "detail": f"Avg ticket ${avg_ticket/100:.2f} is below restaurant benchmark ${benchmark/100:.2f}",
                "recommendation": "Train staff on appetizer/dessert upsells and drink pairings",
            })
        return {"industry_context": self.vertical, "adjustments": adjustments}

    def analyze_products(self, data: dict) -> dict:
        adjustments = []
        products = data.get("products", [])
        low_margin = [p for p in products if p.get("margin_pct", 100) < 40]
        if low_margin:
            adjustments.append({
                "type": "menu_engineering",
                "detail": f"{len(low_margin)} items below 40% food margin",
                "recommendation": "Review portion sizes and supplier pricing for low-margin dishes",
            })
        return {"industry_context": self.vertical, "adjustments": adjustments}

    def analyze_patterns(self, data: dict) -> dict:
        adjustments = []
        peak_share = data.get("peak_hour_revenue_share_pct", 0)
        if peak_share < 50:
            adjustments.append({
                "type": "daypart_gap",
                "detail": f"Peak hours drive only {peak_share:.0f}% of revenue (benchmark: 55%)",
                "recommendation": "Consider happy hour or lunch specials to boost off-peak traffic",
            })
        return {"industry_context": self.vertical, "adjustments": adjustments}

    def calculate_money_left(self, data: dict) -> dict:
        adjustments = []
        waste_pct = data.get("waste_pct", 0)
        if waste_pct > 5:
            daily_rev = data.get("avg_daily_revenue_cents", 0)
            savings = int(daily_rev * (waste_pct - 4) / 100)
            adjustments.append({
                "type": "waste_reduction",
                "detail": f"Food waste at {waste_pct:.1f}% (target: 4%)",
                "potential_daily_savings_cents": savings,
            })
        return {"industry_context": self.vertical, "adjustments": adjustments}
