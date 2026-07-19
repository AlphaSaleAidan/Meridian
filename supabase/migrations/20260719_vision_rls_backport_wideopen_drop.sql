-- ============================================================================
-- CC6.1-RLS R1 — drop residual wide-open vision_* policies + codify live org-scoping
-- ----------------------------------------------------------------------------
-- FINDING (config drift on origin/main @ 159b3423, found by static migration audit
--   2026-07-19; corroborated by the live pg_policies snapshot in
--   compliance/evidence/CC6.1-RLS/pg_policies_live_20260628.md):
--
--   The migration history builds vision_* RLS in a way that a FRESH `supabase db push`
--   from main leaves the tables cross-tenant readable for any authenticated user:
--     1. 20260501_004_vision_intelligence.sql
--          CREATE POLICY vision_<t>_org_isolation ... USING (org_id = auth.uid())
--          (permissive, no TO clause -> roles {public})
--     2. 20260516_vision_cameras.sql   (LATER)
--          CREATE POLICY "Service role full access on vision_<t>" FOR ALL USING (true)
--          (permissive, no TO clause -> roles {public}) -- RE-OPENS the tables
--     3. 20260628_vision_tables_rls.sql (LATER)
--          only REVOKE SELECT ... FROM anon -- drops NOTHING; the wide-open policy
--          from step 2 survives.
--
--   Postgres RLS policies are PERMISSIVE (OR-combined). With both an org-scoped
--   policy AND a `USING(true)` policy present, `USING(true)` wins: any role holding a
--   SELECT grant reads every tenant's rows. anon was revoked in step 3, but
--   `authenticated` retains its default SELECT grant -> ANY logged-in user can read
--   ALL tenants' camera/traffic/visitor data on a main-built database.
--
--   NOTE ON PROD vs MAIN: the live prod DB was hand-corrected on 2026-06-28 to the
--   `vision_<t>_member_isolation` policy (per pg_policies_live_20260628.md), so prod is
--   NOT currently exposed. This migration codifies that live-correct state into main so
--   a rebuild / db push can no longer regress it (the assertion at the end fails CI/apply
--   if any wide-open vision policy is ever reintroduced). Against prod this is an
--   effective no-op (drop the absent wide-open policy; recreate the identical
--   member_isolation policy inside a transaction).
--
-- SAFE BECAUSE (verified):
--   * Backend edge writes/reads vision_* via SUPABASE_SERVICE_ROLE_KEY, which bypasses
--     RLS entirely — service_role behavior is unchanged.
--   * No frontend Supabase-client code reads vision_* (the camera dashboard fetches
--     through the backend API). So there is NO live authenticated user-JWT read path
--     that the tightened policy could break — this cannot reproduce the 42501 grant/RLS
--     regression.
--   * We DO NOT touch grants here (anon SELECT was already revoked in 20260628; the
--     authenticated SELECT grant is left intact so this is purely a policy tightening —
--     no grant a live path needs is stripped).
--   * The member_isolation policy mirrors the live definition byte-for-byte:
--       FOR SELECT TO authenticated
--       USING (org_id IN (SELECT business_id FROM business_users
--                         WHERE user_id = auth.uid() AND is_active IS TRUE))
--
-- Written as explicit per-table statements (not a DO/format loop) so the policy shape
-- is directly auditable by humans and by the static CC6.1 migration test.
-- REVERSIBLE: rollback block at the bottom.
-- ============================================================================

BEGIN;

ALTER TABLE public.vision_cameras  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.vision_traffic  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.vision_visitors ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.vision_visits   ENABLE ROW LEVEL SECURITY;

-- Drop the residual wide-open policies from 20260516 (the actual exposure vector) ----
DROP POLICY IF EXISTS "Service role full access on vision_cameras"  ON public.vision_cameras;
DROP POLICY IF EXISTS "Service role full access on vision_traffic"  ON public.vision_traffic;
DROP POLICY IF EXISTS "Service role full access on vision_visitors" ON public.vision_visitors;
DROP POLICY IF EXISTS "Service role full access on vision_visits"   ON public.vision_visits;

-- Drop the early auth.uid()-based org policy from 20260501_004. org_id is
-- businesses.id (TEXT), never equal to the caller's auth.uid() (a uuid), so that
-- policy never matched and provided no real isolation. Replaced by member_isolation. --
DROP POLICY IF EXISTS vision_cameras_org_isolation  ON public.vision_cameras;
DROP POLICY IF EXISTS vision_traffic_org_isolation  ON public.vision_traffic;
DROP POLICY IF EXISTS vision_visitors_org_isolation ON public.vision_visitors;
DROP POLICY IF EXISTS vision_visits_org_isolation   ON public.vision_visits;

-- Codify the live-correct, membership-scoped read policy (idempotent replace) --------
DROP POLICY IF EXISTS vision_cameras_member_isolation  ON public.vision_cameras;
DROP POLICY IF EXISTS vision_traffic_member_isolation  ON public.vision_traffic;
DROP POLICY IF EXISTS vision_visitors_member_isolation ON public.vision_visitors;
DROP POLICY IF EXISTS vision_visits_member_isolation   ON public.vision_visits;

CREATE POLICY vision_cameras_member_isolation ON public.vision_cameras
    FOR SELECT TO authenticated
    USING (org_id IN (SELECT business_id FROM public.business_users
                      WHERE user_id = auth.uid() AND is_active IS TRUE));
CREATE POLICY vision_traffic_member_isolation ON public.vision_traffic
    FOR SELECT TO authenticated
    USING (org_id IN (SELECT business_id FROM public.business_users
                      WHERE user_id = auth.uid() AND is_active IS TRUE));
CREATE POLICY vision_visitors_member_isolation ON public.vision_visitors
    FOR SELECT TO authenticated
    USING (org_id IN (SELECT business_id FROM public.business_users
                      WHERE user_id = auth.uid() AND is_active IS TRUE));
CREATE POLICY vision_visits_member_isolation ON public.vision_visits
    FOR SELECT TO authenticated
    USING (org_id IN (SELECT business_id FROM public.business_users
                      WHERE user_id = auth.uid() AND is_active IS TRUE));

-- Explicit service_role full-access policy (service_role bypasses RLS anyway, but keep
-- an explicit named policy so intent is legible and drift-checkable) -----------------
DROP POLICY IF EXISTS vision_cameras_service  ON public.vision_cameras;
DROP POLICY IF EXISTS vision_traffic_service  ON public.vision_traffic;
DROP POLICY IF EXISTS vision_visitors_service ON public.vision_visitors;
DROP POLICY IF EXISTS vision_visits_service   ON public.vision_visits;

CREATE POLICY vision_cameras_service  ON public.vision_cameras  FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY vision_traffic_service  ON public.vision_traffic  FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY vision_visitors_service ON public.vision_visitors FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY vision_visits_service   ON public.vision_visits   FOR ALL TO service_role USING (true) WITH CHECK (true);

-- Assert: no wide-open public/anon/authenticated USING(true) policy remains on vision_*
DO $$
DECLARE bad int;
BEGIN
  SELECT count(*) INTO bad FROM pg_policies
  WHERE schemaname='public'
    AND tablename IN ('vision_cameras','vision_traffic','vision_visitors','vision_visits')
    AND qual='true'
    AND roles && ARRAY['public','authenticated','anon']::name[];
  IF bad > 0 THEN
    RAISE EXCEPTION 'vision RLS backport: % wide-open public/authenticated USING(true) policies still present', bad;
  END IF;
END $$;

COMMIT;

-- ============================================================================
-- ROLLBACK (restores the prior — exposed — state; do NOT use except to revert):
--   BEGIN;
--   DROP POLICY IF EXISTS vision_cameras_member_isolation  ON public.vision_cameras;
--   DROP POLICY IF EXISTS vision_traffic_member_isolation  ON public.vision_traffic;
--   DROP POLICY IF EXISTS vision_visitors_member_isolation ON public.vision_visitors;
--   DROP POLICY IF EXISTS vision_visits_member_isolation   ON public.vision_visits;
--   DROP POLICY IF EXISTS vision_cameras_service  ON public.vision_cameras;
--   DROP POLICY IF EXISTS vision_traffic_service  ON public.vision_traffic;
--   DROP POLICY IF EXISTS vision_visitors_service ON public.vision_visitors;
--   DROP POLICY IF EXISTS vision_visits_service   ON public.vision_visits;
--   CREATE POLICY "Service role full access on vision_cameras"  ON public.vision_cameras  FOR ALL USING (true) WITH CHECK (true);
--   CREATE POLICY "Service role full access on vision_traffic"  ON public.vision_traffic  FOR ALL USING (true) WITH CHECK (true);
--   CREATE POLICY "Service role full access on vision_visitors" ON public.vision_visitors FOR ALL USING (true) WITH CHECK (true);
--   CREATE POLICY "Service role full access on vision_visits"   ON public.vision_visits   FOR ALL USING (true) WITH CHECK (true);
--   COMMIT;
-- ============================================================================
