from .base import BaseAgent


class CashFlowForecastAgent(BaseAgent):
    name = "cashflow_forecast"
    description = "30-day cash flow projection with danger zone detection"
    tier = 5

    async def analyze(self) -> dict:
        avail = self.get_data_availability()
        agent_outputs = getattr(self.ctx, "agent_outputs", {})
        daily = getattr(self.ctx, "daily_revenue", []) or []

        if len(daily) < 7:
            return self._insufficient_data("At least 7 days of revenue data")

        cashflow_output = agent_outputs.get("cash_flow", {})
        forecast_output = agent_outputs.get("forecaster", {})
        seasonality_output = agent_outputs.get("seasonality", {})

        if avail.is_full and forecast_output.get("status") == "complete":
            path = "full"
            confidence = min(0.75, avail.quality_score)
        elif avail.is_partial:
            path = "partial"
            confidence = min(0.55, avail.quality_score)
        else:
            path = "minimal"
            confidence = min(0.35, avail.quality_score)

        insights = []
        recommendations = []

        sorted_days = sorted(daily, key=lambda d: d.get("date", ""))
        daily_revenues = [d.get("revenue_cents", 0) for d in sorted_days]
        avg_daily_revenue = sum(daily_revenues) / max(len(daily_revenues), 1)

        # Net cash ratio: revenue after estimated expenses
        cf_data = cashflow_output.get("data", {})
        processing_fee_pct = cf_data.get("processing_fee_pct", 2.6)
        net_ratio = (100 - processing_fee_pct) / 100

        # Seasonal indices (day-of-week)
        seasonal_data = seasonality_output.get("data", {})
        dow_effects = seasonal_data.get("day_of_week_effects", {})

        # Get forecast if available
        forecast_data = forecast_output.get("data", {})
        forecast_daily = forecast_data.get("daily_forecast", [])

        # Build 30-day projection
        from datetime import datetime, timedelta
        today = datetime.now()
        projections = []

        for i in range(30):
            day = today + timedelta(days=i)
            dow = day.strftime("%A")

            if path == "full" and i < len(forecast_daily):
                base = forecast_daily[i].get("predicted_cents", int(avg_daily_revenue))
            elif path == "partial":
                # Moving average extrapolation
                window = daily_revenues[-14:] if len(daily_revenues) >= 14 else daily_revenues
                base = sum(window) // max(len(window), 1)
            else:
                # Minimal: use overall average
                base = int(avg_daily_revenue)

            # Apply DOW seasonal adjustment
            dow_idx = dow_effects.get(dow, 1.0) if isinstance(dow_effects, dict) else 1.0
            if isinstance(dow_idx, dict):
                dow_idx = dow_idx.get("index", 1.0)
            adjusted = int(base * float(dow_idx))

            # Estimate expenses as % of revenue (industry heuristic: 85-92% of revenue goes to costs)
            expense_ratio = self.get_benchmark("cogs_pct") or 35
            labor_ratio = self.get_benchmark("labor_cost_pct") or 28
            total_expense_pct = min(92, expense_ratio + labor_ratio + 15)  # COGS + labor + overhead
            est_expenses = int(adjusted * total_expense_pct / 100)

            net = int(adjusted * net_ratio) - est_expenses
            projections.append({
                "date": day.strftime("%Y-%m-%d"),
                "day_of_week": dow,
                "projected_revenue_cents": adjusted,
                "est_expenses_cents": est_expenses,
                "net_cash_cents": net,
            })

        # Cumulative cash flow
        cumulative = 0
        cumulative_series = []
        danger_zones = []
        for p in projections:
            cumulative += p["net_cash_cents"]
            cumulative_series.append(cumulative)
            if cumulative < 0:
                danger_zones.append(p["date"])

        total_projected_revenue = sum(p["projected_revenue_cents"] for p in projections)
        total_net = sum(p["net_cash_cents"] for p in projections)

        insights.append({
            "type": "cashflow_projection",
            "title": f"30-Day Net Cash: ${total_net / 100:,.0f}",
            "detail": f"Projected revenue ${total_projected_revenue / 100:,.0f} "
                      f"with estimated ${(total_projected_revenue - total_net) / 100:,.0f} in expenses",
            "impact_cents": total_net,
            "estimated": path != "full",
        })

        if danger_zones:
            insights.append({
                "type": "cash_danger_zone",
                "title": f"Cash flow risk: {len(danger_zones)} tight days ahead",
                "detail": f"Cumulative cash turns negative around {danger_zones[0]}. "
                          "Consider timing large purchases after peak revenue days.",
                "impact_cents": abs(min(cumulative_series)),
            })
            recommendations.append({
                "action": f"Avoid large purchases before {danger_zones[0]} — cash gets tight",
                "impact_cents": abs(min(cumulative_series)),
                "effort": "low",
            })

        # Optimal purchase timing: buy after highest-revenue days
        best_days = sorted(projections[:14], key=lambda p: p["projected_revenue_cents"], reverse=True)[:3]
        if best_days:
            recommendations.append({
                "action": f"Schedule inventory purchases after {best_days[0]['day_of_week']}s (highest cash inflow)",
                "impact_cents": 0,
                "effort": "low",
            })

        if path != "full":
            recommendations.append({
                "action": "Connect expense data for precise cash flow tracking",
                "impact": "Replaces estimates with actual expense patterns",
                "effort": "medium",
            })

        score = max(0, min(100, 50 + int(total_net / max(total_projected_revenue, 1) * 200)))

        data = {
            "total_projected_revenue_cents": total_projected_revenue,
            "total_net_cash_cents": total_net,
            "danger_zone_days": danger_zones,
            "daily_projections": projections[:7],  # First week detail
            "cumulative_30d_cents": cumulative,
            "expense_ratio_pct": round(total_expense_pct, 1),
        }

        return self._result(
            summary=f"30-day net cash ${total_net / 100:,.0f} | "
                    f"{len(danger_zones)} danger days" if danger_zones
                    else f"30-day net cash ${total_net / 100:,.0f} | healthy",
            score=score,
            insights=insights,
            recommendations=recommendations,
            data=data,
            confidence=confidence,
            calculation_path=path,
        )
