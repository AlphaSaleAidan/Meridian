from .base import BaseAgent
from collections import defaultdict


class EmployeePerformanceAgent(BaseAgent):
    name = "employee_performance"
    description = "Per-employee revenue, upsell, and tip analysis"
    tier = 4

    async def analyze(self) -> dict:
        avail = self.get_data_availability()

        if avail.is_full:
            confidence = avail.quality_score
            path = "full"
        elif avail.is_partial:
            confidence = avail.quality_score
            path = "partial"
        else:
            confidence = min(0.4, avail.quality_score)
            path = "minimal"

        txns = self.ctx.transactions
        with_employee = [t for t in txns if t.get("employee_name")]

        # --- MINIMAL path: no employee data at all ---
        if not avail.has_employees or len(with_employee) < 10:
            confidence = 0.0
            return self._insufficient_data(
                "No employee data — connect POS with employee tracking to enable performance analysis"
            )

        emp_stats = defaultdict(
            lambda: {"revenue": 0, "tips": 0, "txns": 0, "items": 0, "discounts": 0}
        )
        for t in with_employee:
            name = t["employee_name"]
            emp_stats[name]["revenue"] += t.get("total_cents", 0)
            emp_stats[name]["tips"] += t.get("tip_cents", 0)
            emp_stats[name]["txns"] += 1
            emp_stats[name]["discounts"] += t.get("discount_cents", 0)

        employees = []
        for name, s in emp_stats.items():
            avg_ticket = s["revenue"] // max(s["txns"], 1)
            tip_rate = round(s["tips"] / max(s["revenue"], 1) * 100, 1)
            employees.append({
                "employee": name,
                "total_revenue_cents": s["revenue"],
                "transaction_count": s["txns"],
                "avg_ticket_cents": avg_ticket,
                "tip_rate_pct": tip_rate,
                "total_tips_cents": s["tips"],
                "total_discounts_cents": s["discounts"],
            })

        employees.sort(key=lambda e: e["total_revenue_cents"], reverse=True)
        top = employees[0] if employees else None
        coaching = (
            [
                e for e in employees
                if e["avg_ticket_cents"] < employees[0]["avg_ticket_cents"] * 0.7
            ]
            if len(employees) > 1
            else []
        )

        overall_avg_ticket = (
            sum(e["avg_ticket_cents"] for e in employees)
            // max(len(employees), 1)
        )

        # Performance gap and revenue-if-leveled
        if len(employees) >= 2:
            top_ticket = employees[0]["avg_ticket_cents"]
            bottom_ticket = employees[-1]["avg_ticket_cents"]
            performance_gap = top_ticket - bottom_ticket
            bottom_txn_count = employees[-1]["transaction_count"]
            revenue_if_leveled = performance_gap * bottom_txn_count
        else:
            performance_gap = 0
            revenue_if_leveled = 0

        # FULL path: per-employee metrics with upsell rate
        if path == "full":
            confidence = 0.9
        # PARTIAL path: basic per-employee counts
        elif path == "partial":
            confidence = min(confidence, 0.7)

        score = 70

        insights = []
        if top:
            insights.append({
                "type": "top_performer",
                "detail": (
                    f"Top performer: {top['employee']}"
                    f" — ${top['total_revenue_cents'] / 100:,.0f} revenue,"
                    f" ${top['avg_ticket_cents'] / 100:.2f} avg ticket"
                ),
            })
        if coaching:
            insights.append({
                "type": "coaching_needed",
                "detail": (
                    f"{len(coaching)} employees significantly below"
                    " top performer on avg ticket"
                ),
            })

        recommendations = []
        if coaching:
            for c in coaching[:2]:
                gap = top["avg_ticket_cents"] - c["avg_ticket_cents"]
                recommendations.append({
                    "action": (
                        f"Coach {c['employee']} on upselling"
                        f" — ${gap / 100:.2f} below top performer per ticket"
                    ),
                    "impact_cents": gap * c["transaction_count"],
                })

        if path != "full":
            recommendations.append({
                "action": "Connect more data sources for precise analysis",
                "impact": "Improves accuracy from estimated to actual",
                "effort": "low",
            })

        return self._result(
            summary=(
                f"{len(employees)} employees tracked,"
                f" top: {top['employee'] if top else 'N/A'},"
                f" avg ticket ${overall_avg_ticket / 100:.2f}"
            ),
            score=score,
            insights=insights,
            recommendations=recommendations,
            data={
                "employees": employees,
                "top_performer": top,
                "coaching_candidates": coaching,
                "performance_gap_cents": performance_gap,
                "revenue_if_leveled_cents": revenue_if_leveled,
            },
            confidence=confidence,
            calculation_path=path,
        )
