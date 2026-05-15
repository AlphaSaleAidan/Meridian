from .base import IndustryAnalyzer, register


@register
class AutoRepairAnalyzer(IndustryAnalyzer):
    vertical = "auto_repair"
    label = "Auto Repair Shop"

    def get_kpis(self) -> list[str]:
        return [
            "labor_utilization_rate", "parts_margin_pct", "avg_repair_order_cents",
            "bay_efficiency", "comeback_rate", "declined_service_pct",
            "hours_per_ro", "effective_labor_rate",
        ]

    def get_peak_hours(self) -> list[int]:
        return [8, 9, 10, 11, 12, 13, 14, 15, 16]

    def analyze_revenue(self, data: dict) -> dict:
        adjustments = []
        avg_ro = data.get("avg_repair_order_cents", 0)
        benchmark = self.benchmarks.get("avg_ticket_cents")
        if benchmark and avg_ro < benchmark * 0.8:
            adjustments.append({
                "type": "repair_order_value",
                "detail": f"Avg repair order ${avg_ro/100:.2f} below benchmark ${benchmark/100:.2f}",
                "recommendation": "Perform thorough multi-point inspections — present findings with photo documentation",
            })

        labor_rate = data.get("effective_labor_rate_cents", 0)
        if labor_rate and labor_rate < 12000:
            adjustments.append({
                "type": "labor_rate",
                "detail": f"Effective labor rate ${labor_rate/100:.2f}/hr (target: $120+/hr)",
                "recommendation": "Review posted rate vs effective rate — reduce discounting and unbilled time",
            })

        return {"industry_context": self.vertical, "adjustments": adjustments}

    def analyze_products(self, data: dict) -> dict:
        adjustments = []
        parts_margin = data.get("parts_margin_pct", 0)
        if parts_margin and parts_margin < 45:
            adjustments.append({
                "type": "parts_margin",
                "detail": f"Parts margin at {parts_margin:.0f}% (target: 50%+)",
                "recommendation": "Review parts matrix — apply tiered markup (higher % on lower-cost parts)",
            })

        products = data.get("products", [])
        services = [p for p in products if p.get("category", "").lower() in ("service", "labor")]
        parts = [p for p in products if p.get("category", "").lower() in ("parts", "part")]
        if services and parts:
            labor_rev = sum(p.get("revenue_cents", 0) for p in services)
            parts_rev = sum(p.get("revenue_cents", 0) for p in parts)
            total = labor_rev + parts_rev or 1
            labor_share = labor_rev / total
            if labor_share < 0.45:
                adjustments.append({
                    "type": "labor_parts_mix",
                    "detail": f"Labor is only {labor_share:.0%} of revenue (target: 50%+ for profitability)",
                    "recommendation": "Bill all diagnostic and inspection time — labor is your highest-margin line",
                })

        return {"industry_context": self.vertical, "adjustments": adjustments}

    def analyze_patterns(self, data: dict) -> dict:
        adjustments = []
        bay_util = data.get("bay_utilization_pct", 0)
        if bay_util and bay_util < 70:
            adjustments.append({
                "type": "bay_efficiency",
                "detail": f"Bay utilization at {bay_util:.0f}% (target: 80%+)",
                "recommendation": "Improve scheduling — stagger appointments to minimize empty-bay gaps",
            })

        monday_share = data.get("monday_revenue_share_pct", 0)
        friday_share = data.get("friday_revenue_share_pct", 0)
        if monday_share and monday_share > 25:
            adjustments.append({
                "type": "monday_surge",
                "detail": f"Monday is {monday_share:.0f}% of weekly revenue — likely causing backlog",
                "recommendation": "Offer Tue-Thu appointment incentives to flatten the week",
            })
        if friday_share and friday_share < 15:
            adjustments.append({
                "type": "friday_dropoff",
                "detail": f"Friday only {friday_share:.0f}% of weekly revenue",
                "recommendation": "Promote quick services (oil change, tire rotation) as Friday specials",
            })

        return {"industry_context": self.vertical, "adjustments": adjustments}

    def calculate_money_left(self, data: dict) -> dict:
        adjustments = []

        # Declined service follow-up
        declined_pct = data.get("declined_service_pct", 0)
        avg_ro = data.get("avg_repair_order_cents", 35000)
        monthly_ros = data.get("monthly_repair_orders", 0)
        if declined_pct > 20 and monthly_ros > 0:
            potential = int(monthly_ros * (declined_pct / 100) * avg_ro * 0.3)
            adjustments.append({
                "type": "declined_service_followup",
                "detail": f"{declined_pct:.0f}% of recommended services declined — recovering 30% adds ${potential/100:.0f}/mo",
                "potential_monthly_cents": potential,
                "recommendation": "Automated 30/60/90-day follow-up texts for declined services with photos",
            })

        # Preventive maintenance upsell
        pm_share = data.get("preventive_maintenance_share_pct", 0)
        if pm_share < 25:
            adjustments.append({
                "type": "pm_upsell",
                "detail": f"Preventive maintenance is only {pm_share:.0f}% of revenue (target: 30%+)",
                "recommendation": "Build a mileage-based maintenance menu — send reminders tied to last service date",
            })

        # Parts markup optimization
        low_margin_parts = data.get("parts_below_40_margin_pct", 0)
        if low_margin_parts > 30:
            adjustments.append({
                "type": "parts_matrix",
                "detail": f"{low_margin_parts:.0f}% of parts sold below 40% margin",
                "recommendation": "Implement tiered parts matrix: 70% markup on <$10, 55% on $10-50, 45% on $50+",
            })

        return {"industry_context": self.vertical, "adjustments": adjustments}
