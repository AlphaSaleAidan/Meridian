-- ============================================================================
-- READ-ONLY verification for the 2026-07-19 SOC 2 RLS batch
-- ----------------------------------------------------------------------------
-- Run against any Meridian Supabase DB (prod/staging) with a role that can read
-- pg_policies + information_schema. Makes NO changes. Confirms the end-state the
-- two migrations codify:
--   * 20260719_fix_wideopen_rls_email_spaces.sql   (DB-2 / DB-3)
--   * 20260719_vision_rls_backport_wideopen_drop.sql (vision R1)
--
-- Usage:  psql "$DATABASE_URL" -f scripts/compliance/verify_rls_soc2_20260719.sql
-- Expected: every check row reports status 'OK'. Any 'FAIL' row is a live exposure.
-- ============================================================================

\echo '== 1. No anon/public USING(true) policy on the batch tables (must be empty) =='
SELECT tablename, policyname, roles, qual
FROM pg_policies
WHERE schemaname = 'public'
  AND tablename IN ('email_send_log','space_processing_jobs','spaces','space_zones',
                    'vision_cameras','vision_traffic','vision_visitors','vision_visits')
  AND qual = 'true'
  AND roles && ARRAY['public','anon']::name[]
ORDER BY tablename, policyname;

\echo '== 2. anon holds NO SELECT grant on the batch tables (must be empty) =='
SELECT table_name, grantee, privilege_type
FROM information_schema.role_table_grants
WHERE table_schema = 'public'
  AND grantee = 'anon'
  AND privilege_type = 'SELECT'
  AND table_name IN ('email_send_log','space_processing_jobs','spaces','space_zones',
                     'vision_cameras','vision_traffic','vision_visitors','vision_visits')
ORDER BY table_name;

\echo '== 3. Backend-only tables have NO authenticated read policy (must be empty) =='
-- email_send_log / space_processing_jobs / vision_* are read via service_role only.
SELECT tablename, policyname, roles, cmd, qual
FROM pg_policies
WHERE schemaname = 'public'
  AND tablename IN ('email_send_log','space_processing_jobs',
                    'vision_cameras','vision_traffic','vision_visitors','vision_visits')
  AND roles && ARRAY['authenticated']::name[]
  AND qual = 'true'
ORDER BY tablename, policyname;

\echo '== 4. spaces / space_zones DO keep an authenticated SELECT policy (must show 2 rows) =='
SELECT tablename, policyname, roles, cmd
FROM pg_policies
WHERE schemaname = 'public'
  AND tablename IN ('spaces','space_zones')
  AND roles && ARRAY['authenticated']::name[]
  AND cmd = 'SELECT'
ORDER BY tablename;

\echo '== 5. vision_* DO keep a membership-scoped read policy (must show 4 rows, org-scoped) =='
SELECT tablename, policyname, roles, cmd, qual
FROM pg_policies
WHERE schemaname = 'public'
  AND tablename IN ('vision_cameras','vision_traffic','vision_visitors','vision_visits')
  AND policyname LIKE '%member_isolation'
ORDER BY tablename;

\echo '== 6. Consolidated verdict =='
WITH checks AS (
  SELECT 'anon_public_wideopen' AS check_name,
         (SELECT count(*) FROM pg_policies
          WHERE schemaname='public'
            AND tablename IN ('email_send_log','space_processing_jobs','spaces','space_zones',
                              'vision_cameras','vision_traffic','vision_visitors','vision_visits')
            AND qual='true' AND roles && ARRAY['public','anon']::name[]) AS cnt,
         0 AS expected
  UNION ALL
  SELECT 'anon_select_grant',
         (SELECT count(*) FROM information_schema.role_table_grants
          WHERE table_schema='public' AND grantee='anon' AND privilege_type='SELECT'
            AND table_name IN ('email_send_log','space_processing_jobs','spaces','space_zones',
                               'vision_cameras','vision_traffic','vision_visitors','vision_visits')), 0
  UNION ALL
  SELECT 'backend_only_auth_wideopen',
         (SELECT count(*) FROM pg_policies
          WHERE schemaname='public'
            AND tablename IN ('email_send_log','space_processing_jobs',
                              'vision_cameras','vision_traffic','vision_visitors','vision_visits')
            AND roles && ARRAY['authenticated']::name[] AND qual='true'), 0
  UNION ALL
  SELECT 'spaces_auth_read_present',
         (SELECT count(*) FROM pg_policies
          WHERE schemaname='public' AND tablename IN ('spaces','space_zones')
            AND roles && ARRAY['authenticated']::name[] AND cmd='SELECT'), 2
  UNION ALL
  SELECT 'vision_member_isolation_present',
         (SELECT count(*) FROM pg_policies
          WHERE schemaname='public'
            AND tablename IN ('vision_cameras','vision_traffic','vision_visitors','vision_visits')
            AND policyname LIKE '%member_isolation'), 4
)
SELECT check_name, cnt, expected,
       CASE WHEN cnt = expected THEN 'OK' ELSE 'FAIL' END AS status
FROM checks
ORDER BY check_name;
