-- us_leads per-rep row-level isolation
--
-- Context: 20260522_us_leads_rls.sql created wide-open policies
-- (USING(true)) for all authenticated users, and 20260603_fix_us_leads_grants.sql
-- additionally granted SELECT to the anon role. Together these expose every
-- US lead to any logged-in user and to unauthenticated reads via the public
-- Supabase anon key.
--
-- ASSUMPTION: us_leads.rep_id is the owner column, typed UUID, referencing
-- sales_reps(id). This mirrors the canada_leads schema. If the column name
-- differs (e.g. assigned_rep_id or owner_id), update the USING clauses below.
-- Verify with: SELECT column_name FROM information_schema.columns
--              WHERE table_name = 'us_leads';
--
-- Fix:
--   - Scope SELECT/UPDATE/DELETE to the owning rep via the same email-join
--     pattern proven on canada_leads (auth.uid() != sales_reps.id, but
--     auth.email() = sales_reps.email is the correct join key).
--   - Unassigned leads (rep_id IS NULL) remain readable by all authenticated
--     reps so newly created leads appear before assignment.
--   - REVOKE SELECT from anon (closes the public-key read vector).
--   - INSERT is tightened so a rep cannot create leads owned by another rep.
--
-- ROLLBACK: see comment block at the bottom of this file.
-- DO NOT apply without a Supabase snapshot in place.
-- ============================================================================

BEGIN;

-- Remove the existing wide-open policies. Prod carried TWO overlapping sets
-- (Postgres OR's permissive policies, so BOTH must go or the table stays open):
--   (a) the named "Authenticated users can ..." set, and
--   (b) the "us_leads_*_authenticated" set (role public, USING auth.uid() IS NOT NULL).
DROP POLICY IF EXISTS "Authenticated users can read US leads"   ON public.us_leads;
DROP POLICY IF EXISTS "Authenticated users can insert US leads" ON public.us_leads;
DROP POLICY IF EXISTS "Authenticated users can update US leads" ON public.us_leads;
DROP POLICY IF EXISTS "Authenticated users can delete US leads" ON public.us_leads;
DROP POLICY IF EXISTS us_leads_select_authenticated ON public.us_leads;
DROP POLICY IF EXISTS us_leads_insert_authenticated ON public.us_leads;
DROP POLICY IF EXISTS us_leads_update_authenticated ON public.us_leads;
DROP POLICY IF EXISTS us_leads_delete_authenticated ON public.us_leads;

-- Ensure RLS is still enabled (idempotent) ------------------------------------
ALTER TABLE public.us_leads ENABLE ROW LEVEL SECURITY;

-- ── SELECT ────────────────────────────────────────────────────────────────────
CREATE POLICY "US reps can read own leads"
  ON public.us_leads FOR SELECT
  TO authenticated
  USING (
    rep_id IS NULL
    OR rep_id IN (
      SELECT id FROM public.sales_reps WHERE email = auth.email()
    )
  );

-- ── INSERT ────────────────────────────────────────────────────────────────────
CREATE POLICY "US reps can insert own leads"
  ON public.us_leads FOR INSERT
  TO authenticated
  WITH CHECK (
    rep_id IS NULL
    OR rep_id IN (
      SELECT id FROM public.sales_reps WHERE email = auth.email()
    )
  );

-- ── UPDATE ────────────────────────────────────────────────────────────────────
CREATE POLICY "US reps can update own leads"
  ON public.us_leads FOR UPDATE
  TO authenticated
  USING (
    rep_id IN (
      SELECT id FROM public.sales_reps WHERE email = auth.email()
    )
  )
  WITH CHECK (
    rep_id IN (
      SELECT id FROM public.sales_reps WHERE email = auth.email()
    )
  );

-- ── DELETE ────────────────────────────────────────────────────────────────────
CREATE POLICY "US reps can delete own leads"
  ON public.us_leads FOR DELETE
  TO authenticated
  USING (
    rep_id IN (
      SELECT id FROM public.sales_reps WHERE email = auth.email()
    )
  );

-- ── Revoke anon read (closed the open anonymous read vector) ─────────────────
REVOKE SELECT ON public.us_leads FROM anon;

COMMIT;

-- ============================================================================
-- ROLLBACK (if needed):
-- BEGIN;
-- DROP POLICY IF EXISTS "US reps can read own leads"   ON public.us_leads;
-- DROP POLICY IF EXISTS "US reps can insert own leads" ON public.us_leads;
-- DROP POLICY IF EXISTS "US reps can update own leads" ON public.us_leads;
-- DROP POLICY IF EXISTS "US reps can delete own leads" ON public.us_leads;
-- GRANT SELECT ON public.us_leads TO anon;
-- CREATE POLICY "Authenticated users can read US leads"
--   ON public.us_leads FOR SELECT TO authenticated USING (true);
-- CREATE POLICY "Authenticated users can insert US leads"
--   ON public.us_leads FOR INSERT TO authenticated WITH CHECK (true);
-- CREATE POLICY "Authenticated users can update US leads"
--   ON public.us_leads FOR UPDATE TO authenticated USING (true) WITH CHECK (true);
-- CREATE POLICY "Authenticated users can delete US leads"
--   ON public.us_leads FOR DELETE TO authenticated USING (true);
-- COMMIT;
-- ============================================================================
