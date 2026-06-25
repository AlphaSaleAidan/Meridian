-- 028_unified_stripe_connect.sql
-- Unified payments: one processor (Stripe Connect) across any POS.
--
-- A merchant gets a Stripe *connected account* during onboarding; the customer
-- pays via Stripe Checkout with the funds routed to that account (destination
-- charge) minus a Meridian application fee. Payment is then decoupled from which
-- POS the merchant runs — the order still goes to their POS via the existing
-- dispatcher, but "take the money" is always Stripe.
--
-- Additive + nullable. The unified path is gated by UNIFIED_PAYMENTS_ENABLED and
-- only used for merchants whose stripe_charges_enabled = true, so this is inert
-- until both are set (no change to the live per-POS payment-link flow).

ALTER TABLE phone_agent_config
    ADD COLUMN IF NOT EXISTS stripe_account_id      TEXT,    -- acct_... connected account
    ADD COLUMN IF NOT EXISTS stripe_charges_enabled BOOLEAN NOT NULL DEFAULT false;

COMMENT ON COLUMN phone_agent_config.stripe_account_id IS
    'Stripe Connect connected-account id (acct_...) for unified checkout. NULL until the merchant completes Connect onboarding.';
COMMENT ON COLUMN phone_agent_config.stripe_charges_enabled IS
    'True once Stripe reports the connected account can accept charges (account.updated webhook). Gates the unified-checkout path.';

-- The checkout-session record the payment-link layer already writes to but which
-- never had a migration (insert silently failed). Now it backs the unified flow.
-- id is TEXT so both the new Stripe flow (uuid) and the legacy meridian-checkout
-- fallback (12-char id) work; legacy columns kept nullable for back-compat.
CREATE TABLE IF NOT EXISTS checkout_sessions (
    id              TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    merchant_id     TEXT NOT NULL,
    pos_order_id    TEXT,
    provider        TEXT NOT NULL DEFAULT 'stripe',   -- stripe | square | toast | clover | meridian
    provider_ref    TEXT,                              -- Stripe Checkout Session id (cs_...) etc.
    amount_cents    INTEGER,
    currency        TEXT NOT NULL DEFAULT 'cad',
    status          TEXT NOT NULL DEFAULT 'created',   -- created | paid | expired | failed
    checkout_url    TEXT,
    short_code      TEXT,                              -- branded short link: <pay base>/p/<code> -> checkout_url
    caller_phone    TEXT,
    -- legacy meridian-hosted-checkout columns (back-compat with _create_meridian_checkout)
    customer_name   TEXT,
    customer_phone  TEXT,
    order_type      TEXT,
    items           JSONB,
    subtotal        NUMERIC,
    tax             NUMERIC,
    total           NUMERIC,
    pos_system      TEXT,
    source          TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- legacy DBs that already have checkout_sessions need the new column added
ALTER TABLE checkout_sessions ADD COLUMN IF NOT EXISTS short_code TEXT;

CREATE INDEX IF NOT EXISTS idx_checkout_sessions_merchant ON checkout_sessions (merchant_id);
CREATE INDEX IF NOT EXISTS idx_checkout_sessions_provider_ref ON checkout_sessions (provider_ref);
CREATE UNIQUE INDEX IF NOT EXISTS idx_checkout_sessions_short_code ON checkout_sessions (short_code) WHERE short_code IS NOT NULL;
