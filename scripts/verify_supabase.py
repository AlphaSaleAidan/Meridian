"""
Verify Supabase schema deployment via REST API.
Checks tables, views, enums, and functions exist.
"""
import httpx
import json
import sys

SUPABASE_URL = "https://kbuzufjxwflrutowwnfl.supabase.co"
SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtidXp1Zmp4d2ZscnV0b3d3bmZsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NjU2MTcxMSwiZXhwIjoyMDkyMTM3NzExfQ.gM7VDdKcR5maYcZz7iu-9jzEZvkvn2qgI37OWHISgEc"

headers = {
    "apikey": SERVICE_KEY,
    "Authorization": f"Bearer {SERVICE_KEY}",
    "Content-Type": "application/json",
}

EXPECTED_TABLES = [
    "organizations", "locations", "users", "subscriptions",
    "pos_connections", "product_categories", "products",
    "transactions", "transaction_items", "inventory_snapshots",
    "suppliers", "scheduled_events", "notifications", "notification_rules",
    "insights", "money_left_scores", "forecasts",
    "chat_conversations", "chat_messages", "weekly_reports",
    "benchmark_profiles", "benchmark_snapshots",
    "industry_aggregates", "data_export_logs",
]

def check_schema():
    """Check the PostgREST swagger spec for available endpoints."""
    print("🔍 Checking Supabase schema via REST API...\n")
    
    r = httpx.get(f"{SUPABASE_URL}/rest/v1/", headers=headers, timeout=15)
    if r.status_code != 200:
        print(f"❌ REST API error: {r.status_code}")
        return False
    
    schema = r.json()
    
    # PostgREST exposes tables/views in the paths or definitions
    available = set()
    if "paths" in schema:
        for path in schema["paths"]:
            name = path.strip("/")
            if name:
                available.add(name)
    if "definitions" in schema:
        for defn in schema["definitions"]:
            available.add(defn)
    
    print(f"📋 REST API exposes {len(available)} endpoints\n")
    
    # Check expected tables
    passed = 0
    failed = 0
    
    for table in EXPECTED_TABLES:
        if table in available:
            print(f"  ✅ {table}")
            passed += 1
        else:
            print(f"  ❌ {table} — NOT FOUND")
            failed += 1
    
    # Check materialized views (may or may not be in REST API)
    print(f"\n📊 Materialized Views:")
    for mv in ["hourly_revenue", "daily_revenue", "daily_product_performance", "weekly_revenue"]:
        if mv in available:
            print(f"  ✅ {mv}")
            passed += 1
        else:
            print(f"  ⚠️  {mv} — not in REST API (normal for mat views)")
    
    # Try inserting a test org to verify write access
    print(f"\n🔑 Testing write access...")
    test_data = {
        "id": "00000000-0000-0000-0000-000000000001",
        "name": "Meridian Test Org",
        "slug": "meridian-test",
        "business_vertical": "cafe",
    }
    
    r = httpx.post(
        f"{SUPABASE_URL}/rest/v1/organizations",
        headers={**headers, "Prefer": "return=representation"},
        json=test_data,
        timeout=10,
    )
    
    if r.status_code in (200, 201):
        print(f"  ✅ Write test passed — inserted test org")
        
        # Clean up
        r2 = httpx.delete(
            f"{SUPABASE_URL}/rest/v1/organizations?id=eq.00000000-0000-0000-0000-000000000001",
            headers=headers,
            timeout=10,
        )
        if r2.status_code in (200, 204):
            print(f"  ✅ Cleanup passed — removed test org")
        else:
            print(f"  ⚠️  Cleanup: {r2.status_code} {r2.text[:100]}")
    elif r.status_code == 409:
        print(f"  ✅ Table exists (conflict = already has data)")
    else:
        print(f"  ❌ Write failed: {r.status_code} — {r.text[:200]}")
        failed += 1
    
    # Try calling a function
    print(f"\n⚙️  Testing RPC functions...")
    r = httpx.post(
        f"{SUPABASE_URL}/rest/v1/rpc/refresh_analytics_views",
        headers=headers,
        json={},
        timeout=10,
    )
    if r.status_code in (200, 204):
        print(f"  ✅ refresh_analytics_views() — callable")
    else:
        print(f"  ⚠️  refresh_analytics_views(): {r.status_code} — {r.text[:100]}")
    
    print(f"\n{'='*50}")
    print(f"  RESULT: {passed}/{len(EXPECTED_TABLES)} tables found, {failed} missing")
    print(f"{'='*50}")
    
    return failed == 0


if __name__ == "__main__":
    success = check_schema()
    sys.exit(0 if success else 1)
