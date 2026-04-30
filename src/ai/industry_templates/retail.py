from .base import IndustryAnalyzer, register


@register
class RetailAnalyzer(IndustryAnalyzer):
    vertical = "retail"
    label = "Retail Store"

    def get_kpis(self) -> list[str]:
        return ["revenue", "avg_ticket", "units_per_transaction", "inventory_turnover", "shrinkage_pct"]

    def get_peak_hours(self) -> list[int]:
        return [11, 12, 13, 14, 15, 16]

    def analyze_revenue(self, data: dict) -> dict:
        adjustments = []
        upt = data.get("units_per_transaction", 0)
        if upt < 2.0:
            adjustments.append({
                "type": "cross_sell",
                "detail": f"Units per transaction {upt:.1f} — room for cross-selling",
                "recommendation": "Add complementary product displays near checkout",
            })
        return {"industry_context": self.vertical, "adjustments": adjustments}

    def analyze_products(self, data: dict) -> dict:
        adjustments = []
        products = data.get("products", [])
        dead_stock = [p for p in products if p.get("days_since_last_sale", 0) > 60]
        if dead_stock:
            adjustments.append({
                "type": "dead_stock_clearance",
                "detail": f"{len(dead_stock)} products unsold for 60+ days",
                "recommendation": "Mark down by 30-50% or bundle with fast movers",
            })
        return {"industry_context": self.vertical, "adjustments": adjustments}

    def analyze_patterns(self, data: dict) -> dict:
        return {"industry_context": self.vertical, "adjustments": []}

    def calculate_money_left(self, data: dict) -> dict:
        adjustments = []
        shrinkage = data.get("shrinkage_pct", 0)
        if shrinkage > 2.0:
            daily_rev = data.get("avg_daily_revenue_cents", 0)
            loss = int(daily_rev * (shrinkage - 1.6) / 100)
            adjustments.append({
                "type": "shrinkage_control",
                "detail": f"Inventory shrinkage {shrinkage:.1f}% (industry avg: 1.6%)",
                "potential_daily_savings_cents": loss,
            })
        return {"industry_context": self.vertical, "adjustments": adjustments}
