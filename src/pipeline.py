"""
Meridian Live Pipeline — Square → Supabase → AI Engine.

End-to-end orchestration:
  1. Pull data from Square POS (sandbox or production)
  2. Map to Meridian schema
  3. Store in Supabase via REST API
  4. Refresh materialized views
  5. Run AI analysis engine
  6. Persist insights, forecasts, and scores

Usage:
    pipeline = MeridianPipeline(org_id="...", square_token="...", supabase_url="...", supabase_key="...")
    result = await pipeline.run_full_sync()
"""
import logging
from datetime import datetime, timezone
from uuid import uuid4

from .square.client import SquareClient
from .square.sync_engine import SyncEngine
from .square.mappers import DataMapper
from .db.supabase_rest import SupabaseREST
from .ai.engine import MeridianAI, AnalysisContext
from .sync.customer_app import sync_to_customer_app

logger = logging.getLogger("meridian.pipeline")


class PipelineResult:
    """Tracks the full pipeline execution."""
    
    def __init__(self):
        self.started_at = datetime.now(timezone.utc)
        self.completed_at: datetime | None = None
        self.phases: dict[str, dict] = {}
        self.errors: list[str] = []
        
    def record_phase(self, name: str, data: dict):
        self.phases[name] = {**data, "completed_at": datetime.now(timezone.utc).isoformat()}
        
    @property
    def summary(self) -> dict:
        return {
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": (
                (self.completed_at - self.started_at).total_seconds()
                if self.completed_at else None
            ),
            "phases": self.phases,
            "errors": self.errors,
            "success": len(self.errors) == 0,
        }


class MeridianPipeline:
    """
    Full Square → Supabase → AI pipeline.
    
    Connects the Square sync engine, Supabase REST client, and AI engine
    into a single orchestrated flow.
    """
    
    def __init__(
        self,
        org_id: str,
        org_name: str = "Business",
        business_vertical: str = "other",
        square_token: str = "",
        square_environment: str = "sandbox",
        supabase_url: str = "",
        supabase_key: str = "",
        pos_connection_id: str | None = None,
    ):
        self.org_id = org_id
        self.org_name = org_name
        self.business_vertical = business_vertical
        self.pos_connection_id = pos_connection_id or str(uuid4())
        
        # Square client
        self.square = SquareClient(
            access_token=square_token,
            environment=square_environment,
        )
        
        # Supabase REST client
        self.db = SupabaseREST(url=supabase_url, service_key=supabase_key)
        
        # AI Engine
        self.ai = MeridianAI()
        
        # Mapper (initialized after location sync)
        self._mapper: DataMapper | None = None
        
        # Lookup tables (built during sync)
        self._location_lookup: dict[str, str] = {}    # square_id → meridian_uuid
        self._product_lookup: dict[str, str] = {}     # square_id → meridian_uuid
        self._category_lookup: dict[str, str] = {}    # square_id → meridian_uuid
    
    async def run_full_sync(self) -> PipelineResult:
        """
        Run the complete pipeline: Square → Supabase → AI.
        
        Phases:
          1. setup       — Create/verify org, POS connection
          2. locations    — Sync locations from Square
          3. catalog      — Sync products and categories
          4. transactions — Sync orders/transactions
          5. analytics    — Refresh views + run AI engine
        """
        result = PipelineResult()
        
        try:
            # Phase 1: Setup
            logger.info(f"🚀 Starting full sync for {self.org_name} ({self.org_id})")
            await self._setup_org()
            result.record_phase("setup", {"status": "ok", "org_id": self.org_id})
            
            # Phase 2: Sync locations
            locations = await self._sync_locations()
            result.record_phase("locations", {
                "synced": len(locations),
                "location_ids": list(self._location_lookup.values()),
            })
            
            # Phase 3: Sync catalog (categories + products)
            cat_count, prod_count = await self._sync_catalog()
            result.record_phase("catalog", {
                "categories": cat_count,
                "products": prod_count,
            })
            
            # Phase 4: Sync transactions
            txn_count, item_count = await self._sync_transactions()
            result.record_phase("transactions", {
                "transactions": txn_count,
                "line_items": item_count,
            })
            
            # Phase 5: Analytics
            await self.db.refresh_views()
            ai_result = await self._run_ai_analysis()
            result.record_phase("analytics", {
                "insights": ai_result.get("insights", 0),
                "forecasts": ai_result.get("forecasts", 0),
                "money_left_score": ai_result.get("money_left_cents", 0),
                "anomalies": ai_result.get("anomalies", 0),
            })
            
            # Phase 6: Sync to customer portal
            try:
                customer_sync = await self._sync_to_customer_app(ai_result)
                result.record_phase("customer_app_sync", customer_sync)
            except Exception as e:
                logger.warning(f"Customer app sync failed (non-fatal): {e}")
                result.record_phase("customer_app_sync", {"status": "failed", "error": str(e)})
            
            result.completed_at = datetime.now(timezone.utc)
            logger.info(f"✅ Full sync complete: {result.summary}")
            
        except Exception as e:
            result.errors.append(str(e))
            result.completed_at = datetime.now(timezone.utc)
            logger.error(f"❌ Pipeline failed: {e}", exc_info=True)
        
        finally:
            await self.close()
        
        return result
    
    async def run_incremental_sync(self, since: datetime | None = None) -> PipelineResult:
        """
        Incremental sync — only new/updated transactions since last sync.
        Much faster than full sync, designed for the 15-minute cron.
        """
        result = PipelineResult()
        
        try:
            # Get sync cursor
            conn = await self.db.get_pos_connection(self.org_id)
            if not conn:
                result.errors.append("No active POS connection found")
                return result
            
            # Sync only new transactions
            sync_engine = SyncEngine(
                self.square,
                org_id=self.org_id,
                pos_connection_id=conn["id"],
            )
            
            sync_result = await sync_engine.run_incremental_sync(
                since=since or conn.get("last_sync_at"),
            )
            
            # Store new transactions
            if sync_result.transactions:
                await self.db.batch_insert("transactions", sync_result.transactions)
            if sync_result.transaction_items:
                await self.db.batch_insert("transaction_items", sync_result.transaction_items)
            
            # Refresh views + quick AI check
            await self.db.refresh_views()
            
            result.record_phase("incremental", {
                "transactions": len(sync_result.transactions),
                "line_items": len(sync_result.transaction_items),
            })
            
            # Update sync cursor
            await self.db.update_sync_status(
                conn["id"], "connected",
                cursor=datetime.now(timezone.utc).isoformat(),
            )
            
            result.completed_at = datetime.now(timezone.utc)
            
        except Exception as e:
            result.errors.append(str(e))
            result.completed_at = datetime.now(timezone.utc)
            logger.error(f"Incremental sync failed: {e}", exc_info=True)
        
        finally:
            await self.close()
        
        return result
    
    # ─── Phase Implementations ────────────────────────────────

    async def _setup_org(self):
        """Ensure org and POS connection exist in Supabase."""
        # Upsert organization
        await self.db.upsert(
            "organizations",
            {
                "id": self.org_id,
                "name": self.org_name,
                "slug": self.org_name.lower().replace(" ", "-").replace("'", ""),
                "vertical": self.business_vertical,
                "timezone": "America/Los_Angeles",
            },
            on_conflict="id",
        )
        logger.info(f"✅ Org ready: {self.org_name} ({self.org_id})")
        
        # Upsert POS connection
        await self.db.upsert(
            "pos_connections",
            {
                "id": self.pos_connection_id,
                "org_id": self.org_id,
                "provider": "square",
                "status": "syncing",
                "environment": self.square.environment,
                "connected_at": datetime.now(timezone.utc).isoformat(),
            },
            on_conflict="id",
        )
        logger.info(f"✅ POS connection ready: {self.pos_connection_id[:8]}...")

    async def _sync_locations(self) -> list[dict]:
        """Pull locations from Square and store in Supabase."""
        logger.info("📍 Syncing locations...")
        
        sq_locations = await self.square.list_locations()
        mapper = DataMapper(
            org_id=self.org_id,
            pos_connection_id=self.pos_connection_id,
        )
        
        stored_locations = []
        for i, sq_loc in enumerate(sq_locations):
            row = mapper.map_location(sq_loc)
            
            # Check if location already exists by external reference
            existing = await self.db.select(
                "locations",
                filters={"org_id": f"eq.{self.org_id}", "name": f"eq.{row['name']}"},
                limit=1,
            )
            
            if existing:
                row["id"] = existing[0]["id"]
            
            result = await self.db.upsert("locations", row, on_conflict="id")
            stored = result[0] if result else row
            stored_locations.append(stored)
            
            # Build lookup: Square location ID → Meridian UUID
            sq_id = sq_loc.get("id", "")
            self._location_lookup[sq_id] = stored["id"]
            
            if i == 0:
                row["is_primary"] = True
            
            logger.info(f"  📍 {stored['name']} → {stored['id'][:8]}...")
        
        # Initialize mapper with location lookup
        self._mapper = DataMapper(
            org_id=self.org_id,
            location_lookup=self._location_lookup,
            pos_connection_id=self.pos_connection_id,
        )
        
        return stored_locations

    async def _sync_catalog(self) -> tuple[int, int]:
        """Pull catalog (categories + products) from Square."""
        logger.info("📦 Syncing catalog...")
        
        # Categories
        sq_categories = await self.square.list_catalog(types=["CATEGORY"])
        cat_count = 0
        for sq_cat in sq_categories:
            row = self._mapper.map_category(sq_cat)
            
            existing = await self.db.select(
                "product_categories",
                filters={"org_id": f"eq.{self.org_id}", "name": f"eq.{row['name']}"},
                limit=1,
            )
            if existing:
                row["id"] = existing[0]["id"]
            
            result = await self.db.upsert("product_categories", row, on_conflict="id")
            stored = result[0] if result else row
            self._category_lookup[sq_cat.get("id", "")] = stored["id"]
            cat_count += 1
        
        logger.info(f"  📂 {cat_count} categories synced")
        
        # Products
        self._mapper.category_lookup = self._category_lookup
        sq_items = await self.square.list_catalog(types=["ITEM"])
        prod_count = 0
        for sq_item in sq_items:
            products = self._mapper.map_products(sq_item)
            for row in products:
                existing = await self.db.select(
                    "products",
                    filters={
                        "org_id": f"eq.{self.org_id}",
                        "external_id": f"eq.{row.get('external_id', '')}",
                    },
                    limit=1,
                )
                if existing:
                    row["id"] = existing[0]["id"]
                
                result = await self.db.upsert("products", row, on_conflict="id")
                stored = result[0] if result else row
                ext_id = row.get("external_id", "")
                if ext_id:
                    self._product_lookup[ext_id] = stored["id"]
                prod_count += 1
        
        self._mapper.product_lookup = self._product_lookup
        logger.info(f"  📦 {prod_count} products synced")
        
        return cat_count, prod_count

    async def _sync_transactions(self) -> tuple[int, int]:
        """Pull orders from Square and store as transactions."""
        logger.info("💳 Syncing transactions...")
        
        # Use sync engine with required args to pull orders
        sync_engine = SyncEngine(
            self.square,
            org_id=self.org_id,
            pos_connection_id=self.pos_connection_id,
        )
        sync_engine._mapper = self._mapper
        
        # Pull all locations for order search
        location_ids = list(self._location_lookup.keys())
        if not location_ids:
            logger.warning("No locations found — skipping transaction sync")
            return 0, 0
        
        # Use public backfill method
        sync_result = await sync_engine.run_initial_backfill()
        
        # Store transactions in batches
        txn_count = 0
        if sync_result.transactions:
            txn_count = await self.db.batch_insert(
                "transactions",
                sync_result.transactions,
                chunk_size=200,
            )
        
        item_count = 0
        if sync_result.transaction_items:
            item_count = await self.db.batch_insert(
                "transaction_items",
                sync_result.transaction_items,
                chunk_size=200,
            )
        
        logger.info(f"  💳 {txn_count} transactions, {item_count} line items stored")
        
        # Update POS connection status
        await self.db.update_sync_status(
            self.pos_connection_id,
            "connected",
            cursor=datetime.now(timezone.utc).isoformat(),
        )
        
        return txn_count, item_count

    async def _run_ai_analysis(self) -> dict:
        """Run the AI engine on stored data."""
        logger.info("🧠 Running AI analysis...")
        
        # Load data from Supabase for AI context
        daily_rev = await self.db.get_daily_revenue(self.org_id, days=90)
        hourly_rev = await self.db.get_hourly_revenue(self.org_id, days=30)
        product_perf = await self.db.get_product_performance(self.org_id, days=30)
        transactions = await self.db.get_recent_transactions(self.org_id, days=30)
        products = await self.db.get_products(self.org_id)
        
        if not daily_rev and not transactions:
            logger.info("  ⏭️  No data yet for AI analysis — skipping")
            return {"insights": 0, "forecasts": 0, "money_left_cents": 0, "anomalies": 0}
        
        # Build AI context
        context = AnalysisContext(
            org_id=self.org_id,
            daily_revenue=daily_rev,
            hourly_revenue=hourly_rev,
            product_performance=product_perf,
            transactions=transactions,
            business_vertical=self.business_vertical,
        )
        
        # Run analysis
        ai_result = await self.ai.analyze(context)
        
        # Persist results
        insights_saved = await self.db.save_insights(ai_result.insights)
        forecasts_saved = await self.db.save_forecasts(ai_result.forecasts)
        
        if ai_result.money_left_score:
            await self.db.save_money_left_score(ai_result.money_left_score)
        
        summary = {
            "insights": insights_saved,
            "forecasts": forecasts_saved,
            "money_left_cents": ai_result.money_left_score.get("total_score_cents", 0) if ai_result.money_left_score else 0,
            "anomalies": len(ai_result.revenue_analysis.get("anomalies", [])),
        }
        
        logger.info(f"  🧠 AI: {summary['insights']} insights, {summary['forecasts']} forecasts, "
                     f"${summary['money_left_cents']/100:.0f}/mo money left")
        
        return summary

    async def _sync_to_customer_app(self, ai_result: dict) -> dict:
        """
        Phase 6: Push processed data to the customer-facing portal.
        
        Sends org info, AI insights, forecasts, and revenue data
        to the customer app's HTTP ingest API.
        """
        logger.info("📱 Syncing to customer portal...")
        
        # Load data for customer app
        insights_raw = await self.db.get_insights(self.org_id)
        forecasts_raw = await self.db.get_forecasts(self.org_id)
        daily_revenue = await self.db.get_daily_revenue(self.org_id, days=90)
        products = await self.db.get_products(self.org_id)
        transactions = await self.db.get_recent_transactions(self.org_id, days=30)
        
        # Format insights for customer app
        insights = []
        for i in (insights_raw or []):
            insights.append({
                "type": i.get("type", "general"),
                "title": i.get("title", "Insight"),
                "summary": i.get("summary", i.get("description", "")),
                "impact": i.get("impact_cents", i.get("impact")),
                "confidence": i.get("confidence"),
                "priority": i.get("priority"),
                "actions": i.get("actions", i.get("recommended_actions")),
                "generatedAt": i.get("generated_at", datetime.now(timezone.utc).isoformat()),
            })
        
        # Format forecasts for customer app
        forecasts = []
        for f in (forecasts_raw or []):
            forecasts.append({
                "forecastType": f.get("forecast_type", "revenue"),
                "periodStart": f.get("period_start", ""),
                "periodEnd": f.get("period_end"),
                "predictedCents": f.get("predicted_cents", 0),
                "lowerBound": f.get("lower_bound", 0),
                "upperBound": f.get("upper_bound", 0),
                "confidence": f.get("confidence"),
                "generatedAt": f.get("generated_at", datetime.now(timezone.utc).isoformat()),
            })
        
        # Format revenue data for customer app
        revenue_data = []
        for d in (daily_revenue or []):
            revenue_data.append({
                "date": d.get("date", ""),
                "revenueCents": d.get("revenue_cents", 0),
                "transactionCount": d.get("transaction_count", 0),
                "avgTicketCents": d.get("avg_ticket_cents"),
            })
        
        # Sync to customer app
        sync_result = await sync_to_customer_app(
            org_id=self.org_id,
            org_name=self.org_name,
            business_type=self.business_vertical,
            plan="starter",
            status="active",
            locations_count=len(self._location_lookup),
            products_count=len(products or []),
            transactions_count=len(transactions or []),
            insights=insights,
            forecasts=forecasts,
            revenue_data=revenue_data,
        )
        
        logger.info(f"  📱 Customer app sync: {sync_result.get('success', False)}")
        return sync_result

    async def close(self):
        """Cleanup connections."""
        await self.db.close()
        await self.square.close()


# ─── Convenience Runner ──────────────────────────────────────

async def run_pipeline(
    org_id: str | None = None,
    org_name: str = "Test Business",
    business_vertical: str = "cafe",
) -> PipelineResult:
    """
    Quick-start: Run the full pipeline with env config.
    
    Reads Square and Supabase credentials from environment/.env.
    """
    import os
    
    # Load .env
    env = {}
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    env[key.strip()] = val.strip()
    
    pipeline = MeridianPipeline(
        org_id=org_id or str(uuid4()),
        org_name=org_name,
        business_vertical=business_vertical,
        square_token=env.get("SQUARE_ACCESS_TOKEN", os.environ.get("SQUARE_ACCESS_TOKEN", "")),
        square_environment=env.get("SQUARE_ENVIRONMENT", "sandbox"),
        supabase_url=env.get("SUPABASE_URL", os.environ.get("SUPABASE_URL", "")),
        supabase_key=env.get("SUPABASE_SERVICE_KEY", os.environ.get("SUPABASE_SERVICE_KEY", "")),
    )
    
    return await pipeline.run_full_sync()
