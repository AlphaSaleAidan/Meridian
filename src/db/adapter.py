"""
AI Engine Database Adapter — Unified interface for AI analysis pipeline.

Wraps the SupabaseDB client with convenience methods for:
  • Loading AnalysisContext data (daily, hourly, products, transactions, inventory)
  • Persisting AI outputs (insights, forecasts, alerts, agent outputs)
  • Org metadata lookup (business_vertical, timezone, tier)

Usage:
    from src.db.adapter import AIAdapter
    adapter = AIAdapter(supabase_db)
    ctx = await adapter.load_context(org_id, days=30)
"""
import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger("meridian.db.adapter")


class AIAdapter:
    """Thin adapter over SupabaseDB for the AI engine."""

    def __init__(self, db):
        self._db = db

    # ─── Context Loading ─────────────────────────────────────

    async def get_daily_revenue(self, org_id: str, days: int = 30) -> list:
        return await self._db.get_daily_revenue(org_id, days)

    async def get_hourly_revenue(self, org_id: str, days: int = 30) -> list:
        return await self._db.get_hourly_revenue(org_id, days)

    async def get_product_performance(self, org_id: str, days: int = 30) -> list:
        return await self._db.get_product_performance(org_id, days)

    async def get_transaction_details(self, org_id: str, days: int = 30) -> list:
        return await self._db.get_transaction_details(org_id, days)

    async def get_inventory_current(self, org_id: str) -> list:
        return await self._db.get_inventory_current(org_id)

    async def get_org_metadata(self, org_id: str) -> dict:
        """Fetch org business_vertical, timezone, and tier."""
        try:
            row = await self._db.fetchrow(
                """
                SELECT business_type, timezone, plan_tier
                FROM organizations
                WHERE id = $1
                """,
                org_id,
            )
            if row:
                return {
                    "business_vertical": row["business_type"] or "other",
                    "timezone": row["timezone"] or "America/Los_Angeles",
                    "tier": row["plan_tier"] or "starter",
                }
        except Exception as e:
            logger.warning(f"Failed to fetch org metadata for {org_id}: {e}")
        return {
            "business_vertical": "other",
            "timezone": "America/Los_Angeles",
            "tier": "starter",
        }

    # ─── Persist Results ─────────────────────────────────────

    async def save_insight(self, insight: dict) -> str:
        return await self._db.save_insight(insight)

    async def save_money_left_score(self, score: dict) -> str:
        return await self._db.save_money_left_score(score)

    async def save_forecasts(self, forecasts: list[dict]) -> int:
        return await self._db.save_forecasts(forecasts)

    async def save_weekly_report(self, report: dict) -> str:
        return await self._db.save_weekly_report(report)

    async def save_alerts(self, org_id: str, alerts: list[dict]) -> int:
        """Persist fired alerts to the alerts table."""
        if not alerts:
            return 0
        count = 0
        for alert in alerts:
            try:
                await self._db.execute(
                    """
                    INSERT INTO alerts (
                        id, org_id, alert_name, severity, title,
                        detail, metric_value, threshold,
                        impact_cents, metadata, fired_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10::jsonb, $11)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    alert.get("id", str(uuid4())),
                    org_id,
                    alert.get("alert_name", "unknown"),
                    alert.get("severity", "info"),
                    alert.get("title", ""),
                    alert.get("detail", ""),
                    alert.get("metric_value"),
                    alert.get("threshold"),
                    alert.get("impact_cents"),
                    json.dumps(alert.get("metadata", {})),
                    alert.get("fired_at", datetime.now(timezone.utc)),
                )
                count += 1
            except Exception as e:
                logger.error(f"Failed to save alert: {e}")
        return count

    async def save_agent_outputs(self, org_id: str, outputs: dict) -> None:
        """Save the full agent swarm output snapshot."""
        try:
            await self._db.execute(
                """
                INSERT INTO agent_outputs (
                    id, org_id, outputs, generated_at
                ) VALUES ($1, $2, $3::jsonb, $4)
                """,
                str(uuid4()),
                org_id,
                json.dumps(outputs, default=str),
                datetime.now(timezone.utc),
            )
        except Exception as e:
            logger.error(f"Failed to save agent outputs for {org_id}: {e}")
