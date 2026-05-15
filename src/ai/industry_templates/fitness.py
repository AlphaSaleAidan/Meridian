from .base import IndustryAnalyzer, register


@register
class FitnessAnalyzer(IndustryAnalyzer):
    vertical = "fitness"
    label = "Gym / Fitness Studio"

    def get_kpis(self) -> list[str]:
        return [
            "revenue_per_member", "retention_rate", "class_fill_rate",
            "ancillary_revenue_pct", "pt_conversion_rate", "avg_member_visits_per_month",
            "new_member_rate", "retail_attach_rate",
        ]

    def get_peak_hours(self) -> list[int]:
        return [6, 7, 17, 18]

    def analyze_revenue(self, data: dict) -> dict:
        adjustments = []
        rev_per_member = data.get("revenue_per_member_cents", 0)
        benchmark = self.benchmarks.get("avg_ticket_cents")

        if rev_per_member and rev_per_member < 5000:
            adjustments.append({
                "type": "member_value",
                "detail": f"Revenue per member ${rev_per_member/100:.2f}/mo (target: $55+/mo)",
                "recommendation": "Introduce tiered memberships — premium tier with classes, towels, guest passes",
            })

        ancillary_pct = data.get("ancillary_revenue_pct", 0)
        if ancillary_pct < 20:
            adjustments.append({
                "type": "ancillary_gap",
                "detail": f"Non-dues revenue is only {ancillary_pct:.0f}% (target: 25%+)",
                "recommendation": "Grow personal training, retail, smoothie bar, and locker rental revenue streams",
            })

        return {"industry_context": self.vertical, "adjustments": adjustments}

    def analyze_products(self, data: dict) -> dict:
        adjustments = []
        products = data.get("products", [])

        pt_items = [p for p in products if "personal" in p.get("name", "").lower() or "training" in p.get("category", "").lower()]
        retail_items = [p for p in products if p.get("category", "").lower() in ("retail", "merchandise", "supplement", "drink")]

        pt_rev = sum(p.get("revenue_cents", 0) for p in pt_items)
        total_rev = sum(p.get("revenue_cents", 0) for p in products) or 1
        pt_share = pt_rev / total_rev

        if pt_share < 0.15:
            adjustments.append({
                "type": "pt_underpenetration",
                "detail": f"Personal training is only {pt_share:.0%} of revenue (target: 20%+)",
                "recommendation": "Offer free intro PT session to every new member — 40% convert to paid packages",
            })

        retail_rev = sum(p.get("revenue_cents", 0) for p in retail_items)
        retail_margin = data.get("retail_margin_pct", 0)
        if retail_items and retail_margin < 50:
            adjustments.append({
                "type": "retail_margin",
                "detail": f"Retail margin at {retail_margin:.0f}% (target: 55%+)",
                "recommendation": "Shift to private-label supplements and branded merchandise for higher margins",
            })

        return {"industry_context": self.vertical, "adjustments": adjustments}

    def analyze_patterns(self, data: dict) -> dict:
        adjustments = []

        morning_util = data.get("morning_capacity_pct", 0)
        evening_util = data.get("evening_capacity_pct", 0)

        if evening_util and evening_util > 90:
            adjustments.append({
                "type": "peak_overcrowding",
                "detail": f"Evening capacity at {evening_util:.0f}% — overcrowding causes churn",
                "recommendation": "Add popular classes at 5:30 AM and lunch to spread peak load",
            })

        if morning_util and morning_util < 40:
            adjustments.append({
                "type": "morning_underuse",
                "detail": f"Morning capacity only {morning_util:.0f}%",
                "recommendation": "Target retirees and remote workers with mid-morning programming",
            })

        class_fill = data.get("class_fill_rate_pct", 0)
        if class_fill and class_fill < 65:
            adjustments.append({
                "type": "class_fill",
                "detail": f"Average class fill rate {class_fill:.0f}% (target: 75%+)",
                "recommendation": "Consolidate underperforming time slots — fewer classes at higher capacity",
            })

        return {"industry_context": self.vertical, "adjustments": adjustments}

    def calculate_money_left(self, data: dict) -> dict:
        adjustments = []

        # Member upsell to premium tier
        basic_members = data.get("basic_tier_member_count", 0)
        premium_delta = data.get("premium_tier_delta_cents", 2000)
        if basic_members > 100:
            potential = int(basic_members * 0.15 * premium_delta * 12)
            adjustments.append({
                "type": "tier_upsell",
                "detail": f"Upgrading 15% of {basic_members} basic members = ${potential/100:.0f}/year",
                "potential_annual_cents": potential,
                "recommendation": "Run 30-day premium trial for basic members — 15% convert permanently",
            })

        # Personal training conversion
        pt_rate = data.get("pt_conversion_rate_pct", 0)
        active_members = data.get("active_member_count", 0)
        avg_pt_package = data.get("avg_pt_package_cents", 30000)
        if pt_rate < 10 and active_members > 0:
            potential = int(active_members * 0.05 * avg_pt_package)
            adjustments.append({
                "type": "pt_conversion",
                "detail": f"PT conversion at {pt_rate:.0f}% — each 5% lift = ${potential/100:.0f}/mo",
                "potential_monthly_cents": potential,
                "recommendation": "Offer complimentary fitness assessment — leads to PT conversation",
            })

        # Retail attach rate
        retail_attach = data.get("retail_attach_rate_pct", 0)
        if retail_attach < 8:
            adjustments.append({
                "type": "retail_attach",
                "detail": f"Retail attach rate {retail_attach:.0f}% (target: 12%+)",
                "recommendation": "Place grab-and-go drinks and protein bars at front desk checkout",
            })

        return {"industry_context": self.vertical, "adjustments": adjustments}
