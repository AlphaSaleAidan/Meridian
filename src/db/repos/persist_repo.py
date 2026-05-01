"""
Persist Repository — AI output persistence and migration runner.

Writes generated insights, forecasts, scores, and reports.
"""
import json
import logging
from pathlib import Path

logger = logging.getLogger("meridian.db.persist_repo")


class PersistRepo:
    """AI output persistence operations against the connection pool."""

    def __init__(self, pool):
        self._pool = pool

    async def save_insight(self, insight: dict) -> str:
        async with self._pool.acquire() as conn:
            return await conn.fetchval(
                """
                INSERT INTO insights (
                    id, org_id, location_id, type, title, summary,
                    details, estimated_monthly_impact_cents, confidence_score,
                    related_products, related_categories,
                    valid_until, model_version, metadata
                ) VALUES (
                    $1, $2, $3, $4::insight_type, $5, $6,
                    $7::jsonb, $8, $9, $10, $11, $12, $13, $14::jsonb
                )
                RETURNING id
                """,
                insight["id"], insight["org_id"], insight.get("location_id"),
                insight["type"], insight["title"], insight["summary"],
                json.dumps(insight.get("details", {})),
                insight.get("estimated_monthly_impact_cents"),
                insight.get("confidence_score"),
                insight.get("related_products", []),
                insight.get("related_categories", []),
                insight.get("valid_until"),
                insight.get("model_version", "meridian-v1"),
                json.dumps(insight.get("metadata", {})),
            )

    async def save_money_left_score(self, score: dict) -> str:
        async with self._pool.acquire() as conn:
            return await conn.fetchval(
                """
                INSERT INTO money_left_scores (
                    id, org_id, location_id, total_score_cents,
                    components, scored_at, model_version
                ) VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7)
                RETURNING id
                """,
                score["id"], score["org_id"], score.get("location_id"),
                score["total_score_cents"],
                json.dumps(score["components"]),
                score["scored_at"], score.get("model_version", "meridian-v1"),
            )

    async def save_forecasts(self, forecasts: list[dict]) -> int:
        if not forecasts:
            return 0

        async with self._pool.acquire() as conn:
            count = 0
            for f in forecasts:
                await conn.execute(
                    """
                    INSERT INTO forecasts (
                        id, org_id, location_id, forecast_type,
                        period_start, period_end,
                        predicted_value_cents, lower_bound_cents,
                        upper_bound_cents, confidence_score,
                        model_version, features_used, generated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12::jsonb, $13)
                    """,
                    f["id"], f["org_id"], f.get("location_id"),
                    f["forecast_type"], f["period_start"], f["period_end"],
                    f["predicted_value_cents"],
                    f.get("lower_bound_cents"), f.get("upper_bound_cents"),
                    f.get("confidence_score"),
                    f.get("model_version", "meridian-v1"),
                    json.dumps(f.get("features_used", {})),
                    f["generated_at"],
                )
                count += 1

            logger.info(f"Saved {count} forecasts for org {forecasts[0]['org_id']}")
            return count

    async def save_weekly_report(self, report: dict) -> str:
        async with self._pool.acquire() as conn:
            return await conn.fetchval(
                """
                INSERT INTO weekly_reports (
                    id, org_id, location_id, week_start, week_end,
                    report_data, model_version
                ) VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7)
                ON CONFLICT (org_id, location_id, week_start)
                DO UPDATE SET
                    report_data = EXCLUDED.report_data,
                    model_version = EXCLUDED.model_version
                RETURNING id
                """,
                report["id"], report["org_id"], report.get("location_id"),
                report["week_start"], report["week_end"],
                json.dumps(report["report_data"]),
                report.get("model_version", "meridian-v1"),
            )

    # ─── Migration Runner ─────────────────────────────────────

    async def run_migrations(self, migrations_dir: str) -> list[str]:
        migrations_path = Path(migrations_dir)
        files = sorted(migrations_path.glob("*.sql"))

        applied = []
        async with self._pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS _migrations (
                    filename TEXT PRIMARY KEY,
                    applied_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)

            for f in files:
                filename = f.name
                existing = await conn.fetchval(
                    "SELECT filename FROM _migrations WHERE filename = $1",
                    filename,
                )
                if existing:
                    logger.info(f"Migration {filename} already applied, skipping")
                    continue

                sql = f.read_text()
                try:
                    await conn.execute(sql)
                    await conn.execute(
                        "INSERT INTO _migrations (filename) VALUES ($1)",
                        filename,
                    )
                    applied.append(filename)
                    logger.info(f"Applied migration: {filename}")
                except Exception as e:
                    logger.error(f"Migration {filename} failed: {e}")
                    raise

        if applied:
            logger.info(f"Applied {len(applied)} migrations: {applied}")
        else:
            logger.info("No new migrations to apply")

        return applied
