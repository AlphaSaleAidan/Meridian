-- ============================================================================
-- 071 — Repoint commission ledger to the LIVE Canada account entity (businesses)
-- ============================================================================
--
-- DECISION (Option B): the commission ledger must key accounts to the SAME
-- entity the live Canada portal uses. Migration 046 FK'd
-- commission_milestones.account_id -> organizations(id) [uuid], but a live
-- Canada deal (canada.create_customer) provisions a businesses(id) [text] row
-- and never touches organizations / rep_client_assignments (0 rows). Auto-
-- accruing against organizations would silently FK-fail on every close.
--
-- This migration realigns account_id to businesses(id):
--   * drops whatever FK currently guards account_id (organizations),
--   * changes account_id uuid -> text (commission_milestones is EMPTY, so this
--     is a no-data type change),
--   * adds a FK to businesses(id) ON DELETE CASCADE.
-- assignment_id (nullable, -> rep_client_assignments) is LEFT as-is; the
-- Canada close path simply leaves it NULL. Rep identity is resolved from the
-- closing rep's JWT email -> sales_reps (same join the read API already uses).
--
-- Idempotent + reversible. Additive elsewhere.
-- ============================================================================

BEGIN;

-- 1) Drop the existing FK on account_id (name defaults to
--    commission_milestones_account_id_fkey, but discover it to be safe).
DO $$
DECLARE fk text;
BEGIN
  SELECT tc.constraint_name INTO fk
  FROM information_schema.table_constraints tc
  JOIN information_schema.key_column_usage kcu
    ON tc.constraint_name = kcu.constraint_name
   AND tc.table_schema = kcu.table_schema
  WHERE tc.table_schema = 'public'
    AND tc.table_name = 'commission_milestones'
    AND tc.constraint_type = 'FOREIGN KEY'
    AND kcu.column_name = 'account_id'
  LIMIT 1;
  IF fk IS NOT NULL THEN
    EXECUTE format('ALTER TABLE public.commission_milestones DROP CONSTRAINT %I', fk);
  END IF;
END $$;

-- 2) uuid -> text (empty table; cast is trivial).
ALTER TABLE public.commission_milestones
  ALTER COLUMN account_id TYPE text USING account_id::text;

-- 3) Re-point the FK at the live account entity.
ALTER TABLE public.commission_milestones
  ADD CONSTRAINT commission_milestones_account_id_businesses_fkey
  FOREIGN KEY (account_id) REFERENCES public.businesses(id) ON DELETE CASCADE;

-- 4) Verify the realignment stuck.
DO $$
DECLARE refs text;
BEGIN
  SELECT ccu.table_name INTO refs
  FROM information_schema.table_constraints tc
  JOIN information_schema.constraint_column_usage ccu
    ON tc.constraint_name = ccu.constraint_name
  JOIN information_schema.key_column_usage kcu
    ON tc.constraint_name = kcu.constraint_name
  WHERE tc.table_schema = 'public'
    AND tc.table_name = 'commission_milestones'
    AND tc.constraint_type = 'FOREIGN KEY'
    AND kcu.column_name = 'account_id'
  LIMIT 1;
  IF refs IS DISTINCT FROM 'businesses' THEN
    RAISE EXCEPTION '071 verify failed: account_id FK references % (expected businesses)', refs;
  END IF;
  RAISE NOTICE '071 commission account_id -> businesses(id) verified OK';
END $$;

COMMIT;
