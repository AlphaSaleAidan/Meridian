from .base import IndustryAnalyzer, register


@register
class FoodTruckAnalyzer(IndustryAnalyzer):
    vertical = "food_truck"
    label = "Food Truck"

    def get_kpis(self) -> list[str]:
        return [
            "revenue_per_hour", "location_performance_index", "weather_impact_pct",
            "social_media_conversion", "avg_ticket", "orders_per_hour",
            "food_cost_pct", "catering_revenue_pct",
        ]

    def get_peak_hours(self) -> list[int]:
        return [11, 12, 13]

    def analyze_revenue(self, data: dict) -> dict:
        adjustments = []
        rev_per_hour = data.get("revenue_per_hour_cents", 0)
        if rev_per_hour and rev_per_hour < 20000:
            adjustments.append({
                "type": "hourly_revenue",
                "detail": f"Revenue per service hour ${rev_per_hour/100:.2f} (target: $250+/hr)",
                "recommendation": "Focus on high-traffic locations only — one great spot beats three mediocre ones",
            })

        avg_ticket = data.get("avg_ticket_cents", 0)
        benchmark = self.benchmarks.get("avg_ticket_cents")
        if benchmark and avg_ticket < benchmark * 0.85:
            adjustments.append({
                "type": "ticket_value",
                "detail": f"Avg ticket ${avg_ticket/100:.2f} below food truck benchmark ${benchmark/100:.2f}",
                "recommendation": "Add a drink or side to every combo — 'make it a meal' for $3 more",
            })

        return {"industry_context": self.vertical, "adjustments": adjustments}

    def analyze_products(self, data: dict) -> dict:
        adjustments = []
        products = data.get("products", [])
        menu_size = len(products)

        if menu_size > 12:
            adjustments.append({
                "type": "menu_complexity",
                "detail": f"Menu has {menu_size} items — too many slows service and increases waste",
                "recommendation": "Trim to 6-8 core items — food trucks win on speed and consistency, not variety",
            })

        food_cost = data.get("food_cost_pct", 0)
        if food_cost and food_cost > 35:
            adjustments.append({
                "type": "food_cost",
                "detail": f"Food cost at {food_cost:.0f}% (target: 28-32%)",
                "recommendation": "Reduce protein portions slightly, negotiate bulk pricing, pre-prep more off-site",
            })

        top_item_share = data.get("top_item_revenue_share_pct", 0)
        if top_item_share and top_item_share > 50:
            adjustments.append({
                "type": "signature_dependency",
                "detail": f"Top item is {top_item_share:.0f}% of revenue — great for branding, risky for supply issues",
                "recommendation": "Develop a strong #2 item to reduce single-item dependency — feature it on social media",
            })

        return {"industry_context": self.vertical, "adjustments": adjustments}

    def analyze_patterns(self, data: dict) -> dict:
        adjustments = []

        # Location performance
        locations = data.get("locations", [])
        if len(locations) > 1:
            rev_by_loc = sorted(locations, key=lambda l: l.get("avg_revenue_cents", 0), reverse=True)
            best = rev_by_loc[0].get("avg_revenue_cents", 0)
            worst = rev_by_loc[-1].get("avg_revenue_cents", 0)
            if best > 0 and worst < best * 0.4:
                adjustments.append({
                    "type": "location_variance",
                    "detail": f"Best location ${best/100:.0f} vs worst ${worst/100:.0f} — 60%+ variance",
                    "recommendation": f"Drop underperforming spots — double down on top locations or find similar ones nearby",
                })

        weather_impact = data.get("rain_day_revenue_drop_pct", 0)
        if weather_impact and weather_impact > 40:
            adjustments.append({
                "type": "weather_vulnerability",
                "detail": f"Rain days see {weather_impact:.0f}% revenue drop",
                "recommendation": "Build catering and pre-order channels as weather-proof revenue — or find covered locations",
            })

        return {"industry_context": self.vertical, "adjustments": adjustments}

    def calculate_money_left(self, data: dict) -> dict:
        adjustments = []

        # Location optimization
        operating_days = data.get("operating_days_per_week", 0)
        if operating_days and operating_days < 5:
            avg_daily_rev = data.get("avg_daily_revenue_cents", 0)
            potential = int(avg_daily_rev * (5 - operating_days) * 4)
            adjustments.append({
                "type": "operating_days",
                "detail": f"Operating {operating_days} days/week — adding days = ${potential/100:.0f}/month",
                "potential_monthly_cents": potential,
                "recommendation": "Add weekend event days (farmers markets, breweries, festivals) for incremental revenue",
            })

        # Menu simplification savings
        menu_items = data.get("menu_item_count", 0)
        waste_pct = data.get("waste_pct", 0)
        if menu_items > 10 and waste_pct > 8:
            daily_cost = data.get("daily_food_cost_cents", 0)
            savings = int(daily_cost * (waste_pct - 5) / 100 * 30)
            adjustments.append({
                "type": "menu_simplification",
                "detail": f"{menu_items} items causing {waste_pct:.0f}% waste — simplify to save ${savings/100:.0f}/mo",
                "potential_monthly_cents": savings,
                "recommendation": "Cut menu to top 8 sellers — reduces waste, prep time, and ingredient inventory",
            })

        # Catering conversion
        catering_pct = data.get("catering_revenue_pct", 0)
        monthly_rev = data.get("avg_monthly_revenue_cents", 0)
        if catering_pct < 15 and monthly_rev > 0:
            potential = int(monthly_rev * 0.20)
            adjustments.append({
                "type": "catering_conversion",
                "detail": f"Catering is {catering_pct:.0f}% of revenue (target: 20%+)",
                "potential_monthly_cents": potential,
                "recommendation": "Create a catering menu (min 20 people) — hand out cards at every service, post on social",
            })

        # Social media
        social_conversion = data.get("social_media_conversion_pct", 0)
        if social_conversion < 5:
            adjustments.append({
                "type": "social_conversion",
                "detail": f"Social media conversion at {social_conversion:.0f}% (target: 8%+)",
                "recommendation": "Post daily location + menu photo — tag the neighborhood, use location-based hashtags",
            })

        return {"industry_context": self.vertical, "adjustments": adjustments}
