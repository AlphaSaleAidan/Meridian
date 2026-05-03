from .base import BaseAgent


class LoyaltyArchitectAgent(BaseAgent):
    name = "loyalty_architect"
    description = "Loyalty program design, redemption rates, reward ROI, and retention impact"
    tier = 3

    async def analyze(self) -> dict:
        transactions = self.ctx.transactions or []
        customers = getattr(self.ctx, "customers", [])
        loyalty = getattr(self.ctx, "loyalty_data", [])

        if not transactions:
            return self._insufficient_data("Transaction data")

        # Identify repeat customers from transaction data
        customer_txn_counts: dict[str, int] = {}
        customer_spend: dict[str, float] = {}
        for txn in transactions:
            cid = txn.get("customer_id") or txn.get("customer_email", "")
            if not cid:
                continue
            customer_txn_counts[cid] = customer_txn_counts.get(cid, 0) + 1
            customer_spend[cid] = customer_spend.get(cid, 0) + (
                txn.get("total_cents", 0) / 100
            )

        total_customers = max(len(customer_txn_counts), 1)
        repeat_customers = sum(1 for c in customer_txn_counts.values() if c >= 2)
        repeat_rate = repeat_customers / total_customers
        loyal_customers = sum(1 for c in customer_txn_counts.values() if c >= 5)
        loyal_rate = loyal_customers / total_customers

        avg_loyal_spend = 0
        avg_one_time_spend = 0
        loyal_ids = [cid for cid, cnt in customer_txn_counts.items() if cnt >= 5]
        one_time_ids = [cid for cid, cnt in customer_txn_counts.items() if cnt == 1]

        if loyal_ids:
            avg_loyal_spend = sum(customer_spend.get(c, 0) for c in loyal_ids) / len(loyal_ids)
        if one_time_ids:
            avg_one_time_spend = sum(customer_spend.get(c, 0) for c in one_time_ids) / len(one_time_ids)

        loyalty_multiplier = (avg_loyal_spend / avg_one_time_spend) if avg_one_time_spend > 0 else 0

        insights = []
        recommendations = []

        if repeat_rate < 0.25:
            insights.append({
                "type": "low_repeat_rate",
                "detail": f"Only {repeat_rate:.0%} of customers return — loyalty program could boost this significantly",
                "severity": "high",
            })
            recommendations.append({
                "action": "Launch a simple stamp-card or points-based loyalty program to incentivize return visits",
                "impact_estimate": "10-20% increase in repeat rate within 90 days",
            })

        if loyalty_multiplier > 3:
            insights.append({
                "type": "high_loyalty_value",
                "detail": f"Loyal customers spend {loyalty_multiplier:.1f}x more than one-time buyers — worth investing in retention",
                "severity": "medium",
            })
            recommendations.append({
                "action": "Create VIP tiers to reward top spenders and prevent churn",
                "impact_estimate": f"Protect ${avg_loyal_spend:.0f}/customer in lifetime value",
            })

        if loyal_rate > 0.15:
            insights.append({
                "type": "strong_loyalty_base",
                "detail": f"{loyal_rate:.0%} of customers are loyal (5+ visits) — this is above typical for most verticals",
                "severity": "low",
            })

        if not insights:
            insights.append({
                "type": "baseline_loyalty",
                "detail": f"Repeat rate: {repeat_rate:.0%}, loyal (5+ visits): {loyal_rate:.0%}",
                "severity": "info",
            })

        score = min(100, int(repeat_rate * 200 + loyal_rate * 200))

        return self._result(
            summary=f"Repeat rate {repeat_rate:.0%}, {loyal_customers} loyal customers ({loyal_rate:.0%}), loyalty multiplier {loyalty_multiplier:.1f}x",
            score=score,
            insights=insights,
            recommendations=recommendations,
            data={
                "total_customers": total_customers,
                "repeat_customers": repeat_customers,
                "repeat_rate": round(repeat_rate, 3),
                "loyal_customers": loyal_customers,
                "loyal_rate": round(loyal_rate, 3),
                "loyalty_multiplier": round(loyalty_multiplier, 2),
                "avg_loyal_spend": round(avg_loyal_spend, 2),
                "avg_one_time_spend": round(avg_one_time_spend, 2),
            },
        )
