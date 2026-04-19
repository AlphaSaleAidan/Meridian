"""
Weekly Report Generator — Compiles all analyses into a merchant report.

Generates a pre-computed weekly report snapshot that includes:
  • Revenue summary (total, change, trend)
  • Top & worst products
  • Key insights (top 5)
  • Forecast for next week
  • Money Left on Table score
  • Action items

These are stored as JSON in the weekly_reports table and can be
rendered as email, PDF, or dashboard view.
"""
import logging
from datetime import datetime, date, timedelta, timezone
from uuid import uuid4
from typing import Any

logger = logging.getLogger("meridian.ai.generators.reports")


class ReportGenerator:
    """Compiles weekly merchant reports."""

    MODEL_VERSION = "meridian-report-v1"

    def generate(
        self,
        ctx,
        revenue: dict,
        products: dict,
        patterns: dict,
        money_left: dict,
        insights: list[dict],
        forecasts: list[dict],
    ) -> dict:
        """
        Generate a complete weekly report.
        
        Returns a report dict ready for DB insertion.
        """
        now = datetime.now(timezone.utc)
        week_end = now.date()
        week_start = week_end - timedelta(days=6)

        # ── Revenue Section ───────────────────────────────────
        kpis = revenue.get("kpis", {})
        trend = revenue.get("trend", {})
        comparison = revenue.get("comparison", {})
        
        revenue_section = {
            "total_cents": kpis.get("total_revenue_cents", 0),
            "total_dollars": f"${kpis.get('total_revenue_cents', 0)/100:,.2f}",
            "transactions": kpis.get("total_transactions", 0),
            "avg_ticket_cents": kpis.get("avg_ticket_cents", 0),
            "avg_ticket_dollars": f"${kpis.get('avg_ticket_cents', 0)/100:,.2f}",
            "trend_direction": trend.get("direction", "unknown"),
            "wow_change_pct": trend.get("wow_growth_pct"),
            "vs_previous_period": {
                "revenue_change_pct": comparison.get("revenue_change_pct", 0),
                "transaction_change_pct": comparison.get("transaction_change_pct", 0),
                "ticket_change_pct": comparison.get("avg_ticket_change_pct", 0),
            },
            "daily_breakdown": revenue.get("daily_breakdown", [])[-7:],
        }

        # ── Product Section ───────────────────────────────────
        top_products = products.get("top_performers", [])[:5]
        worst_products = products.get("worst_performers", [])[:5]
        dead_stock = products.get("dead_stock", [])

        product_section = {
            "total_active": products.get("total_products", 0),
            "top_performers": [
                {
                    "name": p.get("name", "Unknown"),
                    "revenue_cents": p.get("revenue_cents", 0),
                    "revenue_dollars": f"${p.get('revenue_cents', 0)/100:,.2f}",
                    "times_sold": p.get("times_sold", 0),
                }
                for p in top_products
            ],
            "worst_performers": [
                {
                    "name": p.get("name", "Unknown"),
                    "revenue_cents": p.get("revenue_cents", 0),
                    "times_sold": p.get("times_sold", 0),
                }
                for p in worst_products
            ],
            "dead_stock_count": len(dead_stock),
            "concentration_risk": products.get("concentration_risk", {}).get("risk_level", "unknown"),
        }

        # ── Pattern Section ───────────────────────────────────
        peak_data = patterns.get("peak_hours", {})
        dow_data = patterns.get("day_of_week", {})

        pattern_section = {
            "golden_window": peak_data.get("golden_window", {}),
            "best_day": dow_data.get("best_day"),
            "worst_day": dow_data.get("worst_day"),
            "weekend_vs_weekday_pct": dow_data.get("weekend_vs_weekday_pct", 0),
            "payment_mix": patterns.get("payment_patterns", {}),
        }

        # ── Insights Section (top 5) ─────────────────────────
        top_insights = sorted(
            insights,
            key=lambda x: abs(x.get("estimated_monthly_impact_cents", 0)),
            reverse=True,
        )[:5]
        
        insight_section = [
            {
                "title": i.get("title", ""),
                "summary": i.get("summary", ""),
                "impact_cents": i.get("estimated_monthly_impact_cents", 0),
                "impact_dollars": f"${i.get('estimated_monthly_impact_cents', 0)/100:,.0f}",
                "type": i.get("type", "general"),
            }
            for i in top_insights
        ]

        # ── Forecast Section ──────────────────────────────────
        weekly_forecasts = [
            f for f in forecasts 
            if f.get("forecast_type") == "weekly_revenue"
        ][:2]
        
        forecast_section = {
            "next_week": (
                {
                    "predicted_cents": weekly_forecasts[0].get("predicted_value_cents", 0),
                    "predicted_dollars": f"${weekly_forecasts[0].get('predicted_value_cents', 0)/100:,.2f}",
                    "lower_bound_dollars": f"${weekly_forecasts[0].get('lower_bound_cents', 0)/100:,.2f}",
                    "upper_bound_dollars": f"${weekly_forecasts[0].get('upper_bound_cents', 0)/100:,.2f}",
                    "confidence": weekly_forecasts[0].get("confidence_score", 0),
                }
                if weekly_forecasts else None
            ),
        }

        # ── Money Left Score ──────────────────────────────────
        money_left_section = {
            "total_cents": money_left.get("total_score_cents", 0),
            "total_dollars": money_left.get("total_score_dollars", "$0"),
            "top_actions": [
                {
                    "description": a.get("description", ""),
                    "impact_dollars": f"${a.get('impact_cents', 0)/100:,.0f}",
                    "effort": a.get("effort", "medium"),
                }
                for a in money_left.get("top_actions", [])[:3]
            ],
        }

        # ── Assemble Report ───────────────────────────────────
        report_data = {
            "revenue": revenue_section,
            "products": product_section,
            "patterns": pattern_section,
            "insights": insight_section,
            "forecast": forecast_section,
            "money_left": money_left_section,
            "generated_at": now.isoformat(),
            "analysis_period_days": ctx.analysis_days,
        }

        report = {
            "id": str(uuid4()),
            "org_id": ctx.org_id,
            "location_id": ctx.location_id,
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "report_data": report_data,
            "model_version": self.MODEL_VERSION,
        }

        logger.info(
            f"Weekly report generated for {ctx.org_id}: "
            f"${kpis.get('total_revenue_cents', 0)/100:,.0f} revenue, "
            f"{len(insight_section)} insights"
        )
        return report
