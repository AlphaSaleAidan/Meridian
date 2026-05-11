from .base import BaseAlert, AlertSeverity
import statistics

try:
    import numpy as _np
    if not hasattr(_np, "asscalar"):
        _np.asscalar = lambda a: a.item()
    from luminol.anomaly_detector import AnomalyDetector as LuminolDetector
    HAS_LUMINOL = True
except ImportError:
    HAS_LUMINOL = False


class RevenueAnomalyAlert(BaseAlert):
    name = "revenue_anomaly"
    description = "Detects abnormal daily revenue via z-score + Luminol time-series analysis"
    cooldown_hours = 24

    async def evaluate(self) -> list[dict]:
        daily = getattr(self.ctx, "daily_revenue", []) or []
        if len(daily) < 14:
            return self.no_alerts()

        sorted_days = sorted(daily, key=lambda d: d.get("date", ""))
        revenues = [d.get("revenue_cents", 0) for d in sorted_days]

        baseline = revenues[-30:] if len(revenues) >= 30 else revenues
        if len(baseline) < 7:
            return self.no_alerts()

        mean = statistics.mean(baseline[:-1])
        stdev = statistics.stdev(baseline[:-1]) if len(baseline) > 2 else 1

        if stdev == 0:
            return self.no_alerts()

        today_rev = revenues[-1]
        z_score = (today_rev - mean) / stdev
        pct_diff = (today_rev - mean) / mean * 100

        # Luminol time-series anomaly detection for richer context
        luminol_score = 0.0
        luminol_anomalies = []
        if HAS_LUMINOL and len(revenues) >= 14:
            try:
                ts_dict = {i: float(v) for i, v in enumerate(revenues)}
                detector = LuminolDetector(ts_dict)
                luminol_anomalies = detector.get_anomalies()
                if luminol_anomalies:
                    last = luminol_anomalies[-1]
                    if last.end_timestamp >= len(revenues) - 2:
                        luminol_score = last.anomaly_score
            except Exception:
                pass

        alerts = []
        is_luminol_anomaly = luminol_score > 0
        luminol_note = f" Luminol score: {luminol_score:.0f}." if is_luminol_anomaly else ""

        if z_score < -3.0:
            alerts.append(self.fire(
                AlertSeverity.URGENT,
                f"Worst revenue day in 30 days — ${today_rev / 100:.0f}",
                f"Revenue ${today_rev / 100:.0f} is {abs(pct_diff):.0f}% below normal "
                f"(z-score: {z_score:.1f}).{luminol_note} Something is significantly wrong — "
                f"check foot traffic, staffing, local events, or POS issues.",
                metric_value=today_rev,
                threshold=mean,
                impact_cents=int(mean - today_rev),
            ))
        elif z_score < -2.0 or (is_luminol_anomaly and z_score < -1.5):
            alerts.append(self.fire(
                AlertSeverity.WARNING,
                f"Revenue tracking {abs(pct_diff):.0f}% below normal",
                f"Today ${today_rev / 100:.0f} vs expected ${mean / 100:.0f} "
                f"(z-score: {z_score:.1f}).{luminol_note} Check foot traffic, staffing, or local events.",
                metric_value=today_rev,
                threshold=mean,
                impact_cents=int(mean - today_rev),
            ))
        elif z_score > 2.0 or (is_luminol_anomaly and z_score > 1.5):
            alerts.append(self.fire(
                AlertSeverity.INFO,
                f"Revenue {pct_diff:.0f}% above normal today!",
                f"Today ${today_rev / 100:.0f} vs expected ${mean / 100:.0f} "
                f"(z-score: {z_score:.1f}).{luminol_note} Investigate what's driving this so you can repeat it.",
                metric_value=today_rev,
                threshold=mean,
                impact_cents=int(today_rev - mean),
            ))

        return alerts
