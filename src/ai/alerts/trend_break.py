from .base import BaseAlert, AlertSeverity
import statistics

class TrendBreakAlert(BaseAlert):
    name = "trend_break"
    description = "CUSUM-based trend change detection"
    cooldown_hours = 72

    async def evaluate(self) -> list[dict]:
        daily = getattr(self.ctx, "daily_revenue", []) or []
        if len(daily) < 21:
            return self.no_alerts()

        sorted_days = sorted(daily, key=lambda d: d.get("date", ""))
        revenues = [d.get("revenue_cents", 0) for d in sorted_days]
        dates = [d.get("date", "") for d in sorted_days]

        # CUSUM algorithm
        target = statistics.mean(revenues[-30:]) if len(revenues) >= 30 else statistics.mean(revenues)
        stdev = statistics.stdev(revenues[-30:]) if len(revenues) >= 30 else statistics.stdev(revenues)

        if stdev == 0:
            return self.no_alerts()

        drift = 0.5 * stdev
        threshold = 4 * stdev

        # Detect upward shift
        s_pos = 0.0
        s_neg = 0.0
        break_date = None
        break_direction = None

        for i, x in enumerate(revenues):
            s_pos = max(0, s_pos + (x - target - drift))
            s_neg = max(0, s_neg + (target - drift - x))

            if s_pos > threshold and break_date is None:
                break_date = dates[i]
                break_direction = "up"
            elif s_neg > threshold and break_date is None:
                break_date = dates[i]
                break_direction = "down"

        if not break_date:
            return self.no_alerts()

        # Calculate before/after averages
        break_idx = dates.index(break_date)
        before_avg = statistics.mean(revenues[max(0, break_idx - 14):break_idx]) if break_idx > 0 else target
        after_avg = statistics.mean(revenues[break_idx:]) if break_idx < len(revenues) else target
        shift_pct = (after_avg - before_avg) / before_avg * 100

        severity = AlertSeverity.WARNING if abs(shift_pct) < 25 else AlertSeverity.CRITICAL

        alerts = [self.fire(
            severity,
            f"Significant trend {'increase' if break_direction == 'up' else 'decrease'} detected",
            f"Revenue shifted from ~${before_avg / 100:.0f}/day to ~${after_avg / 100:.0f}/day "
            f"around {break_date} ({shift_pct:+.0f}%). This isn't random variation — "
            f"something fundamental changed. Check product mix, staffing, or seasonal patterns.",
            metric_value=after_avg,
            threshold=before_avg,
            impact_cents=int(abs(after_avg - before_avg) * 30),
            metadata={"break_date": break_date, "direction": break_direction, "shift_pct": round(shift_pct, 1)},
        )]

        return alerts
