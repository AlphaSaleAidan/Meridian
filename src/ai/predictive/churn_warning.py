"""
Churn Early Warning System — Predictive 2.

For businesses with identifiable repeat customers (card fingerprint,
loyalty ID, or tender pattern), detects churn signals and estimates
revenue at risk.
"""
import logging
import math
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("meridian.ai.predictive.churn")


class ChurnWarningAgent:
    """Detect customer churn signals and prioritize win-back targets."""

    name = "churn_warning"
    tier = 6

    def __init__(self, ctx, agent_outputs: dict | None = None):
        self.ctx = ctx
        self.outputs = agent_outputs or getattr(ctx, "agent_outputs", {})

    async def analyze(self) -> dict:
        txns = self.ctx.transactions or []
        if len(txns) < 20:
            return {
                "agent_name": self.name,
                "status": "insufficient_data",
                "summary": "Need 20+ transactions for churn analysis",
            }

        # Build customer profiles from card fingerprint or customer_id
        customers = self._build_customer_profiles(txns)
        if len(customers) < 5:
            return {
                "agent_name": self.name,
                "status": "insufficient_data",
                "summary": "Need 5+ identifiable repeat customers",
            }

        # Segment customers
        segments = {"regulars": [], "occasionals": [], "at_risk": [], "churned": []}
        now = datetime.now(timezone.utc)

        for cid, profile in customers.items():
            visits = profile["visit_count"]
            avg_interval = profile["avg_interval_days"]
            days_since_last = (now - profile["last_visit"]).days
            monthly_value = profile["total_cents"] / max(profile["span_days"], 1) * 30

            # Churn probability: sigmoid(days_since_last / avg_interval - 2)
            if avg_interval > 0:
                x = days_since_last / avg_interval - 2
            else:
                x = 0
            churn_prob = 1 / (1 + math.exp(-x))

            # Adjustments
            if profile.get("ticket_trend") == "declining":
                churn_prob = min(1.0, churn_prob + 0.1)
            elif profile.get("ticket_trend") == "growing":
                churn_prob = max(0.0, churn_prob - 0.1)

            profile["churn_probability"] = round(churn_prob, 3)
            profile["monthly_value_cents"] = int(monthly_value)
            profile["days_since_last"] = days_since_last
            profile["customer_id"] = cid

            if visits >= 4 and days_since_last <= avg_interval * 1.5:
                segments["regulars"].append(profile)
            elif days_since_last > avg_interval * 4:
                segments["churned"].append(profile)
            elif days_since_last > avg_interval * 2:
                segments["at_risk"].append(profile)
            else:
                segments["occasionals"].append(profile)

        # Revenue at risk
        at_risk = segments["at_risk"]
        churn_revenue = sum(
            int(c["churn_probability"] * c["monthly_value_cents"]) for c in at_risk
        )

        # Win-back priority: monthly_value * (1 - churn_probability)
        win_back = sorted(
            at_risk,
            key=lambda c: c["monthly_value_cents"] * (1 - c["churn_probability"]),
            reverse=True,
        )[:10]

        return {
            "agent_name": self.name,
            "status": "complete",
            "summary": (
                f"${churn_revenue/100:.0f}/month at risk from "
                f"{len(at_risk)} customers showing churn signals"
            ),
            "segments": {
                "regulars": len(segments["regulars"]),
                "occasionals": len(segments["occasionals"]),
                "at_risk": len(segments["at_risk"]),
                "churned": len(segments["churned"]),
            },
            "churn_revenue_at_risk_cents": churn_revenue,
            "win_back_priority": [
                {
                    "customer_id": c["customer_id"],
                    "monthly_value_cents": c["monthly_value_cents"],
                    "churn_probability": c["churn_probability"],
                    "days_since_last": c["days_since_last"],
                    "visit_count": c["visit_count"],
                }
                for c in win_back[:5]
            ],
            "total_customers_tracked": len(customers),
            "data_quality": 0.6 if len(customers) >= 20 else 0.4,
            "insights": [
                {
                    "type": "churn_warning",
                    "title": (
                        f"${churn_revenue/100:.0f}/month revenue at risk from "
                        f"{len(at_risk)} customers showing churn signals"
                    ),
                    "detail": (
                        f"Top {min(5, len(win_back))} customers to save represent "
                        f"${sum(c['monthly_value_cents'] for c in win_back[:5])/100:.0f}/month"
                    ),
                    "severity": "warning" if churn_revenue > 10000 else "info",
                    "data_quality": 0.6,
                }
            ],
            "recommendations": [
                {
                    "action": "Launch targeted win-back campaign for top 5 at-risk customers",
                    "impact_cents": int(churn_revenue * 0.3),
                    "effort": "medium",
                },
                {
                    "action": "Implement loyalty program to increase visit frequency",
                    "impact_cents": int(churn_revenue * 0.5),
                    "effort": "high",
                },
            ],
        }

    def _build_customer_profiles(self, txns: list[dict]) -> dict:
        """Group transactions by customer identifier."""
        profiles: dict[str, dict] = {}

        for t in txns:
            cid = (
                t.get("customer_id")
                or t.get("card_fingerprint")
                or t.get("card_brand", "") + t.get("last_4", "")
            )
            if not cid or len(cid) < 3:
                continue

            ts = t.get("created_at") or t.get("date") or ""
            try:
                visit_time = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            except (ValueError, TypeError):
                continue

            amount = t.get("total_cents", 0) or t.get("amount_cents", 0) or 0

            if cid not in profiles:
                profiles[cid] = {
                    "visit_count": 0,
                    "total_cents": 0,
                    "visits": [],
                    "tickets": [],
                }

            profiles[cid]["visit_count"] += 1
            profiles[cid]["total_cents"] += amount
            profiles[cid]["visits"].append(visit_time)
            profiles[cid]["tickets"].append(amount)

        # Calculate derived metrics
        result = {}
        for cid, p in profiles.items():
            if p["visit_count"] < 2:
                continue

            visits = sorted(p["visits"])
            intervals = [
                (visits[i+1] - visits[i]).days
                for i in range(len(visits) - 1)
            ]
            avg_interval = sum(intervals) / len(intervals) if intervals else 30
            span_days = max((visits[-1] - visits[0]).days, 1)

            # Ticket trend
            tickets = p["tickets"]
            if len(tickets) >= 4:
                first_half = sum(tickets[:len(tickets)//2]) / (len(tickets)//2)
                second_half = sum(tickets[len(tickets)//2:]) / (len(tickets) - len(tickets)//2)
                if second_half < first_half * 0.9:
                    ticket_trend = "declining"
                elif second_half > first_half * 1.1:
                    ticket_trend = "growing"
                else:
                    ticket_trend = "stable"
            else:
                ticket_trend = "unknown"

            result[cid] = {
                "visit_count": p["visit_count"],
                "total_cents": p["total_cents"],
                "avg_ticket_cents": p["total_cents"] // p["visit_count"],
                "avg_interval_days": round(avg_interval, 1),
                "span_days": span_days,
                "first_visit": visits[0],
                "last_visit": visits[-1],
                "ticket_trend": ticket_trend,
            }

        return result
