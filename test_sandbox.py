"""
Meridian × Square — Sandbox Integration Test
=============================================
Tests against the live Square sandbox using Aidan's credentials.
Validates: client, rate limiter, all 6 data mappers, sync engine.
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

# Add parent so relative imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def load_dotenv(path):
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip()
load_dotenv("/work/meridian/.env")

from meridian.app.services.square.client import SquareClient, SquareAPIError
from meridian.app.services.square.rate_limiter import SquareRateLimiter, TokenBucket
from meridian.app.services.square.oauth import generate_auth_url
from meridian.app.services.square.mappers import (
    map_location, map_organization_from_location,
    map_category, map_product_from_item,
    map_transaction, map_transaction_items,
    map_payment_enrichment, map_inventory_count,
    build_employee_lookup,
)
from meridian.app.services.square.webhook_handlers import verify_square_webhook
from meridian.app.services.square.sync_engine import (
    SyncContext, sync_locations, sync_catalog, sync_team_members,
    sync_orders_range, sync_inventory,
)

# ── Globals ───────────────────────────────────────────────────────────────
ACCESS_TOKEN = os.getenv("SQUARE_ACCESS_TOKEN", "")
ENVIRONMENT = os.getenv("SQUARE_ENVIRONMENT", "sandbox")
RESULTS: list[dict] = []
PASS = 0
FAIL = 0


def record(name: str, passed: bool, detail: str = ""):
    global PASS, FAIL
    status = "✅ PASS" if passed else "❌ FAIL"
    RESULTS.append({"test": name, "status": status, "detail": detail})
    if passed:
        PASS += 1
    else:
        FAIL += 1
    print(f"  {status}  {name}" + (f"  — {detail}" if detail else ""))


# ══════════════════════════════════════════════════════════════════════════
# 1. RATE LIMITER (unit test, no network)
# ══════════════════════════════════════════════════════════════════════════
async def test_rate_limiter():
    print("\n─── 1. Rate Limiter ───")
    bucket = TokenBucket(rate=100.0, capacity=5.0)

    # 5 immediate acquisitions should succeed (burst capacity)
    t0 = time.monotonic()
    for _ in range(5):
        await bucket.acquire()
    elapsed = time.monotonic() - t0
    record("Burst capacity (5 tokens)", elapsed < 0.1,
           f"elapsed={elapsed:.3f}s")

    # 6th should block briefly
    t0 = time.monotonic()
    await bucket.acquire()
    elapsed = time.monotonic() - t0
    record("Throttle after burst", elapsed >= 0.005,
           f"waited={elapsed:.3f}s")


# ══════════════════════════════════════════════════════════════════════════
# 2. OAUTH URL GENERATION (no network)
# ══════════════════════════════════════════════════════════════════════════
async def test_oauth_url():
    print("\n─── 2. OAuth URL Generation ───")
    url, state = generate_auth_url()
    has_scopes = all(s in url for s in [
        "MERCHANT_PROFILE_READ", "ITEMS_READ", "ORDERS_READ",
        "PAYMENTS_READ", "INVENTORY_READ", "EMPLOYEES_READ", "CUSTOMERS_READ",
    ])
    record("Auth URL contains all 7 scopes", has_scopes,
           f"url_length={len(url)}")
    record("State token is non-empty", len(state) > 16,
           f"state_length={len(state)}")
    record("URL targets sandbox", "squareupsandbox.com" in url)


# ══════════════════════════════════════════════════════════════════════════
# 3. CLIENT — List Locations (live sandbox call)
# ══════════════════════════════════════════════════════════════════════════
async def test_list_locations():
    print("\n─── 3. Client: List Locations ───")
    async with SquareClient(ACCESS_TOKEN, ENVIRONMENT) as client:
        locations = await client.list_locations()

    record("Locations returned", len(locations) > 0,
           f"count={len(locations)}")

    loc = locations[0]
    record("Location has id", bool(loc.get("id")),
           f"id={loc.get('id', 'MISSING')}")
    record("Location has name", bool(loc.get("name")),
           f"name={loc.get('name', 'MISSING')}")

    # Test mapper
    mapped = map_location(loc, "test-org-001")
    record("Mapper: location has all keys",
           all(k in mapped for k in ["id", "org_id", "name", "is_active"]),
           f"keys={list(mapped.keys())}")

    org_data = map_organization_from_location(loc)
    record("Mapper: org extraction", bool(org_data.get("timezone")),
           f"timezone={org_data.get('timezone')}")

    return locations


# ══════════════════════════════════════════════════════════════════════════
# 4. CLIENT — List Catalog
# ══════════════════════════════════════════════════════════════════════════
async def test_catalog():
    print("\n─── 4. Client: Catalog ───")
    async with SquareClient(ACCESS_TOKEN, ENVIRONMENT) as client:
        objects = await client.list_catalog()

    record("Catalog objects returned", isinstance(objects, list),
           f"count={len(objects)}")

    # Breakdown by type
    type_counts: dict[str, int] = {}
    for obj in objects:
        t = obj.get("type", "UNKNOWN")
        type_counts[t] = type_counts.get(t, 0) + 1
    record("Catalog types breakdown", True,
           f"types={type_counts}")

    # Test category mapper
    cats = [o for o in objects if o.get("type") == "CATEGORY"]
    if cats:
        mapped_cat = map_category(cats[0], "test-org-001")
        record("Mapper: category", bool(mapped_cat.get("name")),
               f"name={mapped_cat.get('name')}")

    # Test product mapper
    items = [o for o in objects if o.get("type") == "ITEM"]
    if items:
        mapped_prods = map_product_from_item(items[0], "test-org-001", {}, {})
        record("Mapper: product from item",
               len(mapped_prods) > 0,
               f"variations={len(mapped_prods)}, name={mapped_prods[0].get('name') if mapped_prods else 'N/A'}")

    return objects


# ══════════════════════════════════════════════════════════════════════════
# 5. CLIENT — Search Orders
# ══════════════════════════════════════════════════════════════════════════
async def test_orders(location_ids: list[str]):
    print("\n─── 5. Client: Search Orders ───")
    since = datetime.now(timezone.utc) - timedelta(days=365)
    body = {
        "location_ids": location_ids,
        "query": {
            "filter": {
                "date_time_filter": {
                    "updated_at": {"start_at": since.isoformat()}
                },
                "state_filter": {"states": ["COMPLETED", "CANCELED"]},
            },
            "sort": {"sort_field": "UPDATED_AT", "sort_order": "ASC"},
        },
        "limit": 100,
    }

    async with SquareClient(ACCESS_TOKEN, ENVIRONMENT) as client:
        orders = await client.search_orders(body)

    record("Orders query succeeded", isinstance(orders, list),
           f"count={len(orders)}")

    if orders:
        order = orders[0]
        record("Order has id", bool(order.get("id")),
               f"id={order.get('id', 'MISSING')}")

        # Test mapper
        txn = map_transaction(order, "test-org-001", {}, {})
        record("Mapper: transaction",
               all(k in txn for k in ["external_id", "total_cents", "type", "transaction_at"]),
               f"total=${txn.get('total_cents', 0)/100:.2f}, type={txn.get('type')}")

        items = map_transaction_items(order, "test-org-001", txn["id"], txn["transaction_at"], {})
        record("Mapper: transaction items",
               isinstance(items, list),
               f"items={len(items)}")

    return orders


# ══════════════════════════════════════════════════════════════════════════
# 6. CLIENT — Payments
# ══════════════════════════════════════════════════════════════════════════
async def test_payments():
    print("\n─── 6. Client: Payments ───")
    since = (datetime.now(timezone.utc) - timedelta(days=365)).isoformat()

    async with SquareClient(ACCESS_TOKEN, ENVIRONMENT) as client:
        payments = await client.list_payments(begin_time=since)

    record("Payments query succeeded", isinstance(payments, list),
           f"count={len(payments)}")

    if payments:
        enrichment = map_payment_enrichment(payments[0])
        record("Mapper: payment enrichment",
               isinstance(enrichment, dict),
               f"fields={list(enrichment.keys())}")

    return payments


# ══════════════════════════════════════════════════════════════════════════
# 7. CLIENT — Team Members
# ══════════════════════════════════════════════════════════════════════════
async def test_team_members():
    print("\n─── 7. Client: Team Members ───")
    async with SquareClient(ACCESS_TOKEN, ENVIRONMENT) as client:
        try:
            members = await client.search_team_members()
            record("Team members query succeeded", isinstance(members, list),
                   f"count={len(members)}")

            if members:
                lookup = build_employee_lookup(members)
                record("Mapper: employee lookup",
                       len(lookup) > 0,
                       f"names={list(lookup.values())[:3]}")
        except Exception as e:
            record("Team members query", False, f"error={e}")


# ══════════════════════════════════════════════════════════════════════════
# 8. CLIENT — Inventory
# ══════════════════════════════════════════════════════════════════════════
async def test_inventory(catalog_objects: list[dict], location_ids: list[str]):
    print("\n─── 8. Client: Inventory ───")
    item_var_ids = []
    for obj in catalog_objects:
        if obj.get("type") == "ITEM":
            for var in obj.get("item_data", {}).get("variations", []):
                item_var_ids.append(var["id"])
    item_var_ids = item_var_ids[:50]  # limit for test

    if not item_var_ids:
        record("Inventory (skipped — no catalog items)", True, "no items in catalog")
        return

    async with SquareClient(ACCESS_TOKEN, ENVIRONMENT) as client:
        counts = await client.batch_retrieve_inventory_counts({
            "catalog_object_ids": item_var_ids,
            "location_ids": location_ids,
        })

    record("Inventory counts returned", isinstance(counts, list),
           f"count={len(counts)}")

    if counts:
        row = map_inventory_count(counts[0], "test-org-001", {}, {})
        record("Mapper: inventory count",
               row is None or isinstance(row, dict),
               f"row={'mapped' if row else 'skipped (no product lookup)'}")


# ══════════════════════════════════════════════════════════════════════════
# 9. WEBHOOK SIGNATURE VERIFICATION (unit test)
# ══════════════════════════════════════════════════════════════════════════
async def test_webhook_verification():
    print("\n─── 9. Webhook Signature Verification ───")
    import base64, hashlib, hmac as hmac_mod

    body = b'{"type":"order.created","data":{"id":"abc123"}}'
    key = "test-signature-key-12345"
    url = "https://app.meridianpos.ai/api/webhooks/square"

    combined = url.encode() + body
    expected = base64.b64encode(
        hmac_mod.new(key.encode(), combined, hashlib.sha256).digest()
    ).decode()

    record("Valid signature passes",
           verify_square_webhook(body, expected, key, url))

    record("Invalid signature fails",
           not verify_square_webhook(body, "wrong-signature", key, url))

    record("Empty signature fails",
           not verify_square_webhook(body, "", key, url))


# ══════════════════════════════════════════════════════════════════════════
# 10. SYNC ENGINE — End-to-End
# ══════════════════════════════════════════════════════════════════════════
async def test_sync_engine():
    print("\n─── 10. Sync Engine (end-to-end) ───")
    ctx = SyncContext(org_id="test-org-001")

    async with SquareClient(ACCESS_TOKEN, ENVIRONMENT) as client:
        # Locations
        loc_rows = await sync_locations(client, ctx)
        record("Sync: locations", len(loc_rows) > 0,
               f"count={len(loc_rows)}, lookup_size={len(ctx.location_lookup)}")

        # Catalog
        cat_rows, prod_rows = await sync_catalog(client, ctx)
        record("Sync: catalog",
               isinstance(cat_rows, list) and isinstance(prod_rows, list),
               f"categories={len(cat_rows)}, products={len(prod_rows)}")

        # Team Members
        emp = await sync_team_members(client, ctx)
        record("Sync: team members", isinstance(emp, dict),
               f"count={len(emp)}")

        # Orders (last 30 days)
        since = datetime.now(timezone.utc) - timedelta(days=30)
        until = datetime.now(timezone.utc)
        txn_rows, item_rows = await sync_orders_range(client, ctx, since, until)
        record("Sync: orders (30 days)",
               isinstance(txn_rows, list),
               f"transactions={len(txn_rows)}, items={len(item_rows)}")

        # Inventory
        inv_rows = await sync_inventory(client, ctx)
        record("Sync: inventory", isinstance(inv_rows, list),
               f"snapshots={len(inv_rows)}")


# ══════════════════════════════════════════════════════════════════════════
# RUNNER
# ══════════════════════════════════════════════════════════════════════════
async def main():
    print("=" * 60)
    print("  MERIDIAN × SQUARE — SANDBOX TEST SUITE")
    print(f"  Environment: {ENVIRONMENT}")
    print(f"  Token: {ACCESS_TOKEN[:16]}…")
    print("=" * 60)

    t0 = time.time()

    await test_rate_limiter()
    await test_oauth_url()
    locations = await test_list_locations()
    catalog = await test_catalog()

    location_ids = [loc["id"] for loc in locations]
    orders = await test_orders(location_ids)
    await test_payments()
    await test_team_members()
    await test_inventory(catalog, location_ids)
    await test_webhook_verification()
    await test_sync_engine()

    elapsed = time.time() - t0

    print("\n" + "=" * 60)
    print(f"  RESULTS: {PASS} passed, {FAIL} failed  ({elapsed:.1f}s)")
    print("=" * 60)

    # Write results JSON for reporting
    summary = {
        "passed": PASS,
        "failed": FAIL,
        "elapsed_seconds": round(elapsed, 1),
        "tests": RESULTS,
        "locations_found": len(locations),
        "catalog_objects": len(catalog),
        "orders_found": len(orders),
    }
    with open("/work/meridian/test_results.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)

    return FAIL == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
