-- 025_cpa_taxes_expenses.sql
-- Taxes & Expenses ("CPA Handoff packet") — expense + bank/card feed storage.
--
-- Tax-paperwork PREPARATION only. These tables hold the EXPENSE side of a
-- merchant's books (income stays in phone_orders / POS) so Meridian can organize
-- revenue + sales tax collected + categorized expenses (with a per-card
-- breakdown) into a CPA-ready packet (CSV + printable report). Meridian does NOT
-- calculate income tax, file returns, or give tax advice.
--
-- Three tables:
--   cpa_expenses          -- manual entries + CSV imports
--   cpa_bank_connections  -- one row per connected bank/card provider item
--   cpa_transactions      -- bank/card transactions (debits feed the expense total)
--
-- Run manually in the Supabase SQL editor (like every other migration here).
-- Org-scoped, RLS-enabled, with the EXPLICIT `authenticated` GRANTs the repo
-- needs: enabling RLS alone leaves the `authenticated` role without table
-- privileges, so user-JWT calls 500 with Postgres error 42501. RLS decides
-- WHICH rows; GRANT decides whether the role may touch the table AT ALL.
--
-- FK target is `businesses(id)` (TEXT): the app's org_id IS businesses.id
-- (verified against auth.py::_check_org_membership, which authorizes by
-- businesses.id == org_id / business_users.business_id == org_id, and against
-- phone_orders.merchant_id which is also TEXT). organizations.id (uuid) is a
-- different key and is NOT what the API passes. The backend writes via the
-- service role, so member-RLS only governs future direct user-JWT access.

-- Shared updated_at trigger fn (idempotent).
CREATE OR REPLACE FUNCTION set_cpa_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Reusable membership predicate, inlined per policy (no shared SQL fn to keep
-- this migration self-contained):
--   owner:  businesses.owner_user_id = auth.uid()
--   member: business_users(business_id, user_id, is_active)

-- ═══════════════════════════════════════════════════════════════
-- 1. cpa_expenses — manual entries + CSV imports
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS cpa_expenses (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id        TEXT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,

    expense_date  DATE NOT NULL,
    category      TEXT NOT NULL DEFAULT 'other',   -- supplies|cogs|rent|utilities|payroll|marketing|equipment|fees|other
    vendor        TEXT NOT NULL,
    amount_cents  BIGINT NOT NULL CHECK (amount_cents > 0),  -- CAD cents
    note          TEXT,
    source        TEXT NOT NULL DEFAULT 'manual',  -- manual|import

    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_cpa_expenses_org      ON cpa_expenses (org_id);
CREATE INDEX IF NOT EXISTS idx_cpa_expenses_org_date ON cpa_expenses (org_id, expense_date);

ALTER TABLE cpa_expenses ENABLE ROW LEVEL SECURITY;

CREATE POLICY "cpa_expenses_member_read" ON cpa_expenses
    FOR SELECT USING (
        EXISTS (SELECT 1 FROM businesses b
                WHERE b.id = cpa_expenses.org_id AND b.owner_user_id = auth.uid())
        OR EXISTS (SELECT 1 FROM business_users bu
                   WHERE bu.business_id = cpa_expenses.org_id
                     AND bu.user_id = auth.uid() AND bu.is_active)
    );
CREATE POLICY "cpa_expenses_member_insert" ON cpa_expenses
    FOR INSERT WITH CHECK (
        EXISTS (SELECT 1 FROM businesses b
                WHERE b.id = cpa_expenses.org_id AND b.owner_user_id = auth.uid())
        OR EXISTS (SELECT 1 FROM business_users bu
                   WHERE bu.business_id = cpa_expenses.org_id
                     AND bu.user_id = auth.uid() AND bu.is_active)
    );
CREATE POLICY "cpa_expenses_member_update" ON cpa_expenses
    FOR UPDATE USING (
        EXISTS (SELECT 1 FROM businesses b
                WHERE b.id = cpa_expenses.org_id AND b.owner_user_id = auth.uid())
        OR EXISTS (SELECT 1 FROM business_users bu
                   WHERE bu.business_id = cpa_expenses.org_id
                     AND bu.user_id = auth.uid() AND bu.is_active)
    );
CREATE POLICY "cpa_expenses_member_delete" ON cpa_expenses
    FOR DELETE USING (
        EXISTS (SELECT 1 FROM businesses b
                WHERE b.id = cpa_expenses.org_id AND b.owner_user_id = auth.uid())
        OR EXISTS (SELECT 1 FROM business_users bu
                   WHERE bu.business_id = cpa_expenses.org_id
                     AND bu.user_id = auth.uid() AND bu.is_active)
    );
CREATE POLICY "cpa_expenses_service_all" ON cpa_expenses
    FOR ALL USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

GRANT SELECT, INSERT, UPDATE, DELETE ON cpa_expenses TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON cpa_expenses TO service_role;

DROP TRIGGER IF EXISTS trg_cpa_expenses_updated_at ON cpa_expenses;
CREATE TRIGGER trg_cpa_expenses_updated_at
    BEFORE UPDATE ON cpa_expenses
    FOR EACH ROW EXECUTE FUNCTION set_cpa_updated_at();

-- ═══════════════════════════════════════════════════════════════
-- 2. cpa_bank_connections — one row per connected provider item
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS cpa_bank_connections (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id            TEXT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,

    provider          TEXT NOT NULL DEFAULT 'plaid',   -- plaid|demo
    access_ref        TEXT,                             -- opaque access token ref (encrypt in prod); 'demo' for the demo provider
    item_id           TEXT,                             -- provider item id
    institution_name  TEXT,
    status            TEXT NOT NULL DEFAULT 'connected',-- connected|error|disconnected

    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_cpa_bank_conn_org ON cpa_bank_connections (org_id);

ALTER TABLE cpa_bank_connections ENABLE ROW LEVEL SECURITY;

-- Members may READ their connections (so the UI can list them). Writes go through
-- the service role only — access_ref is sensitive and is never written by a
-- browser-held JWT.
CREATE POLICY "cpa_bank_conn_member_read" ON cpa_bank_connections
    FOR SELECT USING (
        EXISTS (SELECT 1 FROM businesses b
                WHERE b.id = cpa_bank_connections.org_id AND b.owner_user_id = auth.uid())
        OR EXISTS (SELECT 1 FROM business_users bu
                   WHERE bu.business_id = cpa_bank_connections.org_id
                     AND bu.user_id = auth.uid() AND bu.is_active)
    );
CREATE POLICY "cpa_bank_conn_service_all" ON cpa_bank_connections
    FOR ALL USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- authenticated may SELECT only (no INSERT/UPDATE/DELETE — backend service-role
-- owns the secret-bearing writes). service_role gets full DML.
GRANT SELECT ON cpa_bank_connections TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON cpa_bank_connections TO service_role;

DROP TRIGGER IF EXISTS trg_cpa_bank_conn_updated_at ON cpa_bank_connections;
CREATE TRIGGER trg_cpa_bank_conn_updated_at
    BEFORE UPDATE ON cpa_bank_connections
    FOR EACH ROW EXECUTE FUNCTION set_cpa_updated_at();

-- ═══════════════════════════════════════════════════════════════
-- 3. cpa_transactions — bank/card transactions (debits feed expenses)
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS cpa_transactions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    connection_id   UUID NOT NULL REFERENCES cpa_bank_connections(id) ON DELETE CASCADE,
    org_id          TEXT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,  -- denormalized for RLS + org-scoped queries

    account_id      TEXT,
    card_last4      TEXT,                              -- per-card breakdown key
    account_label   TEXT,                              -- e.g. 'RBC Business Visa'
    posted_date     DATE NOT NULL,
    amount_cents    BIGINT NOT NULL,                   -- CAD cents (positive)
    direction       TEXT NOT NULL DEFAULT 'debit',     -- debit|credit (only debit feeds expenses)
    merchant_name   TEXT,
    category        TEXT NOT NULL DEFAULT 'other',     -- same enum as cpa_expenses; merchant-overridable
    provider_txn_id TEXT,                              -- provider's transaction id, for dedup
    raw_json        JSONB DEFAULT '{}',

    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Dedup: a provider transaction id is unique within a connection.
    UNIQUE (connection_id, provider_txn_id)
);

CREATE INDEX IF NOT EXISTS idx_cpa_txn_org       ON cpa_transactions (org_id);
CREATE INDEX IF NOT EXISTS idx_cpa_txn_org_date  ON cpa_transactions (org_id, posted_date);
CREATE INDEX IF NOT EXISTS idx_cpa_txn_conn      ON cpa_transactions (connection_id);
CREATE INDEX IF NOT EXISTS idx_cpa_txn_card      ON cpa_transactions (org_id, card_last4);

ALTER TABLE cpa_transactions ENABLE ROW LEVEL SECURITY;

-- Members READ + UPDATE (category override) their org's transactions. Inserts are
-- service-role only (they come from the provider sync, never the browser).
CREATE POLICY "cpa_txn_member_read" ON cpa_transactions
    FOR SELECT USING (
        EXISTS (SELECT 1 FROM businesses b
                WHERE b.id = cpa_transactions.org_id AND b.owner_user_id = auth.uid())
        OR EXISTS (SELECT 1 FROM business_users bu
                   WHERE bu.business_id = cpa_transactions.org_id
                     AND bu.user_id = auth.uid() AND bu.is_active)
    );
CREATE POLICY "cpa_txn_member_update" ON cpa_transactions
    FOR UPDATE USING (
        EXISTS (SELECT 1 FROM businesses b
                WHERE b.id = cpa_transactions.org_id AND b.owner_user_id = auth.uid())
        OR EXISTS (SELECT 1 FROM business_users bu
                   WHERE bu.business_id = cpa_transactions.org_id
                     AND bu.user_id = auth.uid() AND bu.is_active)
    );
CREATE POLICY "cpa_txn_service_all" ON cpa_transactions
    FOR ALL USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

GRANT SELECT, UPDATE ON cpa_transactions TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON cpa_transactions TO service_role;

DROP TRIGGER IF EXISTS trg_cpa_txn_updated_at ON cpa_transactions;
CREATE TRIGGER trg_cpa_txn_updated_at
    BEFORE UPDATE ON cpa_transactions
    FOR EACH ROW EXECUTE FUNCTION set_cpa_updated_at();
