-- ============================================================================
-- PROPOSED FIX MIGRATION — CC6.1-RLS — remediate LIVE wide-open RLS exposure
-- ----------------------------------------------------------------------------
-- STATUS: AUTHORED, **NOT APPLIED**. Reviewable artifact for SOC 2 readiness.
-- Scoped from the R0 live pg_policies snapshot (pg_policies_live_20260628.md),
-- NOT from the migration files. DO NOT apply until:
--   (1) Aidan reviews + merges via PR, AND
--   (2) a DB snapshot is taken first, AND
--   (3) it is confirmed the frontend does NOT rely on anon/authenticated reads of
--       these tables directly (all access should go through the API service-role).
--
-- LIVE GROUND TRUTH (2026-06-28):
--   * phone_agent_config / phone_call_logs / phone_orders : RLS on, policy
--     `FOR ALL USING(true)` TO public, AND anon+authenticated hold a SELECT GRANT
--     -> readable with the PUBLIC anon key. phone_agent_config holds pos_access_token,
--     phone_orders holds customer name/phone. ANONYMOUS exposure.
--   * schedule_staff / schedule_shifts / published_schedules : same pattern.
--   * vision_* : ALREADY org-scoped in prod (member_isolation) — DO NOT touch here;
--     instead backport the live policy into a migration on main (see bottom).
--   * sms_optout_tracking : not present in prod catalog — verify before adding.
--
-- THE EXPOSURE VECTOR IS TWO THINGS TOGETHER: the USING(true) policy AND the
-- anon/authenticated SELECT grant. This migration removes BOTH.
-- ============================================================================

BEGIN;

-- ---- phone_* (tenant key: merchant_id TEXT; written by backend service-role) ----
DROP POLICY IF EXISTS "Service role full access on phone_agent_config" ON phone_agent_config;
DROP POLICY IF EXISTS "Service role full access on phone_call_logs"    ON phone_call_logs;
DROP POLICY IF EXISTS "Service role full access on phone_orders"       ON phone_orders;

CREATE POLICY phone_agent_config_service ON phone_agent_config FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY phone_call_logs_service    ON phone_call_logs    FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY phone_orders_service       ON phone_orders       FOR ALL TO service_role USING (true) WITH CHECK (true);

-- Remove the public read grant — THIS is what makes the rows anon-readable today.
REVOKE SELECT ON phone_agent_config FROM anon, authenticated;
REVOKE SELECT ON phone_call_logs    FROM anon, authenticated;
REVOKE SELECT ON phone_orders       FROM anon, authenticated;
-- phone_agent_config holds pos_access_token — it must NEVER be exposed to a client
-- role. All reads go through the API using the service-role key + enforce_service_member.

-- ---- schedule_* (tenant key: merchant_id UUID; written by backend service-role) ----
DROP POLICY IF EXISTS schedule_staff_service      ON schedule_staff;
DROP POLICY IF EXISTS schedule_shifts_service     ON schedule_shifts;
DROP POLICY IF EXISTS published_schedules_service ON published_schedules;

CREATE POLICY schedule_staff_service      ON schedule_staff      FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY schedule_shifts_service     ON schedule_shifts     FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY published_schedules_service ON published_schedules FOR ALL TO service_role USING (true) WITH CHECK (true);

REVOKE SELECT ON schedule_staff      FROM anon, authenticated;
REVOKE SELECT ON schedule_shifts     FROM anon, authenticated;
REVOKE SELECT ON published_schedules FROM anon, authenticated;

-- ---- safety assertion: no permissive public/authenticated USING(true) remains ----
DO $$
DECLARE bad int;
BEGIN
  SELECT count(*) INTO bad
  FROM pg_policies
  WHERE schemaname = 'public'
    AND tablename IN ('phone_agent_config','phone_call_logs','phone_orders',
                      'schedule_staff','schedule_shifts','published_schedules')
    AND qual = 'true'
    AND roles && ARRAY['public','authenticated','anon'];
  IF bad > 0 THEN
    RAISE EXCEPTION 'CC6.1-RLS: % wide-open public/authenticated USING(true) policies still present', bad;
  END IF;
END $$;

COMMIT;

-- ============================================================================
-- SEPARATE follow-ups (own migrations / PRs — see CC6.1-RLS.md):
--   * vision_*: prod is already org-scoped. Backport the LIVE policy into a
--     migration on `main` so a rebuild / db push cannot regress it, and restore
--     tests/e2e/test_camera_tenancy_rls.py to CI. (No prod change needed now.)
--   * If a table needs direct authenticated reads, add an org-scoped SELECT policy
--     mirroring vision_*_member_isolation AND re-grant SELECT to authenticated only.
--     Confirm the tenant-key column/type first (org_id is businesses.id = TEXT).
--   * Verify sms_optout_tracking exists in prod; if so apply the same pattern.
--   * Define get_user_org_id() or rewrite benchmark_snapshots policy (20260501_006:30).
--   * Fix cline_*/merchant_health policies scoped via business_id = auth.uid().
-- ============================================================================
