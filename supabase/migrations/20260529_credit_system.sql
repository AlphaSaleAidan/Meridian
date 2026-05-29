-- Credit metering: per-merchant balance + immutable transaction ledger.
-- Used by phone agent (per-minute call deduction) and SMS responder
-- (per-inbound + per-outbound deduction). Mirrors the credit model the
-- Content page mocked in frontend; this is the persistent backend for it.

-- Current balance per merchant. One row per merchant, updated in place.
CREATE TABLE IF NOT EXISTS merchant_credits (
    merchant_id     TEXT PRIMARY KEY,
    balance         INTEGER NOT NULL DEFAULT 0 CHECK (balance >= 0),
    lifetime_used   INTEGER NOT NULL DEFAULT 0,
    lifetime_granted INTEGER NOT NULL DEFAULT 0,
    free_granted    INTEGER NOT NULL DEFAULT 0,
    last_low_balance_notified_at TIMESTAMPTZ,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Append-only ledger: every grant, deduction, and refund.
-- delta is positive for grants, negative for deductions.
-- action_type examples:
--   'phone_call', 'sms_inbound', 'sms_outbound',
--   'content_social_post', 'content_seo_article', 'content_image_regen',
--   'starter_grant', 'admin_grant', 'stripe_purchase', 'refund'
CREATE TABLE IF NOT EXISTS credit_ledger (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id     TEXT NOT NULL REFERENCES merchant_credits(merchant_id) ON DELETE CASCADE,
    delta           INTEGER NOT NULL,
    action_type     TEXT NOT NULL,
    action_id       TEXT,
    balance_after   INTEGER NOT NULL,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_credit_ledger_merchant ON credit_ledger(merchant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_credit_ledger_action_type ON credit_ledger(action_type);
CREATE INDEX IF NOT EXISTS idx_credit_ledger_action_id ON credit_ledger(action_id) WHERE action_id IS NOT NULL;

-- Atomic deduct: returns the new balance and inserts the ledger row in
-- a single transaction. Rejects with NULL if balance would go negative.
-- Callers should treat NULL as "insufficient balance" and refuse the action.
CREATE OR REPLACE FUNCTION credits_deduct(
    p_merchant_id TEXT,
    p_amount      INTEGER,
    p_action_type TEXT,
    p_action_id   TEXT DEFAULT NULL,
    p_metadata    JSONB DEFAULT '{}'
) RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_new_balance INTEGER;
BEGIN
    IF p_amount <= 0 THEN
        RAISE EXCEPTION 'credits_deduct: amount must be positive (got %)', p_amount;
    END IF;

    UPDATE merchant_credits
    SET balance = balance - p_amount,
        lifetime_used = lifetime_used + p_amount,
        updated_at = now()
    WHERE merchant_id = p_merchant_id
      AND balance >= p_amount
    RETURNING balance INTO v_new_balance;

    IF v_new_balance IS NULL THEN
        RETURN NULL;
    END IF;

    INSERT INTO credit_ledger (merchant_id, delta, action_type, action_id, balance_after, metadata)
    VALUES (p_merchant_id, -p_amount, p_action_type, p_action_id, v_new_balance, p_metadata);

    RETURN v_new_balance;
END;
$$;

-- Atomic grant: upserts the balance row (so first-time merchants get
-- created with the starter grant), inserts the ledger row.
CREATE OR REPLACE FUNCTION credits_grant(
    p_merchant_id TEXT,
    p_amount      INTEGER,
    p_action_type TEXT,
    p_action_id   TEXT DEFAULT NULL,
    p_metadata    JSONB DEFAULT '{}',
    p_is_free     BOOLEAN DEFAULT FALSE
) RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_new_balance INTEGER;
BEGIN
    IF p_amount <= 0 THEN
        RAISE EXCEPTION 'credits_grant: amount must be positive (got %)', p_amount;
    END IF;

    INSERT INTO merchant_credits (merchant_id, balance, lifetime_granted, free_granted)
    VALUES (
        p_merchant_id,
        p_amount,
        p_amount,
        CASE WHEN p_is_free THEN p_amount ELSE 0 END
    )
    ON CONFLICT (merchant_id) DO UPDATE
    SET balance = merchant_credits.balance + p_amount,
        lifetime_granted = merchant_credits.lifetime_granted + p_amount,
        free_granted = merchant_credits.free_granted + (CASE WHEN p_is_free THEN p_amount ELSE 0 END),
        updated_at = now()
    RETURNING balance INTO v_new_balance;

    INSERT INTO credit_ledger (merchant_id, delta, action_type, action_id, balance_after, metadata)
    VALUES (p_merchant_id, p_amount, p_action_type, p_action_id, v_new_balance, p_metadata);

    RETURN v_new_balance;
END;
$$;

-- RLS
ALTER TABLE merchant_credits ENABLE ROW LEVEL SECURITY;
ALTER TABLE credit_ledger    ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on merchant_credits"
    ON merchant_credits FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access on credit_ledger"
    ON credit_ledger FOR ALL USING (true) WITH CHECK (true);
