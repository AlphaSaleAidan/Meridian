from .base import IndustryAnalyzer, register


@register
class SmokeShopAnalyzer(IndustryAnalyzer):
    vertical = "smoke_shop"
    label = "Smoke Shop / Tobacco Retail"

    def get_kpis(self) -> list[str]:
        return ["revenue", "avg_ticket", "sku_velocity", "inventory_turnover", "margin_pct"]

    def get_peak_hours(self) -> list[int]:
        return [10, 11, 15, 16, 17, 20, 21]

    def analyze_revenue(self, data: dict) -> dict:
        adjustments = []
        avg_ticket = data.get("avg_ticket_cents", 0)
        benchmark = self.benchmarks.get("avg_ticket_cents")
        if benchmark and avg_ticket < benchmark * 0.85:
            adjustments.append({
                "type": "basket_building",
                "detail": f"Avg ticket ${avg_ticket/100:.2f} below benchmark ${benchmark/100:.2f}",
                "recommendation": "Bundle accessories (lighters, papers, tips) with primary purchases at register",
            })
        return {"industry_context": self.vertical, "adjustments": adjustments}

    def analyze_products(self, data: dict) -> dict:
        adjustments = []
        products = data.get("products", [])
        slow_movers = [p for p in products if p.get("velocity_score", 1) < 0.3]
        if len(slow_movers) > len(products) * 0.3:
            adjustments.append({
                "type": "sku_rationalization",
                "detail": f"{len(slow_movers)} SKUs with low velocity — tying up shelf space",
                "recommendation": "Consider discontinuing bottom 20% SKUs and replacing with trending brands",
            })
        return {"industry_context": self.vertical, "adjustments": adjustments}

    def analyze_patterns(self, data: dict) -> dict:
        adjustments = []
        weekend_share = data.get("weekend_revenue_share_pct", 0)
        if weekend_share > 40:
            adjustments.append({
                "type": "weekend_heavy",
                "detail": f"Weekend drives {weekend_share:.0f}% of revenue",
                "recommendation": "Ensure full inventory restocking by Friday morning",
            })
        return {"industry_context": self.vertical, "adjustments": adjustments}

    def calculate_money_left(self, data: dict) -> dict:
        adjustments = []
        turnover = data.get("inventory_turnover", 0)
        if turnover < 12:
            adjustments.append({
                "type": "slow_inventory",
                "detail": f"Inventory turns {turnover:.1f}x/year (benchmark: 15x)",
                "recommendation": "Reduce order quantities for slow movers, increase for top sellers",
            })
        return {"industry_context": self.vertical, "adjustments": adjustments}
