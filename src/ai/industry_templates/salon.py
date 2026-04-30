from .base import IndustryAnalyzer, register


@register
class SalonAnalyzer(IndustryAnalyzer):
    vertical = "salon"
    label = "Salon / Barbershop"

    def get_kpis(self) -> list[str]:
        return ["revenue", "avg_service_ticket", "rebooking_rate", "product_attach_rate", "utilization_pct"]

    def get_peak_hours(self) -> list[int]:
        return [10, 11, 14, 15, 16]

    def analyze_revenue(self, data: dict) -> dict:
        adjustments = []
        avg_ticket = data.get("avg_ticket_cents", 0)
        benchmark = self.benchmarks.get("avg_ticket_cents")
        if benchmark and avg_ticket < benchmark * 0.8:
            adjustments.append({
                "type": "service_upsell",
                "detail": f"Avg ticket ${avg_ticket/100:.2f} below salon benchmark ${benchmark/100:.2f}",
                "recommendation": "Train staff to suggest add-on services (deep conditioning, styling, scalp treatment)",
            })
        return {"industry_context": self.vertical, "adjustments": adjustments}

    def analyze_products(self, data: dict) -> dict:
        adjustments = []
        product_attach = data.get("product_attach_rate_pct", 0)
        if product_attach < 30:
            adjustments.append({
                "type": "retail_attach",
                "detail": f"Product attach rate {product_attach:.0f}% (target: 30%+)",
                "recommendation": "Display take-home products at stations, recommend products used during service",
            })
        return {"industry_context": self.vertical, "adjustments": adjustments}

    def analyze_patterns(self, data: dict) -> dict:
        adjustments = []
        midweek = data.get("tue_wed_thu_utilization_pct", 0)
        if midweek < 60:
            adjustments.append({
                "type": "midweek_gap",
                "detail": f"Midweek chair utilization only {midweek:.0f}%",
                "recommendation": "Offer 10-15% midweek discount or loyalty points bonus for Tue-Thu bookings",
            })
        return {"industry_context": self.vertical, "adjustments": adjustments}

    def calculate_money_left(self, data: dict) -> dict:
        adjustments = []
        rebook_rate = data.get("rebooking_rate_pct", 0)
        if rebook_rate < 50:
            avg_ticket = data.get("avg_ticket_cents", 4500)
            lost_monthly = int((50 - rebook_rate) / 100 * data.get("monthly_clients", 100) * avg_ticket)
            adjustments.append({
                "type": "rebooking_gap",
                "detail": f"Rebooking rate {rebook_rate:.0f}% (target: 50%+)",
                "potential_monthly_loss_cents": lost_monthly,
            })
        return {"industry_context": self.vertical, "adjustments": adjustments}
