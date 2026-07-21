-- ============================================================================
-- Fix wide-open RLS: menu/phone-telemetry/careers tables (anon-key exposure).
-- ----------------------------------------------------------------------------
-- 9 tables carried "Service role full access" policies written FOR ALL
-- USING(true) WITH CHECK(true) WITHOUT `TO service_role`, so their role was
-- {public} (anon + authenticated) — readable/writable with the anon key in the
-- frontend bundle. This locks each to service_role and revokes anon/authenticated.
--
-- TABLE-GUARDED + IDEMPOTENT: each block runs only if the table exists in this
-- project (some were never created in every environment) and drops both the old
-- and new policy names before creating, so re-applying is safe. Backend uses the
-- service-role key (bypasses RLS) → unchanged. Frontend grep confirms recruiters'
-- public read is the ONLY anon-client access among these (preserved — only its
-- wide-open WRITE is closed); careers submit via POST /api/canada/careers/apply
-- (backend). Applied to prod kbuzufjxwflrutowwnfl 2026-07-22 for the 6 tables
-- that exist there; snapshot in /root/.secrets/snapshots/rls_pre_20260722.json.
-- ============================================================================

BEGIN;

DO $$
BEGIN
  IF to_regclass('public.menu_items') IS NOT NULL THEN
    EXECUTE 'DROP POLICY IF EXISTS "Service role full access on menu_items" ON public.menu_items';
    EXECUTE 'DROP POLICY IF EXISTS menu_items_service ON public.menu_items';
    EXECUTE 'CREATE POLICY menu_items_service ON public.menu_items FOR ALL TO service_role USING (true) WITH CHECK (true)';
    EXECUTE 'REVOKE SELECT, INSERT, UPDATE, DELETE ON public.menu_items FROM anon, authenticated';
  END IF;
END $$;
DO $$
BEGIN
  IF to_regclass('public.merchant_menus') IS NOT NULL THEN
    EXECUTE 'DROP POLICY IF EXISTS "Service role full access on merchant_menus" ON public.merchant_menus';
    EXECUTE 'DROP POLICY IF EXISTS merchant_menus_service ON public.merchant_menus';
    EXECUTE 'CREATE POLICY merchant_menus_service ON public.merchant_menus FOR ALL TO service_role USING (true) WITH CHECK (true)';
    EXECUTE 'REVOKE SELECT, INSERT, UPDATE, DELETE ON public.merchant_menus FROM anon, authenticated';
  END IF;
END $$;
DO $$
BEGIN
  IF to_regclass('public.voice_call_endings') IS NOT NULL THEN
    EXECUTE 'DROP POLICY IF EXISTS "Service role full access on voice_call_endings" ON public.voice_call_endings';
    EXECUTE 'DROP POLICY IF EXISTS voice_call_endings_service ON public.voice_call_endings';
    EXECUTE 'CREATE POLICY voice_call_endings_service ON public.voice_call_endings FOR ALL TO service_role USING (true) WITH CHECK (true)';
    EXECUTE 'REVOKE SELECT, INSERT, UPDATE, DELETE ON public.voice_call_endings FROM anon, authenticated';
  END IF;
END $$;
DO $$
BEGIN
  IF to_regclass('public.forwarding_verifications') IS NOT NULL THEN
    EXECUTE 'DROP POLICY IF EXISTS "Service role full access on forwarding_verifications" ON public.forwarding_verifications';
    EXECUTE 'DROP POLICY IF EXISTS forwarding_verifications_service ON public.forwarding_verifications';
    EXECUTE 'CREATE POLICY forwarding_verifications_service ON public.forwarding_verifications FOR ALL TO service_role USING (true) WITH CHECK (true)';
    EXECUTE 'REVOKE SELECT, INSERT, UPDATE, DELETE ON public.forwarding_verifications FROM anon, authenticated';
  END IF;
END $$;
DO $$
BEGIN
  IF to_regclass('public.phone_activation_events') IS NOT NULL THEN
    EXECUTE 'DROP POLICY IF EXISTS "Service role full access on phone_activation_events" ON public.phone_activation_events';
    EXECUTE 'DROP POLICY IF EXISTS phone_activation_events_service ON public.phone_activation_events';
    EXECUTE 'CREATE POLICY phone_activation_events_service ON public.phone_activation_events FOR ALL TO service_role USING (true) WITH CHECK (true)';
    EXECUTE 'REVOKE SELECT, INSERT, UPDATE, DELETE ON public.phone_activation_events FROM anon, authenticated';
  END IF;
END $$;
DO $$
BEGIN
  IF to_regclass('public.sms_optout_tracking') IS NOT NULL THEN
    EXECUTE 'DROP POLICY IF EXISTS "Service role full access on sms_optout_tracking" ON public.sms_optout_tracking';
    EXECUTE 'DROP POLICY IF EXISTS sms_optout_tracking_service ON public.sms_optout_tracking';
    EXECUTE 'CREATE POLICY sms_optout_tracking_service ON public.sms_optout_tracking FOR ALL TO service_role USING (true) WITH CHECK (true)';
    EXECUTE 'REVOKE SELECT, INSERT, UPDATE, DELETE ON public.sms_optout_tracking FROM anon, authenticated';
  END IF;
END $$;
DO $$
BEGIN
  IF to_regclass('public.career_applications') IS NOT NULL THEN
    EXECUTE 'DROP POLICY IF EXISTS "Service role full access on career_applications" ON public.career_applications';
    EXECUTE 'DROP POLICY IF EXISTS career_applications_service ON public.career_applications';
    EXECUTE 'CREATE POLICY career_applications_service ON public.career_applications FOR ALL TO service_role USING (true) WITH CHECK (true)';
    EXECUTE 'REVOKE SELECT, INSERT, UPDATE, DELETE ON public.career_applications FROM anon, authenticated';
  END IF;
END $$;
DO $$
BEGIN
  IF to_regclass('public.canada_career_applications') IS NOT NULL THEN
    EXECUTE 'DROP POLICY IF EXISTS "Service role full access on canada_career_applications" ON public.canada_career_applications';
    EXECUTE 'DROP POLICY IF EXISTS canada_career_applications_service ON public.canada_career_applications';
    EXECUTE 'CREATE POLICY canada_career_applications_service ON public.canada_career_applications FOR ALL TO service_role USING (true) WITH CHECK (true)';
    EXECUTE 'REVOKE SELECT, INSERT, UPDATE, DELETE ON public.canada_career_applications FROM anon, authenticated';
  END IF;
END $$;
DO $$
BEGIN
  IF to_regclass('public.recruiters') IS NOT NULL THEN
    EXECUTE 'DROP POLICY IF EXISTS "Service role full access on recruiters" ON public.recruiters';
    EXECUTE 'DROP POLICY IF EXISTS recruiters_service ON public.recruiters';
    EXECUTE 'CREATE POLICY recruiters_service ON public.recruiters FOR ALL TO service_role USING (true) WITH CHECK (true)';
    EXECUTE 'REVOKE INSERT, UPDATE, DELETE ON public.recruiters FROM anon, authenticated';
    -- public SELECT policy on recruiters is intentionally kept (frontend reads it).
  END IF;
END $$;
COMMIT;
