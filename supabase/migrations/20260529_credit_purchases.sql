-- Credit pack purchases via Square custom invoices.
-- Lifecycle:
--   1. /api/credits/purchase inserts a row with status='pending', creates a
--      Square invoice, stores invoice_id + invoice_url.
--   2. Customer pays via the hosted Square invoice link.
--   3. Square webhook fires invoice.payment_made → /api/credits/webhook/square.
--   4. Handler finds the row by square_invoice_id, idempotently flips status
--      to 'paid', grants credits via credits_grant() in the same logical
--      transaction, sets granted_at.

CREATE TYPE credit_purchase_status AS ENUM (
    'pending',
    'paid',
    'failed',
    'canceled',
    'refunded'
);

CREATE TABLE IF NOT EXISTS credit_purchases (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id        TEXT NOT NULL,
    pack_id            TEXT NOT NULL,           -- 'starter' | 'popular' | 'pro' | 'agency' | 'custom_<n>'
    credit_amount      INTEGER NOT NULL CHECK (credit_amount > 0),
    price_cents        INTEGER NOT NULL CHECK (price_cents > 0),
    currency           TEXT NOT NULL DEFAULT 'USD',

    -- Square IDs filled in as the flow progresses.
    square_invoice_id  TEXT UNIQUE,
    square_order_id    TEXT,
    square_payment_id  TEXT,
    square_customer_id TEXT,
    invoice_url        TEXT,

    status             credit_purchase_status NOT NULL DEFAULT 'pending',

    customer_email     TEXT,
    customer_name      TEXT,

    -- App-level idempotency key (separate from Square's own dedup window).
    -- We reuse this on retries so a single user click can't double-create
    -- a Square invoice.
    idempotency_key    TEXT UNIQUE NOT NULL,
    metadata           JSONB DEFAULT '{}',

    paid_at            TIMESTAMPTZ,
    granted_at         TIMESTAMPTZ,
    expires_at         TIMESTAMPTZ,

    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_credit_purchases_merchant
    ON credit_purchases(merchant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_credit_purchases_status_open
    ON credit_purchases(status, created_at)
    WHERE status IN ('pending', 'paid');
CREATE INDEX IF NOT EXISTS idx_credit_purchases_square_invoice
    ON credit_purchases(square_invoice_id)
    WHERE square_invoice_id IS NOT NULL;

-- Touch updated_at on every UPDATE so dashboards can show "last activity"
-- without us threading the timestamp through every code path.
CREATE OR REPLACE FUNCTION credit_purchases_touch_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_credit_purchases_touch ON credit_purchases;
CREATE TRIGGER trg_credit_purchases_touch
    BEFORE UPDATE ON credit_purchases
    FOR EACH ROW EXECUTE FUNCTION credit_purchases_touch_updated_at();

ALTER TABLE credit_purchases ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role full access on credit_purchases"
    ON credit_purchases FOR ALL USING (true) WITH CHECK (true);
