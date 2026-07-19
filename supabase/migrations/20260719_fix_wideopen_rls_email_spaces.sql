-- ============================================================================
-- Fix wide-open RLS on email_send_log, space_processing_jobs, spaces, space_zones
-- ----------------------------------------------------------------------------
-- FINDING (verified live via read-only pg_policies + role_table_grants, 2026-07-06;
--   re-confirmed still-present on origin/main @ 159b3423 by static migration audit,
--   2026-07-19):
--   Each table has RLS enabled with a single permissive policy named
--   "Service role full access on <t>" written `FOR ALL USING(true) WITH CHECK(true)`
--   but WITHOUT a `TO service_role` clause — so its role is {public} (anon +
--   authenticated), AND each table carries the Supabase-default `SELECT` GRANT to
--   both `anon` and `authenticated`. Together these make every row readable with the
--   PUBLIC anon key embedded in the frontend bundle.
--     * email_send_log  -> customer email addresses, subjects, open/click timestamps (PII)
--     * spaces / space_zones / space_processing_jobs -> 3D-scan metadata + asset URLs
--   Same boilerplate omission already fixed for phone_*/schedule_* in
--   20260628_fix_phone_schedule_rls_anon_exposure.sql; these 4 are the residual tables.
--   (This is the SOC 2 REMEDIATION-MAP items DB-2 and DB-3. The verified fix was
--   authored 2026-07-06 but never landed on main; this re-lands it unchanged in shape.)
--
-- SAFE BECAUSE (verified against origin/main):
--   * Backend reads/writes all four via get_db() = SUPABASE_SERVICE_ROLE_KEY, which
--     bypasses RLS — backend behavior is unchanged. The new `TO service_role` policy
--     preserves full DML for the backend; NO grant the backend path needs is stripped
--     (service_role is not affected by the anon/authenticated REVOKEs below).
--   * email_send_log: no frontend Supabase-client access; only /api/email/log & /stats
--     read it, both `Depends(require_admin)`. Full lockdown is safe.
--   * space_processing_jobs: no frontend Supabase-client access (jobs go through the
--     backend API / localStorage). Full lockdown is safe.
--   * spaces / space_zones: read by the LOGGED-IN Space tab via the Supabase client
--     (frontend/src/lib/spaces-service.ts: .from('spaces'|'space_zones').select). Those
--     reads run as the authenticated user's JWT. We therefore KEEP the authenticated
--     SELECT grant and add an explicit `FOR SELECT TO authenticated USING(true)` policy
--     to preserve exactly today's read behavior, while REVOKING only `anon` (the
--     public-key vector). Frontend writes (saveZone insert, delete) already fail today
--     — anon/authenticated hold no INSERT/DELETE grant — and go through the backend
--     API, so no write path changes.
--
-- GRANT-CONSISTENCY (the 42501 regression guard): the prior repo incident broke auth
-- by tightening RLS while stripping a grant a live user-JWT path relied on. Here the
-- ONLY authenticated read path is spaces/space_zones, and for those we ADD an explicit
-- authenticated SELECT policy AND keep the authenticated SELECT grant — so the
-- logged-in Space tab is unchanged. For email_send_log / space_processing_jobs no
-- authenticated path exists (backend-only, service_role), so revoking is safe.
--
-- REVERSIBLE: rollback block at the bottom restores the prior state exactly.
-- Apply deliberately (snapshot first). Additive/defensive; wrapped in a transaction
-- with a post-condition assertion.
-- ============================================================================

BEGIN;

-- 1. email_send_log — backend-only, customer PII -> service_role only ---------
DROP POLICY IF EXISTS "Service role full access on email_send_log" ON public.email_send_log;
CREATE POLICY email_send_log_service ON public.email_send_log
    FOR ALL TO service_role USING (true) WITH CHECK (true);
REVOKE SELECT ON public.email_send_log FROM anon, authenticated;

-- 2. space_processing_jobs — backend-only -> service_role only ----------------
DROP POLICY IF EXISTS "Service role full access on space_processing_jobs" ON public.space_processing_jobs;
CREATE POLICY space_processing_jobs_service ON public.space_processing_jobs
    FOR ALL TO service_role USING (true) WITH CHECK (true);
REVOKE SELECT ON public.space_processing_jobs FROM anon, authenticated;

-- 3. spaces — logged-in Space tab reads -> preserve authenticated, drop anon ---
DROP POLICY IF EXISTS "Service role full access on spaces" ON public.spaces;
CREATE POLICY spaces_service ON public.spaces
    FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY spaces_authenticated_read ON public.spaces
    FOR SELECT TO authenticated USING (true);
REVOKE SELECT ON public.spaces FROM anon;

-- 4. space_zones — logged-in Space tab reads -> preserve authenticated, drop anon
DROP POLICY IF EXISTS "Service role full access on space_zones" ON public.space_zones;
CREATE POLICY space_zones_service ON public.space_zones
    FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY space_zones_authenticated_read ON public.space_zones
    FOR SELECT TO authenticated USING (true);
REVOKE SELECT ON public.space_zones FROM anon;

-- Assert: no wide-open policy grants row visibility to anon on any of the 4 -----
DO $$
DECLARE bad int;
BEGIN
  SELECT count(*) INTO bad FROM pg_policies
  WHERE schemaname='public'
    AND tablename IN ('email_send_log','space_processing_jobs','spaces','space_zones')
    AND qual = 'true'
    AND roles && ARRAY['public','anon']::name[];
  IF bad > 0 THEN
    RAISE EXCEPTION 'wide-open public/anon USING(true) policy still present on % table(s)', bad;
  END IF;
END $$;

-- Assert: anon retains NO SELECT grant on any of the 4 ------------------------
DO $$
DECLARE leaked text;
BEGIN
  SELECT string_agg(table_name, ', ') INTO leaked
  FROM information_schema.role_table_grants
  WHERE table_schema='public' AND grantee='anon' AND privilege_type='SELECT'
    AND table_name IN ('email_send_log','space_processing_jobs','spaces','space_zones');
  IF leaked IS NOT NULL THEN
    RAISE EXCEPTION 'anon still has SELECT on: %', leaked;
  END IF;
END $$;

COMMIT;

-- ============================================================================
-- ROLLBACK (restores prior state exactly):
--   BEGIN;
--   DROP POLICY IF EXISTS email_send_log_service ON public.email_send_log;
--   DROP POLICY IF EXISTS space_processing_jobs_service ON public.space_processing_jobs;
--   DROP POLICY IF EXISTS spaces_service ON public.spaces;
--   DROP POLICY IF EXISTS spaces_authenticated_read ON public.spaces;
--   DROP POLICY IF EXISTS space_zones_service ON public.space_zones;
--   DROP POLICY IF EXISTS space_zones_authenticated_read ON public.space_zones;
--   CREATE POLICY "Service role full access on email_send_log"       ON public.email_send_log       FOR ALL USING (true) WITH CHECK (true);
--   CREATE POLICY "Service role full access on space_processing_jobs" ON public.space_processing_jobs FOR ALL USING (true) WITH CHECK (true);
--   CREATE POLICY "Service role full access on spaces"               ON public.spaces               FOR ALL USING (true) WITH CHECK (true);
--   CREATE POLICY "Service role full access on space_zones"          ON public.space_zones          FOR ALL USING (true) WITH CHECK (true);
--   GRANT SELECT ON public.email_send_log, public.space_processing_jobs, public.spaces, public.space_zones TO anon, authenticated;
--   COMMIT;
-- ============================================================================
