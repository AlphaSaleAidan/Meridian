"""
Run the Meridian pipeline end-to-end: Square Sandbox → Supabase Live → AI Engine.

This script:
  1. Connects to the Square sandbox and pulls real test data
  2. Maps everything to Meridian schema
  3. Stores in the live Supabase database
  4. Refreshes materialized views
  5. Runs the AI engine and persists insights
"""
import asyncio
import logging
import os
import sys
import json
from datetime import datetime, timezone
from uuid import uuid4

# Setup path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Load .env
env = {}
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            env[key.strip()] = val.strip()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("run_pipeline")

# Import after path setup
from src.square.client import SquareClient
from src.square.mappers import DataMapper
from src.db.supabase_rest import SupabaseREST


async def main():
    print("=" * 60)
    print("  MERIDIAN LIVE PIPELINE — Square → Supabase → AI")
    print("=" * 60)
    print()
    
    # Initialize clients
    square = SquareClient(
        access_token=env["SQUARE_ACCESS_TOKEN"],
        environment="sandbox",
    )
    
    db = SupabaseREST(
        url=env["SUPABASE_URL"],
        service_key=env["SUPABASE_SERVICE_KEY"],
    )
    
    org_id = str(uuid4())
    pos_conn_id = str(uuid4())
    
    try:
        # ── Phase 1: Health checks ────────────────────────────
        print("Phase 1: Health Checks")
        print("-" * 40)
        
        health = await db.health_check()
        print(f"  Supabase: {health['status']} ({health.get('tables', 0)} tables)")
        
        # Quick Square test
        locations = await square.list_locations()
        print(f"  Square:   connected ({len(locations)} locations)")
        print()
        
        # ── Phase 2: Setup org ────────────────────────────────
        print("Phase 2: Setup Organization")
        print("-" * 40)
        
        await db.upsert("organizations", {
            "id": org_id,
            "name": "Meridian Demo Cafe",
            "slug": "meridian-demo-cafe",
            "vertical": "cafe",
            "city": "Los Angeles",
            "state": "CA",
            "timezone": "America/Los_Angeles",
        }, on_conflict="id")
        print(f"  ✅ Created org: Meridian Demo Cafe ({org_id[:8]}...)")
        
        await db.upsert("pos_connections", {
            "id": pos_conn_id,
            "org_id": org_id,
            "provider": "square",
            "status": "syncing",
            
            
        }, on_conflict="id")
        print(f"  ✅ Created POS connection ({pos_conn_id[:8]}...)")
        print()
        
        # ── Phase 3: Sync locations ──────────────────────────
        print("Phase 3: Sync Locations from Square")
        print("-" * 40)
        
        location_lookup = {}
        mapper = DataMapper(org_id=org_id, pos_connection_id=pos_conn_id)
        
        for sq_loc in locations:
            row = mapper.map_location(sq_loc)
            result = await db.upsert("locations", row, on_conflict="id")
            stored = result[0] if result else row
            location_lookup[sq_loc["id"]] = stored["id"]
            print(f"  📍 {stored['name']} → {stored['id'][:8]}...")
        
        print(f"  ✅ {len(location_lookup)} location(s) synced")
        print()
        
        # ── Phase 4: Sync catalog ────────────────────────────
        print("Phase 4: Sync Catalog from Square")
        print("-" * 40)
        
        mapper = DataMapper(
            org_id=org_id,
            location_lookup=location_lookup,
            pos_connection_id=pos_conn_id,
        )
        
        category_lookup = {}
        product_lookup = {}
        
        # Categories
        try:
            sq_categories, _ = await square.list_catalog(types=["CATEGORY"])
            for sq_cat in sq_categories:
                row = mapper.map_category(sq_cat)
                result = await db.upsert("product_categories", row, on_conflict="id")
                stored = result[0] if result else row
                category_lookup[sq_cat.get("id", "")] = stored["id"]
            print(f"  📂 {len(category_lookup)} categories synced")
        except Exception as e:
            print(f"  ⚠️  Categories: {e} (continuing...)")
        
        # Products
        mapper.category_lookup = category_lookup
        try:
            sq_items, _ = await square.list_catalog(types=["ITEM"])
            for sq_item in sq_items:
                products = mapper.map_products(sq_item)
                for row in products:
                    result = await db.upsert("products", row, on_conflict="id")
                    stored = result[0] if result else row
                    ext_id = row.get("external_id", "")
                    if ext_id:
                        product_lookup[ext_id] = stored["id"]
            print(f"  📦 {len(product_lookup)} products synced")
        except Exception as e:
            print(f"  ⚠️  Products: {e} (continuing...)")
        
        mapper.product_lookup = product_lookup
        print()
        
        # ── Phase 5: Sync transactions ───────────────────────
        print("Phase 5: Sync Transactions from Square")
        print("-" * 40)
        
        location_ids = list(location_lookup.keys())
        txn_count = 0
        item_count = 0
        
        try:
            orders, _ = await square.search_orders(
                location_ids=location_ids,
            )
            
            for sq_order in orders:
                txn = mapper.map_transaction(sq_order)
                items = mapper.map_transaction_items(sq_order)
                
                await db.insert("transactions", txn, return_data=False)
                txn_count += 1
                
                if items:
                    await db.batch_insert("transaction_items", items)
                    item_count += len(items)
            
            print(f"  💳 {txn_count} transactions synced")
            print(f"  📋 {item_count} line items synced")
        except Exception as e:
            print(f"  ⚠️  Transactions: {e}")
            # Square sandbox might not have orders, that's OK
            if txn_count == 0:
                print("  ℹ️  No transactions in Square sandbox — generating sample data...")
                txn_count, item_count = await _generate_sample_data(db, org_id, location_lookup, product_lookup)
        
        # If no transactions from Square, generate sample data
        if txn_count == 0:
            print("  ℹ️  Empty sandbox — generating sample data for demo...")
            txn_count, item_count = await _generate_sample_data(db, org_id, location_lookup, product_lookup)
        
        print()
        
        # ── Phase 6: Refresh views ───────────────────────────
        print("Phase 6: Refresh Analytics Views")
        print("-" * 40)
        
        await db.refresh_views()
        
        # Check view data
        daily = await db.get_daily_revenue(org_id, days=90)
        hourly = await db.get_hourly_revenue(org_id, days=90)
        print(f"  📊 daily_revenue: {len(daily)} rows")
        print(f"  📊 hourly_revenue: {len(hourly)} rows")
        print()
        
        # ── Phase 7: AI Engine ───────────────────────────────
        print("Phase 7: AI Analysis Engine")
        print("-" * 40)
        
        if daily or hourly:
            from src.ai.engine import MeridianAI, AnalysisContext
            
            product_perf = await db.get_product_performance(org_id, days=90)
            transactions = await db.get_recent_transactions(org_id, days=90)
            
            context = AnalysisContext(
                org_id=org_id,
                daily_revenue=daily,
                hourly_revenue=hourly,
                product_performance=product_perf,
                transactions=transactions,
                business_vertical="cafe",
            )
            
            ai = MeridianAI()
            ai_result = await ai.analyze(context)
            
            print(f"  🧠 Insights generated: {len(ai_result.insights)}")
            print(f"  📈 Forecasts generated: {len(ai_result.forecasts)}")
            print(f"  💰 Money Left score: ${ai_result.money_left_score.get('total_score_cents', 0) / 100:.0f}/mo" if ai_result.money_left_score else "  💰 Money Left: N/A")
            anomalies = ai_result.revenue_analysis.get("anomalies", [])
            print(f"  ⚠️  Anomalies found: {len(anomalies)}")
            
            # Persist AI results
            if ai_result.insights:
                saved = await db.save_insights(ai_result.insights)
                print(f"  💾 Saved {saved} insights to Supabase")
            
            if ai_result.forecasts:
                saved = await db.save_forecasts(ai_result.forecasts)
                print(f"  💾 Saved {saved} forecasts to Supabase")
            
            if ai_result.money_left_score:
                await db.save_money_left_score(ai_result.money_left_score)
                print(f"  💾 Saved money_left_score to Supabase")
        else:
            print("  ⏭️  No aggregated data yet — AI analysis skipped")
        
        print()
        
        # ── Phase 8: Final verification ──────────────────────
        print("Phase 8: Final Verification")
        print("-" * 40)
        
        org_count = await db.count("organizations", {"id": f"eq.{org_id}"})
        loc_count = await db.count("locations", {"org_id": f"eq.{org_id}"})
        prod_count = await db.count("products", {"org_id": f"eq.{org_id}"})
        txn_final = await db.count("transactions", {"org_id": f"eq.{org_id}"})
        insight_count = await db.count("insights", {"org_id": f"eq.{org_id}"})
        
        print(f"  Organizations:  {org_count}")
        print(f"  Locations:      {loc_count}")
        print(f"  Products:       {prod_count}")
        print(f"  Transactions:   {txn_final}")
        print(f"  AI Insights:    {insight_count}")
        
        # Update connection status
        await db.update_sync_status(pos_conn_id, "connected")
        
        print()
        print("=" * 60)
        print("  ✅ PIPELINE COMPLETE — All data live in Supabase!")
        print(f"  📊 Org ID: {org_id}")
        print("=" * 60)
        
        return org_id
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        print(f"\n❌ ERROR: {e}")
        raise
    
    finally:
        await db.close()
        await square.close()


async def _generate_sample_data(
    db: SupabaseREST,
    org_id: str,
    location_lookup: dict,
    product_lookup: dict,
) -> tuple[int, int]:
    """Generate realistic sample transactions for demo purposes."""
    import random
    from datetime import timedelta
    
    location_id = list(location_lookup.values())[0] if location_lookup else None
    
    # Create sample products if none from Square
    if not product_lookup:
        sample_products = [
            {"name": "Espresso", "sku": "ESP-001", "price_cents": 450, "cost_cents": 120},
            {"name": "Latte", "sku": "LAT-001", "price_cents": 575, "cost_cents": 150},
            {"name": "Cappuccino", "sku": "CAP-001", "price_cents": 550, "cost_cents": 145},
            {"name": "Drip Coffee", "sku": "DRP-001", "price_cents": 325, "cost_cents": 80},
            {"name": "Cold Brew", "sku": "CLB-001", "price_cents": 525, "cost_cents": 110},
            {"name": "Mocha", "sku": "MOC-001", "price_cents": 625, "cost_cents": 170},
            {"name": "Croissant", "sku": "CRO-001", "price_cents": 425, "cost_cents": 150},
            {"name": "Muffin", "sku": "MUF-001", "price_cents": 375, "cost_cents": 130},
            {"name": "Bagel", "sku": "BAG-001", "price_cents": 350, "cost_cents": 100},
            {"name": "Scone", "sku": "SCO-001", "price_cents": 395, "cost_cents": 120},
        ]
        
        for prod in sample_products:
            prod_id = str(uuid4())
            await db.insert("products", {
                "id": prod_id,
                "org_id": org_id,
                **prod,
            })
            product_lookup[prod["sku"]] = prod_id
        
        print(f"  📦 Created {len(sample_products)} sample products")
    
    # Build product lookups
    product_ids = list(product_lookup.values())
    product_prices = {pid: random.randint(300, 700) for pid in product_ids}
    product_names = {}
    for key, pid in product_lookup.items():
        product_names[pid] = key.replace("-001", "").replace("-", " ").title()
    
    now = datetime.now(timezone.utc)
    txn_count = 0
    item_count = 0
    txn_batch = []
    item_batch = []
    
    for day_offset in range(30, 0, -1):
        day = now - timedelta(days=day_offset)
        is_weekend = day.weekday() >= 5
        
        # More transactions on weekends
        daily_txns = random.randint(40, 70) if is_weekend else random.randint(25, 50)
        
        for _ in range(daily_txns):
            # Random time (weighted toward morning rush)
            hour = random.choices(
                range(6, 21),
                weights=[3, 8, 10, 8, 5, 4, 6, 7, 5, 4, 3, 2, 2, 1, 1],
            )[0]
            minute = random.randint(0, 59)
            txn_time = day.replace(hour=hour, minute=minute, second=random.randint(0, 59))
            
            # 1-3 items per transaction
            num_items = random.choices([1, 2, 3], weights=[50, 35, 15])[0]
            selected_products = random.sample(product_ids, min(num_items, len(product_ids)))
            
            total_cents = 0
            txn_id = str(uuid4())
            txn_items = []
            
            for pid in selected_products:
                qty = random.choices([1, 2], weights=[85, 15])[0]
                price = product_prices.get(pid, 500)
                item_total = price * qty
                total_cents += item_total
                
                txn_items.append({
                    "id": str(uuid4()),
                    "org_id": org_id,
                    "transaction_id": txn_id,
                    "transaction_at": txn_time.isoformat(),
                    "product_id": pid,
                    "product_name": product_names.get(pid, "Item"),
                    "quantity": qty,
                    "unit_price_cents": price,
                    "total_cents": item_total,
                })
            
            tax_cents = int(total_cents * 0.0875)
            tip_cents = random.choices(
                [0, int(total_cents * 0.15), int(total_cents * 0.18), int(total_cents * 0.20)],
                weights=[30, 25, 25, 20],
            )[0]
            
            payment = random.choices(
                ["credit_card", "cash", "mobile_pay", "debit_card"],
                weights=[45, 25, 20, 10],
            )[0]
            
            # Occasional refunds
            txn_type = "refund" if random.random() < 0.03 else "sale"
            
            txn_batch.append({
                "id": txn_id,
                "org_id": org_id,
                "location_id": location_id,
                "type": txn_type,
                "subtotal_cents": total_cents,
                "tax_cents": tax_cents,
                "tip_cents": tip_cents,
                "discount_cents": 0,
                "total_cents": total_cents + tax_cents + tip_cents,
                "payment_method": payment,
                "transaction_at": txn_time.isoformat(),
                "customer_count": random.randint(1, 4),
            })
            
            item_batch.extend(txn_items)
            txn_count += 1
            item_count += len(txn_items)
    
    # Batch insert
    await db.batch_insert("transactions", txn_batch, chunk_size=200)
    await db.batch_insert("transaction_items", item_batch, chunk_size=200)
    
    print(f"  💳 Generated {txn_count} transactions ({item_count} line items)")
    print(f"     30 days of realistic cafe data")
    
    return txn_count, item_count


if __name__ == "__main__":
    asyncio.run(main())
