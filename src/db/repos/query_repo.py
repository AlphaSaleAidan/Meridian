"""
Query Repository — Analytics queries for the AI engine.

Read-only queries against materialized views and aggregation tables.
"""
import logging

logger = logging.getLogger("meridian.db.query_repo")


class QueryRepo:
    """Analytics query operations against the connection pool."""

    def __init__(self, pool):
        self._pool = pool

    async def get_daily_revenue(self, org_id: str, days: int = 30) -> list:
        return await self._pool.fetch(
            """
            SELECT
                day_bucket::date as date,
                transaction_count,
                total_revenue_cents,
                avg_ticket_cents,
                total_tax_cents,
                total_tip_cents,
                total_discount_cents,
                total_customers,
                refund_total_cents,
                refund_count
            FROM daily_revenue
            WHERE org_id = $1
              AND day_bucket >= CURRENT_DATE - ($2 || ' days')::INTERVAL
            ORDER BY day_bucket
            """,
            org_id, str(days),
        )

    async def get_hourly_revenue(self, org_id: str, days: int = 30) -> list:
        return await self._pool.fetch(
            """
            SELECT
                hour_bucket,
                transaction_count,
                total_revenue_cents,
                avg_ticket_cents,
                cash_count, credit_count, debit_count, mobile_count,
                sale_count, refund_count, void_count
            FROM hourly_revenue
            WHERE org_id = $1
              AND hour_bucket >= NOW() - ($2 || ' days')::INTERVAL
            ORDER BY hour_bucket
            """,
            org_id, str(days),
        )

    async def get_product_performance(self, org_id: str, days: int = 30) -> list:
        return await self._pool.fetch(
            """
            SELECT
                dpp.product_id,
                p.name AS product_name,
                p.sku,
                p.price_cents AS current_price_cents,
                p.cost_cents,
                SUM(dpp.times_sold)::BIGINT AS times_sold,
                SUM(dpp.total_quantity)::NUMERIC AS total_quantity,
                SUM(dpp.total_revenue_cents)::BIGINT AS total_revenue_cents,
                SUM(dpp.total_cost_cents)::BIGINT AS total_cost_cents,
                AVG(dpp.avg_unit_price_cents)::INTEGER AS avg_price_cents,
                SUM(dpp.total_discount_cents)::BIGINT AS total_discount_cents
            FROM daily_product_performance dpp
            JOIN products p ON p.id = dpp.product_id
            WHERE dpp.org_id = $1
              AND dpp.day_bucket >= CURRENT_DATE - ($2 || ' days')::INTERVAL
              AND p.is_active = TRUE
            GROUP BY dpp.product_id, p.name, p.sku, p.price_cents, p.cost_cents
            ORDER BY SUM(dpp.total_revenue_cents) DESC
            """,
            org_id, str(days),
        )

    async def get_transaction_details(self, org_id: str, days: int = 30) -> list:
        return await self._pool.fetch(
            """
            SELECT
                t.id, t.external_id, t.type, t.total_cents,
                t.subtotal_cents, t.tax_cents, t.tip_cents,
                t.discount_cents, t.payment_method,
                t.employee_name, t.transaction_at,
                t.location_id
            FROM transactions t
            WHERE t.org_id = $1
              AND t.transaction_at >= NOW() - ($2 || ' days')::INTERVAL
            ORDER BY t.transaction_at DESC
            """,
            org_id, str(days),
        )

    async def get_inventory_current(self, org_id: str) -> list:
        return await self._pool.fetch(
            """
            SELECT DISTINCT ON (product_id, location_id)
                product_id, location_id,
                quantity_on_hand, quantity_sold,
                quantity_received, quantity_wasted,
                snapshot_at
            FROM inventory_snapshots
            WHERE org_id = $1
            ORDER BY product_id, location_id, snapshot_at DESC
            """,
            org_id,
        )

    async def get_dashboard_summary(
        self, org_id: str, start_date: str | None = None, end_date: str | None = None
    ):
        return await self._pool.fetchval(
            "SELECT get_dashboard_summary($1, $2::date, $3::date)",
            org_id,
            start_date or "NOW() - INTERVAL '30 days'",
            end_date or "NOW()",
        )
