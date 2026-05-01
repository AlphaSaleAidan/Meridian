"""
Revenue Goal Tracker — Predictive 6.

Tracks monthly revenue goal progress with daily countdown,
pace metrics, and stretch analysis.
"""
import logging
from calendar import monthrange
from datetime import datetime, timezone

logger = logging.getLogger("meridian.ai.predictive.goals")


class GoalTrackerAgent:
    """Track monthly revenue goal progress and predict end-of-month."""

    name = "goal_tracker"
    tier = 6

    def __init__(self, ctx, agent_outputs: dict | None = None):
        self.ctx = ctx
        self.outputs = agent_outputs or getattr(ctx, "agent_outputs", {})

    async def analyze(self, monthly_goal_cents: int | None = None) -> dict:
        daily = self.ctx.daily_revenue or []
        if not daily:
            return {
                "agent_name": self.name,
                "status": "insufficient_data",
                "summary": "Need daily revenue data for goal tracking",
            }

        now = datetime.now(timezone.utc)
        year, month = now.year, now.month
        days_in_month = monthrange(year, month)[1]
        days_elapsed = now.day
        days_remaining = days_in_month - days_elapsed

        # Calculate MTD revenue
        current_month_str = f"{year}-{month:02d}"
        mtd_data = [
            d for d in daily
            if str(d.get("date", "")).startswith(current_month_str)
        ]
        actual_mtd = sum(d.get("revenue_cents", 0) for d in mtd_data)

        # Default goal: previous month * 1.05
        if monthly_goal_cents is None:
            prev_month_str = f"{year}-{month-1:02d}" if month > 1 else f"{year-1}-12"
            prev_data = [
                d for d in daily
                if str(d.get("date", "")).startswith(prev_month_str)
            ]
            prev_total = sum(d.get("revenue_cents", 0) for d in prev_data)
            if prev_total > 0:
                monthly_goal_cents = int(prev_total * 1.05)
            else:
                # Extrapolate from current
                if days_elapsed > 0:
                    monthly_goal_cents = int(actual_mtd / days_elapsed * days_in_month)
                else:
                    monthly_goal_cents = 0

        if monthly_goal_cents <= 0:
            return {
                "agent_name": self.name,
                "status": "no_goal",
                "summary": "No revenue goal set and insufficient history to estimate",
            }

        # Core metrics
        run_rate = actual_mtd / max(days_elapsed, 1)
        projected_eom = actual_mtd + int(run_rate * days_remaining)

        # Use forecaster agent for better projection if available
        forecaster = self.outputs.get("forecaster", {})
        forecast_remaining = 0
        if forecaster.get("status") == "complete":
            forecasts = forecaster.get("data", {}).get("daily_forecasts", [])
            for f in forecasts:
                fdate = f.get("date", "")
                if fdate.startswith(current_month_str):
                    forecast_remaining += f.get("predicted_cents", 0)
            if forecast_remaining > 0:
                projected_eom = actual_mtd + forecast_remaining

        # Pace metrics
        expected_by_now = monthly_goal_cents * days_elapsed / days_in_month
        pace = actual_mtd / max(expected_by_now, 1)

        needed_daily_avg = (monthly_goal_cents - actual_mtd) / max(days_remaining, 1)
        current_daily_avg = actual_mtd / max(days_elapsed, 1)
        stretch = needed_daily_avg / max(current_daily_avg, 1)

        if stretch < 1.0:
            status_label = "on_track"
            status_text = "On track to exceed goal"
        elif stretch <= 1.2:
            status_label = "achievable"
            status_text = "Achievable with effort"
        elif stretch <= 1.5:
            status_label = "stretch"
            status_text = "Stretch — requires above-average performance"
        else:
            status_label = "unlikely"
            status_text = "Unlikely without intervention"

        countdown = (
            f"Day {days_elapsed}/{days_in_month} | "
            f"${actual_mtd/100:,.0f}/${monthly_goal_cents/100:,.0f} | "
            f"Need ${needed_daily_avg/100:,.0f}/day "
            f"(currently averaging ${current_daily_avg/100:,.0f}) | "
            f"Pace: {pace*100:.0f}%"
        )

        return {
            "agent_name": self.name,
            "status": "complete",
            "summary": countdown,
            "goal_cents": monthly_goal_cents,
            "actual_mtd_cents": actual_mtd,
            "projected_eom_cents": projected_eom,
            "days_elapsed": days_elapsed,
            "days_remaining": days_remaining,
            "days_in_month": days_in_month,
            "run_rate_daily_cents": int(run_rate),
            "needed_daily_cents": int(needed_daily_avg),
            "pace": round(pace, 2),
            "stretch_factor": round(stretch, 2),
            "goal_status": status_label,
            "goal_status_text": status_text,
            "countdown_text": countdown,
            "using_forecast": forecast_remaining > 0,
            "confidence": 0.7 if days_elapsed >= 10 else 0.4,
            "data_quality": 0.7 if len(mtd_data) >= 7 else 0.4,
            "insights": [
                {
                    "type": "goal_tracking",
                    "title": f"Monthly Goal: {pace*100:.0f}% pace — {status_text}",
                    "detail": countdown,
                    "data_quality": 0.7,
                }
            ],
            "recommendations": self._get_recommendations(
                status_label, needed_daily_avg, current_daily_avg, days_remaining
            ),
        }

    def _get_recommendations(
        self, status: str, needed: float, current: float, days_left: int
    ) -> list[dict]:
        recs = []
        gap = needed - current

        if status == "on_track":
            recs.append({
                "action": "Maintain current performance — on track to exceed goal",
                "effort": "low",
            })
        elif status in ("achievable", "stretch"):
            recs.append({
                "action": (
                    f"Need ${gap/100:.0f}/day more. Push upsells and "
                    f"promote high-margin items this {'weekend' if days_left > 5 else 'week'}"
                ),
                "impact_cents": int(gap * days_left * 0.5),
                "effort": "medium",
            })
            if status == "stretch":
                recs.append({
                    "action": "Run a flash promotion to drive traffic in the next 5 days",
                    "impact_cents": int(gap * min(days_left, 5) * 0.3),
                    "effort": "high",
                })
        elif status == "unlikely":
            recs.append({
                "action": (
                    f"Goal requires ${needed/100:.0f}/day vs current ${current/100:.0f}/day. "
                    f"Consider adjusting goal or running aggressive promotions"
                ),
                "effort": "high",
            })

        return recs
