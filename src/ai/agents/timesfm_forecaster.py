"""
TimesFM Forecaster — a tier-5 swarm agent that produces zero-shot 7/30/90-day
revenue forecasts using Google's TimesFM time-series foundation model.

Sits alongside the existing ForecasterAgent (statsforecast / WMA). It emits the
same `data["forecasts"]` shape so the two are directly comparable in the swarm,
and the swarm trainer scores both — over time the more accurate one wins on the
agent scorecards.

Inert by design until TimesFM is provisioned (TIMESFM_ENABLED=1 + the `timesfm`
package + weights on a host with enough RAM). Until then it reports `skipped` and
the existing forecaster remains authoritative — see timesfm_engine.py.
"""
from datetime import datetime, timedelta

from .base import BaseAgent
from ..predictive.timesfm_engine import get_timesfm_engine

# daily_revenue rows are populated from the daily_revenue matview; the field name
# differs by code path (the agent context uses `revenue_cents`, the matview column
# is `total_revenue_cents`). Read whichever is present so we're robust to both.
_REV_KEYS = ("revenue_cents", "total_revenue_cents")
_DATE_KEYS = ("date", "day_bucket")

_HORIZONS = (("7_day", 7, 1), ("30_day", 30, 7), ("90_day", 90, 30))


class TimesFMForecasterAgent(BaseAgent):
    name = "timesfm_forecaster"
    description = "Zero-shot 7/30/90-day revenue forecasts via Google TimesFM"
    tier = 5

    async def analyze(self) -> dict:
        engine = get_timesfm_engine()
        if not engine.is_available():
            # Expected on hosts where TimesFM isn't provisioned — not an error.
            return self._skipped(engine.unavailable_reason or "TimesFM not available")

        daily = self.ctx.daily_revenue or []
        if len(daily) < 14:
            return self._insufficient_data("At least 14 days of revenue history for TimesFM")

        sorted_days = sorted(daily, key=lambda d: self._row_date(d))
        series = [self._row_revenue(d) for d in sorted_days]

        today = datetime.now()
        forecasts: dict[str, list[dict]] = {"7_day": [], "30_day": [], "90_day": []}
        for horizon_key, horizon_days, stride in _HORIZONS:
            fc = engine.forecast(series, horizon_days)
            if fc is None:
                return self._skipped("TimesFM inference returned nothing")
            for i in range(horizon_days):
                idx = i + 1
                if not (horizon_key == "7_day" or idx % stride == 0):
                    continue
                forecasts[horizon_key].append({
                    "date": (today + timedelta(days=idx)).strftime("%Y-%m-%d"),
                    "predicted_cents": max(0, round(fc.point[i])),
                    "lower_bound_cents": max(0, round(fc.lower[i])),
                    "upper_bound_cents": max(0, round(fc.upper[i])),
                    # TimesFM degrades more gracefully with horizon than naive models.
                    "confidence_pct": max(45, round((0.97 ** (idx / 7)) * 100)),
                })

        f7_total = sum(f["predicted_cents"] for f in forecasts["7_day"])
        base_30d = sum(f["predicted_cents"] for f in forecasts["30_day"]) or (f7_total * 30 // 7)
        scenario_analysis = {
            "optimistic_cents": int(base_30d * 1.15),
            "expected_cents": int(base_30d),
            "pessimistic_cents": int(base_30d * 0.85),
        }
        confidence = 0.75 if len(series) >= 30 else 0.6

        return self._result(
            summary=f"TimesFM 7-day forecast: ${f7_total / 100:,.0f}",
            score=round(confidence * 100),
            insights=[{
                "type": "forecast_summary",
                "detail": f"TimesFM zero-shot 7-day forecast: ${f7_total / 100:,.0f} "
                          f"from {len(series)} days of history",
            }],
            recommendations=[],
            data={
                "forecasts": forecasts,
                "scenario_analysis": scenario_analysis,
                "model": "timesfm",
                "training_days": len(series),
            },
            confidence=confidence,
            calculation_path="full",
        )

    # ── helpers ──────────────────────────────────────────────
    @staticmethod
    def _row_revenue(row: dict) -> float:
        for k in _REV_KEYS:
            if row.get(k) is not None:
                return float(row.get(k) or 0)
        return 0.0

    @staticmethod
    def _row_date(row: dict) -> str:
        for k in _DATE_KEYS:
            if row.get(k):
                return str(row.get(k))
        return ""

    def _skipped(self, reason: str) -> dict:
        """A clean no-op result (status 'skipped', score 0) when TimesFM isn't
        active — distinct from 'insufficient_data' so it reads as 'not provisioned'
        rather than 'not enough history'."""
        return {
            "agent_name": self.name,
            "status": "skipped",
            "summary": f"TimesFM not active: {reason}",
            "score": 0,
            "insights": [],
            "recommendations": [],
            "data": {"reason": reason},
            "data_quality": 0.0,
            "calculation_path": "none",
        }
