# Meridian × Square API — Complete Integration Spec

**Version:** 1.0 | **Date:** April 2026 | **Status:** Ready to Build

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│  MERCHANT'S SQUARE POS                                  │
│  (Register, Terminal, Online)                           │
└────────────────────┬────────────────────────────────────┘
                     │ Square API (REST + Webhooks)
                     ▼
┌─────────────────────────────────────────────────────────┐
│  MERIDIAN INTEGRATION LAYER                             │
│  ┌──────────────┐ ┌──────────────┐ ┌────────────────┐  │
│  │ OAuth Module  │ │ Sync Engine  │ │ Webhook Server │  │
│  │ (connect +   │ │ (backfill +  │ │ (real-time     │  │
│  │  refresh)    │ │  incremental)│ │  updates)      │  │
│  └──────────────┘ └──────────────┘ └────────────────┘  │
│  ┌──────────────┐ ┌──────────────┐ ┌────────────────┐  │
│  │ Data Mapper  │ │ Rate Limiter │ │ Error Handler  │  │
│  │ (Square →   │ │ (token bucket│ │ (retry queue + │  │
│  │  Meridian)  │ │  + backoff)  │ │  dead letter)  │  │
│  └──────────────┘ └──────────────┘ └────────────────┘  │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  SUPABASE POSTGRESQL + TIMESCALEDB                      │
│  organizations → pos_connections → products →            │
│  transactions → transaction_items → inventory_snapshots  │
└─────────────────────────────────────────────────────────┘
```

---

## 2. OAuth 2.0 Flow

### 2.1 Scopes Required

We ONLY need **read** permissions. Meridian never writes to the merchant's POS.

| Scope | Purpose |
|-------|---------|
| `MERCHANT_PROFILE_READ` | Get merchant info, locations, business hours |
| `ITEMS_READ` | Read product catalog (items, variations, categories) |
| `ORDERS_READ` | Read all orders/transactions from POS |
| `PAYMENTS_READ` | Read payment details (method, tender, tips) |
| `INVENTORY_READ` | Read inventory counts and adjustments |
| `EMPLOYEES_READ` | Read employee names for staffing analysis |
| `CUSTOMERS_READ` | Read anonymized customer data for repeat-customer analysis |

**Total: 7 scopes, all read-only.** This is important for merchant trust — we never touch their data.

### 2.2 Authorization Flow

```
Step 1: Merchant clicks "Connect Square" on Meridian dashboard
        ↓
Step 2: Redirect to Square authorization page
        GET https://connect.squareup.com/oauth2/authorize
            ?client_id={SQUARE_APP_ID}
            &scope=MERCHANT_PROFILE_READ+ITEMS_READ+ORDERS_READ+PAYMENTS_READ+INVENTORY_READ+EMPLOYEES_READ+CUSTOMERS_READ
            &session=false
            &state={CSRF_TOKEN}
        ↓
Step 3: Merchant approves on Square's page
        ↓
Step 4: Square redirects to our callback
        GET https://app.meridianpos.ai/api/square/callback
            ?code={AUTHORIZATION_CODE}
            &state={CSRF_TOKEN}
        ↓
Step 5: Backend exchanges code for tokens
        POST https://connect.squareup.com/oauth2/token
        {
            "client_id": "{SQUARE_APP_ID}",
            "client_secret": "{SQUARE_APP_SECRET}",
            "code": "{AUTHORIZATION_CODE}",
            "grant_type": "authorization_code"
        }
        ↓
Step 6: Store tokens in pos_connections table
        access_token_enc  → encrypted via Supabase Vault
        refresh_token_enc → encrypted via Supabase Vault
        token_expires_at  → NOW() + 30 days
        status            → 'connected'
```

### 2.3 Token Refresh (automatic)

Square access tokens expire after 30 days. We run a daily cron job:

```python
# Pseudocode for token refresh worker
async def refresh_expiring_tokens():
    """Refresh tokens expiring within 5 days."""
    connections = await db.query("""
        SELECT * FROM pos_connections 
        WHERE provider = 'square' 
        AND status IN ('connected', 'syncing')
        AND token_expires_at < NOW() + INTERVAL '5 days'
    """)
    
    for conn in connections:
        response = square_client.oauth.obtain_token({
            "client_id": SQUARE_APP_ID,
            "client_secret": SQUARE_APP_SECRET,
            "refresh_token": decrypt(conn.refresh_token_enc),
            "grant_type": "refresh_token"
        })
        
        await db.update("pos_connections", conn.id, {
            "access_token_enc": encrypt(response.access_token),
            "refresh_token_enc": encrypt(response.refresh_token),
            "token_expires_at": response.expires_at
        })
```

---

## 3. Square API Endpoints — Complete Mapping

### 3.1 Merchant & Locations

| Square Endpoint | HTTP | Meridian Table | When |
|----------------|------|----------------|------|
| `GET /v2/merchants/{id}` | GET | `organizations` | On connect |
| `GET /v2/locations` | GET | `locations` | On connect + daily |

**Data Mapping — Locations:**
```
Square ListLocations response → Meridian locations table
─────────────────────────────────────────────────────────
location.id                   → external_id (in pos_connections)
location.name                 → name
location.address.address_line_1 → address_line1
location.address.locality     → city
location.address.administrative_district_level_1 → state
location.address.postal_code  → zip_code
location.coordinates.latitude → latitude
location.coordinates.longitude → longitude
location.phone_number         → phone
location.business_hours       → business_hours (JSONB)
location.timezone             → timezone (on organization)
location.status = "ACTIVE"    → is_active
```

### 3.2 Product Catalog

| Square Endpoint | HTTP | Meridian Table | When |
|----------------|------|----------------|------|
| `POST /v2/catalog/list` | POST | `product_categories` + `products` | Initial sync + webhook |
| `POST /v2/catalog/search` | POST | `products` | Incremental sync |
| `POST /v2/catalog/batch-retrieve` | POST | `products` | On-demand detail fetch |

**Data Mapping — Catalog:**
```
Square CatalogObject (type=CATEGORY) → Meridian product_categories
──────────────────────────────────────────────────────────────────
object.id                     → external_id
object.category_data.name     → name
object.category_data.parent_category.id → parent_id (via external_id lookup)
object.is_deleted             → is_active (inverted)

Square CatalogObject (type=ITEM) + ITEM_VARIATION → Meridian products
──────────────────────────────────────────────────────────────────────
object.id                     → external_id (item-level)
object.item_data.name         → name
object.item_data.description  → description
object.item_data.category_id  → category_id (via external_id lookup)
object.item_data.image_ids[0] → image_url (resolve from CatalogImage)
object.item_data.tax_ids      → is_taxable (true if any)
object.item_data.variations[0].id → external_id (variation-level)
variation.item_variation_data.name → variant_attrs.name
variation.item_variation_data.sku → sku
variation.item_variation_data.upc → barcode
variation.item_variation_data.price_money.amount → price_cents
variation.item_variation_data.pricing_type → metadata.pricing_type

** Important: Square items can have multiple variations.
   Each variation becomes a separate row in products with:
   - has_variants = true (on first/main variation)
   - variant_of = main product UUID (on child variations)
   - variant_attrs = {"variation_name": "Large", "sku": "..."} 
```

### 3.3 Orders & Transactions

| Square Endpoint | HTTP | Meridian Table | When |
|----------------|------|----------------|------|
| `POST /v2/orders/search` | POST | `transactions` + `transaction_items` | Backfill + incremental |

**This is our highest-volume endpoint.** SearchOrders is the primary way to get historical and ongoing transaction data.

**Data Mapping — Orders → Transactions:**
```
Square Order → Meridian transactions
──────────────────────────────────────────────────
order.id                      → external_id
order.location_id             → location_id (via external_id lookup)
order.state                   → type:
                                  COMPLETED → 'sale'
                                  CANCELED  → 'void'
order.total_money.amount      → total_cents
order.total_tax_money.amount  → tax_cents
order.total_tip_money.amount  → tip_cents
order.total_discount_money.amount → discount_cents
(total - tax - tip + discount)→ subtotal_cents (calculated)
order.created_at              → transaction_at
order.tenders[0].type         → payment_method:
                                  CARD → 'credit_card'
                                  CASH → 'cash'
                                  SQUARE_GIFT_CARD → 'gift_card'
                                  NO_SALE → 'other'
                                  WALLET → 'mobile_pay'
order.tenders[0].employee_id  → employee_external_id
                                (resolve name from Employees API)
order.fulfillments[0].pickup_details.recipient.display_name
                              → metadata.customer_name (if exists)

Square OrderLineItem → Meridian transaction_items
───────────────────────────────────────────────────
line_item.uid                 → metadata.square_uid
line_item.catalog_object_id   → product_id (via external_id lookup)
line_item.name                → product_name
line_item.quantity            → quantity (parse string to decimal)
line_item.base_price_money.amount → unit_price_cents
line_item.total_money.amount  → total_cents
line_item.total_discount_money.amount → discount_cents
line_item.modifiers[]         → modifiers JSONB:
    [{
        "name": modifier.name,
        "price": modifier.total_price_money.amount
    }]
```

### 3.4 Payments (supplementary detail)

| Square Endpoint | HTTP | Meridian Table | When |
|----------------|------|----------------|------|
| `GET /v2/payments` | GET | `transactions` (enrich) | With each order sync |

We use the Payments API to enrich transaction records with payment-specific details:

```
Square Payment → enrich Meridian transactions
──────────────────────────────────────────────
payment.card_details.card.card_brand → metadata.card_brand
payment.card_details.card.last_4    → metadata.card_last4
payment.tip_money.amount            → tip_cents (more accurate)
payment.processing_fee[0].amount_money → metadata.processing_fee_cents
payment.risk_evaluation.risk_level  → metadata.risk_level
```

### 3.5 Inventory

| Square Endpoint | HTTP | Meridian Table | When |
|----------------|------|----------------|------|
| `POST /v2/inventory/batch-retrieve-counts` | POST | `inventory_snapshots` | Daily + webhook |
| `POST /v2/inventory/batch-retrieve-changes` | POST | `inventory_snapshots` | Incremental |

**Data Mapping — Inventory:**
```
Square InventoryCount → Meridian inventory_snapshots
─────────────────────────────────────────────────────
count.catalog_object_id → product_id (via external_id lookup)
count.location_id       → location_id (via external_id lookup)
count.quantity          → quantity_on_hand (parse string to decimal)
count.calculated_at     → snapshot_at
count.state             → metadata.state (IN_STOCK, SOLD, etc.)

Square InventoryAdjustment → compute deltas
────────────────────────────────────────────
adjustment.from_state / to_state → derive:
    NONE → IN_STOCK           = quantity_received
    IN_STOCK → SOLD           = quantity_sold
    IN_STOCK → WASTE          = quantity_wasted
    adjustment.quantity       = delta amount
```

### 3.6 Employees

| Square Endpoint | HTTP | Meridian Table | When |
|----------------|------|----------------|------|
| `GET /v2/team-members/search` | POST | transactions.employee_name | On connect + weekly |

```
Square TeamMember → employee name cache (in-memory or Redis)
──────────────────────────────────────────────────────────
team_member.id        → key
team_member.given_name + " " + team_member.family_name → value
```

We cache employee names and use them to populate `transactions.employee_name` during order sync.

---

## 4. Sync Strategy

### 4.1 Three Sync Modes

```
MODE 1: INITIAL BACKFILL (runs once on connect)
├── Pull all locations      → locations table
├── Pull full catalog       → product_categories + products
├── Pull orders (last 18mo) → transactions + transaction_items
├── Pull inventory counts   → inventory_snapshots
├── Pull team members       → employee cache
└── Set: historical_import_complete = TRUE

MODE 2: INCREMENTAL SYNC (cron every 15 minutes)
├── SearchOrders since last_sync_at → new/updated transactions
├── Detect new products in orders  → upsert products
├── Update inventory counts        → inventory_snapshots
└── Update: last_sync_at, sync_cursor

MODE 3: REAL-TIME WEBHOOKS (instant)
├── order.created          → insert transaction + items
├── order.updated          → update transaction
├── payment.created        → enrich transaction
├── payment.updated        → update payment details
├── catalog.version.updated → resync changed catalog items
├── inventory.count.updated → upsert inventory snapshot
└── oauth.authorization.revoked → disconnect + notify
```

### 4.2 Initial Backfill Strategy

The backfill is the heaviest operation. Here's how we handle it efficiently:

```python
async def run_initial_backfill(connection_id: str):
    conn = await get_connection(connection_id)
    client = SquareClient(access_token=decrypt(conn.access_token_enc))
    
    # Update status
    await update_connection(conn.id, status='syncing')
    
    # Phase 1: Locations (fast, <1 second)
    locations = await sync_all_locations(client, conn.org_id)
    
    # Phase 2: Catalog (medium, 5-30 seconds)
    await sync_full_catalog(client, conn.org_id)
    
    # Phase 3: Team Members (fast, <2 seconds)
    await sync_team_members(client, conn.org_id)
    
    # Phase 4: Orders — THE BIG ONE (1-30 minutes)
    # We go back 18 months max, chunked by month
    start_date = datetime.now() - timedelta(days=540)  # 18 months
    current = start_date
    
    while current < datetime.now():
        end = min(current + timedelta(days=30), datetime.now())
        
        await sync_orders_range(
            client=client,
            org_id=conn.org_id,
            location_ids=[loc.external_id for loc in locations],
            start_at=current.isoformat(),
            end_at=end.isoformat()
        )
        
        current = end
        # Update progress for UI
        await update_connection(conn.id, 
            metadata={"backfill_progress": current.isoformat()})
    
    # Phase 5: Inventory snapshots (medium, 5-15 seconds)
    await sync_inventory_counts(client, conn.org_id, locations)
    
    # Mark complete
    await update_connection(conn.id, 
        status='connected',
        historical_import_complete=True,
        historical_import_completed_at=datetime.now(),
        last_sync_at=datetime.now())
```

### 4.3 Incremental Sync (every 15 min)

```python
async def run_incremental_sync(connection_id: str):
    conn = await get_connection(connection_id)
    if not conn.historical_import_complete:
        return  # Skip — backfill still running
    
    client = SquareClient(access_token=decrypt(conn.access_token_enc))
    
    # Only fetch orders since last sync
    since = conn.last_sync_at or (datetime.now() - timedelta(hours=1))
    
    orders = await search_orders_since(client, conn.org_id, since)
    await upsert_transactions(conn.org_id, orders)
    
    # Update sync timestamp
    await update_connection(conn.id, last_sync_at=datetime.now())
```

### 4.4 Order Search Query

```python
async def search_orders_since(client, org_id, since, location_ids=None):
    """Search Square orders with pagination."""
    all_orders = []
    cursor = None
    
    while True:
        body = {
            "location_ids": location_ids,
            "query": {
                "filter": {
                    "date_time_filter": {
                        "updated_at": {
                            "start_at": since.isoformat()
                        }
                    },
                    "state_filter": {
                        "states": ["COMPLETED", "CANCELED"]
                    }
                },
                "sort": {
                    "sort_field": "UPDATED_AT",
                    "sort_order": "ASC"
                }
            },
            "limit": 500,  # Max per request
        }
        if cursor:
            body["cursor"] = cursor
        
        response = client.orders.search_orders(body)
        
        if response.is_success():
            orders = response.body.get("orders", [])
            all_orders.extend(orders)
            cursor = response.body.get("cursor")
            if not cursor:
                break
        else:
            raise SyncError(f"Square API error: {response.errors}")
        
        # Rate limit: wait 100ms between calls
        await asyncio.sleep(0.1)
    
    return all_orders
```

---

## 5. Webhook Handler

### 5.1 Endpoint Setup

```
POST https://app.meridianpos.ai/api/webhooks/square
```

### 5.2 Webhook Verification

Square signs every webhook with HMAC-SHA256. We MUST verify:

```python
import hmac
import hashlib

def verify_square_webhook(body: bytes, signature: str, signature_key: str, 
                          notification_url: str) -> bool:
    """Verify Square webhook signature."""
    combined = notification_url.encode() + body
    expected = hmac.new(
        key=signature_key.encode(),
        msg=combined,
        digestmod=hashlib.sha256
    ).digest()
    
    expected_b64 = base64.b64encode(expected).decode()
    return hmac.compare_digest(expected_b64, signature)
```

### 5.3 Event Handler

```python
WEBHOOK_HANDLERS = {
    "order.created": handle_order_created,
    "order.updated": handle_order_updated,
    "payment.created": handle_payment_created,
    "payment.updated": handle_payment_updated,
    "catalog.version.updated": handle_catalog_updated,
    "inventory.count.updated": handle_inventory_updated,
    "oauth.authorization.revoked": handle_auth_revoked,
}

async def handle_square_webhook(request):
    # 1. Verify signature
    body = await request.body()
    signature = request.headers.get("x-square-hmacsha256-signature")
    
    if not verify_square_webhook(body, signature, WEBHOOK_SIGNATURE_KEY, 
                                  WEBHOOK_URL):
        return Response(status_code=403)
    
    # 2. Parse event
    event = json.loads(body)
    event_type = event.get("type")
    merchant_id = event.get("merchant_id")
    
    # 3. Find connection
    conn = await find_connection_by_merchant(merchant_id)
    if not conn:
        return Response(status_code=200)  # ACK but ignore
    
    # 4. Dispatch to handler
    handler = WEBHOOK_HANDLERS.get(event_type)
    if handler:
        # Queue for async processing (respond fast to Square)
        await task_queue.enqueue(handler, event, conn)
    
    # 5. Always respond 200 within 3 seconds (Square requirement)
    return Response(status_code=200)
```

### 5.4 Key Webhook Handlers

```python
async def handle_order_created(event, conn):
    """New order from Square POS."""
    order_id = event["data"]["id"]
    client = get_square_client(conn)
    
    # Fetch full order details
    result = client.orders.retrieve_order(order_id)
    if result.is_success():
        order = result.body["order"]
        await upsert_transaction(conn.org_id, order)

async def handle_catalog_updated(event, conn):
    """Catalog changed — resync affected items."""
    client = get_square_client(conn)
    updated_at = event["data"]["object"]["catalog_version"]["updated_at"]
    
    # Fetch only items changed since last catalog sync
    result = client.catalog.search_catalog_objects({
        "begin_time": conn.metadata.get("last_catalog_sync", updated_at),
        "object_types": ["ITEM", "ITEM_VARIATION", "CATEGORY"]
    })
    
    if result.is_success():
        objects = result.body.get("objects", [])
        await upsert_catalog_objects(conn.org_id, objects)

async def handle_inventory_updated(event, conn):
    """Inventory count changed."""
    counts = event["data"]["object"]["inventory_counts"]
    for count in counts:
        await upsert_inventory_snapshot(conn.org_id, count)

async def handle_auth_revoked(event, conn):
    """Merchant disconnected us from Square Dashboard."""
    await update_connection(conn.id, status='disconnected')
    await send_notification(conn.org_id, 
        title="Square Disconnected",
        body="Your Square POS connection was revoked. Reconnect in Settings.",
        priority='urgent')
```

---

## 6. Rate Limiting & Error Handling

### 6.1 Square Rate Limits

| Endpoint Type | Limit | Our Strategy |
|--------------|-------|-------------|
| Standard endpoints | ~10 req/sec per app | Token bucket: 8 req/sec max |
| Batch endpoints | ~5 req/sec | 4 req/sec max |
| SearchOrders | ~5 req/sec | 4 req/sec, 500 results/page |
| Webhooks | No limit (inbound) | Process async via queue |

### 6.2 Retry Strategy

```python
RETRY_CONFIG = {
    "max_retries": 5,
    "backoff_base": 1,      # 1 second
    "backoff_multiplier": 2, # exponential: 1s, 2s, 4s, 8s, 16s
    "retry_on": [429, 500, 502, 503, 504],
    "dead_letter_after": 5,  # send to dead letter queue after 5 failures
}

async def square_api_call_with_retry(func, *args, **kwargs):
    for attempt in range(RETRY_CONFIG["max_retries"]):
        try:
            result = await func(*args, **kwargs)
            
            if result.is_success():
                return result
            
            status_code = result.status_code
            if status_code == 429:
                # Rate limited — read Retry-After header
                retry_after = int(result.headers.get("Retry-After", 60))
                await asyncio.sleep(retry_after)
                continue
            elif status_code in RETRY_CONFIG["retry_on"]:
                wait = RETRY_CONFIG["backoff_base"] * (
                    RETRY_CONFIG["backoff_multiplier"] ** attempt)
                await asyncio.sleep(wait)
                continue
            else:
                raise SquareAPIError(result.errors)
                
        except ConnectionError:
            wait = RETRY_CONFIG["backoff_base"] * (
                RETRY_CONFIG["backoff_multiplier"] ** attempt)
            await asyncio.sleep(wait)
    
    # All retries exhausted
    await dead_letter_queue.push({
        "func": func.__name__, "args": args,
        "kwargs": kwargs, "attempts": attempt + 1
    })
```

### 6.3 Idempotency

All upserts use `external_id` as the deduplication key:

```sql
-- Upsert transaction (idempotent)
INSERT INTO transactions (
    id, org_id, location_id, external_id, type,
    subtotal_cents, tax_cents, tip_cents, discount_cents, total_cents,
    payment_method, employee_name, transaction_at
)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
ON CONFLICT (org_id, external_id) 
DO UPDATE SET
    total_cents = EXCLUDED.total_cents,
    tax_cents = EXCLUDED.tax_cents,
    tip_cents = EXCLUDED.tip_cents,
    payment_method = EXCLUDED.payment_method,
    updated_at = NOW()
WHERE transactions.total_cents != EXCLUDED.total_cents
   OR transactions.tax_cents != EXCLUDED.tax_cents;
```

---

## 7. Data Volume Estimates

| Merchant Size | Monthly Transactions | Monthly Line Items | Storage/Month |
|--------------|--------------------|--------------------|---------------|
| Small (smoke shop) | 3,000-5,000 | 8,000-15,000 | ~5 MB |
| Medium (restaurant) | 8,000-15,000 | 25,000-50,000 | ~15 MB |
| Large (busy restaurant) | 20,000-40,000 | 60,000-120,000 | ~40 MB |

**18-month backfill for a medium merchant:** ~270K transactions, ~900K line items. With batch processing at 500/request, that's ~540 API calls — completes in ~3-5 minutes.

---

## 8. File Structure

```
meridian/
├── app/
│   ├── api/
│   │   ├── square/
│   │   │   ├── callback.py          # OAuth callback handler
│   │   │   └── webhook.py           # Webhook receiver
│   │   └── ...
│   ├── services/
│   │   ├── square/
│   │   │   ├── __init__.py
│   │   │   ├── client.py            # Square SDK wrapper + token management
│   │   │   ├── oauth.py             # OAuth flow (authorize, callback, refresh)
│   │   │   ├── sync_engine.py       # Orchestrates backfill + incremental
│   │   │   ├── mappers.py           # Square → Meridian data transformers
│   │   │   ├── webhook_handlers.py  # Event-specific handlers
│   │   │   └── rate_limiter.py      # Token bucket rate limiter
│   │   └── ...
│   ├── workers/
│   │   ├── square_backfill.py       # Background backfill worker
│   │   ├── square_incremental.py    # 15-min incremental sync cron
│   │   └── token_refresh.py         # Daily token refresh cron
│   └── ...
```

---

## 9. Environment Variables

```env
# Square OAuth
SQUARE_APP_ID=sq0idp-xxxxxxxxxxxx
SQUARE_APP_SECRET=sq0csp-xxxxxxxxxxxx
SQUARE_ENVIRONMENT=sandbox  # or production
SQUARE_WEBHOOK_SIGNATURE_KEY=xxxxxxxxxxxx

# URLs
SQUARE_REDIRECT_URI=https://app.meridianpos.ai/api/square/callback
SQUARE_WEBHOOK_URL=https://app.meridianpos.ai/api/webhooks/square

# Sync Config
SQUARE_BACKFILL_MONTHS=18
SQUARE_INCREMENTAL_INTERVAL_MINUTES=15
SQUARE_MAX_REQUESTS_PER_SECOND=8
```

---

## 10. Testing Plan

### 10.1 Sandbox Testing

Square provides a full sandbox environment:
- Base URL: `https://connect.squareupsandbox.com`
- Free to use, separate credentials
- Create test accounts with fake transaction data
- Test webhooks via Developer Dashboard "Send Test Event"

### 10.2 Test Scenarios

| # | Scenario | Expected Behavior |
|---|----------|-------------------|
| 1 | OAuth happy path | Merchant authorizes → tokens stored → backfill starts |
| 2 | OAuth denied | Merchant denies → redirect with error → show message |
| 3 | Token refresh | Token near expiry → auto-refresh → no disruption |
| 4 | Token revoked (webhook) | Square sends revoke event → disconnect → notify merchant |
| 5 | Backfill: 50K orders | Completes in <10 min, all data mapped correctly |
| 6 | Incremental: new sale on POS | Appears in Meridian within 15 min (cron) or instant (webhook) |
| 7 | Catalog update | Merchant edits item in Square → webhook → product updated |
| 8 | Rate limit hit | 429 response → exponential backoff → retry succeeds |
| 9 | Square API outage | 500/503 → retry 5x → dead letter queue → alert team |
| 10 | Multi-location merchant | All locations synced, transactions tagged per location |

---

## 11. What Aidan Needs to Do

### RIGHT NOW (10 minutes):

1. **Create a Square Developer Account**
   - Go to: https://developer.squareup.com
   - Sign up (free, no credit card needed)
   - This gives you access to the Developer Dashboard

2. **Create an Application**
   - In the Developer Dashboard, click "New Application"
   - Name it: `Meridian`
   - This generates your `Application ID` and `Application Secret`

3. **Set Up Sandbox Test Account**
   - Go to "Sandbox test accounts" in the left menu
   - Create a test account (simulates a Square merchant)
   - This lets us test the full flow without a real merchant

4. **Share Credentials (securely)**
   - Application ID (starts with `sandbox-sq0idp-...`)
   - Application Secret (starts with `sandbox-sq0csp-...`)
   - Sandbox Access Token (for quick testing)

### BEFORE LAUNCH:

5. **Submit App for Marketplace Review** (when ready for production)
   - Square reviews all apps that use OAuth
   - Review takes 1-2 weeks
   - Requires: privacy policy, terms of service, app description
   - We apply after MVP is working in sandbox

6. **Set Up Webhook URL** (after we deploy the backend)
   - In Developer Dashboard → Webhooks
   - Subscribe to: order.created, order.updated, payment.created, payment.updated, catalog.version.updated, inventory.count.updated, oauth.authorization.revoked

---

## 12. Build Timeline

| Week | Milestone | Details |
|------|-----------|---------|
| 1 | OAuth + Client | OAuth flow, token management, Square SDK wrapper |
| 2 | Sync Engine | Backfill worker, data mappers, incremental sync |
| 3 | Webhooks | Webhook server, event handlers, signature verification |
| 4 | Testing + Polish | Full sandbox testing, error handling, monitoring |

**Square API cost: $0.** All read endpoints are free. We only pay for our own infra.
