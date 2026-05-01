from .base import BaseAgent
from datetime import datetime


class SeasonalityAgent(BaseAgent):
    name = "seasonality"
    description = "Seasonal decomposition and calendar effects"
    tier = 3

    async def analyze(self) -> dict:
        path, confidence = self._select_path()
        avail = self.get_data_availability()

        if avail.date_range_days >= 180:
            confidence = max(confidence, 0.85)
        elif avail.date_range_days < 90:
            confidence = min(confidence, 0.4)

        daily = self.ctx.daily_revenue

        # --- MINIMAL path: industry seasonal pattern ---
        if path == "minimal" or len(daily) < 14:
            bench = self.get_benchmark_range("seasonality_strength_pct")
            source = bench.source if bench else "industry default"
            day_names = [
                "Monday", "Tuesday", "Wednesday", "Thursday",
                "Friday", "Saturday", "Sunday",
            ]
            # Industry default: Fri/Sat strong, Mon/Tue weak
            default_pattern = [
                {"day": "Monday", "seasonal_effect_cents": -500},
                {"day": "Tuesday", "seasonal_effect_cents": -300},
                {"day": "Wednesday", "seasonal_effect_cents": 0},
                {"day": "Thursday", "seasonal_effect_cents": 100},
                {"day": "Friday", "seasonal_effect_cents": 400},
                {"day": "Saturday", "seasonal_effect_cents": 500},
                {"day": "Sunday", "seasonal_effect_cents": -200},
            ]
            return self._result(
                summary=f"Seasonal pattern estimated from industry benchmarks (source: {source})",
                score=50,
                insights=[{
                    "type": "estimated_seasonality",
                    "detail": f"Using industry seasonal pattern — need 30+ days for real decomposition (source: {source})",
                }],
                recommendations=[{
                    "action": "Connect more data sources for precise analysis",
                    "impact": "Improves accuracy from estimated to actual",
                    "effort": "low",
                }],
                data={
                    "seasonal_pattern": default_pattern,
                    "seasonality_strength_pct": 0,
                    "predicted_dips": [],
                    "trend_cents": [],
                    "benchmark_source": source,
                },
                confidence=confidence,
                calculation_path=path,
            )

        # --- PARTIAL path: day-level patterns (< 30 days) ---
        if path == "partial" and len(daily) < 30:
            # Use simpler day-level averages without full decomposition
            pass  # Fall through to main logic which handles short ranges

        sorted_days = sorted(daily, key=lambda d: d.get("date", ""))
        values = [d.get("revenue_cents", 0) for d in sorted_days]
        n = len(values)

        # Simple 7-day moving average for trend
        period = 7
        trend = []
        for i in range(n):
            start = max(0, i - period // 2)
            end = min(n, i + period // 2 + 1)
            trend.append(sum(values[start:end]) // (end - start))

        # Seasonal component: deviation from trend
        seasonal = [values[i] - trend[i] for i in range(n)]

        # Day-of-week seasonal pattern
        dow_seasonal = [0] * 7
        dow_count = [0] * 7
        for i, d in enumerate(sorted_days):
            try:
                dt = datetime.fromisoformat(
                    d.get("date", "").replace("Z", "+00:00")
                )
                dow = dt.weekday()
                dow_seasonal[dow] += seasonal[i]
                dow_count[dow] += 1
            except (ValueError, AttributeError):
                pass

        day_names = [
            "Monday", "Tuesday", "Wednesday", "Thursday",
            "Friday", "Saturday", "Sunday",
        ]
        seasonal_pattern = []
        for i in range(7):
            avg = dow_seasonal[i] // max(dow_count[i], 1)
            seasonal_pattern.append({
                "day": day_names[i],
                "seasonal_effect_cents": avg,
            })

        # Residual (noise) — computed for variance analysis
        def _parse_weekday(date_str: str) -> int:
            return datetime.fromisoformat(
                date_str.replace("Z", "+00:00")
            ).weekday()

        residuals = []
        for i in range(n):
            date_str = sorted_days[i].get("date", "")
            if not date_str:
                continue
            try:
                wd = _parse_weekday(date_str)
                dow_avg = dow_seasonal[wd] // max(dow_count[wd], 1)
                residuals.append(values[i] - trend[i] - dow_avg)
            except (ValueError, AttributeError):
                pass

        # Seasonal strength
        mean_val = sum(values) // n
        total_var = sum((v - mean_val) ** 2 for v in values)
        seasonal_var = sum(s ** 2 for s in seasonal)
        seasonality_strength = round(
            seasonal_var / max(total_var, 1) * 100, 1
        )

        # Predicted dips (based on seasonal pattern)
        avg_daily = sum(values) // n
        predicted_dips = []
        for sp in seasonal_pattern:
            if sp["seasonal_effect_cents"] < -avg_daily * 0.1:
                predicted_dips.append({
                    "day": sp["day"],
                    "expected_drop_pct": round(
                        sp["seasonal_effect_cents"] / max(avg_daily, 1) * 100,
                        1,
                    ),
                })

        score = max(0, 100 - len(predicted_dips) * 10)

        insights = []
        if seasonality_strength > 30:
            insights.append({
                "type": "strong_seasonality",
                "detail": (
                    f"Seasonality explains {seasonality_strength}%"
                    " of revenue variance"
                ),
            })
        best_day = max(
            seasonal_pattern, key=lambda x: x["seasonal_effect_cents"]
        )
        worst_day = min(
            seasonal_pattern, key=lambda x: x["seasonal_effect_cents"]
        )
        insights.append({
            "type": "day_pattern",
            "detail": f"Best day: {best_day['day']}, worst: {worst_day['day']}",
        })

        recommendations = []
        if predicted_dips:
            dip_days = ", ".join(d["day"] for d in predicted_dips)
            recommendations.append({
                "action": f"Run counter-seasonal promotions on {dip_days}",
                "impact_cents": 0,
            })

        if path != "full":
            recommendations.append({
                "action": "Connect more data sources for precise analysis",
                "impact": "Improves accuracy from estimated to actual",
                "effort": "low",
            })

        return self._result(
            summary=(
                f"Seasonality strength {seasonality_strength}%,"
                f" best day {best_day['day']}, worst {worst_day['day']}"
            ),
            score=score,
            insights=insights,
            recommendations=recommendations,
            data={
                "seasonal_pattern": seasonal_pattern,
                "seasonality_strength_pct": seasonality_strength,
                "predicted_dips": predicted_dips,
                "trend_cents": trend[-7:],
            },
            confidence=confidence,
            calculation_path=path,
        )
