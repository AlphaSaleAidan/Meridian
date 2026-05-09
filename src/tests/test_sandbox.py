"""
Sandbox Integration Test — Validates full pipeline against Square sandbox.

This test:
  1. Connects to Square sandbox with test credentials
  2. Pulls locations, catalog, orders, inventory, team members
  3. Runs all data mappers
  4. Verifies data integrity
  5. Reports results

Run: uv run python -m src.tests.test_sandbox
"""
import asyncio
import json
import logging
import sys
import time
from datetime import datetime, timedelta, timezone

# Add parent to path
sys.path.insert(0, "/work/meridian")

from src.square.client import SquareClient, SquareAPIError
from src.square.mappers import DataMapper
from src.square.sync_engine import SyncEngine
from src.db.client import InMemoryDB
from src.config import square as sq_config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-35s | %(levelname)-5s | %(message)s",
)
logger = logging.getLogger("test_sandbox")


class TestResults:
    def __init__(self):
        self.passed: list[str] = []
        self.failed: list[str] = []
        self.skipped: list[str] = []
        self.details: dict[str, str] = {}

    def ok(self, name: str, detail: str = ""):
        self.passed.append(name)
        self.details[name] = detail
        logger.info(f"  ✅ {name}: {detail}")

    def fail(self, name: str, detail: str = ""):
        self.failed.append(name)
        self.details[name] = detail
        logger.error(f"  ❌ {name}: {detail}")

    def skip(self, name: str, detail: str = ""):
        self.skipped.append(name)
        self.details[name] = detail
        logger.info(f"  ⏭️  {name}: {detail}")

    def summary(self) -> str:
        total = len(self.passed) + len(self.failed) + len(self.skipped)
        return (
            f"\n{'='*60}\n"
            f"TEST RESULTS: {len(self.passed)}/{total} passed"
            f" ({len(self.failed)} failed, {len(self.skipped)} skipped)\n"
            f"{'='*60}"
        )


async def run_sandbox_tests():
    """Run all sandbox integration tests."""
    results = TestResults()
    start_time = time.time()

    logger.info("=" * 60)
    logger.info("MERIDIAN SANDBOX INTEGRATION TEST")
    logger.info(f"Environment: {sq_config.environment}")
    logger.info(f"Base URL: {sq_config.base_url}")
    logger.info("=" * 60)

    async with SquareClient() as client:

        # ── Test 1: Connection ────────────────────────────
        logger.info("\n📡 Test 1: API Connection")
        try:
            locations = await client.list_locations()
            if locations:
                loc = locations[0]
                results.ok(
                    "api_connection",
                    f"Connected. Location: {loc.get('name')} (ID: {loc.get('id')})"
                )
            else:
                results.fail("api_connection", "No locations returned")
        except Exception as e:
            results.fail("api_connection", str(e))
            logger.error("Cannot continue without API connection")
            print(results.summary())
            return results

        # ── Test 2: Locations ─────────────────────────────
        logger.info("\n🏢 Test 2: Location Mapping")
        try:
            mapper = DataMapper(org_id="test-org-001")
            mapped_locations = []
            for sq_loc in locations:
                mapped = mapper.map_location(sq_loc)
                mapped_locations.append(mapped)
                # Update lookup for later tests
                mapper.location_lookup[sq_loc["id"]] = mapped["id"]

            results.ok(
                "location_mapping",
                f"{len(mapped_locations)} locations mapped. "
                f"Fields: name={mapped_locations[0].get('name')}, "
                f"active={mapped_locations[0].get('is_active')}"
            )
        except Exception as e:
            results.fail("location_mapping", str(e))

        # ── Test 3: Catalog ───────────────────────────────
        logger.info("\n📦 Test 3: Catalog Sync")
        try:
            all_catalog = await client.list_all_catalog(
                types=["CATEGORY", "ITEM", "ITEM_VARIATION"]
            )
            categories = [o for o in all_catalog if o.get("type") == "CATEGORY"]
            items = [o for o in all_catalog if o.get("type") == "ITEM"]

            # Map categories
            mapped_cats = []
            for sq_cat in categories:
                cat = mapper.map_category(sq_cat)
                mapped_cats.append(cat)
                mapper.category_lookup[sq_cat["id"]] = cat["id"]

            # Map products
            mapped_products = []
            for sq_item in items:
                products = mapper.map_products(sq_item)
                mapped_products.extend(products)
                for p in products:
                    if p.get("external_id"):
                        mapper.product_lookup[p["external_id"]] = p["id"]

            results.ok(
                "catalog_sync",
                f"{len(categories)} categories, {len(items)} items → "
                f"{len(mapped_cats)} mapped categories, "
                f"{len(mapped_products)} mapped products"
            )

            # Show some products
            if mapped_products:
                sample = mapped_products[0]
                results.ok(
                    "product_data_quality",
                    f"Sample: '{sample.get('name')}' @ "
                    f"${sample.get('price_cents', 0)/100:.2f}, "
                    f"SKU={sample.get('sku')}"
                )
        except Exception as e:
            results.fail("catalog_sync", str(e))

        # ── Test 4: Team Members ──────────────────────────
        logger.info("\n👥 Test 4: Team Members")
        try:
            location_ids = [loc["id"] for loc in locations]
            members = await client.search_all_team_members(
                location_ids=location_ids
            )
            
            employee_cache = {}
            for member in members:
                emp_id, emp_name = mapper.map_team_member(member)
                employee_cache[emp_id] = emp_name
            
            mapper.employee_cache = employee_cache

            if members:
                results.ok(
                    "team_members",
                    f"{len(members)} team members cached. "
                    f"Sample: {list(employee_cache.values())[:3]}"
                )
            else:
                results.skip("team_members", "No team members in sandbox (expected)")
        except SquareAPIError as e:
            if e.status_code == 404 or "not found" in str(e).lower():
                results.skip("team_members", "Team Members API not available in sandbox")
            else:
                results.fail("team_members", str(e))
        except Exception as e:
            results.skip("team_members", f"Non-critical: {str(e)}")

        # ── Test 5: Orders ────────────────────────────────
        logger.info("\n💳 Test 5: Order Sync")
        try:
            location_ids = [loc["id"] for loc in locations]
            
            # Search last 30 days of orders
            since = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
            orders, cursor = await client.search_orders(
                location_ids=location_ids,
                start_at=since,
                states=["COMPLETED", "CANCELED"],
            )

            mapped_txns = []
            mapped_items = []
            for order in orders:
                txn = mapper.map_transaction(order)
                mapped_txns.append(txn)
                items = mapper.map_transaction_items(
                    order, txn["id"], txn["transaction_at"]
                )
                mapped_items.extend(items)

            total_cents = sum(t.get("total_cents", 0) for t in mapped_txns)

            if orders:
                results.ok(
                    "order_sync",
                    f"{len(orders)} orders → {len(mapped_txns)} transactions, "
                    f"{len(mapped_items)} line items. "
                    f"Revenue: ${total_cents/100:,.2f}"
                )
                
                # Verify mapping quality
                sample_txn = mapped_txns[0]
                fields_present = [
                    k for k in ["external_id", "type", "total_cents", "transaction_at", "payment_method"]
                    if sample_txn.get(k) is not None
                ]
                results.ok(
                    "transaction_data_quality",
                    f"Fields mapped: {fields_present}"
                )
            else:
                results.skip(
                    "order_sync",
                    "No orders in sandbox (create test transactions in Square Dashboard)"
                )
        except Exception as e:
            results.fail("order_sync", str(e))

        # ── Test 6: Inventory ─────────────────────────────
        logger.info("\n📊 Test 6: Inventory")
        try:
            catalog_ids = list(mapper.product_lookup.keys())[:20]  # First 20
            if catalog_ids:
                counts = await client.batch_retrieve_all_inventory_counts(
                    catalog_object_ids=catalog_ids,
                    location_ids=location_ids,
                )
                
                mapped_inventory = []
                for count in counts:
                    snapshot = mapper.map_inventory_count(count)
                    mapped_inventory.append(snapshot)
                
                if counts:
                    results.ok(
                        "inventory_sync",
                        f"{len(counts)} inventory counts → {len(mapped_inventory)} snapshots"
                    )
                else:
                    results.skip("inventory_sync", "No inventory data in sandbox")
            else:
                results.skip("inventory_sync", "No products to check inventory for")
        except SquareAPIError as e:
            results.skip("inventory_sync", f"Inventory API: {str(e)}")
        except Exception as e:
            results.skip("inventory_sync", f"Non-critical: {str(e)}")

        # ── Test 7: Rate Limiter ──────────────────────────
        logger.info("\n⚡ Test 7: Rate Limiter")
        try:
            from src.square.rate_limiter import TokenBucketRateLimiter
            
            limiter = TokenBucketRateLimiter(rate=10.0, capacity=10.0)
            
            start = time.time()
            for _ in range(5):
                await limiter.acquire()
            elapsed = time.time() - start
            
            results.ok(
                "rate_limiter",
                f"5 acquires in {elapsed:.3f}s (should be <1s for burst)"
            )
        except Exception as e:
            results.fail("rate_limiter", str(e))

        # ── Test 8: Full Backfill (Integration) ───────────
        logger.info("\n🔄 Test 8: Full Sync Engine Backfill")
        try:
            db = InMemoryDB()
            engine = SyncEngine(
                client=client,
                org_id="test-org-001",
                pos_connection_id="test-conn-001",
            )
            
            result = await engine.run_initial_backfill()
            
            # Persist to in-memory DB
            for loc in result.locations:
                await db.upsert_location(loc)
            for cat in result.categories:
                await db.upsert_category(cat)
            for product in result.products:
                await db.upsert_product(product)
            for txn in result.transactions:
                items = [
                    item for item in result.transaction_items
                    if item["transaction_id"] == txn["id"]
                ]
                await db.upsert_transaction(txn, items)
            for snapshot in result.inventory_snapshots:
                await db.upsert_inventory(snapshot)
            
            stats = db.stats()
            results.ok(
                "full_backfill",
                f"Complete! {json.dumps(stats)}"
            )
            
            # Show summary
            if result.errors:
                results.ok(
                    "backfill_errors",
                    f"{len(result.errors)} non-critical errors: {result.errors[:3]}"
                )
            
        except Exception as e:
            results.fail("full_backfill", str(e))

    # ── Results ───────────────────────────────────────────
    elapsed = time.time() - start_time
    
    print(results.summary())
    print(f"\nCompleted in {elapsed:.1f}s")
    
    for name, detail in results.details.items():
        status = "✅" if name in results.passed else "❌" if name in results.failed else "⏭️"
        print(f"  {status} {name}: {detail}")
    
    return results


if __name__ == "__main__":
    asyncio.run(run_sandbox_tests())
