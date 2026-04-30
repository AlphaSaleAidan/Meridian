from .base import BaseAlert, AlertSeverity
import statistics

class RevenueAnomalyAlert(BaseAlert):
    name = "revenue_anomaly"
    description = "Detects abnormal daily revenue via z-score"
    cooldown_hours = 24

    async def evaluate(self) -> list[dict]:
        daily = getattr(self.ctx, "daily_revenue", []) or []
        if len(daily) < 14:
            return self.no_alerts()

        sorted_days = sorted(daily, key=lambda d: d.get("date", ""))
        revenues = [d.get("revenue_cents", 0) for d in sorted_days]

        # Use last 30 days (or all available) for baseline
        baseline = revenues[-30:] if len(revenues) >= 30 else revenues
        if len(baseline) < 7:
            return self.no_alerts()

        mean = statistics.mean(baseline[:-1])  # exclude today
        stdev = statistics.stdev(baseline[:-1]) if len(baseline) > 2 else 1

        if stdev == 0:
            return self.no_alerts()

        today_rev = revenues[-1]

        # Project end-of-day if we have hourly data
        hourly = getattr(self.ctx, "hourly_revenue", []) or []
        if hourly:
            today_hourly = [h for h in hourly if h.get("day_of_week") is not None]
            # Use actual today value as-is (already in daily_revenue)

        z_score = (today_rev - mean) / stdev
        pct_diff = (today_rev - mean) / mean * 100

        alerts = []
        if z_score < -3.0:
            alerts.append(self.fire(
                AlertSeverity.URGENT,
                f"Worst revenue day in 30 days — ${today_rev / 100:.0f}",
                f"Revenue ${today_rev / 100:.0f} is {abs(pct_diff):.0f}% below normal "
                f"(z-score: {z_score:.1f}). Something is significantly wrong — "
                f"check foot traffic, staffing, local events, or POS issues.",
                metric_value=today_rev,
                threshold=mean,
                impact_cents=int(mean - today_rev),
            ))
        elif z_score < -2.0:
            alerts.append(self.fire(
                AlertSeverity.WARNING,
                f"Revenue tracking {abs(pct_diff):.0f}% below normal",
                f"Today ${today_rev / 100:.0f} vs expected ${mean / 100:.0f} "
                f"(z-score: {z_score:.1f}). Check foot traffic, staffing, or local events.",
                metric_value=today_rev,
                threshold=mean,
                impact_cents=int(mean - today_rev),
            ))
        elif z_score > 2.0:
            alerts.append(self.fire(
                AlertSeverity.INFO,
                f"Revenue {pct_diff:.0f}% above normal today!",
                f"Today ${today_rev / 100:.0f} vs expected ${mean / 100:.0f} "
                f"(z-score: {z_score:.1f}). Investigate what's driving this so you can repeat it.",
                metric_value=today_rev,
                threshold=mean,
                impact_cents=int(today_rev - mean),
            ))

        return alerts
