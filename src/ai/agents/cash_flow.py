from .base import BaseAgent
from datetime import datetime, timedelta

class CashFlowAgent(BaseAgent):
    name = "cash_flow"
    description = "14-day cash position forecast and fee analysis"
    tier = 1

    async def analyze(self) -> dict:
        avail = self.get_data_availability()
        daily = self.ctx.daily_revenue
        txns = self.ctx.transactions

        # Choose calculation path
        if avail.is_full:
            confidence = avail.quality_score
            path = "full"
        elif avail.is_partial:
            confidence = avail.quality_score
            path = "partial"
        else:
            confidence = min(0.4, avail.quality_score)
            path = "minimal"

        # MINIMAL: not enough data for meaningful forecast
        if path == "minimal" or len(daily) < 14:
            if len(daily) < 14 and path != "minimal":
                return self._insufficient_data("At least 14 days of revenue data")
            fee_range = self.get_benchmark_range("processing_fee_pct")
            bench_fee = fee_range.mid if fee_range else 2.6
            insights = [{"type": "benchmark_estimate", "detail": f"Using industry benchmark processing fee rate of {bench_fee}%"}]
            if fee_range:
                insights[0]["benchmark"] = {"low": fee_range.low, "mid": fee_range.mid, "high": fee_range.high, "source": fee_range.source}
                insights[0]["estimated"] = True
            recommendations = [{
                "action": "Connect POS line-item data for precise analysis",
                "impact": "Improves accuracy from estimated to actual values",
                "effort": "low",
            }]
            return self._result(
                summary=f"Insufficient data for cash flow forecast (need 14+ days)",
                score=50,
                insights=insights,
                recommendations=recommendations,
                data={"days_available": len(daily), "benchmark_fee_pct": bench_fee, "source": "benchmark"},
                confidence=confidence,
                calculation_path=path,
            )

        # Forecast quality depends on date range
        if avail.date_range_days < 21:
            confidence = max(0.3, confidence - 0.2)

        sorted_days = sorted(daily, key=lambda d: d.get("date", ""))
        revenues = [d.get("revenue_cents", 0) for d in sorted_days]

        # Day-of-week averages for forecasting
        dow_totals = {}
        dow_counts = {}
        for d in sorted_days:
            date_str = d.get("date", "")
            try:
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                dow = dt.weekday()
            except (ValueError, AttributeError):
                continue
            rev = d.get("revenue_cents", 0)
            dow_totals[dow] = dow_totals.get(dow, 0) + rev
            dow_counts[dow] = dow_counts.get(dow, 0) + 1

        dow_avg = {dow: dow_totals[dow] // max(dow_counts[dow], 1) for dow in dow_totals}

        # 14-day forecast based on day-of-week pattern
        today = datetime.now()
        forecast = []
        for i in range(1, 15):
            future = today + timedelta(days=i)
            dow = future.weekday()
            predicted = dow_avg.get(dow, sum(revenues) // len(revenues))
            forecast.append({
                "date": future.strftime("%Y-%m-%d"),
                "predicted_revenue_cents": predicted,
                "day_of_week": future.strftime("%A"),
            })

        forecast_total = sum(f["predicted_revenue_cents"] for f in forecast)

        # Payment processing fee analysis
        total_rev = sum(revenues[-30:]) if len(revenues) >= 30 else sum(revenues)
        card_txns = [t for t in txns if t.get("payment_method") in ("card", "credit_card", "debit_card", "CARD")]
        card_revenue = sum(t.get("total_cents", 0) for t in card_txns)
        # Estimate 2.6% + $0.10 per card transaction
        est_fees = int(card_revenue * 0.026 + len(card_txns) * 10)
        fee_pct = round(est_fees / max(total_rev, 1) * 100, 2)

        # Best day for large purchases (lowest revenue day = most cash buffer)
        if dow_avg:
            best_purchase_dow = min(dow_avg, key=dow_avg.get)
            day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            best_day = day_names[best_purchase_dow]
        else:
            best_day = "midweek"

        score = 70
        insights = []
        recommendations = []

        fee_range = self.get_benchmark_range("processing_fee_pct")
        fee_threshold = fee_range.high if fee_range else 3.0
        if fee_pct > fee_threshold:
            fee_insight = {"type": "high_fees", "detail": f"Processing fees consume {fee_pct}% of revenue (${est_fees/100:,.2f})"}
            if fee_range:
                fee_insight["benchmark"] = {"low": fee_range.low, "mid": fee_range.mid, "high": fee_range.high, "source": fee_range.source}
            fee_insight["estimated"] = path != "full"
            insights.append(fee_insight)
            recommendations.append({"action": f"Negotiate card processing rates — currently losing ${est_fees/100:,.2f}/month to fees", "impact_cents": est_fees // 3})
            score -= 10

        if best_day:
            recommendations.append({"action": f"Schedule large purchases on {best_day}s when revenue is lowest for best cash buffer", "impact_cents": 0})

        if path == "partial":
            recommendations.append({"action": "Connect POS line-item data for precise analysis", "impact": "Improves accuracy from estimated to actual values", "effort": "low"})

        return self._result(
            summary=f"Forecasted ${forecast_total/100:,.0f} over next 14 days, fees at {fee_pct}%",
            score=score,
            insights=insights,
            recommendations=recommendations,
            data={
                "forecast_14_day": forecast,
                "forecast_total_cents": forecast_total,
                "processing_fee_cents": est_fees,
                "fee_pct_of_revenue": fee_pct,
                "best_purchase_day": best_day,
                "card_transaction_count": len(card_txns),
            },
            confidence=confidence,
            calculation_path=path,
        )
