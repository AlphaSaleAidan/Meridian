-- 20260716: structured deal fee terms on the lead rows (fee-parity provisioning).
--
-- Root cause being fixed: reps negotiate monthly price / per-order fee / call
-- overage on the lead, but the lead only carries a freetext-ish monthly_value.
-- Live billing is then re-entered manually and drifts from what was sold.
-- These columns are the machine-readable record of the deal terms, locked at
-- close by the backend (canada.py/us.py create-customer + the close flow) and
-- copied verbatim into merchant_billing_terms at provisioning.
--
-- Canonical per-tier values live in ONE backend module:
--   src/billing/fee_terms.py  (mirrors frontend/src/lib/proposal-plans.ts and
--   canada-proposal-plans.ts — keep all three in sync).
--
-- Idempotent: safe to re-run.

-- ── canada_leads ────────────────────────────────────────────────────────────
ALTER TABLE canada_leads ADD COLUMN IF NOT EXISTS plan_tier text;
ALTER TABLE canada_leads ADD COLUMN IF NOT EXISTS monthly_fee_cents integer
  CHECK (monthly_fee_cents IS NULL OR monthly_fee_cents >= 0);
ALTER TABLE canada_leads ADD COLUMN IF NOT EXISTS order_fee_cents integer
  CHECK (order_fee_cents IS NULL OR order_fee_cents >= 0);
ALTER TABLE canada_leads ADD COLUMN IF NOT EXISTS call_overage_cents_per_min integer
  CHECK (call_overage_cents_per_min IS NULL OR call_overage_cents_per_min >= 0);
ALTER TABLE canada_leads ADD COLUMN IF NOT EXISTS included_call_min integer
  CHECK (included_call_min IS NULL OR included_call_min >= 0);
ALTER TABLE canada_leads ADD COLUMN IF NOT EXISTS fee_terms_locked_at timestamptz;
ALTER TABLE canada_leads ADD COLUMN IF NOT EXISTS fee_terms_locked_by text;

COMMENT ON COLUMN canada_leads.plan_tier IS
  'Locked plan tier at close (standard|premium|command). Canonical fees: src/billing/fee_terms.py.';
COMMENT ON COLUMN canada_leads.monthly_fee_cents IS
  'Locked monthly subscription fee in CAD cents (tier base + rep price bump).';
COMMENT ON COLUMN canada_leads.order_fee_cents IS
  'Locked per-order Meridian fee in CAD cents (rep fee slider, clamped to tier redline).';
COMMENT ON COLUMN canada_leads.call_overage_cents_per_min IS
  'Locked voice-call overage in CAD cents per minute over the included block.';
COMMENT ON COLUMN canada_leads.included_call_min IS
  'Locked included AI-call minutes per call before overage billing starts.';
COMMENT ON COLUMN canada_leads.fee_terms_locked_at IS
  'When the fee terms were locked (deal close / customer creation). NULL = not locked yet.';
COMMENT ON COLUMN canada_leads.fee_terms_locked_by IS
  'Who locked the terms (rep email or user id).';

-- ── us_leads ────────────────────────────────────────────────────────────────
ALTER TABLE public.us_leads ADD COLUMN IF NOT EXISTS plan_tier text;
ALTER TABLE public.us_leads ADD COLUMN IF NOT EXISTS monthly_fee_cents integer
  CHECK (monthly_fee_cents IS NULL OR monthly_fee_cents >= 0);
ALTER TABLE public.us_leads ADD COLUMN IF NOT EXISTS order_fee_cents integer
  CHECK (order_fee_cents IS NULL OR order_fee_cents >= 0);
ALTER TABLE public.us_leads ADD COLUMN IF NOT EXISTS call_overage_cents_per_min integer
  CHECK (call_overage_cents_per_min IS NULL OR call_overage_cents_per_min >= 0);
ALTER TABLE public.us_leads ADD COLUMN IF NOT EXISTS included_call_min integer
  CHECK (included_call_min IS NULL OR included_call_min >= 0);
ALTER TABLE public.us_leads ADD COLUMN IF NOT EXISTS fee_terms_locked_at timestamptz;
ALTER TABLE public.us_leads ADD COLUMN IF NOT EXISTS fee_terms_locked_by text;

COMMENT ON COLUMN public.us_leads.plan_tier IS
  'Locked plan tier at close (standard|premium|command). Canonical fees: src/billing/fee_terms.py.';
COMMENT ON COLUMN public.us_leads.monthly_fee_cents IS
  'Locked monthly subscription fee in USD cents (tier base + rep price bump).';
COMMENT ON COLUMN public.us_leads.order_fee_cents IS
  'Locked per-order Meridian fee in USD cents (rep fee slider, clamped to tier redline).';
COMMENT ON COLUMN public.us_leads.call_overage_cents_per_min IS
  'Locked voice-call overage in USD cents per minute over the included block.';
COMMENT ON COLUMN public.us_leads.included_call_min IS
  'Locked included AI-call minutes per call before overage billing starts.';
COMMENT ON COLUMN public.us_leads.fee_terms_locked_at IS
  'When the fee terms were locked (deal close / customer creation). NULL = not locked yet.';
COMMENT ON COLUMN public.us_leads.fee_terms_locked_by IS
  'Who locked the terms (rep email or user id).';
