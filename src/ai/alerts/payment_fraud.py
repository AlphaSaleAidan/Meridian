from .base import BaseAlert, AlertSeverity
from collections import defaultdict

class PaymentFraudAlert(BaseAlert):
    name = "payment_fraud"
    description = "Detects abnormal refund/void patterns"
    cooldown_hours = 24

    async def evaluate(self) -> list[dict]:
        txns = getattr(self.ctx, "transactions", []) or []
        if not txns:
            return self.no_alerts()

        alerts = []

        # Calculate daily refund/void rates
        daily_stats = defaultdict(lambda: {"total": 0, "refunds": 0, "voids": 0})
        employee_refunds = defaultdict(int)
        employee_txns = defaultdict(int)

        for t in txns:
            date = str(t.get("transaction_at", t.get("created_at", "")))[:10]
            daily_stats[date]["total"] += 1

            refund = t.get("refund_cents", 0) or 0
            is_void = t.get("is_void", False) or t.get("status") == "voided"

            if refund > 0:
                daily_stats[date]["refunds"] += 1
            if is_void:
                daily_stats[date]["voids"] += 1

            emp = t.get("employee_name", t.get("employee_id"))
            if emp:
                employee_txns[emp] += 1
                if refund > 0 or is_void:
                    employee_refunds[emp] += 1

        if not daily_stats:
            return self.no_alerts()

        # Overall refund rate
        sorted_dates = sorted(daily_stats.keys())
        refund_rates = []
        for d in sorted_dates:
            s = daily_stats[d]
            if s["total"] > 0:
                refund_rates.append((s["refunds"] + s["voids"]) / s["total"])

        if not refund_rates:
            return self.no_alerts()

        avg_rate = sum(refund_rates) / len(refund_rates)

        # Check today (latest date)
        today = sorted_dates[-1]
        today_stats = daily_stats[today]
        today_rate = (today_stats["refunds"] + today_stats["voids"]) / max(today_stats["total"], 1)

        if avg_rate > 0 and today_rate > avg_rate * 3:
            alerts.append(self.fire(
                AlertSeverity.WARNING,
                f"Refund/void rate 3x normal today ({today_rate:.0%} vs {avg_rate:.0%} avg)",
                f"Today: {today_stats['refunds']} refunds + {today_stats['voids']} voids "
                f"out of {today_stats['total']} transactions. Check for processing errors, "
                f"unhappy batch, or potential employee theft via fake refunds.",
                metric_value=today_rate,
                threshold=avg_rate * 3,
            ))

        # Check per-employee anomalies
        if employee_refunds and employee_txns:
            avg_emp_rate = sum(employee_refunds.values()) / max(sum(employee_txns.values()), 1)
            for emp, refund_count in employee_refunds.items():
                emp_rate = refund_count / max(employee_txns[emp], 1)
                if avg_emp_rate > 0 and emp_rate > avg_emp_rate * 5 and refund_count >= 3:
                    alerts.append(self.fire(
                        AlertSeverity.CRITICAL,
                        f"{emp}: 5x more refunds/voids than average",
                        f"{emp} processed {refund_count} refunds/voids ({emp_rate:.0%} of their "
                        f"transactions vs team avg {avg_emp_rate:.0%}). Review individual transactions.",
                        metric_value=emp_rate,
                        threshold=avg_emp_rate * 5,
                        metadata={"employee": emp, "refund_count": refund_count},
                    ))

        return alerts
