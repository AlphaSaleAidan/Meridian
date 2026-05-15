from .base import IndustryAnalyzer, register


@register
class CannabisAnalyzer(IndustryAnalyzer):
    vertical = "cannabis"
    label = "Cannabis Dispensary"

    def get_kpis(self) -> list[str]:
        return [
            "revenue_per_sqft", "avg_basket", "compliance_rate",
            "flower_velocity", "edible_velocity", "concentrate_velocity",
            "accessory_attach_rate", "customer_frequency",
        ]

    def get_peak_hours(self) -> list[int]:
        return [11, 12, 13, 16, 17, 18, 19]

    def analyze_revenue(self, data: dict) -> dict:
        adjustments = []
        avg_ticket = data.get("avg_ticket_cents", 0)
        benchmark = self.benchmarks.get("avg_ticket_cents")
        if benchmark and avg_ticket < benchmark * 0.85:
            adjustments.append({
                "type": "basket_building",
                "detail": f"Avg basket ${avg_ticket/100:.2f} below dispensary benchmark ${benchmark/100:.2f}",
                "recommendation": "Train budtenders on accessory add-ons (papers, lighters, stash jars) at register",
            })

        rev_per_sqft = data.get("revenue_per_sqft_cents", 0)
        if rev_per_sqft and rev_per_sqft < 8000:
            adjustments.append({
                "type": "space_efficiency",
                "detail": f"Revenue per sq ft ${rev_per_sqft/100:.2f} (target: $80+)",
                "recommendation": "Optimize floor layout — high-velocity flower near entrance, accessories at checkout",
            })

        return {"industry_context": self.vertical, "adjustments": adjustments}

    def analyze_products(self, data: dict) -> dict:
        adjustments = []
        products = data.get("products", [])

        categories = {}
        for p in products:
            cat = p.get("category", "other").lower()
            categories.setdefault(cat, []).append(p)

        flower_share = sum(p.get("revenue_cents", 0) for p in categories.get("flower", []))
        total_rev = sum(p.get("revenue_cents", 0) for p in products) or 1
        flower_pct = flower_share / total_rev

        if flower_pct > 0.75:
            adjustments.append({
                "type": "category_concentration",
                "detail": f"Flower is {flower_pct:.0%} of revenue — heavy single-category dependency",
                "recommendation": "Expand edible and concentrate displays; offer sample-size concentrates for trial",
            })

        for cat_name in ("edible", "concentrate"):
            items = categories.get(cat_name, [])
            slow = [p for p in items if p.get("velocity_score", 1) < 0.2]
            if len(slow) > len(items) * 0.4 and items:
                adjustments.append({
                    "type": f"{cat_name}_velocity",
                    "detail": f"{len(slow)}/{len(items)} {cat_name} SKUs are slow movers",
                    "recommendation": f"Rotate bottom {cat_name} SKUs monthly — replace with trending brands",
                })

        return {"industry_context": self.vertical, "adjustments": adjustments}

    def analyze_patterns(self, data: dict) -> dict:
        adjustments = []

        weekend_share = data.get("weekend_revenue_share_pct", 0)
        if weekend_share > 45:
            adjustments.append({
                "type": "weekend_concentration",
                "detail": f"Weekends drive {weekend_share:.0f}% of revenue",
                "recommendation": "Staff up Fri-Sun, run midweek promotions (Terp Tuesday, Wax Wednesday)",
            })

        lunch_rush = data.get("lunch_hour_txns", 0)
        afternoon_rush = data.get("afternoon_hour_txns", 0)
        if lunch_rush and afternoon_rush and lunch_rush > afternoon_rush * 1.5:
            adjustments.append({
                "type": "afternoon_gap",
                "detail": f"Lunch rush {lunch_rush} txns vs afternoon {afternoon_rush} — big dropoff",
                "recommendation": "Promote afternoon happy-hour pricing on accessories or edibles",
            })

        return {"industry_context": self.vertical, "adjustments": adjustments}

    def calculate_money_left(self, data: dict) -> dict:
        adjustments = []

        # Strain portfolio optimization
        unique_strains = data.get("unique_strain_count", 0)
        top_strain_share = data.get("top_10_strain_revenue_share_pct", 0)
        if unique_strains > 50 and top_strain_share > 60:
            adjustments.append({
                "type": "strain_rationalization",
                "detail": f"Top 10 strains drive {top_strain_share:.0f}% of flower revenue across {unique_strains} SKUs",
                "recommendation": "Cut bottom 30% of strains — reinvest shelf space in proven sellers and new drops",
            })

        # Price elasticity by THC%
        high_thc_margin = data.get("high_thc_margin_pct", 0)
        if high_thc_margin and high_thc_margin < 35:
            adjustments.append({
                "type": "thc_pricing",
                "detail": f"High-THC products at {high_thc_margin:.0f}% margin (target: 40%+)",
                "recommendation": "Premium THC% commands premium pricing — test $2-5 upcharge on 30%+ THC strains",
            })

        # Accessory upsell
        accessory_attach = data.get("accessory_attach_rate_pct", 0)
        daily_txns = data.get("avg_daily_transactions", 0)
        avg_accessory = data.get("avg_accessory_price_cents", 500)
        if accessory_attach < 15 and daily_txns > 0:
            potential = int((0.15 - accessory_attach / 100) * daily_txns * avg_accessory * 30)
            adjustments.append({
                "type": "accessory_upsell",
                "detail": f"Accessory attach {accessory_attach:.0f}% (target: 15%+)",
                "potential_monthly_cents": potential,
                "recommendation": "Place impulse accessories at checkout — grinders, lighters, rolling trays",
            })

        return {"industry_context": self.vertical, "adjustments": adjustments}
