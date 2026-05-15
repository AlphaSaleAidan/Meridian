from .base import IndustryAnalyzer, register


@register
class BreweryAnalyzer(IndustryAnalyzer):
    vertical = "brewery"
    label = "Brewery / Taproom"

    def get_kpis(self) -> list[str]:
        return [
            "pints_per_visit", "draft_vs_packaged_mix", "food_attach_rate",
            "event_revenue_pct", "avg_tab", "revenue_per_tap_line",
            "cogs_per_pint", "repeat_visit_rate",
        ]

    def get_peak_hours(self) -> list[int]:
        return [16, 17, 18, 19, 20]

    def analyze_revenue(self, data: dict) -> dict:
        adjustments = []
        avg_tab = data.get("avg_ticket_cents", 0)
        benchmark = self.benchmarks.get("avg_ticket_cents")
        if benchmark and avg_tab < benchmark * 0.85:
            adjustments.append({
                "type": "tab_value",
                "detail": f"Avg tab ${avg_tab/100:.2f} below taproom benchmark ${benchmark/100:.2f}",
                "recommendation": "Offer tasting flights to encourage exploration — flights convert to full pours",
            })

        pints_per_visit = data.get("pints_per_visit", 0)
        if pints_per_visit and pints_per_visit < 2.0:
            adjustments.append({
                "type": "consumption_depth",
                "detail": f"Avg {pints_per_visit:.1f} pints per visit (target: 2.5+)",
                "recommendation": "Extend dwell time with board games, live music, or trivia nights",
            })

        return {"industry_context": self.vertical, "adjustments": adjustments}

    def analyze_products(self, data: dict) -> dict:
        adjustments = []
        products = data.get("products", [])

        draft_items = [p for p in products if p.get("category", "").lower() in ("draft", "beer", "pint", "flight")]
        packaged = [p for p in products if p.get("category", "").lower() in ("can", "bottle", "crowler", "growler", "packaged")]
        food = [p for p in products if p.get("category", "").lower() in ("food", "snack", "kitchen")]

        total_bev_rev = sum(p.get("revenue_cents", 0) for p in draft_items + packaged) or 1
        draft_rev = sum(p.get("revenue_cents", 0) for p in draft_items)
        draft_share = draft_rev / total_bev_rev

        if draft_share < 0.60:
            adjustments.append({
                "type": "draft_mix",
                "detail": f"Draft is {draft_share:.0%} of beverage revenue (target: 70%+)",
                "recommendation": "Draft margins are 75-80% — incentivize on-premise pours over packaged sales",
            })

        total_rev = sum(p.get("revenue_cents", 0) for p in products) or 1
        food_rev = sum(p.get("revenue_cents", 0) for p in food)
        food_attach = food_rev / total_rev
        if food_attach < 0.20:
            adjustments.append({
                "type": "food_attach",
                "detail": f"Food is {food_attach:.0%} of revenue (target: 25%+)",
                "recommendation": "Add simple shareable plates — pretzels, nachos, flatbreads pair naturally with beer",
            })

        return {"industry_context": self.vertical, "adjustments": adjustments}

    def analyze_patterns(self, data: dict) -> dict:
        adjustments = []

        thu_sat_share = data.get("thu_sat_revenue_share_pct", 0)
        if thu_sat_share and thu_sat_share > 60:
            adjustments.append({
                "type": "weekend_concentration",
                "detail": f"Thu-Sat drives {thu_sat_share:.0f}% of revenue",
                "recommendation": "Build midweek programming — industry night Mon, trivia Tue, mug club Wed",
            })

        afternoon_share = data.get("afternoon_revenue_share_pct", 0)
        if afternoon_share and afternoon_share < 15:
            adjustments.append({
                "type": "afternoon_gap",
                "detail": f"Pre-5pm traffic is only {afternoon_share:.0f}% of revenue",
                "recommendation": "Target remote workers with 'coworking taproom' — Wi-Fi, coffee, transition to beer at 4pm",
            })

        return {"industry_context": self.vertical, "adjustments": adjustments}

    def calculate_money_left(self, data: dict) -> dict:
        adjustments = []

        # Tap rotation optimization
        tap_count = data.get("active_tap_count", 0)
        bottom_tap_share = data.get("bottom_25pct_tap_revenue_share", 0)
        if tap_count > 8 and bottom_tap_share < 5:
            adjustments.append({
                "type": "tap_rotation",
                "detail": f"Bottom 25% of taps contribute only {bottom_tap_share:.0f}% of draft revenue",
                "recommendation": "Rotate slow taps weekly — replace with seasonal or collab brews to drive discovery",
            })

        # Food pairing upsell
        food_attach = data.get("food_attach_rate_pct", 0)
        avg_tab = data.get("avg_ticket_cents", 2500)
        daily_visitors = data.get("avg_daily_visitors", 0)
        if food_attach < 25 and daily_visitors > 0:
            avg_food_spend = data.get("avg_food_spend_cents", 1200)
            potential = int(daily_visitors * (0.25 - food_attach / 100) * avg_food_spend * 30)
            adjustments.append({
                "type": "food_pairing",
                "detail": f"Food attach at {food_attach:.0f}% — lifting to 25% = ${potential/100:.0f}/month",
                "potential_monthly_cents": potential,
                "recommendation": "Add beer-and-food pairing suggestions on tap list — 'pairs with our smoked porter'",
            })

        # Event/private booking fill rate
        event_util = data.get("event_space_utilization_pct", 0)
        if event_util < 40:
            adjustments.append({
                "type": "event_fill",
                "detail": f"Event space booked {event_util:.0f}% of available slots (target: 50%+)",
                "recommendation": "List on event platforms, offer brewery tour + tasting packages for corporate groups",
            })

        return {"industry_context": self.vertical, "adjustments": adjustments}
