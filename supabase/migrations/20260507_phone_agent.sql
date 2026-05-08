-- Phone Agent — AI phone order system tables
-- Stores merchant phone config, call logs, and phone orders

-- Merchant phone agent configuration
CREATE TABLE IF NOT EXISTS phone_agent_config (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id     TEXT NOT NULL UNIQUE,
    business_name   TEXT NOT NULL DEFAULT '',
    business_type   TEXT NOT NULL DEFAULT 'restaurant',
    phone_number    TEXT,
    greeting        TEXT NOT NULL DEFAULT 'Thank you for calling! How can I help you today?',
    voice           TEXT NOT NULL DEFAULT 'af_bella',
    language        TEXT NOT NULL DEFAULT 'en',
    active          BOOLEAN NOT NULL DEFAULT false,
    menu_items      JSONB DEFAULT '[]',
    pos_system      TEXT,
    pos_access_token TEXT,
    pos_location_id TEXT,
    business_hours  JSONB DEFAULT '{}',
    after_hours_message TEXT DEFAULT 'Thank you for calling. We are currently closed.',
    max_concurrent_calls INTEGER NOT NULL DEFAULT 5,
    order_types     JSONB DEFAULT '["pickup", "delivery"]',
    special_instructions_enabled BOOLEAN NOT NULL DEFAULT true,
    transfer_number TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_phone_config_merchant ON phone_agent_config(merchant_id);
CREATE INDEX IF NOT EXISTS idx_phone_config_phone ON phone_agent_config(phone_number);

-- Phone call logs
CREATE TABLE IF NOT EXISTS phone_call_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id     TEXT NOT NULL,
    call_sid        TEXT,
    caller_phone    TEXT,
    status          TEXT NOT NULL DEFAULT 'in_progress',
    duration_seconds INTEGER,
    order_data      JSONB,
    pos_result      JSONB,
    notes           TEXT,
    transcript      JSONB DEFAULT '[]',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_call_logs_merchant ON phone_call_logs(merchant_id);
CREATE INDEX IF NOT EXISTS idx_call_logs_status ON phone_call_logs(status);
CREATE INDEX IF NOT EXISTS idx_call_logs_created ON phone_call_logs(created_at DESC);

-- Phone orders (denormalized for quick dashboard queries)
CREATE TABLE IF NOT EXISTS phone_orders (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id     TEXT NOT NULL,
    customer_name   TEXT,
    order_type      TEXT NOT NULL DEFAULT 'pickup',
    items           JSONB NOT NULL DEFAULT '[]',
    subtotal        NUMERIC(10,2) DEFAULT 0,
    tax             NUMERIC(10,2) DEFAULT 0,
    total           NUMERIC(10,2) DEFAULT 0,
    delivery_address TEXT,
    special_requests TEXT,
    caller_phone    TEXT,
    pos_system      TEXT,
    pos_order_id    TEXT,
    pos_success     BOOLEAN DEFAULT false,
    source          TEXT NOT NULL DEFAULT 'phone_agent',
    status          TEXT NOT NULL DEFAULT 'placed',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_phone_orders_merchant ON phone_orders(merchant_id);
CREATE INDEX IF NOT EXISTS idx_phone_orders_status ON phone_orders(status);
CREATE INDEX IF NOT EXISTS idx_phone_orders_created ON phone_orders(created_at DESC);

-- RLS
ALTER TABLE phone_agent_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE phone_call_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE phone_orders ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on phone_agent_config"
    ON phone_agent_config FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access on phone_call_logs"
    ON phone_call_logs FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access on phone_orders"
    ON phone_orders FOR ALL USING (true) WITH CHECK (true);
