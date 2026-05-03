from .base import BaseAgent
from collections import defaultdict


class LocationAnalystAgent(BaseAgent):
    name = "location_analyst"
    description = "Multi-location comparison, best-practice transfer, and underperformance flags"
    tier = 3

    async def analyze(self) -> dict:
        transactions = self.ctx.transactions or []

        if not transactions:
            return self._insufficient_data("Transaction data")

        # Group by location
        loc_revenue: dict[str, float] = defaultdict(float)
        loc_txn_count: dict[str, int] = defaultdict(int)
        loc_tickets: dict[str, list] = defaultdict(list)

        for txn in transactions:
            loc = txn.get("location_id") or txn.get("location_name", "primary")
            amount = txn.get("total_cents", 0) / 100
            loc_revenue[loc] += amount
            loc_txn_count[loc] += 1
            loc_tickets[loc].append(amount)

        locations = list(loc_revenue.keys())

        if len(locations) <= 1:
            loc = locations[0] if locations else "primary"
            total_rev = loc_revenue.get(loc, 0)
            total_txns = loc_txn_count.get(loc, 0)
            avg_ticket = total_rev / max(total_txns, 1)

            return self._result(
                summary=f"Single location — ${total_rev:,.0f} revenue, {total_txns} transactions, ${avg_ticket:.2f} avg ticket",
                score=50,
                insights=[{
                    "type": "single_location",
                    "detail": "Only one location detected. Multi-location comparison will activate when additional locations connect.",
                    "severity": "info",
                }],
                recommendations=[{
                    "action": "When expanding, connect all locations to Meridian from day one for real-time cross-location analytics",
                    "impact_estimate": "Enables data-driven site selection and performance benchmarking",
                }],
                data={
                    "location_count": 1,
                    "total_revenue": round(total_rev, 2),
                    "total_transactions": total_txns,
                },
            )

        # Multi-location analysis
        loc_stats = []
        for loc in locations:
            rev = loc_revenue[loc]
            txns = loc_txn_count[loc]
            tickets = loc_tickets[loc]
            avg_ticket = rev / max(txns, 1)
            loc_stats.append({
                "location": loc,
                "revenue": round(rev, 2),
                "transactions": txns,
                "avg_ticket": round(avg_ticket, 2),
                "median_ticket": round(sorted(tickets)[len(tickets) // 2], 2) if tickets else 0,
            })

        loc_stats.sort(key=lambda x: x["revenue"], reverse=True)
        avg_revenue = sum(s["revenue"] for s in loc_stats) / len(loc_stats)
        avg_ticket_all = sum(s["avg_ticket"] for s in loc_stats) / len(loc_stats)

        best = loc_stats[0]
        worst = loc_stats[-1]

        insights = []
        recommendations = []

        # Revenue spread
        revenue_spread = (best["revenue"] - worst["revenue"]) / max(avg_revenue, 1)
        if revenue_spread > 0.5:
            insights.append({
                "type": "wide_revenue_gap",
                "detail": (
                    f"Top location ({best['location']}) earns ${best['revenue']:,.0f} vs "
                    f"bottom ({worst['location']}) at ${worst['revenue']:,.0f} — "
                    f"{revenue_spread:.0%} gap from average"
                ),
                "severity": "high",
            })
            recommendations.append({
                "action": f"Audit {worst['location']} operations — staffing, hours, product mix, and local marketing",
                "impact_estimate": f"Closing half the gap adds ~${(best['revenue'] - worst['revenue']) / 4:,.0f}",
            })

        # Ticket comparison
        if best["avg_ticket"] > worst["avg_ticket"] * 1.3:
            insights.append({
                "type": "ticket_size_variance",
                "detail": (
                    f"{best['location']} avg ticket ${best['avg_ticket']:.2f} vs "
                    f"{worst['location']} ${worst['avg_ticket']:.2f} — "
                    f"suggests upsell/menu differences"
                ),
                "severity": "medium",
            })
            recommendations.append({
                "action": f"Transfer {best['location']}'s upsell tactics and product mix to {worst['location']}",
                "impact_estimate": "5-15% ticket size increase at underperforming locations",
            })

        if not insights:
            insights.append({
                "type": "balanced_locations",
                "detail": f"All {len(locations)} locations performing within normal range",
                "severity": "info",
            })

        score = max(20, 100 - int(revenue_spread * 40))

        return self._result(
            summary=(
                f"{len(locations)} locations analyzed — top: {best['location']} (${best['revenue']:,.0f}), "
                f"bottom: {worst['location']} (${worst['revenue']:,.0f}), spread {revenue_spread:.0%}"
            ),
            score=score,
            insights=insights,
            recommendations=recommendations,
            data={
                "location_count": len(locations),
                "locations": loc_stats,
                "avg_revenue": round(avg_revenue, 2),
                "avg_ticket_all": round(avg_ticket_all, 2),
                "revenue_spread": round(revenue_spread, 3),
            },
        )
