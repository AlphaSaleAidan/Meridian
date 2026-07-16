-- Menu Store — normalized single-source-of-truth menu (one row per item).
--
-- Replaces the phone_agent_config.menu_items JSONB blob as the canonical menu.
-- The JSONB blob is KEPT as a write-through mirror (published, non-sold-out
-- items in the agent's dict shape) so every legacy reader — phone.py TwiML
-- prompt, the setup wizards' menu hydration, merchant_config.py's fallback —
-- keeps working unchanged. See src/services/menu_store.py.
--
-- Money: all prices are integer CENTS (price_cents, topping_price_cents, and
-- the size_prices JSONB values, e.g. {"medium": 1400, "large": 1800}).
-- The legacy JSONB/agent shape stays in dollars; menu_store converts.
--
-- Idempotent: safe to re-run.

CREATE TABLE IF NOT EXISTS menu_items (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id         TEXT NOT NULL,
    name                TEXT NOT NULL,
    description         TEXT,
    price_cents         INTEGER,
    category            TEXT,
    -- ["medium","large"] — display order for size_prices
    sizes               JSONB,
    -- {"medium": 1400, "large": 1800} — CENTS per size
    size_prices         JSONB,
    topping_price_cents INTEGER,
    -- ["pepperoni","mushroom"] — allowed modifications/options
    modifications       JSONB,
    sold_out            BOOLEAN NOT NULL DEFAULT false,
    -- where the row came from; ingestion paths land needs_review=true except pos
    source              TEXT NOT NULL DEFAULT 'manual'
                        CHECK (source IN ('manual','pos','scrape','csv','photo')),
    -- POS catalog object id (dedupe key for re-syncs); NULL for other sources
    source_external_id  TEXT,
    -- extraction confidence 0..1 (LLM/OCR paths); NULL for manual/pos
    confidence          NUMERIC,
    -- true → shows in the review queue (unpublished ingest, or pos w/o price)
    needs_review        BOOLEAN NOT NULL DEFAULT false,
    -- only published rows reach the agent prompt, the JSONB mirror, and /m/{slug}
    published           BOOLEAN NOT NULL DEFAULT true,
    position            INTEGER,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- One row per (merchant, item name, POS external id). lower(name) so "Wings"
-- and "wings" collapse; coalesce so NULL external ids dedupe as ''.
CREATE UNIQUE INDEX IF NOT EXISTS uq_menu_items_merchant_name_ext
    ON menu_items (merchant_id, lower(name), coalesce(source_external_id, ''));

CREATE INDEX IF NOT EXISTS idx_menu_items_merchant ON menu_items (merchant_id);

-- Public hosted menu page metadata (meridian.tips/m/{public_slug}).
CREATE TABLE IF NOT EXISTS merchant_menus (
    merchant_id  TEXT PRIMARY KEY,
    public_slug  TEXT UNIQUE,
    display_name TEXT,
    published    BOOLEAN NOT NULL DEFAULT false,
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_merchant_menus_slug ON merchant_menus (public_slug);

-- RLS: mirror phone_agent_config's posture (20260507_phone_agent.sql) — these
-- tables are service-role-only; the backend enforces org membership at the API
-- layer (require_service_auth + enforce_service_member) and the public /m/{slug}
-- endpoint only exposes published rows.
ALTER TABLE menu_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE merchant_menus ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY "Service role full access on menu_items"
        ON menu_items FOR ALL USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY "Service role full access on merchant_menus"
        ON merchant_menus FOR ALL USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
