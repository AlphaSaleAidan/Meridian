from .base import IndustryAnalyzer, register


@register
class BarNightclubAnalyzer(IndustryAnalyzer):
    vertical = "bar"
    label = "Bar / Nightclub"

    def get_kpis(self) -> list[str]:
        return ["revenue", "avg_ticket", "pour_cost_pct", "tip_rate", "peak_hour_revenue"]

    def get_peak_hours(self) -> list[int]:
        return [17, 18, 19, 20, 21, 22, 23]

    def analyze_revenue(self, data: dict) -> dict:
        adjustments = []
        tip_rate = data.get("tip_rate_pct", 0)
        if tip_rate < 18:
            adjustments.append({
                "type": "tip_optimization",
                "detail": f"Avg tip rate {tip_rate:.1f}% below 18% benchmark",
                "recommendation": "Review POS tip prompt percentages — set defaults to 18/20/25%",
            })
        return {"industry_context": self.vertical, "adjustments": adjustments}

    def analyze_products(self, data: dict) -> dict:
        adjustments = []
        pour_cost = data.get("pour_cost_pct", 0)
        if pour_cost > 25:
            adjustments.append({
                "type": "pour_cost_control",
                "detail": f"Pour cost {pour_cost:.1f}% above 25% target",
                "recommendation": "Audit pour sizes, check for overpouring, review supplier pricing",
            })
        return {"industry_context": self.vertical, "adjustments": adjustments}

    def analyze_patterns(self, data: dict) -> dict:
        adjustments = []
        early_week = data.get("mon_tue_wed_revenue_share_pct", 0)
        if early_week < 20:
            adjustments.append({
                "type": "slow_nights",
                "detail": f"Mon-Wed drives only {early_week:.0f}% of weekly revenue",
                "recommendation": "Introduce themed nights (trivia, karaoke, happy hour specials) early in the week",
            })
        return {"industry_context": self.vertical, "adjustments": adjustments}

    def calculate_money_left(self, data: dict) -> dict:
        return {"industry_context": self.vertical, "adjustments": []}
