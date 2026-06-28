-- ============================================================================
-- Fix CRITICAL RLS exposure on phone_* and schedule_* tables
-- ----------------------------------------------------------------------------
-- FINDING (verified live via read-only pg_policies query, 2026-06-28):
--   phone_agent_config (holds pos_access_token), phone_orders (customer name/phone),
--   phone_call_logs, schedule_staff, schedule_shifts, published_schedules each have:
--     * RLS enabled, with a single permissive policy `... FOR ALL USING(true)` whose
--       roles = {public} (the policy is *named* "service role" but has NO `TO service_role`
--       clause, so it applies to anon + authenticated), AND
--     * a `SELECT` GRANT to BOTH `anon` and `authenticated`.
--   Together these make every row readable with the PUBLIC anon key (the key embedded
--   in the frontend bundle) — an ANONYMOUS data exposure of POS credentials + customer PII.
--
-- SAFE BECAUSE (verified):
--   * No frontend code reads these tables via the Supabase client (grep of frontend/src).
--   * anon/authenticated hold ONLY SELECT (no INSERT/UPDATE/DELETE), so no write path
--     depends on these grants. (A stray schedule_staff insert in an onboarding wizard
--     already cannot execute today — no INSERT grant.)
--   * The backend reads/writes via the service_role key, which bypasses RLS and retains
--     full DML — so backend behavior is unchanged.
--
-- FIX: drop the wide-open policy, scope all access to service_role, and REVOKE the
--      anon/authenticated SELECT grant (defense in depth — RLS would deny anyway once
--      the public policy is gone, but removing the grant closes it at the privilege layer too).
--
-- REVERSIBLE: re-create the old policies and re-GRANT SELECT to restore prior state.
-- Apply deliberately (snapshot first). See compliance/evidence/CC6.1-RLS/.
-- ============================================================================

BEGIN;

-- phone_* (tenant key: merchant_id TEXT) -------------------------------------
DROP POLICY IF EXISTS "Service role full access on phone_agent_config" ON public.phone_agent_config;
DROP POLICY IF EXISTS "Service role full access on phone_call_logs"    ON public.phone_call_logs;
DROP POLICY IF EXISTS "Service role full access on phone_orders"       ON public.phone_orders;

CREATE POLICY phone_agent_config_service ON public.phone_agent_config FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY phone_call_logs_service    ON public.phone_call_logs    FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY phone_orders_service       ON public.phone_orders       FOR ALL TO service_role USING (true) WITH CHECK (true);

-- schedule_* (tenant key: merchant_id UUID) ----------------------------------
DROP POLICY IF EXISTS schedule_staff_service      ON public.schedule_staff;
DROP POLICY IF EXISTS schedule_shifts_service     ON public.schedule_shifts;
DROP POLICY IF EXISTS published_schedules_service ON public.published_schedules;

CREATE POLICY schedule_staff_service2      ON public.schedule_staff      FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY schedule_shifts_service2     ON public.schedule_shifts     FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY published_schedules_service2 ON public.published_schedules FOR ALL TO service_role USING (true) WITH CHECK (true);

-- Remove the public read grant (the actual anonymous-read vector) ------------
REVOKE SELECT ON public.phone_agent_config FROM anon, authenticated;
REVOKE SELECT ON public.phone_call_logs    FROM anon, authenticated;
REVOKE SELECT ON public.phone_orders       FROM anon, authenticated;
REVOKE SELECT ON public.schedule_staff      FROM anon, authenticated;
REVOKE SELECT ON public.schedule_shifts     FROM anon, authenticated;
REVOKE SELECT ON public.published_schedules FROM anon, authenticated;

-- Assert no wide-open public/authenticated policy survives --------------------
DO $$
DECLARE bad int;
BEGIN
  SELECT count(*) INTO bad FROM pg_policies
  WHERE schemaname='public'
    AND tablename IN ('phone_agent_config','phone_call_logs','phone_orders',
                      'schedule_staff','schedule_shifts','published_schedules')
    AND qual = 'true' AND roles && ARRAY['public','authenticated','anon'];
  IF bad > 0 THEN
    RAISE EXCEPTION 'CC6.1-RLS: % wide-open public/authenticated USING(true) policies still present', bad;
  END IF;
END $$;

COMMIT;

-- ROLLBACK (if ever needed): for each table, DROP the *_service policy, re-CREATE the
-- original `FOR ALL USING(true) WITH CHECK(true)` policy, and `GRANT SELECT ... TO anon, authenticated`.
