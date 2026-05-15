from .base import IndustryAnalyzer, register


@register
class SpaAnalyzer(IndustryAnalyzer):
    vertical = "spa"
    label = "Spa / Wellness Center"

    def get_kpis(self) -> list[str]:
        return [
            "therapist_utilization_pct", "retail_attach_rate", "rebooking_rate",
            "package_conversion_pct", "avg_service_ticket", "revenue_per_treatment_room",
            "membership_revenue_pct", "client_retention_rate",
        ]

    def get_peak_hours(self) -> list[int]:
        return [10, 11, 12, 13, 14, 15]

    def analyze_revenue(self, data: dict) -> dict:
        adjustments = []
        avg_ticket = data.get("avg_ticket_cents", 0)
        benchmark = self.benchmarks.get("avg_ticket_cents")
        if benchmark and avg_ticket < benchmark * 0.85:
            adjustments.append({
                "type": "service_value",
                "detail": f"Avg service ticket ${avg_ticket/100:.2f} below spa benchmark ${benchmark/100:.2f}",
                "recommendation": "Offer upgrade add-ons at booking: hot stones +$20, aromatherapy +$15, scalp massage +$10",
            })

        membership_pct = data.get("membership_revenue_pct", 0)
        if membership_pct < 25:
            adjustments.append({
                "type": "membership_gap",
                "detail": f"Membership revenue is {membership_pct:.0f}% (target: 30%+)",
                "recommendation": "Launch a monthly membership — 1 service/mo + retail discount builds predictable recurring revenue",
            })

        return {"industry_context": self.vertical, "adjustments": adjustments}

    def analyze_products(self, data: dict) -> dict:
        adjustments = []
        products = data.get("products", [])

        services = [p for p in products if p.get("category", "").lower() in ("service", "treatment", "massage", "facial", "body")]
        retail = [p for p in products if p.get("category", "").lower() in ("retail", "product", "skincare", "oil", "merchandise")]

        total_rev = sum(p.get("revenue_cents", 0) for p in products) or 1
        retail_rev = sum(p.get("revenue_cents", 0) for p in retail)
        retail_share = retail_rev / total_rev

        if retail_share < 0.15:
            adjustments.append({
                "type": "retail_mix",
                "detail": f"Retail is {retail_share:.0%} of revenue (target: 20%+)",
                "recommendation": "Recommend take-home products used during treatment — 'this is what I used on your skin today'",
            })

        for s in services[:5]:
            utilization = s.get("utilization_pct", 0)
            if utilization and utilization < 50:
                adjustments.append({
                    "type": "service_utilization",
                    "detail": f"{s.get('name', '?')}: {utilization:.0f}% utilization (target: 65%+)",
                    "recommendation": f"Consider bundling {s.get('name', 'this service')} into packages or offering at off-peak discount",
                })

        return {"industry_context": self.vertical, "adjustments": adjustments}

    def analyze_patterns(self, data: dict) -> dict:
        adjustments = []

        weekend_share = data.get("weekend_revenue_share_pct", 0)
        if weekend_share and weekend_share > 50:
            adjustments.append({
                "type": "weekend_concentration",
                "detail": f"Weekends drive {weekend_share:.0f}% of revenue — weekdays underutilized",
                "recommendation": "Offer weekday pricing tiers: Mon-Wed 15% off, build corporate wellness partnerships for midweek",
            })

        therapist_util = data.get("therapist_utilization_pct", 0)
        if therapist_util and therapist_util < 60:
            adjustments.append({
                "type": "utilization_gap",
                "detail": f"Therapist utilization at {therapist_util:.0f}% (target: 70%+)",
                "recommendation": "Stagger therapist schedules to match demand — avoid full staffing during low-traffic hours",
            })

        morning_bookings = data.get("morning_booking_pct", 0)
        if morning_bookings and morning_bookings < 20:
            adjustments.append({
                "type": "morning_gap",
                "detail": f"Morning (before 11am) is only {morning_bookings:.0f}% of bookings",
                "recommendation": "Offer 'early bird' massage pricing for 9-10am slots — attracts before-work crowd",
            })

        return {"industry_context": self.vertical, "adjustments": adjustments}

    def calculate_money_left(self, data: dict) -> dict:
        adjustments = []

        # Rebooking at checkout
        rebook_rate = data.get("rebooking_rate_pct", 0)
        monthly_clients = data.get("monthly_unique_clients", 0)
        avg_ticket = data.get("avg_ticket_cents", 10000)
        if rebook_rate < 50 and monthly_clients > 0:
            additional_visits = int(monthly_clients * (0.50 - rebook_rate / 100))
            potential = additional_visits * avg_ticket
            adjustments.append({
                "type": "rebooking_gap",
                "detail": f"Rebooking rate {rebook_rate:.0f}% (target: 50%+) — {additional_visits} missed rebookings/mo",
                "potential_monthly_cents": potential,
                "recommendation": "Train front desk to rebook every client at checkout — offer $10 off for booking today",
            })

        # Retail product attach
        retail_attach = data.get("retail_attach_rate_pct", 0)
        avg_product_value = data.get("avg_retail_item_cents", 3500)
        if retail_attach < 20 and monthly_clients > 0:
            potential = int(monthly_clients * (0.20 - retail_attach / 100) * avg_product_value)
            adjustments.append({
                "type": "retail_attach",
                "detail": f"Retail attach {retail_attach:.0f}% (target: 25%+) — ${potential/100:.0f}/mo opportunity",
                "potential_monthly_cents": potential,
                "recommendation": "Place products used during service at checkout with 'therapist recommended' cards",
            })

        # Membership conversion
        membership_rate = data.get("membership_conversion_pct", 0)
        if membership_rate < 15:
            adjustments.append({
                "type": "membership_conversion",
                "detail": f"Only {membership_rate:.0f}% of clients on membership (target: 20%+)",
                "recommendation": "Offer first-month membership at single-service price — demonstrate ongoing value",
            })

        # Package upsell
        package_rate = data.get("package_conversion_pct", 0)
        if package_rate < 25:
            adjustments.append({
                "type": "package_upsell",
                "detail": f"Package conversion at {package_rate:.0f}% (target: 30%+)",
                "recommendation": "Offer 3-pack and 6-pack bundles at 10-15% discount — locks in future visits",
            })

        return {"industry_context": self.vertical, "adjustments": adjustments}
