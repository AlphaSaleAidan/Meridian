-- ============================================================
-- Migration: POS beta-operational wiring (additive)
-- Date:      2026-06-03
-- Branch:    pos-beta-wiring
-- Status:    NOT APPLIED — gated by Aidan's explicit approval
-- ============================================================
--
-- Purpose
-- -------
-- The audit (docs/pos_ingestion_audit.md) found the production
-- transactions table has no customer_id column. The POS normalizer
-- (src/services/pos_connectors/normalizer.py) happily fills
-- customer_id from upstream Square/Toast/Clover orders, but it is
-- dropped at the db.batch_upsert("transactions", ...) boundary —
-- the upstream cause of Phase 1's churn-eval infeasibility finding.
-- Currency is also unmodelled, putting the CAD beta at risk of
-- silent CAD/USD mixing once a Canadian merchant connects.
-- pos_connections has no rep-attribution column, blocking concierge
-- commission attribution.
--
-- This migration adds three columns to transactions and one column
-- to pos_connections. Every change is additive and nullable. No
-- existing column is dropped, renamed, or retyped. No data is
-- mutated. All ALTERs use IF NOT EXISTS so the migration is
-- idempotent.
--
-- Rollback
-- --------
-- A rollback block is provided at the end of the file. To roll back,
-- run the statements between `-- ROLLBACK START` and `-- ROLLBACK END`.
-- Rollback is also additive-only (no data loss beyond the new
-- columns themselves, which are by definition new at apply time).
--
-- Application-layer wiring (separate commit, not in this SQL)
-- -----------------------------------------------------------
-- 1. The Square/Toast/Clover/generic sync engines + normalizer will
--    be updated to include the new fields in their batch_upsert
--    payloads so identity+currency actually persist.
-- 2. The POS connect routes will write `connected_by_rep_id` from
--    the authenticated rep's session on every credential/OAuth path.
-- 3. Application default for currency = 'USD' only where the source
--    POS does not surface a currency field; CAD merchants get 'CAD'
--    explicitly from the Square location's currency field on ingest.
-- ============================================================


-- ─── transactions: customer identity ──────────────────────────
-- customer_id is whatever the source POS gives us
--   (Square: orders.customer_id; Clover: orders.customer.id;
--    Toast: orders.customer.guid; generic: normalizer.customer_id).
-- customer_email is what we get from Square Customers API +
--   equivalent endpoints. Nullable because not every POS carries it
--   (Toast does; Square gives it on a separate fetch).
ALTER TABLE transactions
    ADD COLUMN IF NOT EXISTS customer_id TEXT,
    ADD COLUMN IF NOT EXISTS customer_email TEXT;


-- ─── transactions: currency (ISO 4217) ────────────────────────
-- CHAR(3) for ISO 4217 codes (USD, CAD, EUR, ...). Column default
-- intentionally NULL — the application layer is responsible for
-- setting it from each POS location's currency field on ingest.
-- A literal NULL here makes "currency unknown" a first-class state
-- so we can backfill explicitly and audit it later.
ALTER TABLE transactions
    ADD COLUMN IF NOT EXISTS currency CHAR(3);


-- ─── transactions: customer_id lookup index ───────────────────
-- Churn queries scan by customer_id within a time window. Partial
-- WHERE customer_id IS NOT NULL keeps the index tiny until
-- backfilled connectors start populating it.
CREATE INDEX IF NOT EXISTS idx_transactions_customer_id
    ON transactions (customer_id, transaction_at DESC)
    WHERE customer_id IS NOT NULL;


-- ─── pos_connections: rep attribution ─────────────────────────
-- connected_by_rep_id captures the concierge rep who onboarded the
-- merchant. ON DELETE SET NULL so deleting a rep does NOT
-- cascade-delete the merchant's POS connection — connections
-- outlive any single rep's tenure.
ALTER TABLE pos_connections
    ADD COLUMN IF NOT EXISTS connected_by_rep_id UUID;

-- FK in a guarded block — Postgres does not have
-- "ADD CONSTRAINT IF NOT EXISTS" so we catch the duplicate exception.
DO $$
BEGIN
    ALTER TABLE pos_connections
        ADD CONSTRAINT pos_connections_connected_by_rep_id_fkey
        FOREIGN KEY (connected_by_rep_id)
        REFERENCES sales_reps(id)
        ON DELETE SET NULL
        DEFERRABLE INITIALLY DEFERRED;
EXCEPTION WHEN duplicate_object THEN
    NULL;
END
$$;


-- ─── pos_connections: rep lookup index ────────────────────────
-- For "show all merchants this rep connected" dashboard queries.
CREATE INDEX IF NOT EXISTS idx_pos_connections_connected_by_rep
    ON pos_connections (connected_by_rep_id)
    WHERE connected_by_rep_id IS NOT NULL;


-- ─── Comments (self-documenting schema) ───────────────────────
COMMENT ON COLUMN transactions.customer_id IS
    'Customer identifier from the source POS (Square: orders.customer_id, '
    'Clover: orders.customer.id, Toast: orders.customer.guid). '
    'Nullable. Populated by the canonical normalizer on ingest.';
COMMENT ON COLUMN transactions.customer_email IS
    'Customer email when surfaced by the source POS. Nullable.';
COMMENT ON COLUMN transactions.currency IS
    'ISO 4217 currency code for the transaction. Populated by the '
    'connector from the POS location''s currency field on ingest. '
    'NULL means currency unknown — treat as data quality issue, not USD.';
COMMENT ON COLUMN pos_connections.connected_by_rep_id IS
    'Concierge rep who onboarded this connection. ON DELETE SET NULL '
    'so rep churn does not cascade-delete merchant connections.';


-- ============================================================
-- ROLLBACK START — run these statements to undo this migration.
-- They are commented out so a normal apply does NOT undo itself.
-- ============================================================
--
-- ALTER TABLE pos_connections
--     DROP CONSTRAINT IF EXISTS pos_connections_connected_by_rep_id_fkey;
-- DROP INDEX IF EXISTS idx_pos_connections_connected_by_rep;
-- ALTER TABLE pos_connections
--     DROP COLUMN IF EXISTS connected_by_rep_id;
--
-- DROP INDEX IF EXISTS idx_transactions_customer_id;
-- ALTER TABLE transactions
--     DROP COLUMN IF EXISTS currency,
--     DROP COLUMN IF EXISTS customer_email,
--     DROP COLUMN IF EXISTS customer_id;
--
-- ============================================================
-- ROLLBACK END
-- ============================================================
