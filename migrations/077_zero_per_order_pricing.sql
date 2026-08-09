-- 077_zero_per_order_pricing.sql
-- "$0 PER ORDER" pricing model (minutes licensing) — the rep chooses AT CLOSE
-- between the two ways a phone-agent deal can be priced:
--
--   per_order       — today's model, byte-for-byte: tier monthly + per-order
--                     Meridian fee (+ rep-set fee_allocation_mode). NULL means
--                     the same thing (legacy rows), so nothing existing changes.
--   zero_per_order  — the licensing card (Aidan 2026-08-09): a monthly bucket
--                     of AI-call minutes, CA$0.35/min past the bucket, and a
--                     per-order fee of ZERO. No fee_allocation_mode (there is
--                     no per-order fee to allocate). 5-min hard call cap
--                     unchanged.
--
-- Canonical prices live in src/billing/fee_terms.py (ZERO_PER_ORDER_TERMS):
--   CA Premium CA$175 / 600 min, CA Command CA$220 / 1,000 min, CA$0.35/min.
--
-- The model is part of the deal's fee terms: locked onto the lead at close
-- (canada_leads / us_leads) and recorded on merchant_billing_terms
-- (supersede-not-update doctrine unchanged).
--
-- ADDITIVE + idempotent: safe to run more than once. Run manually in the
-- Supabase SQL editor like every other migration here.

-- ═══════════════════════════════════════════════════════════════
-- 1. Fee-terms columns: merchant_billing_terms + both lead tables
-- ═══════════════════════════════════════════════════════════════
ALTER TABLE merchant_billing_terms
    ADD COLUMN IF NOT EXISTS pricing_model text,
    ADD COLUMN IF NOT EXISTS included_monthly_min integer
        CHECK (included_monthly_min IS NULL OR included_monthly_min >= 0),
    ADD COLUMN IF NOT EXISTS monthly_overage_cents_per_min integer
        CHECK (monthly_overage_cents_per_min IS NULL OR monthly_overage_cents_per_min >= 0);

DO $$ BEGIN
    ALTER TABLE merchant_billing_terms
        ADD CONSTRAINT merchant_billing_terms_pricing_model_chk
        CHECK (pricing_model IS NULL
               OR pricing_model IN ('per_order', 'zero_per_order'));
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

COMMENT ON COLUMN merchant_billing_terms.pricing_model IS
  'NULL/per_order = legacy per-order fee model. zero_per_order = minutes licensing: $0/order, monthly minute bucket + per-minute overage.';
COMMENT ON COLUMN merchant_billing_terms.included_monthly_min IS
  'zero_per_order only: AI-call minutes included per calendar month before overage.';
COMMENT ON COLUMN merchant_billing_terms.monthly_overage_cents_per_min IS
  'zero_per_order only: cents per minute past the monthly bucket (billed whole-minute, per call, via voice_ledger source=monthly_overage).';

ALTER TABLE canada_leads
    ADD COLUMN IF NOT EXISTS pricing_model text,
    ADD COLUMN IF NOT EXISTS included_monthly_min integer,
    ADD COLUMN IF NOT EXISTS monthly_overage_cents_per_min integer;

ALTER TABLE us_leads
    ADD COLUMN IF NOT EXISTS pricing_model text,
    ADD COLUMN IF NOT EXISTS included_monthly_min integer,
    ADD COLUMN IF NOT EXISTS monthly_overage_cents_per_min integer;

DO $$ BEGIN
    ALTER TABLE canada_leads
        ADD CONSTRAINT canada_leads_pricing_model_chk
        CHECK (pricing_model IS NULL
               OR pricing_model IN ('per_order', 'zero_per_order'));
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    ALTER TABLE us_leads
        ADD CONSTRAINT us_leads_pricing_model_chk
        CHECK (pricing_model IS NULL
               OR pricing_model IN ('per_order', 'zero_per_order'));
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ═══════════════════════════════════════════════════════════════
-- 2. voice_monthly_calls — idempotent per-call minute meter
-- ═══════════════════════════════════════════════════════════════
-- One row per billed call: the PRIMARY KEY on the Vapi call id is what makes
-- the monthly bucket retry-safe (Vapi re-sends end-of-call reports; the
-- second insert conflicts and the webhook skips re-billing). Month-to-date
-- usage = SUM(billed_min) WHERE merchant/month — computed in
-- vapi_webhook._monthly_bucket_overage, never stored, so there is no counter
-- to drift.
CREATE TABLE IF NOT EXISTS voice_monthly_calls (
  vapi_call_id  text PRIMARY KEY,
  merchant_id   text NOT NULL,
  -- Calendar month bucket, 'YYYY-MM' in UTC (matches the ledger's clock).
  month         text NOT NULL,
  -- Whole minutes billed against the bucket for this call (ceil of duration,
  -- clamped to the merchant's effective hard call cap).
  billed_min    integer NOT NULL CHECK (billed_min >= 0),
  created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_voice_monthly_calls_merchant_month
  ON voice_monthly_calls (merchant_id, month);

-- RLS: backend-only table (service role bypasses RLS). No anon/authenticated
-- policies — usage metering is never read or written from the browser.
ALTER TABLE voice_monthly_calls ENABLE ROW LEVEL SECURITY;
