from .base import BaseAgent
from datetime import datetime, timedelta


class ForecasterAgent(BaseAgent):
    name = "forecaster"
    description = "7/30/90-day revenue forecasts with confidence intervals"
    tier = 5

    async def analyze(self) -> dict:
        # ── Phase 1: Data Discovery ──────────────────────────
        avail = self.get_data_availability()
        daily = self.ctx.daily_revenue or []
        agent_outputs = getattr(self.ctx, "agent_outputs", {})

        if len(daily) < 7 and not agent_outputs:
            return self._insufficient_data("At least 7 days of revenue history")

        # ── Phase 2: Path Selection ──────────────────────────
        n = len(daily)
        if avail.is_full and n >= 30:
            calc_path = "full"
        elif avail.has_transactions and n >= 14:
            calc_path = "partial"
        else:
            calc_path = "minimal"

        sorted_days = sorted(daily, key=lambda d: d.get("date", ""))
        values = [d.get("revenue_cents", 0) for d in sorted_days]
        y_mean = sum(values) / max(n, 1)

        # ── Phase 3: Dynamic Calculation ─────────────────────
        today = datetime.now()
        forecasts = {"7_day": [], "30_day": [], "90_day": []}
        slope = 0.0
        std_dev = 0
        error_rate = 0.3  # default

        if calc_path == "full":
            # FULL: linear regression + DOW seasonality + trend momentum
            x_mean = (n - 1) / 2
            num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
            den = sum((i - x_mean) ** 2 for i in range(n))
            slope = num / max(den, 1)

            # Day-of-week seasonality
            dow_totals = [0] * 7
            dow_counts = [0] * 7
            for d in sorted_days:
                try:
                    dt = datetime.fromisoformat(d.get("date", "").replace("Z", "+00:00"))
                    dow = dt.weekday()
                    dow_totals[dow] += d.get("revenue_cents", 0)
                    dow_counts[dow] += 1
                except (ValueError, AttributeError):
                    pass
            dow_avg = [dow_totals[i] // max(dow_counts[i], 1) for i in range(7)]

            # Residual std dev
            residuals = [values[i] - y_mean - slope * (i - x_mean) for i in range(n)]
            variance = sum(r ** 2 for r in residuals) / max(n - 2, 1)
            std_dev = int(variance ** 0.5)

            # Trend momentum: weight recent slope more
            if n >= 14:
                recent = values[-7:]
                r_mean = sum(recent) / 7
                r_x_mean = 3.0
                r_num = sum((i - r_x_mean) * (v - r_mean) for i, v in enumerate(recent))
                r_den = sum((i - r_x_mean) ** 2 for i in range(7))
                recent_slope = r_num / max(r_den, 1)
                slope = slope * 0.4 + recent_slope * 0.6  # momentum-weighted

            error_rate = std_dev / max(y_mean, 1)

            for horizon_key, horizon_days in [("7_day", 7), ("30_day", 30), ("90_day", 90)]:
                if n < horizon_days // 3:
                    continue
                for i in range(1, horizon_days + 1):
                    future = today + timedelta(days=i)
                    dow = future.weekday()
                    base = dow_avg[dow] if dow_avg[dow] > 0 else int(y_mean)
                    predicted = max(0, base + int(slope * i * 0.5))
                    confidence_decay = 0.95 ** (i / 7)
                    lower = max(0, int(predicted * (1 - error_rate * 1.5)))
                    upper = int(predicted * (1 + error_rate * 1.5))
                    if (
                        horizon_key == "7_day"
                        or (horizon_key == "30_day" and i % 7 == 0)
                        or (horizon_key == "90_day" and i % 30 == 0)
                    ):
                        forecasts[horizon_key].append({
                            "date": future.strftime("%Y-%m-%d"),
                            "predicted_cents": predicted,
                            "lower_bound_cents": lower,
                            "upper_bound_cents": upper,
                            "confidence_pct": round(confidence_decay * 100),
                        })

        elif calc_path == "partial":
            # PARTIAL: simple moving average extrapolation
            window = min(n, 14)
            recent_avg = sum(values[-window:]) / window
            # Simple slope from first half vs second half
            half = window // 2
            first_half = sum(values[-window:-half]) / max(half, 1)
            second_half = sum(values[-half:]) / max(half, 1)
            slope = (second_half - first_half) / max(half, 1)
            error_rate = 0.25

            for horizon_key, horizon_days in [("7_day", 7), ("30_day", 30), ("90_day", 90)]:
                if n < horizon_days // 4:
                    continue
                for i in range(1, horizon_days + 1):
                    predicted = max(0, int(recent_avg + slope * i * 0.5))
                    lower = max(0, int(predicted * (1 - error_rate * 1.5)))
                    upper = int(predicted * (1 + error_rate * 1.5))
                    if (
                        horizon_key == "7_day"
                        or (horizon_key == "30_day" and i % 7 == 0)
                        or (horizon_key == "90_day" and i % 30 == 0)
                    ):
                        forecasts[horizon_key].append({
                            "date": (today + timedelta(days=i)).strftime("%Y-%m-%d"),
                            "predicted_cents": predicted,
                            "lower_bound_cents": lower,
                            "upper_bound_cents": upper,
                            "confidence_pct": max(40, round((0.95 ** (i / 7)) * 80)),
                        })

        else:
            # MINIMAL: benchmark-based growth projection
            bench_range = self.get_benchmark_range("avg_daily_revenue_cents")
            if bench_range is not None:
                base_daily = int(bench_range.mid)
            elif y_mean > 0:
                base_daily = int(y_mean)
            else:
                base_daily = 0

            # Apply modest benchmark growth (2% monthly)
            growth_rate = self.get_benchmark("healthy_wow_growth_pct") or 2.0
            daily_growth = (1 + growth_rate / 100) ** (1 / 7)  # weekly to daily
            error_rate = 0.4

            for horizon_key, horizon_days in [("7_day", 7), ("30_day", 30), ("90_day", 90)]:
                for i in range(1, horizon_days + 1):
                    predicted = max(0, int(base_daily * (daily_growth ** i)))
                    lower = max(0, int(predicted * (1 - error_rate * 1.5)))
                    upper = int(predicted * (1 + error_rate * 1.5))
                    if (
                        horizon_key == "7_day"
                        or (horizon_key == "30_day" and i % 7 == 0)
                        or (horizon_key == "90_day" and i % 30 == 0)
                    ):
                        forecasts[horizon_key].append({
                            "date": (today + timedelta(days=i)).strftime("%Y-%m-%d"),
                            "predicted_cents": predicted,
                            "lower_bound_cents": lower,
                            "upper_bound_cents": upper,
                            "confidence_pct": max(30, round((0.90 ** (i / 7)) * 60)),
                        })

        # Summary totals
        f7_total = sum(f["predicted_cents"] for f in forecasts.get("7_day", []))

        # Scenario analysis
        base_30d = sum(
            f["predicted_cents"]
            for f in forecasts.get("30_day", forecasts.get("7_day", []))
        )
        if not base_30d and f7_total:
            base_30d = f7_total * 30 // 7
        scenario_analysis = {
            "optimistic_cents": int(base_30d * 1.15),
            "expected_cents": int(base_30d),
            "pessimistic_cents": int(base_30d * 0.85),
        }

        # Aggregate projected monthly uplift from all other agents
        monthly_uplift = 0
        for output in agent_outputs.values():
            if isinstance(output, dict):
                for r in output.get("recommendations", []):
                    monthly_uplift += r.get("impact_cents", 0)

        # Confidence determination
        rolling_accuracy = getattr(self.ctx, "rolling_forecast_accuracy", None)
        if rolling_accuracy is not None:
            confidence = round(rolling_accuracy, 2)
        elif n >= 30:
            confidence = 0.7
        elif n >= 14:
            confidence = 0.55
        else:
            confidence = 0.4

        # Minimal path caps confidence
        if calc_path == "minimal":
            confidence = min(confidence, 0.4)

        score = max(0, min(100, round(confidence * 100)))

        insights = [{
            "type": "forecast_summary",
            "detail": f"7-day forecast: ${f7_total/100:,.0f}, trend {'up' if slope > 0 else 'down'} ${abs(slope)/100:.2f}/day",
        }]
        if calc_path != "full":
            insights.append({
                "type": "data_note",
                "detail": (
                    f"Forecast uses {'moving average' if calc_path == 'partial' else 'benchmark-based'} method — "
                    "connect more POS data for higher accuracy"
                ),
            })

        recommendations = []
        if monthly_uplift > 0:
            recommendations.append({
                "action": f"Implementing all recommendations could add ${monthly_uplift/100:,.0f}/month",
                "impact_cents": monthly_uplift,
            })

        return self._result(
            summary=f"7-day: ${f7_total/100:,.0f}, trend {'positive' if slope > 0 else 'negative'} (${slope/100:.2f}/day)",
            score=score,
            insights=insights,
            recommendations=recommendations,
            data={
                "forecasts": forecasts,
                "trend_slope_cents_per_day": round(slope),
                "std_dev_cents": std_dev,
                "error_rate": round(error_rate, 3),
                "scenario_analysis": scenario_analysis,
                "projected_monthly_uplift_cents": monthly_uplift,
            },
            confidence=confidence,
            calculation_path=calc_path,
        )
