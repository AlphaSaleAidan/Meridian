from .base import BaseAgent
from collections import defaultdict


class PaymentOptimizerAgent(BaseAgent):
    name = "payment_optimizer"
    description = "Payment method mix and fee optimization"
    tier = 4

    async def analyze(self) -> dict:
        path, confidence = self._select_path()
        txns = self.ctx.transactions
        if len(txns) < 10:
            return self._insufficient_data("At least 10 transactions")

        # Check if tender_type / payment_method is actually populated
        has_payment_data = any(
            t.get("payment_method") or t.get("tender_type")
            for t in txns[:50]
        )

        # --- MINIMAL path: use industry card/cash split ---
        if path == "minimal" or not has_payment_data:
            confidence = 0.3
            bench = self.get_benchmark_range("card_payment_share_pct")
            source = bench.source if bench else "industry default"
            card_share = bench.mid if bench else 70
            total_rev = sum(t.get("total_cents", 0) for t in txns)
            est_card_rev = int(total_rev * card_share / 100)
            est_fees = int(est_card_rev * 0.026)
            fee_savings_if_more_cash = int(est_card_rev * 0.10 * 0.026)
            return self._result(
                summary=f"Payment mix estimated from industry benchmarks ({card_share}% card, source: {source})",
                score=50,
                insights=[{
                    "type": "estimated_payment_mix",
                    "detail": f"Estimated {card_share}% card / {100 - card_share}% cash (source: {source})",
                }],
                recommendations=[
                    {
                        "action": "Connect more data sources for precise analysis",
                        "impact": "Improves accuracy from estimated to actual",
                        "effort": "low",
                    },
                    {
                        "action": f"Shift 10% from card to cash to save ~${fee_savings_if_more_cash / 100:,.0f}",
                        "impact_cents": fee_savings_if_more_cash,
                    },
                ],
                data={
                    "estimated_card_share_pct": card_share,
                    "est_monthly_fees_cents": est_fees,
                    "fee_savings_if_more_cash_cents": fee_savings_if_more_cash,
                    "benchmark_source": source,
                },
                confidence=confidence,
                calculation_path="minimal",
            )

        # Adjust confidence: real payment data present
        if has_payment_data:
            confidence = max(confidence, 0.85)

        method_stats = defaultdict(
            lambda: {"count": 0, "revenue": 0, "refunds": 0}
        )
        for t in txns:
            method = (t.get("payment_method") or t.get("tender_type") or "unknown").lower()
            method_stats[method]["count"] += 1
            method_stats[method]["revenue"] += t.get("total_cents", 0)

        total_rev = sum(s["revenue"] for s in method_stats.values())
        total_txns = sum(s["count"] for s in method_stats.values())

        breakdown = []
        for method, s in sorted(
            method_stats.items(), key=lambda x: -x[1]["revenue"]
        ):
            share = round(s["revenue"] / max(total_rev, 1) * 100, 1)
            breakdown.append({
                "method": method,
                "count": s["count"],
                "revenue_cents": s["revenue"],
                "share_pct": share,
            })

        # Fee estimation (2.6% + $0.10 for card, 0% for cash)
        card_methods = {
            "card", "credit_card", "debit_card",
            "visa", "mastercard", "amex", "discover",
        }
        card_rev = sum(
            s["revenue"] for m, s in method_stats.items()
            if m in card_methods
        )
        card_count = sum(
            s["count"] for m, s in method_stats.items()
            if m in card_methods
        )
        est_monthly_fees = int(card_rev * 0.026 + card_count * 10)
        cash_rev = method_stats.get("cash", {}).get("revenue", 0)

        # Nudge-to-cash savings
        nudge_target = min(card_rev * 0.1, card_rev)
        nudge_savings = int(nudge_target * 0.026 + (card_count * 0.1) * 10)

        # Fee savings if 10% shifts from card to cash
        fee_savings_if_more_cash = int(card_rev * 0.10 * 0.026 + (card_count * 0.10) * 10)

        fee_pct = round(est_monthly_fees / max(total_rev, 1) * 100, 2)
        score = max(0, 100 - max(0, (fee_pct - 2.5) * 20))

        insights = []
        insights.append({
            "type": "fee_analysis",
            "detail": (
                f"Estimated processing fees:"
                f" ${est_monthly_fees / 100:,.2f} ({fee_pct}% of revenue)"
            ),
        })
        if cash_rev < total_rev * 0.1:
            insights.append({
                "type": "low_cash",
                "detail": "Less than 10% cash — high fee exposure",
            })

        recommendations = []
        if nudge_savings > 500:
            recommendations.append({
                "action": (
                    "Incentivize cash payments (e.g. small discount)"
                    f" to save ~${nudge_savings / 100:,.0f}/month in fees"
                ),
                "impact_cents": nudge_savings,
            })
        if fee_pct > 3.0:
            recommendations.append({
                "action": (
                    "Negotiate lower processing rates"
                    " — current fees above 3%"
                ),
                "impact_cents": int(est_monthly_fees * 0.15),
            })

        if path != "full":
            recommendations.append({
                "action": "Connect more data sources for precise analysis",
                "impact": "Improves accuracy from estimated to actual",
                "effort": "low",
            })

        return self._result(
            summary=(
                f"Processing fees ${est_monthly_fees / 100:,.0f}/month"
                f" ({fee_pct}%), {len(breakdown)} payment methods"
            ),
            score=score,
            insights=insights,
            recommendations=recommendations,
            data={
                "payment_breakdown": breakdown,
                "est_monthly_fees_cents": est_monthly_fees,
                "fee_pct": fee_pct,
                "nudge_to_cash_savings_cents": nudge_savings,
                "fee_savings_if_more_cash_cents": fee_savings_if_more_cash,
            },
            confidence=confidence,
            calculation_path=path,
        )
