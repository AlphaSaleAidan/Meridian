from .base import BaseAlert, AlertSeverity

class EmployeeShiftAlert(BaseAlert):
    name = "employee_performance_shift"
    description = "Detects sudden changes in employee performance"
    cooldown_hours = 48

    async def evaluate(self) -> list[dict]:
        emp_output = self.agent_outputs.get("employee_performance", {})
        txns = getattr(self.ctx, "transactions", []) or []

        if not txns:
            return self.no_alerts()

        alerts = []

        # Check for employees with recent performance shifts
        emp_data = emp_output.get("data", {})
        employees = emp_data.get("employees", emp_data.get("employee_stats", []))
        if not isinstance(employees, list):
            employees = []

        for emp in employees:
            name = emp.get("name", emp.get("employee_name", "Employee"))
            avg_ticket = emp.get("avg_ticket_cents", 0)
            team_avg = emp_data.get("team_avg_ticket_cents", 0)

            if not avg_ticket or not team_avg:
                continue

            # Check for significant underperformance
            if avg_ticket < team_avg * 0.8 and avg_ticket > 0:
                gap_pct = (team_avg - avg_ticket) / team_avg * 100
                alerts.append(self.fire(
                    AlertSeverity.WARNING,
                    f"{name}: avg ticket {gap_pct:.0f}% below team average",
                    f"{name}'s avg ticket ${avg_ticket / 100:.2f} vs team avg "
                    f"${team_avg / 100:.2f}. Possible: less upselling, different shift mix, "
                    f"or needs coaching.",
                    metric_value=avg_ticket,
                    threshold=team_avg * 0.8,
                    metadata={"employee_name": name},
                ))

            # Check for exceptional performance
            if avg_ticket > team_avg * 1.2:
                lift_pct = (avg_ticket - team_avg) / team_avg * 100
                alerts.append(self.fire(
                    AlertSeverity.INFO,
                    f"{name} is crushing it — tickets up {lift_pct:.0f}%",
                    f"{name}'s avg ticket ${avg_ticket / 100:.2f} vs team avg "
                    f"${team_avg / 100:.2f}. Find out what changed and share with team.",
                    metric_value=avg_ticket,
                    threshold=team_avg * 1.2,
                    metadata={"employee_name": name},
                ))

        return alerts
