-- canada_leads per-rep row-level isolation
--
-- Context: 20260511_fix_canada_leads_rls.sql widened SELECT/UPDATE/DELETE to
-- "any authenticated user" after the original policies (20260507_canada_leads.sql)
-- failed because auth.uid() (auth.users UUID) != canada_leads.rep_id
-- (sales_reps UUID — these are created independently via the backend, not via
-- Supabase auth signup).
--
-- The correct join key is email: auth.email() links the current Supabase session
-- to the sales_reps row, which in turn links to canada_leads.rep_id.
--
-- This migration scopes SELECT / UPDATE / DELETE to the owning rep and tightens
-- INSERT to prevent a rep from creating leads owned by a different rep.
-- Unassigned leads (rep_id IS NULL) remain readable by all authenticated reps.
--
-- ROLLBACK: re-apply 20260511_fix_canada_leads_rls.sql to restore the wide-open
-- "any authenticated user" policies. No data is deleted by this migration.
--
-- NOTE: Apply with a Supabase snapshot in place (the main session manages that).
-- DO NOT apply directly to prod without coordination.

-- ── Pre-drop any stale policy names that may exist from earlier migrations ───
-- (Idempotent: safe to run even if these names don't exist yet.)
DROP POLICY IF EXISTS "canada_leads_read"   ON canada_leads;
DROP POLICY IF EXISTS "canada_leads_write"  ON canada_leads;
DROP POLICY IF EXISTS "canada_leads_insert" ON canada_leads;

-- ── SELECT ────────────────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "Authenticated users can read all leads" ON canada_leads;
CREATE POLICY "Reps can read own leads"
  ON canada_leads FOR SELECT
  USING (
    -- Unassigned leads (rep_id IS NULL) are visible to any authenticated rep
    -- so newly created leads appear before assignment.
    rep_id IS NULL
    OR rep_id IN (
      SELECT id FROM sales_reps WHERE email = auth.email()
    )
  );

-- ── UPDATE ────────────────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "Authenticated users can update leads" ON canada_leads;
CREATE POLICY "Reps can update own leads"
  ON canada_leads FOR UPDATE
  USING (
    rep_id IN (
      SELECT id FROM sales_reps WHERE email = auth.email()
    )
  )
  WITH CHECK (
    -- Prevent reassigning a lead away to a different rep via an UPDATE.
    rep_id IN (
      SELECT id FROM sales_reps WHERE email = auth.email()
    )
  );

-- ── DELETE ────────────────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "Authenticated users can delete leads" ON canada_leads;
CREATE POLICY "Reps can delete own leads"
  ON canada_leads FOR DELETE
  USING (
    rep_id IN (
      SELECT id FROM sales_reps WHERE email = auth.email()
    )
  );

-- ── INSERT ────────────────────────────────────────────────────────────────────
-- The original 20260507 policy was WITH CHECK (true); tighten to prevent a
-- rep from inserting a lead with someone else's rep_id.
DROP POLICY IF EXISTS "Sales reps can insert leads" ON canada_leads;
CREATE POLICY "Reps can insert own leads"
  ON canada_leads FOR INSERT
  WITH CHECK (
    -- Allow unassigned inserts (rep_id IS NULL) — used by the backend
    -- service role (which bypasses RLS anyway) and by admin flows.
    rep_id IS NULL
    OR rep_id IN (
      SELECT id FROM sales_reps WHERE email = auth.email()
    )
  );
