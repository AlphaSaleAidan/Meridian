-- ============================================================================
-- PROPOSED MIGRATION — CC6.1-RLS R1 — backport LIVE vision_* RLS into main
-- ----------------------------------------------------------------------------
-- STATUS: AUTHORED, **NOT APPLIED**. To be PROMOTED into supabase/migrations/
-- (e.g. 20260628_camera_rls_backport.sql) via a focused PR Aidan merges.
--
-- WHY: R0 (pg_policies_live_20260628.md) showed vision_* are correctly org-scoped
-- in PROD, but the policy + the camera P0 fix are ABSENT from origin/main. A fresh
-- rebuild / `supabase db push` from main would therefore NOT recreate them — config
-- drift that could silently regress camera isolation. This migration codifies the
-- exact LIVE policy so main matches prod. Applying it to prod is an effective no-op
-- (drop+recreate identical policy inside a transaction).
--
-- Faithful to the live definition captured 2026-06-28:
--   policy <t>_member_isolation  SELECT  TO authenticated
--   USING (org_id IN (SELECT business_id FROM business_users
--                     WHERE user_id = auth.uid() AND is_active IS TRUE))
--   writes: none for authenticated (edge writes via service_role, which bypasses RLS)
-- ============================================================================

BEGIN;

DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['vision_cameras','vision_traffic','vision_visitors','vision_visits']
  LOOP
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', t||'_member_isolation', t);
    EXECUTE format($f$
      CREATE POLICY %I ON public.%I
        FOR SELECT TO authenticated
        USING (org_id IN (SELECT business_id FROM public.business_users
                          WHERE user_id = auth.uid() AND is_active IS TRUE))
    $f$, t||'_member_isolation', t);
    -- Drop any legacy wide-open policy if a rebuild reintroduced it:
    EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', 'Service role full access on '||t, t);
    -- Defense-in-depth: anon never needs to read camera data. anon already cannot
    -- read (no anon policy), so this REVOKE is functionally a no-op but removes the
    -- fragile grant. Remove this line if a backport must be a pure mirror.
    EXECUTE format('REVOKE SELECT ON public.%I FROM anon', t);
  END LOOP;
END $$;

-- Assert no wide-open public/authenticated USING(true) policy exists on vision_*:
DO $$
DECLARE bad int;
BEGIN
  SELECT count(*) INTO bad FROM pg_policies
  WHERE schemaname='public'
    AND tablename IN ('vision_cameras','vision_traffic','vision_visitors','vision_visits')
    AND qual='true' AND roles && ARRAY['public','authenticated','anon'];
  IF bad > 0 THEN RAISE EXCEPTION 'camera RLS backport: % wide-open policies present', bad; END IF;
END $$;

COMMIT;

-- COMPANION: restore the deleted Postgres-level denial test to CI so this cannot
-- regress again — see compliance/evidence/CC6.1-RLS/test_rls_cross_tenant.py (the
-- self-contained replica already proves leak->fix->deny for the vision_cameras shape).
-- Wire it into .github/workflows/syntax-check.yml as the old
-- tests/e2e/test_camera_tenancy_rls.py was.
