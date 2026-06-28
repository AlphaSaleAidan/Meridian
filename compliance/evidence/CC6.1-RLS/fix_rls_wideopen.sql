-- ============================================================================
-- PROPOSED FIX MIGRATION — CC6.1-RLS — remediate wide-open RLS policies
-- ----------------------------------------------------------------------------
-- STATUS: AUTHORED, **NOT APPLIED**. Reviewable artifact for SOC 2 readiness.
-- DO NOT apply to live Supabase until:
--   (1) R0 is done — query live pg_policies to confirm current state, AND
--   (2) Aidan reviews and merges via PR, AND
--   (3) a DB snapshot is taken first (deliberate migration discipline).
--
-- WHAT THIS FIXES: six groups of tables carry policies named "Service role full
-- access" that LACK a `TO service_role` clause, so they apply to the PUBLIC role
-- (anon + authenticated) as `FOR ALL USING(true) WITH CHECK(true)` — i.e. every
-- authenticated JWT can read/write every tenant's rows via PostgREST.
-- See /compliance/controls/CC6.1-RLS.md.
--
-- DESIGN CHOICE (conservative, least-risk): these tables are written and read by
-- the BACKEND using the service-role key; the API mediates all tenant access and
-- enforces membership via enforce_service_member (CC6.1-TENANT). So the correct
-- least-privilege fix is SERVICE-ROLE-ONLY at the DB tier — matching how the
-- credit tables were already remediated in 20260603_drop_wideopen_policies_*.
-- An OPTIONAL org-scoped authenticated-read policy is provided COMMENTED OUT per
-- table; enable it ONLY after confirming the frontend reads that table directly
-- (vs. through the API) AND confirming the tenant-key column + type. The schema
-- mixes org_id(uuid)/merchant_id(text)/merchant_id(uuid) and business_users.
-- business_id is TEXT — do not guess the join; verify before enabling.
-- ============================================================================

BEGIN;

-- ---- vision_* (tenant key: org_id UUID -> businesses(id)) -------------------
DROP POLICY IF EXISTS "Service role full access on vision_cameras"  ON vision_cameras;
DROP POLICY IF EXISTS "Service role full access on vision_traffic"  ON vision_traffic;
DROP POLICY IF EXISTS "Service role full access on vision_visitors" ON vision_visitors;
DROP POLICY IF EXISTS "Service role full access on vision_visits"   ON vision_visits;

CREATE POLICY vision_cameras_service  ON vision_cameras  FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY vision_traffic_service  ON vision_traffic  FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY vision_visitors_service ON vision_visitors FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY vision_visits_service   ON vision_visits   FOR ALL TO service_role USING (true) WITH CHECK (true);
-- OPTIONAL authenticated read (enable only after confirming direct frontend reads):
-- CREATE POLICY vision_cameras_org_read ON vision_cameras FOR SELECT TO authenticated
--   USING (org_id::text IN (SELECT business_id FROM business_users
--                           WHERE user_id = auth.uid() AND is_active));

-- ---- phone_* (tenant key: merchant_id TEXT) --------------------------------
-- NOTE: confirm whether phone_agent_config.merchant_id is the business id or a
-- POS-specific merchant id before enabling any authenticated policy.
DROP POLICY IF EXISTS "Service role full access on phone_agent_config" ON phone_agent_config;
DROP POLICY IF EXISTS "Service role full access on phone_call_logs"    ON phone_call_logs;
DROP POLICY IF EXISTS "Service role full access on phone_orders"       ON phone_orders;

CREATE POLICY phone_agent_config_service ON phone_agent_config FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY phone_call_logs_service    ON phone_call_logs    FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY phone_orders_service       ON phone_orders       FOR ALL TO service_role USING (true) WITH CHECK (true);
-- phone_agent_config holds pos_access_token (a POS credential) — keep it
-- service-role-only; the API must never expose this column to authenticated reads.

-- ---- schedule_* (tenant key: merchant_id UUID) -----------------------------
DROP POLICY IF EXISTS "Service role full access on schedule_staff"      ON schedule_staff;
DROP POLICY IF EXISTS "Service role full access on schedule_shifts"     ON schedule_shifts;
DROP POLICY IF EXISTS "Service role full access on published_schedules" ON published_schedules;

CREATE POLICY schedule_staff_service      ON schedule_staff      FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY schedule_shifts_service     ON schedule_shifts     FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY published_schedules_service ON published_schedules FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ---- sms_optout_tracking (tenant key: merchant_id TEXT) --------------------
DROP POLICY IF EXISTS "Service role full access on sms_optout_tracking" ON sms_optout_tracking;
CREATE POLICY sms_optout_tracking_service ON sms_optout_tracking FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ---- safety assertion: no permissive USING(true) remains on these tables ----
DO $$
DECLARE bad int;
BEGIN
  SELECT count(*) INTO bad
  FROM pg_policies
  WHERE schemaname = 'public'
    AND tablename IN ('vision_cameras','vision_traffic','vision_visitors','vision_visits',
                      'phone_agent_config','phone_call_logs','phone_orders',
                      'schedule_staff','schedule_shifts','published_schedules',
                      'sms_optout_tracking')
    AND qual = 'true'
    AND (roles = '{public}' OR roles = '{authenticated}' OR roles = '{anon}');
  IF bad > 0 THEN
    RAISE EXCEPTION 'CC6.1-RLS: % wide-open public/authenticated USING(true) policies still present', bad;
  END IF;
END $$;

COMMIT;

-- Also TODO (separate migrations, see CC6.1-RLS.md):
--   * Restore 20260624_camera_streaming_phase1.sql + tests/e2e/test_camera_tenancy_rls.py to main.
--   * Define get_user_org_id() or rewrite benchmark_snapshots policy (20260501_006:30).
--   * Fix cline_*/merchant_health policies that scope via business_id = auth.uid() (never matches).
--   * Decide authenticated read for square_/clover_/toast_transactions (currently service-role only).
