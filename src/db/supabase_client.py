"""
Supabase Database Client — Production database operations for Meridian.

Uses direct PostgreSQL via asyncpg for bulk sync operations (fast, 
no connection overhead). Falls back to Supabase REST API for 
RLS-respecting user-facing queries.

Connection modes:
  • DIRECT (asyncpg) — Used by sync engine, workers, AI engine
  • REST (supabase-py) — Used by API routes (respects RLS)
"""
import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

logger = logging.getLogger("meridian.db.supabase")

# ── Lazy imports (asyncpg may not be installed in sandbox) ────
_asyncpg = None

def _get_asyncpg():
    global _asyncpg
    if _asyncpg is None:
        try:
            import asyncpg as _mod
            _asyncpg = _mod
        except ImportError:
            raise ImportError(
                "asyncpg required for Supabase direct connection. "
                "Install with: pip install asyncpg"
            )
    return _asyncpg


class SupabaseConfig:
    """Supabase connection settings."""
    
    def __init__(
        self,
        database_url: str | None = None,
        supabase_url: str | None = None,
        supabase_key: str | None = None,
        supabase_service_key: str | None = None,
        pool_min: int = 2,
        pool_max: int = 10,
    ):
        self.database_url = database_url or os.getenv("DATABASE_URL", "")
        self.supabase_url = supabase_url or os.getenv("SUPABASE_URL", "")
        self.supabase_key = supabase_key or os.getenv("SUPABASE_ANON_KEY", "")
        self.supabase_service_key = (
            supabase_service_key or os.getenv("SUPABASE_SERVICE_KEY", "")
        )
        self.pool_min = pool_min
        self.pool_max = pool_max

    @property
    def direct_url(self) -> str:
        """PostgreSQL direct URL for asyncpg (bypasses PgBouncer)."""
        # Supabase provides both pooled and direct URLs
        # Direct: postgresql://...@db.<ref>.supabase.co:5432/postgres
        # Pooled: postgresql://...@<ref>.pooler.supabase.com:6543/postgres
        url = os.getenv("DATABASE_DIRECT_URL", self.database_url)
        return url


class SupabaseDB:
    """
    Production database client for Meridian.
    
    Handles connection pooling, query execution, and all
    database operations needed by the sync engine and AI.
    
    Usage:
        db = SupabaseDB(config)
        await db.connect()
        
        # Bulk operations (sync engine)
        await db.upsert_locations(org_id, locations)
        await db.upsert_products(org_id, products)
        await db.upsert_transactions(org_id, transactions, items)
        
        # Analytics queries (AI engine)
        revenue = await db.get_daily_revenue(org_id, 30)
        products = await db.get_product_performance(org_id, 30)
        
        await db.close()
    """

    def __init__(self, config: SupabaseConfig | None = None):
        self.config = config or SupabaseConfig()
        self._pool = None

    async def connect(self):
        """Initialize connection pool."""
        asyncpg = _get_asyncpg()
        
        if not self.config.database_url:
            raise ValueError(
                "DATABASE_URL not set. Add to .env:\n"
                "DATABASE_URL=postgresql://postgres:<password>@db.<ref>.supabase.co:5432/postgres"
            )
        
        self._pool = await asyncpg.create_pool(
            self.config.direct_url or self.config.database_url,
            min_size=self.config.pool_min,
            max_size=self.config.pool_max,
            command_timeout=60,
            # Supabase requires SSL
            ssl="prefer",
        )
        logger.info(
            f"Connected to Supabase PostgreSQL "
            f"(pool: {self.config.pool_min}-{self.config.pool_max})"
        )

    async def close(self):
        """Close connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("Database connection pool closed")

    @asynccontextmanager
    async def acquire(self):
        """Acquire a connection from the pool."""
        if not self._pool:
            await self.connect()
        async with self._pool.acquire() as conn:
            yield conn

    async def execute(self, query: str, *args) -> str:
        """Execute a query and return status."""
        async with self.acquire() as conn:
            return await conn.execute(query, *args)

    async def fetch(self, query: str, *args) -> list:
        """Fetch multiple rows."""
        async with self.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args):
        """Fetch a single row."""
        async with self.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetchval(self, query: str, *args):
        """Fetch a single value."""
        async with self.acquire() as conn:
            return await conn.fetchval(query, *args)

    # ─── Bulk Sync Operations ─────────────────────────────────
    # These use COPY or batch INSERT for performance

    async def upsert_locations(self, org_id: str, locations: list[dict]) -> int:
        """Upsert locations from sync engine."""
        if not locations:
            return 0
        
        async with self.acquire() as conn:
            count = 0
            for loc in locations:
                await conn.execute(
                    """
                    INSERT INTO locations (
                        id, org_id, name, is_primary, address_line1, city,
                        state, zip_code, latitude, longitude, phone,
                        business_hours, is_active
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12::jsonb, $13)
                    ON CONFLICT (id) DO UPDATE SET
                        name = EXCLUDED.name,
                        address_line1 = EXCLUDED.address_line1,
                        city = EXCLUDED.city,
                        state = EXCLUDED.state,
                        zip_code = EXCLUDED.zip_code,
                        latitude = EXCLUDED.latitude,
                        longitude = EXCLUDED.longitude,
                        phone = EXCLUDED.phone,
                        business_hours = EXCLUDED.business_hours,
                        is_active = EXCLUDED.is_active
                    """,
                    loc["id"], org_id, loc.get("name", ""),
                    loc.get("is_primary", False),
                    loc.get("address_line1"), loc.get("city"),
                    loc.get("state"), loc.get("zip_code"),
                    loc.get("latitude"), loc.get("longitude"),
                    loc.get("phone"),
                    json.dumps(loc.get("business_hours", {})),
                    loc.get("is_active", True),
                )
                count += 1
            
            logger.info(f"Upserted {count} locations for org {org_id}")
            return count

    async def upsert_categories(self, org_id: str, categories: list[dict]) -> int:
        """Upsert product categories."""
        if not categories:
            return 0
        
        async with self.acquire() as conn:
            count = 0
            for cat in categories:
                await conn.execute(
                    """
                    INSERT INTO product_categories (id, org_id, name, external_id, is_active)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (org_id, external_id) WHERE external_id IS NOT NULL
                    DO UPDATE SET name = EXCLUDED.name, is_active = EXCLUDED.is_active
                    """,
                    cat["id"], org_id, cat.get("name", ""),
                    cat.get("external_id"), cat.get("is_active", True),
                )
                count += 1
            
            logger.info(f"Upserted {count} categories for org {org_id}")
            return count

    async def upsert_products(self, org_id: str, products: list[dict]) -> int:
        """Upsert products from sync engine."""
        if not products:
            return 0
        
        async with self.acquire() as conn:
            count = 0
            for p in products:
                await conn.execute(
                    """
                    INSERT INTO products (
                        id, org_id, category_id, external_id, name, description,
                        sku, barcode, price_cents, has_variants, variant_of,
                        variant_attrs, is_active, is_taxable, image_url, metadata
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11,
                        $12::jsonb, $13, $14, $15, $16::jsonb
                    )
                    ON CONFLICT (org_id, external_id) WHERE external_id IS NOT NULL
                    DO UPDATE SET
                        name = EXCLUDED.name, description = EXCLUDED.description,
                        sku = EXCLUDED.sku, barcode = EXCLUDED.barcode,
                        price_cents = EXCLUDED.price_cents,
                        is_active = EXCLUDED.is_active, image_url = EXCLUDED.image_url,
                        metadata = products.metadata || EXCLUDED.metadata
                    """,
                    p["id"], org_id, p.get("category_id"),
                    p.get("external_id"), p.get("name", ""),
                    p.get("description"), p.get("sku"), p.get("barcode"),
                    p.get("price_cents", 0), p.get("has_variants", False),
                    p.get("variant_of"),
                    json.dumps(p.get("variant_attrs", {})),
                    p.get("is_active", True), p.get("is_taxable", True),
                    p.get("image_url"),
                    json.dumps(p.get("metadata", {})),
                )
                count += 1
            
            logger.info(f"Upserted {count} products for org {org_id}")
            return count

    async def upsert_transactions_batch(
        self,
        org_id: str,
        transactions: list[dict],
        items: list[dict],
    ) -> tuple[int, int]:
        """
        Batch upsert transactions and their line items.
        
        Uses a single transaction for atomicity.
        """
        if not transactions:
            return 0, 0

        async with self.acquire() as conn:
            async with conn.transaction():
                txn_count = 0
                for txn in transactions:
                    await conn.execute(
                        """
                        INSERT INTO transactions (
                            id, org_id, location_id, pos_connection_id, external_id,
                            type, subtotal_cents, tax_cents, tip_cents, discount_cents,
                            total_cents, payment_method, employee_name, employee_external_id,
                            transaction_at, metadata
                        ) VALUES (
                            $1, $2, $3, $4, $5, $6::transaction_type,
                            $7, $8, $9, $10, $11,
                            $12::payment_method, $13, $14, $15, $16::jsonb
                        )
                        ON CONFLICT (org_id, external_id) 
                        DO UPDATE SET
                            total_cents = EXCLUDED.total_cents,
                            tax_cents = EXCLUDED.tax_cents,
                            tip_cents = EXCLUDED.tip_cents,
                            discount_cents = EXCLUDED.discount_cents,
                            payment_method = EXCLUDED.payment_method,
                            employee_name = EXCLUDED.employee_name,
                            metadata = transactions.metadata || EXCLUDED.metadata
                        """,
                        txn["id"], org_id, txn.get("location_id"),
                        txn.get("pos_connection_id"), txn.get("external_id"),
                        txn.get("type", "sale"),
                        txn.get("subtotal_cents", 0), txn.get("tax_cents", 0),
                        txn.get("tip_cents", 0), txn.get("discount_cents", 0),
                        txn.get("total_cents", 0),
                        txn.get("payment_method", "other"),
                        txn.get("employee_name"), txn.get("employee_external_id"),
                        txn.get("transaction_at"),
                        json.dumps(txn.get("metadata", {})),
                    )
                    txn_count += 1

                item_count = 0
                for item in items:
                    await conn.execute(
                        """
                        INSERT INTO transaction_items (
                            id, transaction_id, transaction_at, org_id,
                            product_id, product_name, quantity,
                            unit_price_cents, total_cents, discount_cents,
                            modifiers, metadata
                        ) VALUES (
                            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                            $11::jsonb, $12::jsonb
                        )
                        ON CONFLICT (id, transaction_at)
                        DO UPDATE SET
                            quantity = EXCLUDED.quantity,
                            total_cents = EXCLUDED.total_cents,
                            discount_cents = EXCLUDED.discount_cents
                        """,
                        item["id"], item["transaction_id"],
                        item.get("transaction_at"), org_id,
                        item.get("product_id"), item.get("product_name", ""),
                        item.get("quantity", 1),
                        item.get("unit_price_cents", 0),
                        item.get("total_cents", 0),
                        item.get("discount_cents", 0),
                        json.dumps(item.get("modifiers", {})),
                        json.dumps(item.get("metadata", {})),
                    )
                    item_count += 1

        logger.info(
            f"Upserted {txn_count} transactions, {item_count} items for org {org_id}"
        )
        return txn_count, item_count

    async def upsert_inventory_snapshots(
        self, org_id: str, snapshots: list[dict]
    ) -> int:
        """Upsert inventory count snapshots."""
        if not snapshots:
            return 0
        
        async with self.acquire() as conn:
            count = 0
            for snap in snapshots:
                await conn.execute(
                    """
                    INSERT INTO inventory_snapshots (
                        id, org_id, location_id, product_id,
                        quantity_on_hand, quantity_sold, quantity_received,
                        quantity_wasted, snapshot_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT (id, snapshot_at)
                    DO UPDATE SET
                        quantity_on_hand = EXCLUDED.quantity_on_hand,
                        quantity_sold = EXCLUDED.quantity_sold,
                        quantity_received = EXCLUDED.quantity_received,
                        quantity_wasted = EXCLUDED.quantity_wasted
                    """,
                    snap["id"], org_id, snap.get("location_id"),
                    snap.get("product_id"),
                    snap.get("quantity_on_hand", 0),
                    snap.get("quantity_sold", 0),
                    snap.get("quantity_received", 0),
                    snap.get("quantity_wasted", 0),
                    snap.get("snapshot_at"),
                )
                count += 1
            
            logger.info(f"Upserted {count} inventory snapshots for org {org_id}")
            return count

    # ─── POS Connection Management ────────────────────────────

    async def upsert_pos_connection(self, connection: dict) -> str:
        """Create or update a POS connection."""
        async with self.acquire() as conn:
            return await conn.fetchval(
                """
                INSERT INTO pos_connections (
                    id, org_id, location_id, provider, status,
                    access_token_enc, refresh_token_enc, token_expires_at,
                    external_merchant_id, external_location_id, metadata
                ) VALUES ($1, $2, $3, 'square', $4, $5, $6, $7, $8, $9, $10::jsonb)
                ON CONFLICT (id) DO UPDATE SET
                    status = EXCLUDED.status,
                    access_token_enc = EXCLUDED.access_token_enc,
                    refresh_token_enc = EXCLUDED.refresh_token_enc,
                    token_expires_at = EXCLUDED.token_expires_at
                RETURNING id
                """,
                connection["id"], connection["org_id"],
                connection.get("location_id"),
                connection.get("status", "connected"),
                connection.get("access_token_enc"),
                connection.get("refresh_token_enc"),
                connection.get("token_expires_at"),
                connection.get("external_merchant_id"),
                connection.get("external_location_id"),
                json.dumps(connection.get("metadata", {})),
            )

    async def update_connection_sync_status(
        self,
        connection_id: str,
        status: str,
        last_sync_status: str | None = None,
        historical_complete: bool | None = None,
    ):
        """Update connection sync state."""
        async with self.acquire() as conn:
            await conn.execute(
                """
                UPDATE pos_connections SET
                    status = $2,
                    last_sync_at = NOW(),
                    last_sync_status = COALESCE($3, last_sync_status),
                    historical_import_complete = COALESCE($4, historical_import_complete),
                    historical_import_completed_at = CASE
                        WHEN $4 = TRUE THEN NOW()
                        ELSE historical_import_completed_at
                    END
                WHERE id = $1
                """,
                connection_id, status, last_sync_status, historical_complete,
            )

    async def get_active_connections(self) -> list:
        """Get all connections ready for incremental sync."""
        return await self.fetch(
            """
            SELECT * FROM pos_connections
            WHERE provider = 'square'
              AND status = 'connected'
              AND historical_import_complete = TRUE
            ORDER BY last_sync_at ASC NULLS FIRST
            """
        )

    async def get_connections_needing_refresh(self) -> list:
        """Get connections with tokens expiring within 5 days."""
        return await self.fetch(
            """
            SELECT * FROM pos_connections
            WHERE provider = 'square'
              AND status IN ('connected', 'syncing')
              AND token_expires_at < NOW() + INTERVAL '5 days'
            """
        )

    # ─── Analytics Queries (for AI Engine) ────────────────────

    async def get_daily_revenue(
        self, org_id: str, days: int = 30
    ) -> list:
        """Daily revenue aggregates for AI analysis."""
        return await self.fetch(
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

    async def get_hourly_revenue(
        self, org_id: str, days: int = 30
    ) -> list:
        """Hourly revenue for peak analysis."""
        return await self.fetch(
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

    async def get_product_performance(
        self, org_id: str, days: int = 30
    ) -> list:
        """Product performance for the AI analyzer."""
        return await self.fetch(
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

    async def get_transaction_details(
        self, org_id: str, days: int = 30
    ) -> list:
        """Raw transaction data for detailed analysis."""
        return await self.fetch(
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
        """Latest inventory counts per product."""
        return await self.fetch(
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
        """Call the get_dashboard_summary PostgreSQL function."""
        return await self.fetchval(
            "SELECT get_dashboard_summary($1, $2::date, $3::date)",
            org_id,
            start_date or "NOW() - INTERVAL '30 days'",
            end_date or "NOW()",
        )

    # ─── AI Insight Operations ────────────────────────────────

    async def save_insight(self, insight: dict) -> str:
        """Save a generated AI insight."""
        async with self.acquire() as conn:
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
        """Save a daily Money Left on Table score."""
        async with self.acquire() as conn:
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
        """Save revenue forecasts."""
        if not forecasts:
            return 0
        
        async with self.acquire() as conn:
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
        """Save a weekly report snapshot."""
        async with self.acquire() as conn:
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
        """
        Run SQL migration files in order.
        
        Reads all .sql files from the directory, sorts by name,
        and executes each one. Tracks applied migrations.
        """
        import glob as glob_mod
        from pathlib import Path

        migrations_path = Path(migrations_dir)
        files = sorted(migrations_path.glob("*.sql"))
        
        applied = []
        async with self.acquire() as conn:
            # Create migrations tracking table if needed
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS _migrations (
                    filename TEXT PRIMARY KEY,
                    applied_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            
            for f in files:
                filename = f.name
                # Skip if already applied
                existing = await conn.fetchval(
                    "SELECT filename FROM _migrations WHERE filename = $1",
                    filename,
                )
                if existing:
                    logger.info(f"Migration {filename} already applied, skipping")
                    continue
                
                # Read and execute
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

    # ─── Health Check ─────────────────────────────────────────

    async def health_check(self) -> dict:
        """Verify database connectivity and basic stats."""
        try:
            version = await self.fetchval("SELECT version()")
            now = await self.fetchval("SELECT NOW()")
            
            # Check tables exist
            table_count = await self.fetchval(
                """
                SELECT COUNT(*) FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_type = 'BASE TABLE'
                """
            )
            
            return {
                "status": "healthy",
                "postgres_version": version.split(",")[0] if version else None,
                "server_time": str(now),
                "public_tables": table_count,
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
            }
