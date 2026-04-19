"""
Forecast Generator — Revenue and demand predictions.

Uses historical daily revenue data to produce:
  • 7-day daily revenue forecasts
  • 30-day weekly revenue forecasts  
  • Confidence intervals (lower/upper bounds)

Methods:
  • Weighted Moving Average (primary) — recent data weighted more
  • Day-of-Week adjustment — accounts for weekly seasonality
  • Trend adjustment — applies recent momentum

No external ML libraries needed. These are statistical forecasts
that work well for small business POS data where patterns are
relatively stable.
"""
import logging
import math
from datetime import datetime, date, timedelta, timezone
from uuid import uuid4
from typing import Any

logger = logging.getLogger("meridian.ai.generators.forecasts")


class ForecastGenerator:
    """Generates revenue forecasts from historical data."""

    MODEL_VERSION = "meridian-forecast-v1"

    def generate(self, ctx) -> list[dict]:
        """
        Generate forecasts from daily revenue data.
        
        Returns list of forecast dicts ready for DB insertion.
        """
        daily = ctx.daily_revenue
        if len(daily) < 14:
            logger.warning(
                f"Need 14+ days for forecasting, got {len(daily)}"
            )
            return []

        forecasts = []

        # ── 7-Day Daily Forecasts ─────────────────────────────
        daily_forecasts = self._forecast_daily(ctx, daily, horizon=7)
        forecasts.extend(daily_forecasts)

        # ── 4-Week Weekly Forecasts ───────────────────────────
        weekly_forecasts = self._forecast_weekly(ctx, daily, horizon=4)
        forecasts.extend(weekly_forecasts)

        logger.info(
            f"Generated {len(forecasts)} forecasts for {ctx.org_id} "
            f"({len(daily_forecasts)} daily, {len(weekly_forecasts)} weekly)"
        )
        return forecasts

    def _forecast_daily(
        self, ctx, daily: list[dict], horizon: int = 7
    ) -> list[dict]:
        """
        Forecast daily revenue for the next N days.
        
        Method: Day-of-week adjusted weighted moving average.
        
        1. Compute day-of-week averages (last 4 weeks)
        2. Compute overall trend (momentum from last 2 weeks)
        3. Blend: base = dow_avg * (1 + trend_adjustment)
        4. Confidence intervals from historical variance
        """
        if len(daily) < 7:
            return []

        # Extract time series
        revenues = []
        dates = []
        for d in daily:
            rev = d.get("total_revenue_cents", 0)
            dt = d.get("date")
            if dt:
                if isinstance(dt, str):
                    try:
                        dt = datetime.fromisoformat(dt).date() if 'T' in dt else date.fromisoformat(dt)
                    except ValueError:
                        continue
                elif isinstance(dt, datetime):
                    dt = dt.date()
                revenues.append(rev)
                dates.append(dt)
        
        if len(revenues) < 7:
            return []

        # Step 1: Day-of-week averages (weighted: recent weeks count more)
        dow_avgs = self._weighted_dow_averages(revenues, dates)

        # Step 2: Compute trend (last 14 days vs previous 14)
        trend_factor = self._compute_trend_factor(revenues)

        # Step 3: Historical variance for confidence intervals
        dow_variance = self._dow_variance(revenues, dates, dow_avgs)

        # Step 4: Generate forecasts
        last_date = dates[-1]
        forecasts = []

        for i in range(1, horizon + 1):
            forecast_date = last_date + timedelta(days=i)
            dow = forecast_date.weekday()

            # Base prediction: day-of-week average × trend
            base = dow_avgs.get(dow, sum(revenues[-7:]) / 7)
            predicted = int(base * (1 + trend_factor))
            predicted = max(0, predicted)  # Never negative

            # Confidence interval (±1.5 std dev)
            std_dev = math.sqrt(dow_variance.get(dow, 0))
            lower = max(0, int(predicted - 1.5 * std_dev))
            upper = int(predicted + 1.5 * std_dev)

            # Confidence decays with horizon
            base_confidence = 0.75
            confidence = round(base_confidence * (0.95 ** (i - 1)), 2)

            forecasts.append({
                "id": str(uuid4()),
                "org_id": ctx.org_id,
                "location_id": ctx.location_id,
                "forecast_type": "daily_revenue",
                "period_start": forecast_date.isoformat(),
                "period_end": forecast_date.isoformat(),
                "predicted_value_cents": predicted,
                "lower_bound_cents": lower,
                "upper_bound_cents": upper,
                "confidence_score": confidence,
                "model_version": self.MODEL_VERSION,
                "features_used": {
                    "method": "dow_weighted_ma",
                    "training_days": len(revenues),
                    "trend_factor": round(trend_factor, 4),
                    "day_of_week": dow,
                },
                "generated_at": datetime.now(timezone.utc).isoformat(),
            })

        return forecasts

    def _forecast_weekly(
        self, ctx, daily: list[dict], horizon: int = 4
    ) -> list[dict]:
        """
        Forecast weekly revenue totals.
        
        Simpler than daily: uses 4-week weighted moving average.
        """
        revenues = [d.get("total_revenue_cents", 0) for d in daily]
        
        if len(revenues) < 14:
            return []

        # Build weekly totals
        weekly_totals = []
        for i in range(0, len(revenues), 7):
            week = revenues[i:i+7]
            if len(week) == 7:
                weekly_totals.append(sum(week))

        if len(weekly_totals) < 2:
            return []

        # Weighted average of recent weeks
        weights = [1, 2, 3, 4]  # Most recent gets highest weight
        recent = weekly_totals[-4:] if len(weekly_totals) >= 4 else weekly_totals
        w = weights[-len(recent):]
        
        weighted_avg = sum(v * wt for v, wt in zip(recent, w)) / sum(w)
        
        # Trend
        if len(weekly_totals) >= 2:
            trend = (weekly_totals[-1] - weekly_totals[-2]) / max(weekly_totals[-2], 1)
        else:
            trend = 0
        
        # Variance for confidence
        if len(weekly_totals) >= 3:
            mean = sum(weekly_totals[-4:]) / min(len(weekly_totals), 4)
            variance = sum((x - mean) ** 2 for x in weekly_totals[-4:]) / min(len(weekly_totals), 4)
            std_dev = math.sqrt(variance)
        else:
            std_dev = weighted_avg * 0.15  # Default 15% uncertainty

        # Generate weekly forecasts
        last_date = None
        for d in daily:
            dt = d.get("date")
            if dt:
                if isinstance(dt, str):
                    try:
                        last_date = datetime.fromisoformat(dt).date() if 'T' in dt else date.fromisoformat(dt)
                    except ValueError:
                        pass
                elif isinstance(dt, (datetime, date)):
                    last_date = dt if isinstance(dt, date) else dt.date()
        
        if not last_date:
            return []

        forecasts = []
        for i in range(1, horizon + 1):
            week_start = last_date + timedelta(days=(i-1) * 7 + 1)
            week_end = week_start + timedelta(days=6)

            predicted = int(weighted_avg * (1 + trend * i * 0.5))
            predicted = max(0, predicted)
            
            lower = max(0, int(predicted - 1.5 * std_dev))
            upper = int(predicted + 1.5 * std_dev)
            
            confidence = round(0.7 * (0.9 ** (i - 1)), 2)

            forecasts.append({
                "id": str(uuid4()),
                "org_id": ctx.org_id,
                "location_id": ctx.location_id,
                "forecast_type": "weekly_revenue",
                "period_start": week_start.isoformat(),
                "period_end": week_end.isoformat(),
                "predicted_value_cents": predicted,
                "lower_bound_cents": lower,
                "upper_bound_cents": upper,
                "confidence_score": confidence,
                "model_version": self.MODEL_VERSION,
                "features_used": {
                    "method": "weighted_ma",
                    "training_weeks": len(weekly_totals),
                    "trend_factor": round(trend, 4),
                },
                "generated_at": datetime.now(timezone.utc).isoformat(),
            })

        return forecasts

    # ─── Statistical Helpers ──────────────────────────────────

    def _weighted_dow_averages(
        self, revenues: list[int], dates: list
    ) -> dict[int, float]:
        """
        Compute day-of-week averages with recency weighting.
        
        Recent weeks get higher weight (exponential decay).
        """
        dow_values = {}  # dow → [(value, weight), ...]
        
        total_days = len(revenues)
        for i, (rev, dt) in enumerate(zip(revenues, dates)):
            try:
                dow = dt.weekday()
            except AttributeError:
                continue
            
            # Weight: more recent = higher (exponential)
            recency = i / max(total_days - 1, 1)  # 0 = oldest, 1 = newest
            weight = 0.5 + recency * 1.5  # Range: 0.5 to 2.0
            
            if dow not in dow_values:
                dow_values[dow] = []
            dow_values[dow].append((rev, weight))
        
        # Weighted average per DOW
        dow_avgs = {}
        for dow, values in dow_values.items():
            total_weight = sum(w for _, w in values)
            if total_weight > 0:
                dow_avgs[dow] = sum(v * w for v, w in values) / total_weight
            else:
                dow_avgs[dow] = 0
        
        return dow_avgs

    def _compute_trend_factor(self, revenues: list[int]) -> float:
        """
        Compute trend as a multiplier.
        
        Compares recent 7-day average to previous 7-day average.
        Returns a small adjustment factor (-0.1 to +0.1).
        """
        if len(revenues) < 14:
            return 0.0
        
        recent = sum(revenues[-7:]) / 7
        previous = sum(revenues[-14:-7]) / 7
        
        if previous == 0:
            return 0.0
        
        raw_trend = (recent - previous) / previous
        
        # Clamp to ±10% to avoid wild extrapolation
        return max(-0.10, min(0.10, raw_trend))

    def _dow_variance(
        self,
        revenues: list[int],
        dates: list,
        dow_avgs: dict[int, float],
    ) -> dict[int, float]:
        """Compute variance per day-of-week."""
        dow_diffs = {}
        
        for rev, dt in zip(revenues, dates):
            try:
                dow = dt.weekday()
            except AttributeError:
                continue
            
            avg = dow_avgs.get(dow, 0)
            diff_sq = (rev - avg) ** 2
            
            if dow not in dow_diffs:
                dow_diffs[dow] = []
            dow_diffs[dow].append(diff_sq)
        
        variances = {}
        for dow, diffs in dow_diffs.items():
            if diffs:
                variances[dow] = sum(diffs) / len(diffs)
            else:
                variances[dow] = 0
        
        return variances
