-- 048_fee_allocation_mode.sql
-- Phone-order fee allocation: three modes for the per-order Meridian + Stripe
-- fee, SET BY THE SALES REP AT CLOSE and FIXED thereafter.
--
--   business_pays  — the fee is absorbed by the owner (customer total == order
--                    subtotal; the whole per-order fee comes out of the payout).
--   split_5050     — half the fee is added to the customer total, half absorbed
--                    by the business. The ODD CENT goes to the CUSTOMER side
--                    (customer = ceil(F/2), business = floor(F/2)).
--   customer_pays  — the full fee is added to the customer total (owner absorbs
--                    nothing).
--
-- Where F = Meridian's per-order fee (plan tier / rep override) + Stripe's
-- 2.9% + 30¢. The math lives in services/phone_agent/payment_links.allocate_fee.
--
-- The mode is a property of the merchant, stored on phone_agent_config. A NULL
-- value means "legacy": callers keep the pre-existing FEE_SPLIT / gross-up
-- behavior byte-for-byte, so existing merchants and deploys are unaffected until
-- a rep explicitly sets a mode at provisioning.
--
-- The owner CANNOT change the mode from settings; they see it read-only and may
-- file a fee_change_requests ticket (below) that notifies HQ. HQ / the service
-- role changes the mode on phone_agent_config out of band.
--
-- ADDITIVE + idempotent: safe to run more than once. Run manually in the
-- Supabase SQL editor like every other migration here.

-- ═══════════════════════════════════════════════════════════════
-- 1. phone_agent_config.fee_allocation_mode — the rep-set, FIXED mode
-- ═══════════════════════════════════════════════════════════════
ALTER TABLE phone_agent_config
    ADD COLUMN IF NOT EXISTS fee_allocation_mode text;

-- Guard the enum at the DB (NULL allowed = legacy behavior).
DO $$ BEGIN
    ALTER TABLE phone_agent_config
        ADD CONSTRAINT phone_agent_config_fee_allocation_mode_chk
        CHECK (fee_allocation_mode IS NULL
               OR fee_allocation_mode IN ('business_pays', 'split_5050', 'customer_pays'));
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

COMMENT ON COLUMN phone_agent_config.fee_allocation_mode IS
    'Rep-set fee allocation mode, FIXED at close: business_pays | split_5050 | '
    'customer_pays. NULL = legacy fee-split / env-default behavior. Owner sees '
    'it read-only and files fee_change_requests to change it (migration 048).';

-- ═══════════════════════════════════════════════════════════════
-- 2. fee_change_requests — owner-filed "change my fee mode" tickets
-- ═══════════════════════════════════════════════════════════════
-- Org-scoped, RLS-enabled, with the EXPLICIT `authenticated` GRANTs the repo
-- needs (enabling RLS alone leaves `authenticated` without table privileges →
-- user-JWT calls 500 with Postgres 42501). RLS decides WHICH rows; GRANT decides
-- whether the role may touch the table AT ALL. Membership predicate mirrors
-- migration 025 (cpa_expenses): businesses.owner_user_id OR active business_users.
-- FK target is businesses(id) (TEXT) — the app's org_id.
CREATE TABLE IF NOT EXISTS fee_change_requests (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id            TEXT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,

    current_mode      TEXT,                              -- mode at request time (nullable = legacy)
    requested_mode    TEXT NOT NULL
        CHECK (requested_mode IN ('business_pays', 'split_5050', 'customer_pays')),
    reason            TEXT,
    status            TEXT NOT NULL DEFAULT 'open'
        CHECK (status IN ('open', 'approved', 'denied', 'closed')),

    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- HQ triages newest-first; cheap org-scoped ordering.
CREATE INDEX IF NOT EXISTS idx_fee_change_requests_org
    ON fee_change_requests (org_id, created_at DESC);

ALTER TABLE fee_change_requests ENABLE ROW LEVEL SECURITY;

-- Owner / active member of the org may READ + INSERT their own org's rows.
DO $$ BEGIN
    CREATE POLICY "fee_change_requests_member_read" ON fee_change_requests
        FOR SELECT USING (
            EXISTS (SELECT 1 FROM businesses b
                    WHERE b.id = fee_change_requests.org_id AND b.owner_user_id = auth.uid())
            OR EXISTS (SELECT 1 FROM business_users bu
                       WHERE bu.business_id = fee_change_requests.org_id
                         AND bu.user_id = auth.uid() AND bu.is_active)
        );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE POLICY "fee_change_requests_member_insert" ON fee_change_requests
        FOR INSERT WITH CHECK (
            EXISTS (SELECT 1 FROM businesses b
                    WHERE b.id = fee_change_requests.org_id AND b.owner_user_id = auth.uid())
            OR EXISTS (SELECT 1 FROM business_users bu
                       WHERE bu.business_id = fee_change_requests.org_id
                         AND bu.user_id = auth.uid() AND bu.is_active)
        );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- HQ / service role reads (and manages) ALL rows.
DO $$ BEGIN
    CREATE POLICY "fee_change_requests_service_all" ON fee_change_requests
        FOR ALL USING (auth.role() = 'service_role')
        WITH CHECK (auth.role() = 'service_role');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- RLS governs rows; grants govern table access. Owners insert/read; service_role
-- gets full DML (triage: approve/deny/close).
GRANT SELECT, INSERT ON fee_change_requests TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON fee_change_requests TO service_role;
