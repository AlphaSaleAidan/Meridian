-- ============================================================================
-- us_leads: ADDITIVE "Managers can read downline leads" policy — the mirror of
-- the canada_leads policy from 20260716_sales_hierarchy.sql.
--
-- Why: 20260716 skipped us_leads on the assumption that the backend plane
-- (src/api/hierarchy.py) covers the US portal. That is true for /api/us/leads,
-- but the US portal ALSO reads us_leads DIRECTLY from Supabase in the browser
-- (frontend/src/lib/us-leads-service.ts) under the 20260628 own-leads-only
-- policy — so a US manager cannot see downline leads at all through the
-- portal's primary read path. This restores the canada/us symmetry: managers
-- (any role above sales_rep) read leads owned by reps strictly inside their
-- subtree; admins read all. Writes stay owner-only (unchanged from 20260628).
--
-- Depends on 20260716_sales_hierarchy.sql (current_rep_role / current_rep_path
-- / rep_path_for helpers + sales_reps.path). Apply 20260716 FIRST.
--
-- Idempotent. NOT applied automatically — apply with a Supabase snapshot in
-- place, coordinated with the main session. Tested by
-- tests/rls/hierarchy_policies.test.sql (us_leads persona cases; runs against
-- a scratch postgres — see that file's header for the exact run order).
--
-- ROLLBACK:
--   DROP POLICY IF EXISTS "Managers can read downline leads" ON public.us_leads;
-- (The 20260628 own-leads policies are untouched; permissive policies OR
-- together, so dropping this one simply returns us_leads to own-leads-only.)
-- ============================================================================

-- Copy of the canada_leads pattern, verbatim except for the table name.
DROP POLICY IF EXISTS "Managers can read downline leads" ON public.us_leads;
CREATE POLICY "Managers can read downline leads" ON public.us_leads FOR SELECT TO authenticated
  USING (
    current_rep_role() = 'admin'
    OR (
      current_rep_role() IS NOT NULL
      AND current_rep_role() <> 'sales_rep'
      AND rep_id IS NOT NULL
      AND rep_path_for(rep_id) LIKE current_rep_path() || '.%'
    )
  );
