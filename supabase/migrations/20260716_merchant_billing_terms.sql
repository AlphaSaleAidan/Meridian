-- 20260716: merchant_billing_terms — the provisioned billing contract, and the
-- single source of truth for what a live merchant should be charged.
--
-- Written automatically at provisioning (onboarding.provision_customer /
-- canada.create_customer / us.create_customer) from the lead's locked fee
-- terms — no manual re-entry. Manual/legacy provisions record
-- override_reason='manual_provision'.
--
-- AUDIT TRAIL DOCTRINE: rows are NEVER updated in place. A change (admin
-- override, re-negotiation) supersedes the active row (sets superseded_at)
-- and inserts a new one — row history IS the audit trail. Exactly one active
-- (superseded_at IS NULL) row per merchant, enforced by a partial unique index.
--
-- Idempotent: safe to re-run.

CREATE TABLE IF NOT EXISTS merchant_billing_terms (
  id                          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  -- businesses.id is text (uuid-shaped); keep the same type to avoid casts.
  merchant_id                 text NOT NULL,
  source_lead_id              uuid,
  source_market               text CHECK (source_market IS NULL OR source_market IN ('ca', 'us')),
  plan_tier                   text,
  monthly_fee_cents           integer CHECK (monthly_fee_cents IS NULL OR monthly_fee_cents >= 0),
  order_fee_cents             integer CHECK (order_fee_cents IS NULL OR order_fee_cents >= 0),
  call_overage_cents_per_min  integer CHECK (call_overage_cents_per_min IS NULL OR call_overage_cents_per_min >= 0),
  included_call_min           integer CHECK (included_call_min IS NULL OR included_call_min >= 0),
  effective_at                timestamptz NOT NULL DEFAULT now(),
  superseded_at               timestamptz,
  created_by                  text NOT NULL DEFAULT '',
  override_reason             text,
  created_at                  timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE merchant_billing_terms IS
  'Provisioned billing contract per merchant. Supersede-not-update: history is the audit trail. Consumed fail-open by billing_service (monthly), vapi_webhook (call overage) and the order-fee rails; reconciled by src/billing/fee_reconciliation.py.';
COMMENT ON COLUMN merchant_billing_terms.superseded_at IS
  'NULL = the active contract. Set (never deleted) when a newer row replaces it.';
COMMENT ON COLUMN merchant_billing_terms.override_reason IS
  'Required for admin overrides and manual (lead-less) provisions; NULL only for automatic lead-sourced provisioning.';

-- Exactly one ACTIVE terms row per merchant.
CREATE UNIQUE INDEX IF NOT EXISTS uq_merchant_billing_terms_active
  ON merchant_billing_terms (merchant_id)
  WHERE superseded_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_merchant_billing_terms_merchant
  ON merchant_billing_terms (merchant_id, effective_at DESC);
CREATE INDEX IF NOT EXISTS idx_merchant_billing_terms_lead
  ON merchant_billing_terms (source_lead_id)
  WHERE source_lead_id IS NOT NULL;

-- RLS: backend-only table (service role bypasses RLS). No anon/authenticated
-- policies — billing contracts are never read or written from the browser.
ALTER TABLE merchant_billing_terms ENABLE ROW LEVEL SECURITY;
