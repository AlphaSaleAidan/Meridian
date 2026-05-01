from .base import BaseAgent
from collections import defaultdict
import math


class StaffingAgent(BaseAgent):
    name = "staffing"
    description = "Optimal headcount per hour and labor efficiency"
    tier = 4

    async def analyze(self) -> dict:
        path, confidence = self._select_path()
        hourly = self.ctx.hourly_revenue

        # --- MINIMAL path: skip, not enough data ---
        if path == "minimal" or len(hourly) < 24:
            return self._insufficient_data(
                "Need hourly transaction data for staffing analysis — connect POS with hourly breakdowns"
            )

        # Avg transactions per hour
        hour_txns = defaultdict(list)
        for h in hourly:
            hour = h.get("hour", 0)
            hour_txns[hour].append(h.get("transaction_count", 0))

        # FULL path: hourly txns + employee data -> ideal headcount
        if avail.has_employees and len(hourly) >= 24:
            confidence = 0.7
            path = "full"
        else:
            # PARTIAL path: hourly txns only -> estimate ideal
            confidence = 0.4
            path = "partial"

        # Target: 15 transactions per employee per hour
        TXN_PER_EMPLOYEE = 15
        hourly_recs = []
        overstaffed = []
        understaffed = []

        for hour in range(24):
            counts = hour_txns.get(hour, [0])
            avg_txns = sum(counts) / max(len(counts), 1)
            optimal = max(1, math.ceil(avg_txns / TXN_PER_EMPLOYEE))
            hour_entries = [
                h for h in hourly if h.get("hour") == hour
            ]
            rev_sum = sum(
                h.get("revenue_cents", 0) for h in hour_entries
            )
            avg_rev = rev_sum // max(len(hour_entries), 1)

            entry = {
                "hour": hour,
                "avg_transactions": round(avg_txns, 1),
                "ideal_staff": optimal,
                "optimal_staff": optimal,
                "avg_revenue_cents": avg_rev,
            }
            hourly_recs.append(entry)

            if avg_txns < TXN_PER_EMPLOYEE * 0.5 and optimal > 0:
                overstaffed.append({
                    **entry,
                    "reason": "Very low transaction volume",
                })
            elif avg_txns > TXN_PER_EMPLOYEE * 1.5:
                understaffed.append({
                    **entry,
                    "reason": (
                        "High transaction volume — potential lost sales"
                    ),
                })

        score = max(
            0, 100 - len(overstaffed) * 5 - len(understaffed) * 10
        )

        insights = []
        if overstaffed:
            insights.append({
                "type": "overstaffed",
                "detail": f"{len(overstaffed)} hours likely overstaffed",
            })
        if understaffed:
            insights.append({
                "type": "understaffed",
                "detail": (
                    f"{len(understaffed)} hours likely understaffed"
                    " — potential lost sales"
                ),
            })

        recommendations = []
        if overstaffed:
            hours = ", ".join(f"{h['hour']}:00" for h in overstaffed[:3])
            recommendations.append({
                "action": f"Reduce staffing during: {hours}",
                "impact_cents": 0,
            })
        if understaffed:
            hours = ", ".join(f"{h['hour']}:00" for h in understaffed[:3])
            recommendations.append({
                "action": (
                    f"Add staff during peak: {hours}"
                    " — understaffed, losing sales"
                ),
                "impact_cents": 0,
            })

        if path != "full":
            recommendations.append({
                "action": "Connect more data sources for precise analysis",
                "impact": "Improves accuracy from estimated to actual",
                "effort": "low",
            })

        return self._result(
            summary=(
                f"{len(overstaffed)} overstaffed hours,"
                f" {len(understaffed)} understaffed hours"
            ),
            score=score,
            insights=insights,
            recommendations=recommendations,
            data={
                "hourly_staffing": hourly_recs,
                "overstaffed_hours": overstaffed,
                "understaffed_hours": understaffed,
                "target_txn_per_employee": TXN_PER_EMPLOYEE,
            },
            confidence=confidence,
            calculation_path=path,
        )
