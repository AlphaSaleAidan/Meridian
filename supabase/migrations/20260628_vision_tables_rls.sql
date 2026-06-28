-- Vision tables RLS hardening
--
-- Context: 20260516_vision_cameras.sql created four tables (vision_cameras,
-- vision_traffic, vision_visitors, vision_visits) with wide-open FOR ALL
-- USING(true) WITH CHECK(true) policies that have no TO clause — meaning
-- they apply to PUBLIC (anon + authenticated). Combined with any SELECT
-- GRANT to anon or authenticated, every row is readable unauthenticated.
--
-- This mirrors the finding in 20260628_fix_phone_schedule_rls_anon_exposure.sql
-- for phone_* and schedule_* tables.
--
-- Fix:
--   - Drop the four wide-open policies.
--   - Recreate scoped TO service_role (backend reads/writes via service_role key
--     which bypasses RLS — no backend behaviour changes).
--   - REVOKE SELECT from anon and authenticated (defense-in-depth; RLS would
--     deny anyway once the public policy is gone, but removing the grant closes
--     the vector at the privilege layer too).
--
-- Safe because (verify before applying):
--   - No frontend code reads vision tables via the Supabase anon client.
--   - Only the backend vision intelligence service writes to these tables using
--     the service_role key, which bypasses RLS.
--
-- ROLLBACK: see comment block at the bottom of this file.
-- DO NOT apply without a Supabase snapshot in place.
-- ============================================================================

BEGIN;

-- Drop the wide-open public policies ----------------------------------------
DROP POLICY IF EXISTS "Service role full access on vision_cameras"   ON public.vision_cameras;
DROP POLICY IF EXISTS "Service role full access on vision_traffic"   ON public.vision_traffic;
DROP POLICY IF EXISTS "Service role full access on vision_visitors"  ON public.vision_visitors;
DROP POLICY IF EXISTS "Service role full access on vision_visits"    ON public.vision_visits;

-- Recreate scoped TO service_role --------------------------------------------
CREATE POLICY vision_cameras_service
  ON public.vision_cameras FOR ALL TO service_role
  USING (true) WITH CHECK (true);

CREATE POLICY vision_traffic_service
  ON public.vision_traffic FOR ALL TO service_role
  USING (true) WITH CHECK (true);

CREATE POLICY vision_visitors_service
  ON public.vision_visitors FOR ALL TO service_role
  USING (true) WITH CHECK (true);

CREATE POLICY vision_visits_service
  ON public.vision_visits FOR ALL TO service_role
  USING (true) WITH CHECK (true);

-- Revoke public read grant (closes the anonymous read vector) ----------------
REVOKE SELECT ON public.vision_cameras  FROM anon, authenticated;
REVOKE SELECT ON public.vision_traffic  FROM anon, authenticated;
REVOKE SELECT ON public.vision_visitors FROM anon, authenticated;
REVOKE SELECT ON public.vision_visits   FROM anon, authenticated;

-- Assert no wide-open public/authenticated policy survives -------------------
DO $$
DECLARE bad int;
BEGIN
  SELECT count(*) INTO bad FROM pg_policies
  WHERE schemaname = 'public'
    AND tablename IN ('vision_cameras', 'vision_traffic', 'vision_visitors', 'vision_visits')
    AND qual = 'true'
    AND roles && ARRAY['public', 'authenticated', 'anon']::name[];
  IF bad > 0 THEN
    RAISE EXCEPTION 'CC6.1-RLS: % wide-open public/authenticated USING(true) policies still present on vision tables', bad;
  END IF;
END $$;

COMMIT;

-- ============================================================================
-- ROLLBACK (if needed): for each table, DROP the *_service policy,
-- re-CREATE the original FOR ALL USING(true) WITH CHECK(true) policy
-- (no TO clause), and GRANT SELECT to anon, authenticated.
--
-- BEGIN;
-- DROP POLICY IF EXISTS vision_cameras_service   ON public.vision_cameras;
-- DROP POLICY IF EXISTS vision_traffic_service   ON public.vision_traffic;
-- DROP POLICY IF EXISTS vision_visitors_service  ON public.vision_visitors;
-- DROP POLICY IF EXISTS vision_visits_service    ON public.vision_visits;
-- CREATE POLICY "Service role full access on vision_cameras"  ON public.vision_cameras  FOR ALL USING (true) WITH CHECK (true);
-- CREATE POLICY "Service role full access on vision_traffic"  ON public.vision_traffic  FOR ALL USING (true) WITH CHECK (true);
-- CREATE POLICY "Service role full access on vision_visitors" ON public.vision_visitors FOR ALL USING (true) WITH CHECK (true);
-- CREATE POLICY "Service role full access on vision_visits"   ON public.vision_visits   FOR ALL USING (true) WITH CHECK (true);
-- GRANT SELECT ON public.vision_cameras  TO anon, authenticated;
-- GRANT SELECT ON public.vision_traffic  TO anon, authenticated;
-- GRANT SELECT ON public.vision_visitors TO anon, authenticated;
-- GRANT SELECT ON public.vision_visits   TO anon, authenticated;
-- COMMIT;
-- ============================================================================
