"""
Revenue Analyzer — Trends, growth, anomalies, and comparisons.

Analyzes daily revenue data to produce:
  • Current period KPIs (total, avg ticket, growth rate)
  • Trend direction and momentum
  • Week-over-week and period-over-period comparisons
  • Revenue anomalies (unusual spikes or drops)
  • Payment method distribution shifts
  • Refund rate analysis
"""
import logging
import math

logger = logging.getLogger("meridian.ai.analyzers.revenue")


class RevenueAnalyzer:
    """Produces revenue analysis from daily aggregate data."""

    def analyze(self, ctx) -> dict:
        """
        Run full revenue analysis.
        
        Returns:
            {
                "kpis": {current period metrics},
                "trend": {direction, momentum, moving averages},
                "comparison": {period-over-period changes},
                "anomalies": [{unusual days}],
                "payment_mix": {method breakdown},
                "refund_analysis": {rate, trend},
            }
        """
        daily = ctx.daily_revenue
        if not daily:
            logger.warning(f"No daily revenue data for {ctx.org_id}")
            return {"error": "insufficient_data", "min_days_needed": 7}

        result = {}
        
        result["kpis"] = self._compute_kpis(daily)
        result["trend"] = self._compute_trend(daily)
        result["comparison"] = self._compute_comparison(daily)
        result["anomalies"] = self._detect_anomalies(daily)
        result["refund_analysis"] = self._analyze_refunds(daily)
        result["daily_breakdown"] = self._daily_breakdown(daily)
        
        logger.info(
            f"Revenue analysis complete: "
            f"${result['kpis']['total_revenue_cents']/100:,.0f} revenue, "
            f"trend={result['trend']['direction']}, "
            f"{len(result['anomalies'])} anomalies"
        )
        return result

    def _compute_kpis(self, daily: list[dict]) -> dict:
        """Core KPIs for the analysis period."""
        total_revenue = sum((d.get("total_revenue_cents") or 0) for d in daily)
        total_txns = sum((d.get("transaction_count") or 0) for d in daily)
        total_tax = sum((d.get("total_tax_cents") or 0) for d in daily)
        total_tips = sum((d.get("total_tip_cents") or 0) for d in daily)
        total_discounts = sum((d.get("total_discount_cents") or 0) for d in daily)
        total_customers = sum((d.get("total_customers") or 0) for d in daily)
        
        active_days = len([d for d in daily if (d.get("transaction_count") or 0) > 0])
        
        return {
            "total_revenue_cents": total_revenue,
            "total_transactions": total_txns,
            "total_tax_cents": total_tax,
            "total_tip_cents": total_tips,
            "total_discount_cents": total_discounts,
            "total_customers": total_customers,
            "active_days": active_days,
            "total_days": len(daily),
            "avg_daily_revenue_cents": (
                total_revenue // active_days if active_days > 0 else 0
            ),
            "avg_ticket_cents": (
                total_revenue // total_txns if total_txns > 0 else 0
            ),
            "avg_transactions_per_day": (
                round(total_txns / active_days, 1) if active_days > 0 else 0
            ),
            "tip_rate_pct": (
                round(total_tips / total_revenue * 100, 1)
                if total_revenue > 0 else 0
            ),
            "discount_rate_pct": (
                round(total_discounts / total_revenue * 100, 1)
                if total_revenue > 0 else 0
            ),
        }

    def _compute_trend(self, daily: list[dict]) -> dict:
        """
        Trend analysis: direction, momentum, moving averages.
        
        Uses 7-day and 14-day moving averages to determine
        trend direction and strength.
        """
        if len(daily) < 7:
            return {"direction": "insufficient_data", "momentum": 0}
        
        # Extract revenue time series
        revenues = [(d.get("total_revenue_cents") or 0) for d in daily]
        
        # 7-day moving averages
        ma7 = self._moving_average(revenues, 7)
        
        # Trend direction: compare last 7-day MA to previous
        if len(ma7) >= 2:
            recent = ma7[-1]
            previous = ma7[-2] if len(ma7) >= 2 else ma7[0]
            
            if recent > previous * 1.03:
                direction = "growing"
            elif recent < previous * 0.97:
                direction = "declining"
            else:
                direction = "stable"
        else:
            direction = "insufficient_data"

        # Momentum: slope of last 7 MA values (normalized)
        if len(ma7) >= 7:
            recent_ma = ma7[-7:]
            slope = (recent_ma[-1] - recent_ma[0]) / max(recent_ma[0], 1)
            momentum = round(slope * 100, 2)  # percent change over period
        else:
            momentum = 0

        # Week-over-week growth rate
        if len(revenues) >= 14:
            this_week = sum(revenues[-7:])
            last_week = sum(revenues[-14:-7])
            wow_growth = (
                round((this_week - last_week) / max(last_week, 1) * 100, 1)
            )
        else:
            wow_growth = None

        return {
            "direction": direction,
            "momentum": momentum,
            "wow_growth_pct": wow_growth,
            "ma7_latest": ma7[-1] if ma7 else 0,
            "ma7_series": ma7[-14:],  # last 14 points
        }

    def _compute_comparison(self, daily: list[dict]) -> dict:
        """Period-over-period comparison (this period vs previous)."""
        n = len(daily)
        if n < 2:
            return {}
        
        half = n // 2
        current_period = daily[half:]
        previous_period = daily[:half]
        
        curr_rev = sum((d.get("total_revenue_cents") or 0) for d in current_period)
        prev_rev = sum((d.get("total_revenue_cents") or 0) for d in previous_period)
        
        curr_txns = sum((d.get("transaction_count") or 0) for d in current_period)
        prev_txns = sum((d.get("transaction_count") or 0) for d in previous_period)
        
        curr_avg_ticket = curr_rev // max(curr_txns, 1)
        prev_avg_ticket = prev_rev // max(prev_txns, 1)

        def pct_change(curr, prev):
            if prev == 0:
                return 0
            return round((curr - prev) / prev * 100, 1)

        return {
            "period_days": half,
            "revenue_change_pct": pct_change(curr_rev, prev_rev),
            "transaction_change_pct": pct_change(curr_txns, prev_txns),
            "avg_ticket_change_pct": pct_change(curr_avg_ticket, prev_avg_ticket),
            "current_revenue_cents": curr_rev,
            "previous_revenue_cents": prev_rev,
            "current_transactions": curr_txns,
            "previous_transactions": prev_txns,
        }

    def _detect_anomalies(self, daily: list[dict]) -> list[dict]:
        """
        Detect revenue anomalies using statistical thresholds.
        
        An anomaly is a day where revenue deviates >2 standard 
        deviations from the rolling 7-day mean.
        """
        if len(daily) < 14:
            return []
        
        revenues = [(d.get("total_revenue_cents") or 0) for d in daily]
        anomalies = []
        
        for i in range(7, len(revenues)):
            window = revenues[max(0, i-7):i]
            mean = sum(window) / len(window)
            
            if mean == 0:
                continue
            
            variance = sum((x - mean) ** 2 for x in window) / len(window)
            std_dev = math.sqrt(variance)
            
            if std_dev == 0:
                continue
            
            z_score = (revenues[i] - mean) / std_dev
            
            if abs(z_score) > 2.0:
                day_data = daily[i]
                anomalies.append({
                    "date": str(day_data.get("date", "")),
                    "revenue_cents": revenues[i],
                    "expected_cents": int(mean),
                    "deviation_pct": round(
                        (revenues[i] - mean) / mean * 100, 1
                    ),
                    "z_score": round(z_score, 2),
                    "type": "spike" if z_score > 0 else "drop",
                    "severity": (
                        "high" if abs(z_score) > 3 
                        else "medium" if abs(z_score) > 2.5 
                        else "low"
                    ),
                })
        
        return sorted(anomalies, key=lambda x: abs(x["z_score"]), reverse=True)

    def _analyze_refunds(self, daily: list[dict]) -> dict:
        """Refund rate and trend analysis."""
        total_revenue = sum((d.get("total_revenue_cents") or 0) for d in daily)
        total_refund_cents = sum(d.get("refund_total_cents") or 0 for d in daily)
        total_refund_count = sum((d.get("refund_count") or 0) for d in daily)
        total_txns = sum((d.get("transaction_count") or 0) for d in daily)
        
        return {
            "total_refund_cents": total_refund_cents,
            "refund_count": total_refund_count,
            "refund_rate_pct": (
                round(total_refund_cents / max(total_revenue, 1) * 100, 2)
            ),
            "refund_frequency_pct": (
                round(total_refund_count / max(total_txns, 1) * 100, 2)
            ),
            "is_concerning": total_refund_cents > total_revenue * 0.05,
        }

    def _daily_breakdown(self, daily: list[dict]) -> list[dict]:
        """Per-day summary for charting."""
        return [
            {
                "date": str(d.get("date", "")),
                "revenue_cents": (d.get("total_revenue_cents") or 0),
                "transactions": (d.get("transaction_count") or 0),
                "avg_ticket_cents": (d.get("avg_ticket_cents") or 0),
            }
            for d in daily
        ]

    # ─── Utilities ────────────────────────────────────────────

    @staticmethod
    def _moving_average(values: list[int | float], window: int) -> list[float]:
        """Compute simple moving average."""
        if len(values) < window:
            return [sum(values) / len(values)] if values else []
        
        result = []
        for i in range(window - 1, len(values)):
            avg = sum(values[i - window + 1 : i + 1]) / window
            result.append(round(avg, 0))
        return result
