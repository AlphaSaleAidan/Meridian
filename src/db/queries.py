"""
SQL Query Templates — Parameterized queries for all Meridian database operations.

All upserts use external_id for idempotency (safe to replay syncs).
All money in cents (INTEGER). All timestamps in UTC.
"""

# ─── Location Queries ─────────────────────────────────────────

UPSERT_LOCATION = """
INSERT INTO locations (
    id, org_id, name, is_primary, address_line1, city, state,
    zip_code, latitude, longitude, phone, business_hours, is_active
) VALUES (
    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12::jsonb, $13
)
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
    is_active = EXCLUDED.is_active,
    updated_at = NOW()
RETURNING id;
"""

# ─── POS Connection Queries ──────────────────────────────────

UPSERT_POS_CONNECTION = """
INSERT INTO pos_connections (
    id, org_id, location_id, provider, status,
    access_token_enc, refresh_token_enc, token_expires_at,
    external_merchant_id, external_location_id, metadata
) VALUES (
    $1, $2, $3, 'square', $4, $5, $6, $7, $8, $9, $10::jsonb
)
ON CONFLICT (id) DO UPDATE SET
    status = EXCLUDED.status,
    access_token_enc = EXCLUDED.access_token_enc,
    refresh_token_enc = EXCLUDED.refresh_token_enc,
    token_expires_at = EXCLUDED.token_expires_at,
    updated_at = NOW()
RETURNING id;
"""

UPDATE_CONNECTION_STATUS = """
UPDATE pos_connections SET
    status = $2,
    last_sync_at = COALESCE($3, last_sync_at),
    last_sync_status = $4,
    historical_import_complete = COALESCE($5, historical_import_complete),
    historical_import_completed_at = COALESCE($6, historical_import_completed_at),
    metadata = metadata || COALESCE($7::jsonb, '{}'),
    updated_at = NOW()
WHERE id = $1;
"""

GET_CONNECTIONS_NEEDING_REFRESH = """
SELECT * FROM pos_connections
WHERE provider = 'square'
  AND status IN ('connected', 'syncing')
  AND token_expires_at < NOW() + INTERVAL '5 days';
"""

GET_ACTIVE_CONNECTIONS = """
SELECT * FROM pos_connections
WHERE provider = 'square'
  AND status = 'connected'
  AND historical_import_complete = TRUE;
"""

FIND_CONNECTION_BY_MERCHANT = """
SELECT * FROM pos_connections
WHERE provider = 'square'
  AND external_merchant_id = $1
  AND status IN ('connected', 'syncing')
LIMIT 1;
"""

# ─── Category Queries ─────────────────────────────────────────

UPSERT_CATEGORY = """
INSERT INTO product_categories (
    id, org_id, name, external_id, parent_id, is_active
) VALUES ($1, $2, $3, $4, $5, $6)
ON CONFLICT (org_id, external_id) WHERE external_id IS NOT NULL
DO UPDATE SET
    name = EXCLUDED.name,
    parent_id = EXCLUDED.parent_id,
    is_active = EXCLUDED.is_active,
    updated_at = NOW()
RETURNING id;
"""

# ─── Product Queries ──────────────────────────────────────────

UPSERT_PRODUCT = """
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
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    sku = EXCLUDED.sku,
    barcode = EXCLUDED.barcode,
    price_cents = EXCLUDED.price_cents,
    is_active = EXCLUDED.is_active,
    image_url = EXCLUDED.image_url,
    metadata = products.metadata || EXCLUDED.metadata,
    updated_at = NOW()
RETURNING id;
"""

# ─── Transaction Queries ──────────────────────────────────────

UPSERT_TRANSACTION = """
INSERT INTO transactions (
    id, org_id, location_id, pos_connection_id, external_id,
    type, subtotal_cents, tax_cents, tip_cents, discount_cents,
    total_cents, payment_method, employee_name, employee_external_id,
    transaction_at, metadata
) VALUES (
    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
    $11, $12, $13, $14, $15, $16::jsonb
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
WHERE transactions.total_cents != EXCLUDED.total_cents
   OR transactions.tax_cents != EXCLUDED.tax_cents
   OR transactions.tip_cents != EXCLUDED.tip_cents;
"""

UPSERT_TRANSACTION_ITEM = """
INSERT INTO transaction_items (
    id, transaction_id, transaction_at, org_id, product_id,
    product_name, quantity, unit_price_cents, total_cents,
    discount_cents, modifiers, metadata
) VALUES (
    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11::jsonb, $12::jsonb
)
ON CONFLICT (id, transaction_at)
DO UPDATE SET
    quantity = EXCLUDED.quantity,
    total_cents = EXCLUDED.total_cents,
    discount_cents = EXCLUDED.discount_cents;
"""

ENRICH_TRANSACTION_FROM_PAYMENT = """
UPDATE transactions SET
    tip_cents = COALESCE($2, tip_cents),
    metadata = metadata || $3::jsonb,
    updated_at = NOW()
WHERE org_id = $1 AND external_id = $4;
"""

# ─── Inventory Queries ────────────────────────────────────────

UPSERT_INVENTORY_SNAPSHOT = """
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
    quantity_wasted = EXCLUDED.quantity_wasted;
"""

# ─── Dashboard Queries (for quick validation) ─────────────────

COUNT_TRANSACTIONS_BY_ORG = """
SELECT 
    COUNT(*) as total_transactions,
    SUM(total_cents) as total_revenue_cents,
    MIN(transaction_at) as earliest,
    MAX(transaction_at) as latest
FROM transactions
WHERE org_id = $1;
"""

COUNT_PRODUCTS_BY_ORG = """
SELECT COUNT(*) as total_products
FROM products
WHERE org_id = $1 AND is_active = TRUE;
"""

TOP_PRODUCTS_BY_REVENUE = """
SELECT 
    ti.product_name,
    COUNT(*) as times_sold,
    SUM(ti.total_cents) as revenue_cents
FROM transaction_items ti
WHERE ti.org_id = $1
  AND ti.transaction_at >= NOW() - INTERVAL '30 days'
GROUP BY ti.product_name
ORDER BY revenue_cents DESC
LIMIT 20;
"""
