-- 029_voice_ledger.sql
-- Per-merchant voice ledger: track the economics of the AI phone agent per account.
--
-- Each row is a single posting:
--   credit  → revenue we earned from this merchant's phone orders (the Stripe
--             service fee we auto-take on each paid order, source 'stripe_fee')
--   debit   → cost we incurred serving this merchant's calls (the Vapi
--             end-of-call cost, source 'vapi_call')
--
-- Balance(merchant) = SUM(credit) - SUM(debit). A positive balance means the
-- merchant's phone orders have more than paid for their voice usage. This is the
-- accounting view behind the auto-reload concept — revenue funds usage per
-- account. Vapi native auto-top-up (card on file) handles the global float; this
-- ledger is the per-merchant P&L + an optional low-balance fallback gate.
--
-- Additive. amount_cents is always positive; `kind` carries the sign.
-- Idempotent on (source, ref): the Stripe session id / Vapi call id is the ref,
-- so a webhook retry never double-posts.

CREATE TABLE IF NOT EXISTS voice_ledger (
    id           BIGSERIAL PRIMARY KEY,
    merchant_id  TEXT NOT NULL,
    kind         TEXT NOT NULL CHECK (kind IN ('credit', 'debit')),
    amount_cents INTEGER NOT NULL CHECK (amount_cents >= 0),
    source       TEXT NOT NULL,            -- 'stripe_fee' | 'vapi_call' | 'manual'
    ref          TEXT,                     -- idempotency key (cs_... / vapi call id)
    note         TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_voice_ledger_merchant ON voice_ledger (merchant_id);

-- A given external event posts at most once.
CREATE UNIQUE INDEX IF NOT EXISTS idx_voice_ledger_source_ref
    ON voice_ledger (source, ref) WHERE ref IS NOT NULL;

COMMENT ON TABLE voice_ledger IS
    'Per-merchant voice-agent economics: credit = Stripe service-fee revenue, debit = Vapi call cost. Balance = SUM(credit)-SUM(debit).';
