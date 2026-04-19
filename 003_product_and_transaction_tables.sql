-- ============================================================
-- PART 3: PRODUCT CATALOG & TRANSACTIONS
-- ============================================================

-- ============================================================
-- PRODUCT CATEGORIES
-- ============================================================
CREATE TABLE product_categories (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    parent_id       UUID REFERENCES product_categories(id) ON DELETE SET NULL,
    external_id     TEXT,  -- ID from POS system
    sort_order      INTEGER DEFAULT 0,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_product_categories_org ON product_categories(org_id);

-- ============================================================
-- PRODUCTS
-- ============================================================
CREATE TABLE products (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    category_id     UUID REFERENCES product_categories(id) ON DELETE SET NULL,
    external_id     TEXT,  -- ID from POS system
    name            TEXT NOT NULL,
    description     TEXT,
    sku             TEXT,
    barcode         TEXT,
    price_cents     INTEGER,  -- current price in cents
    cost_cents      INTEGER,  -- cost/COGS in cents (if available)
    -- Variants tracking (e.g., size, color for clothing)
    has_variants    BOOLEAN DEFAULT FALSE,
    variant_of      UUID REFERENCES products(id) ON DELETE SET NULL,
    variant_attrs   JSONB DEFAULT '{}',  -- {"size": "XL", "color": "blue"}
    -- Status
    is_active       BOOLEAN DEFAULT TRUE,
    is_taxable      BOOLEAN DEFAULT TRUE,
    -- AI-generated fields
    meridian_score  DECIMAL(5,2),  -- 0-100 product performance score
    last_scored_at  TIMESTAMPTZ,
    -- Metadata
    image_url       TEXT,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_products_org ON products(org_id);
CREATE INDEX idx_products_category ON products(org_id, category_id);
CREATE INDEX idx_products_external ON products(org_id, external_id);
CREATE INDEX idx_products_sku ON products(org_id, sku);
CREATE INDEX idx_products_score ON products(org_id, meridian_score DESC);
CREATE INDEX idx_products_active ON products(org_id, is_active) WHERE is_active = TRUE;

-- ============================================================
-- TRANSACTIONS (TimescaleDB Hypertable)
-- This is the core time-series table. Every sale, refund, void.
-- ============================================================
CREATE TABLE transactions (
    id              UUID DEFAULT uuid_generate_v4(),
    org_id          UUID NOT NULL,  -- FK enforced at app level for hypertable compat
    location_id     UUID,
    pos_connection_id UUID,
    external_id     TEXT,  -- transaction ID from POS
    -- Transaction details
    type            transaction_type NOT NULL DEFAULT 'sale',
    subtotal_cents  INTEGER NOT NULL DEFAULT 0,
    tax_cents       INTEGER NOT NULL DEFAULT 0,
    tip_cents       INTEGER NOT NULL DEFAULT 0,
    discount_cents  INTEGER NOT NULL DEFAULT 0,
    total_cents     INTEGER NOT NULL DEFAULT 0,
    -- Payment
    payment_method  payment_method,
    -- Context
    employee_name   TEXT,
    employee_external_id TEXT,
    customer_count  INTEGER,  -- party size (restaurants)
    -- Timing
    transaction_at  TIMESTAMPTZ NOT NULL,  -- when the sale happened
    -- Metadata
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Composite PK for hypertable
    PRIMARY KEY (id, transaction_at)
);

-- Convert to TimescaleDB hypertable (partitioned by transaction_at)
SELECT create_hypertable('transactions', 'transaction_at',
    chunk_time_interval => INTERVAL '1 month',
    if_not_exists => TRUE
);

CREATE INDEX idx_transactions_org_time ON transactions(org_id, transaction_at DESC);
CREATE INDEX idx_transactions_location ON transactions(location_id, transaction_at DESC);
CREATE INDEX idx_transactions_type ON transactions(org_id, type, transaction_at DESC);
CREATE INDEX idx_transactions_external ON transactions(org_id, external_id);
CREATE INDEX idx_transactions_employee ON transactions(org_id, employee_external_id, transaction_at DESC);

-- ============================================================
-- TRANSACTION LINE ITEMS
-- Individual items within each transaction
-- ============================================================
CREATE TABLE transaction_items (
    id              UUID DEFAULT uuid_generate_v4(),
    transaction_id  UUID NOT NULL,
    transaction_at  TIMESTAMPTZ NOT NULL,  -- denormalized for hypertable join
    org_id          UUID NOT NULL,
    product_id      UUID,
    -- Item details
    product_name    TEXT NOT NULL,  -- denormalized for speed
    quantity        DECIMAL(10, 3) NOT NULL DEFAULT 1,
    unit_price_cents INTEGER NOT NULL DEFAULT 0,
    total_cents     INTEGER NOT NULL DEFAULT 0,
    discount_cents  INTEGER NOT NULL DEFAULT 0,
    cost_cents      INTEGER,  -- COGS if available
    -- Metadata
    modifiers       JSONB DEFAULT '[]',  -- e.g., [{"name": "Extra cheese", "price": 150}]
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, transaction_at)
);

SELECT create_hypertable('transaction_items', 'transaction_at',
    chunk_time_interval => INTERVAL '1 month',
    if_not_exists => TRUE
);

CREATE INDEX idx_txn_items_transaction ON transaction_items(transaction_id, transaction_at);
CREATE INDEX idx_txn_items_org_time ON transaction_items(org_id, transaction_at DESC);
CREATE INDEX idx_txn_items_product ON transaction_items(org_id, product_id, transaction_at DESC);

-- ============================================================
-- INVENTORY SNAPSHOTS (daily tracking)
-- ============================================================
CREATE TABLE inventory_snapshots (
    id              UUID DEFAULT uuid_generate_v4(),
    org_id          UUID NOT NULL,
    location_id     UUID,
    product_id      UUID NOT NULL,
    quantity_on_hand DECIMAL(10, 3),
    quantity_sold    DECIMAL(10, 3) DEFAULT 0,
    quantity_received DECIMAL(10, 3) DEFAULT 0,
    quantity_wasted  DECIMAL(10, 3) DEFAULT 0,
    snapshot_at     TIMESTAMPTZ NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, snapshot_at)
);

SELECT create_hypertable('inventory_snapshots', 'snapshot_at',
    chunk_time_interval => INTERVAL '1 month',
    if_not_exists => TRUE
);

CREATE INDEX idx_inventory_org_product ON inventory_snapshots(org_id, product_id, snapshot_at DESC);
