from .base import IndustryAnalyzer, register


@register
class PizzaAnalyzer(IndustryAnalyzer):
    vertical = "pizza"
    label = "Pizzeria"

    def get_kpis(self) -> list[str]:
        return [
            "delivery_vs_dinein_mix", "avg_pizza_size", "topping_upsell_rate",
            "delivery_radius_efficiency", "avg_ticket", "orders_per_hour",
            "food_cost_pct", "delivery_time_minutes",
        ]

    def get_peak_hours(self) -> list[int]:
        return [17, 18, 19, 20]

    def analyze_revenue(self, data: dict) -> dict:
        adjustments = []
        avg_ticket = data.get("avg_ticket_cents", 0)
        benchmark = self.benchmarks.get("avg_ticket_cents")
        if benchmark and avg_ticket < benchmark * 0.85:
            adjustments.append({
                "type": "ticket_value",
                "detail": f"Avg ticket ${avg_ticket/100:.2f} below pizzeria benchmark ${benchmark/100:.2f}",
                "recommendation": "Default combos to include breadsticks or drink — 'complete your meal' at checkout",
            })

        delivery_share = data.get("delivery_revenue_share_pct", 0)
        dinein_share = data.get("dinein_revenue_share_pct", 0)
        if delivery_share and delivery_share > 70:
            adjustments.append({
                "type": "channel_imbalance",
                "detail": f"Delivery is {delivery_share:.0f}% of revenue — heavy third-party fee exposure",
                "recommendation": "Build direct ordering (website/app) to recapture 15-30% third-party commission",
            })

        return {"industry_context": self.vertical, "adjustments": adjustments}

    def analyze_products(self, data: dict) -> dict:
        adjustments = []
        products = data.get("products", [])

        pizzas = [p for p in products if p.get("category", "").lower() in ("pizza", "pie")]
        sides = [p for p in products if p.get("category", "").lower() in ("side", "appetizer", "breadstick", "wing", "salad")]

        total_rev = sum(p.get("revenue_cents", 0) for p in products) or 1
        sides_rev = sum(p.get("revenue_cents", 0) for p in sides)
        sides_share = sides_rev / total_rev

        if sides_share < 0.20:
            adjustments.append({
                "type": "sides_attach",
                "detail": f"Sides/appetizers are {sides_share:.0%} of revenue (target: 25%+)",
                "recommendation": "Auto-suggest wings or garlic knots on every pizza order — sides are 65-70% margin",
            })

        topping_upsell = data.get("topping_upsell_rate_pct", 0)
        if topping_upsell and topping_upsell < 30:
            adjustments.append({
                "type": "topping_upsell",
                "detail": f"Only {topping_upsell:.0f}% of orders add premium toppings (target: 35%+)",
                "recommendation": "Feature specialty pizzas with premium toppings — customers pay $2-4 more per premium pie",
            })

        food_cost = data.get("food_cost_pct", 0)
        if food_cost and food_cost > 32:
            adjustments.append({
                "type": "food_cost",
                "detail": f"Food cost at {food_cost:.0f}% (pizza target: 28-30%)",
                "recommendation": "Audit cheese portioning — cheese is 40% of pizza food cost, 0.5oz variance compounds fast",
            })

        return {"industry_context": self.vertical, "adjustments": adjustments}

    def analyze_patterns(self, data: dict) -> dict:
        adjustments = []

        dinner_share = data.get("dinner_revenue_share_pct", 0)
        lunch_share = data.get("lunch_revenue_share_pct", 0)
        if lunch_share and lunch_share < 20:
            adjustments.append({
                "type": "lunch_gap",
                "detail": f"Lunch is only {lunch_share:.0f}% of revenue (target: 25%+)",
                "recommendation": "Launch lunch special — personal pizza + drink for $8.99, ready in 10 minutes",
            })

        weekend_share = data.get("weekend_revenue_share_pct", 0)
        if weekend_share and weekend_share > 50:
            adjustments.append({
                "type": "weekend_peak",
                "detail": f"Weekends drive {weekend_share:.0f}% — midweek needs attention",
                "recommendation": "Run weeknight deals: Monday BOGO, Taco Tuesday (calzones), Wing Wednesday",
            })

        peak_delivery_time = data.get("peak_delivery_time_minutes", 0)
        if peak_delivery_time and peak_delivery_time > 45:
            adjustments.append({
                "type": "delivery_speed",
                "detail": f"Peak delivery time {peak_delivery_time:.0f} min (target: <35 min)",
                "recommendation": "Tighten delivery radius during peak — better to be fast in 3 miles than slow in 5",
            })

        return {"industry_context": self.vertical, "adjustments": adjustments}

    def calculate_money_left(self, data: dict) -> dict:
        adjustments = []

        # Delivery zone optimization
        far_delivery_pct = data.get("deliveries_beyond_3mi_pct", 0)
        if far_delivery_pct and far_delivery_pct > 25:
            adjustments.append({
                "type": "delivery_zone",
                "detail": f"{far_delivery_pct:.0f}% of deliveries beyond 3 miles — high cost, slow times, cold pizza",
                "recommendation": "Add delivery fee tiers: free <2mi, $2 at 2-3mi, $4 at 3-5mi — or tighten radius",
            })

        # Combo pricing
        combo_rate = data.get("combo_order_rate_pct", 0)
        avg_ticket = data.get("avg_ticket_cents", 0)
        daily_orders = data.get("avg_daily_orders", 0)
        if combo_rate < 30 and daily_orders > 0:
            upsell_value = 400  # $4 avg combo upsell
            potential = int(daily_orders * (0.30 - combo_rate / 100) * upsell_value * 30)
            adjustments.append({
                "type": "combo_pricing",
                "detail": f"Combo rate {combo_rate:.0f}% (target: 35%+) — ${potential/100:.0f}/mo opportunity",
                "potential_monthly_cents": potential,
                "recommendation": "Pre-build 3 combo tiers (solo, duo, family) — default suggestion on every order",
            })

        # Lunch push
        lunch_rev_share = data.get("lunch_revenue_share_pct", 0)
        daily_rev = data.get("avg_daily_revenue_cents", 0)
        if lunch_rev_share < 20 and daily_rev > 0:
            potential = int(daily_rev * 0.10 * 30)
            adjustments.append({
                "type": "lunch_push",
                "detail": f"Lunch is {lunch_rev_share:.0f}% — adding a lunch program could add ${potential/100:.0f}/mo",
                "potential_monthly_cents": potential,
                "recommendation": "Offer a lunch slice + drink combo, advertise to nearby offices and schools",
            })

        return {"industry_context": self.vertical, "adjustments": adjustments}
