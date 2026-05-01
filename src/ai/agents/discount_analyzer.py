from .base import BaseAgent

class DiscountAnalyzerAgent(BaseAgent):
    name = "discount_analyzer"
    description = "Discount ROI and cannibalization analysis"
    tier = 1

    async def analyze(self) -> dict:
        path, confidence = self._select_path()
        txns = self.ctx.transactions

        if path == "minimal" or len(txns) < 10:
            if len(txns) < 10 and path != "minimal":
                return self._insufficient_data("At least 10 transactions")
            bench = self.get_benchmark_range("healthy_discount_rate_pct")
            bench_discount = bench.mid if bench else 4.0
            return self._benchmark_fallback(
                "healthy_discount_rate_pct",
                f"Estimated healthy discount rate ~{bench_discount}% (industry benchmark)",
                {"benchmark_discount_pct": bench_discount, "transaction_count": len(txns)},
            )

        discounted = [t for t in txns if t.get("discount_cents", 0) > 0]
        non_discounted = [t for t in txns if t.get("discount_cents", 0) == 0]

        total_revenue = sum(t.get("total_cents", 0) for t in txns)
        total_discount = sum(t.get("discount_cents", 0) for t in discounted)
        discount_pct_of_revenue = round(total_discount / max(total_revenue, 1) * 100, 1)

        discount_addiction_score = round(len(discounted) / max(len(txns), 1) * 100, 1)

        avg_discounted_ticket = sum(t.get("total_cents", 0) for t in discounted) // max(len(discounted), 1) if discounted else 0
        avg_normal_ticket = sum(t.get("total_cents", 0) for t in non_discounted) // max(len(non_discounted), 1) if non_discounted else 0

        # Discount ROI: did discounts lift total ticket size enough to justify?
        if avg_normal_ticket > 0 and avg_discounted_ticket > 0:
            avg_discount_per_txn = total_discount // max(len(discounted), 1)
            lift = avg_discounted_ticket - avg_normal_ticket + avg_discount_per_txn
            roi = round(lift / max(avg_discount_per_txn, 1) * 100 - 100, 1)
        else:
            roi = 0.0

        discount_range = self.get_benchmark_range("healthy_discount_rate_pct")
        benchmark_max = discount_range.mid if discount_range else (self.get_benchmark("healthy_discount_rate_pct") or 4.0)
        score = max(0, 100 - max(0, (discount_pct_of_revenue - benchmark_max) * 15))

        insights = []
        if discount_pct_of_revenue > benchmark_max:
            disc_insight = {"type": "excessive_discounting", "detail": f"Discounts at {discount_pct_of_revenue}% of revenue (healthy max: {benchmark_max}%)", "severity": "high"}
            if discount_range:
                disc_insight["benchmark"] = {"low": discount_range.low, "mid": discount_range.mid, "high": discount_range.high, "source": discount_range.source}
            disc_insight["estimated"] = path != "full"
            insights.append(disc_insight)
        if discount_addiction_score > 30:
            insights.append({"type": "discount_addiction", "detail": f"{discount_addiction_score}% of transactions are discounted — customers may be trained to expect deals", "estimated": path != "full"})

        recommendations = []
        if discount_pct_of_revenue > benchmark_max:
            savings = int(total_revenue * (discount_pct_of_revenue - benchmark_max) / 100)
            recommendations.append({"action": f"Reduce discount rate from {discount_pct_of_revenue}% to {benchmark_max}%", "impact_cents": savings})
        if discount_addiction_score > 30:
            recommendations.append({"action": "Shift from blanket discounts to targeted, time-limited promotions", "impact_cents": 0})

        if path == "partial":
            recommendations.append({"action": "Connect POS line-item data for precise analysis", "impact": "Improves accuracy from estimated to actual values", "effort": "low"})

        return self._result(
            summary=f"Discounts at {discount_pct_of_revenue}% of revenue, ROI {roi}%, addiction score {discount_addiction_score}%",
            score=score,
            insights=insights,
            recommendations=recommendations,
            data={
                "total_discount_cents": total_discount,
                "discount_pct_of_revenue": discount_pct_of_revenue,
                "discount_addiction_score": discount_addiction_score,
                "discount_roi_pct": roi,
                "avg_discounted_ticket_cents": avg_discounted_ticket,
                "avg_normal_ticket_cents": avg_normal_ticket,
                "discounted_txn_count": len(discounted),
                "total_txn_count": len(txns),
            },
            confidence=confidence,
            calculation_path=path,
        )
