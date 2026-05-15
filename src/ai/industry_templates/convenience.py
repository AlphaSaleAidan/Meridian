from .base import IndustryAnalyzer, register


@register
class ConvenienceAnalyzer(IndustryAnalyzer):
    vertical = "convenience"
    label = "Convenience Store"

    def get_kpis(self) -> list[str]:
        return [
            "avg_basket_cents", "impulse_purchase_rate", "prepared_food_margin_pct",
            "lottery_tobacco_mix_pct", "transactions_per_day", "sales_per_sqft",
            "shrinkage_pct", "loyalty_capture_rate",
        ]

    def get_peak_hours(self) -> list[int]:
        return [7, 8, 16, 17, 18]

    def analyze_revenue(self, data: dict) -> dict:
        adjustments = []
        basket = data.get("avg_ticket_cents", 0)
        benchmark = self.benchmarks.get("avg_ticket_cents")
        if benchmark and basket < benchmark * 0.85:
            adjustments.append({
                "type": "basket_size",
                "detail": f"Avg basket ${basket/100:.2f} below c-store benchmark ${benchmark/100:.2f}",
                "recommendation": "Add '2 for $X' deals on high-velocity items near register — snacks, drinks, candy",
            })

        txns_per_day = data.get("avg_daily_transactions", 0)
        if txns_per_day and txns_per_day < 200:
            adjustments.append({
                "type": "foot_traffic",
                "detail": f"Avg {txns_per_day:.0f} transactions/day (target: 250+)",
                "recommendation": "Improve curb appeal, add exterior signage for gas prices or coffee — drive-by conversion",
            })

        return {"industry_context": self.vertical, "adjustments": adjustments}

    def analyze_products(self, data: dict) -> dict:
        adjustments = []
        products = data.get("products", [])

        prepared = [p for p in products if p.get("category", "").lower() in ("prepared", "hot food", "deli", "fresh", "foodservice")]
        tobacco = [p for p in products if p.get("category", "").lower() in ("tobacco", "cigarette", "vape", "lottery")]

        total_rev = sum(p.get("revenue_cents", 0) for p in products) or 1
        prepared_rev = sum(p.get("revenue_cents", 0) for p in prepared)
        prepared_share = prepared_rev / total_rev

        if prepared_share < 0.15:
            adjustments.append({
                "type": "prepared_food_mix",
                "detail": f"Prepared food is {prepared_share:.0%} of revenue (target: 20%+)",
                "recommendation": "Expand hot food program — roller grills, pizza, fresh sandwiches yield 50-60% margins",
            })

        tobacco_rev = sum(p.get("revenue_cents", 0) for p in tobacco)
        tobacco_share = tobacco_rev / total_rev
        if tobacco_share > 0.40:
            adjustments.append({
                "type": "tobacco_dependency",
                "detail": f"Tobacco/lottery is {tobacco_share:.0%} of revenue — high dependency on low-margin regulated category",
                "recommendation": "Diversify into higher-margin categories: prepared food, private-label beverages, snacks",
            })

        return {"industry_context": self.vertical, "adjustments": adjustments}

    def analyze_patterns(self, data: dict) -> dict:
        adjustments = []

        morning_share = data.get("morning_revenue_share_pct", 0)
        if morning_share and morning_share > 40:
            adjustments.append({
                "type": "morning_heavy",
                "detail": f"Morning commute drives {morning_share:.0f}% — maximize grab-and-go speed",
                "recommendation": "Pre-stage coffee, pastries, and breakfast sandwiches by 6am — speed is everything for commuters",
            })

        evening_share = data.get("evening_revenue_share_pct", 0)
        if evening_share and evening_share > 35:
            adjustments.append({
                "type": "evening_opportunity",
                "detail": f"Evening drives {evening_share:.0f}% — likely beer/snack runs",
                "recommendation": "Create evening meal-deal bundles — drink + snack + prepared food at one price",
            })

        midday_share = data.get("midday_revenue_share_pct", 0)
        if midday_share and midday_share < 15:
            adjustments.append({
                "type": "midday_gap",
                "detail": f"Midday (11am-2pm) only {midday_share:.0f}% — missing lunch crowd",
                "recommendation": "Add lunch-focused prepared food (hot dogs, sandwiches, salads) with visible exterior signage",
            })

        return {"industry_context": self.vertical, "adjustments": adjustments}

    def calculate_money_left(self, data: dict) -> dict:
        adjustments = []

        # Product placement optimization
        impulse_rate = data.get("impulse_purchase_rate_pct", 0)
        daily_txns = data.get("avg_daily_transactions", 0)
        avg_impulse_value = data.get("avg_impulse_item_cents", 250)
        if impulse_rate < 20 and daily_txns > 0:
            potential = int(daily_txns * (0.20 - impulse_rate / 100) * avg_impulse_value * 30)
            adjustments.append({
                "type": "impulse_placement",
                "detail": f"Impulse rate {impulse_rate:.0f}% (target: 20%+) — ${potential/100:.0f}/mo opportunity",
                "potential_monthly_cents": potential,
                "recommendation": "Redesign register zone — candy, gum, energy shots, phone chargers at eye level",
            })

        # Prepared food expansion
        prepared_margin = data.get("prepared_food_margin_pct", 0)
        prepared_share = data.get("prepared_food_share_pct", 0)
        daily_rev = data.get("avg_daily_revenue_cents", 0)
        if prepared_share < 20 and daily_rev > 0:
            incremental = int(daily_rev * (0.20 - prepared_share / 100) * 0.55 * 30)
            adjustments.append({
                "type": "prepared_food_growth",
                "detail": f"Growing prepared food from {prepared_share:.0f}% to 20% adds ${incremental/100:.0f}/mo in gross profit",
                "potential_monthly_cents": incremental,
                "recommendation": "Start with roller grill and hot coffee — low labor, high margin, drives repeat visits",
            })

        # Loyalty capture
        loyalty_rate = data.get("loyalty_capture_rate_pct", 0)
        if loyalty_rate < 25:
            adjustments.append({
                "type": "loyalty_capture",
                "detail": f"Loyalty capture at {loyalty_rate:.0f}% (target: 30%+)",
                "recommendation": "Offer instant fuel discount or free coffee at signup — c-store loyalty drives 2x visit frequency",
            })

        return {"industry_context": self.vertical, "adjustments": adjustments}
