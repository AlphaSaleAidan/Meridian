-- ============================================================================
-- Fix wide-open RLS: menu_items, merchant_menus, voice_call_endings,
--   forwarding_verifications, phone_activation_events, sms_optout_tracking,
--   career_applications, canada_career_applications, recruiters (write).
-- ----------------------------------------------------------------------------
-- FINDING (static migration audit, 2026-07-22): each table below carries a
--   single permissive policy "Service role full access on <t>" written
--   `FOR ALL USING(true) WITH CHECK(true)` but WITHOUT `TO service_role`, so its
--   role is {public} (anon + authenticated) and every row is readable/writable
--   with the PUBLIC anon key in the frontend bundle. These tables were added
--   AFTER the 2026-06-28 / 2026-07-19 backports and were never covered.
--     * menu_items / merchant_menus            -> merchant menu + pricing
--     * voice_call_endings / forwarding_verifications / phone_activation_events
--                                              -> call telemetry
--     * sms_optout_tracking                    -> phone numbers that opted out (PII)
--     * career_applications / canada_career_applications -> applicant PII
--     * recruiters                             -> wide-open WRITE (public read is fine)
--
-- SAFE BECAUSE (verified against origin/main + frontend/src):
--   * Backend reads/writes all of these via get_db() = SUPABASE_SERVICE_ROLE_KEY,
--     which BYPASSES RLS — backend behavior is unchanged. The new
--     `TO service_role` policy preserves full DML for the backend.
--   * FRONTEND anon-client access to these tables (grep of frontend/src for
--     `.from('<t>')`): the ONLY hit is recruiters (CanadaCareersPage reads the
--     public recruiter list) — that read is preserved by the existing
--     "Public read access on recruiters" FOR SELECT policy; we only close its
--     wide-open WRITE policy. The careers FORM submits via
--     POST /api/canada/careers/apply (backend, service_role), NOT an anon insert,
--     so locking career_applications / canada_career_applications is safe.
--     No other table is touched by the frontend Supabase client.
--
-- GRANT-CONSISTENCY (42501 regression guard): no authenticated user-JWT path
--   reads any of these (all backend or, for recruiters, anon public read), so
--   revoking anon/authenticated SELECT strips nothing a live path relies on.
--   recruiters keeps its anon SELECT grant (public read) untouched.
--
-- Apply DELIBERATELY (snapshot first). Wrapped in a transaction with a
-- post-condition assertion. Reversible — rollback block at the bottom.
-- ============================================================================

BEGIN;

-- Backend-only tables -> service_role only, revoke anon + authenticated --------
DROP POLICY IF EXISTS "Service role full access on menu_items" ON public.menu_items;
CREATE POLICY menu_items_service ON public.menu_items
    FOR ALL TO service_role USING (true) WITH CHECK (true);
REVOKE SELECT, INSERT, UPDATE, DELETE ON public.menu_items FROM anon, authenticated;

DROP POLICY IF EXISTS "Service role full access on merchant_menus" ON public.merchant_menus;
CREATE POLICY merchant_menus_service ON public.merchant_menus
    FOR ALL TO service_role USING (true) WITH CHECK (true);
REVOKE SELECT, INSERT, UPDATE, DELETE ON public.merchant_menus FROM anon, authenticated;

DROP POLICY IF EXISTS "Service role full access on voice_call_endings" ON public.voice_call_endings;
CREATE POLICY voice_call_endings_service ON public.voice_call_endings
    FOR ALL TO service_role USING (true) WITH CHECK (true);
REVOKE SELECT, INSERT, UPDATE, DELETE ON public.voice_call_endings FROM anon, authenticated;

DROP POLICY IF EXISTS "Service role full access on forwarding_verifications" ON public.forwarding_verifications;
CREATE POLICY forwarding_verifications_service ON public.forwarding_verifications
    FOR ALL TO service_role USING (true) WITH CHECK (true);
REVOKE SELECT, INSERT, UPDATE, DELETE ON public.forwarding_verifications FROM anon, authenticated;

DROP POLICY IF EXISTS "Service role full access on phone_activation_events" ON public.phone_activation_events;
CREATE POLICY phone_activation_events_service ON public.phone_activation_events
    FOR ALL TO service_role USING (true) WITH CHECK (true);
REVOKE SELECT, INSERT, UPDATE, DELETE ON public.phone_activation_events FROM anon, authenticated;

DROP POLICY IF EXISTS "Service role full access on sms_optout_tracking" ON public.sms_optout_tracking;
CREATE POLICY sms_optout_tracking_service ON public.sms_optout_tracking
    FOR ALL TO service_role USING (true) WITH CHECK (true);
REVOKE SELECT, INSERT, UPDATE, DELETE ON public.sms_optout_tracking FROM anon, authenticated;

DROP POLICY IF EXISTS "Service role full access on career_applications" ON public.career_applications;
CREATE POLICY career_applications_service ON public.career_applications
    FOR ALL TO service_role USING (true) WITH CHECK (true);
REVOKE SELECT, INSERT, UPDATE, DELETE ON public.career_applications FROM anon, authenticated;

DROP POLICY IF EXISTS "Service role full access on canada_career_applications" ON public.canada_career_applications;
CREATE POLICY canada_career_applications_service ON public.canada_career_applications
    FOR ALL TO service_role USING (true) WITH CHECK (true);
REVOKE SELECT, INSERT, UPDATE, DELETE ON public.canada_career_applications FROM anon, authenticated;

-- recruiters -> keep public SELECT (frontend reads it), close wide-open WRITE ---
DROP POLICY IF EXISTS "Service role full access on recruiters" ON public.recruiters;
CREATE POLICY recruiters_service ON public.recruiters
    FOR ALL TO service_role USING (true) WITH CHECK (true);
-- "Public read access on recruiters" (FOR SELECT) is intentionally kept.
REVOKE INSERT, UPDATE, DELETE ON public.recruiters FROM anon, authenticated;

-- Assert: no wide-open public/anon USING(true) policy remains on the locked set
DO $$
DECLARE bad int;
BEGIN
  SELECT count(*) INTO bad FROM pg_policies
  WHERE schemaname = 'public'
    AND tablename IN ('menu_items','merchant_menus','voice_call_endings',
                      'forwarding_verifications','phone_activation_events',
                      'sms_optout_tracking','career_applications',
                      'canada_career_applications')
    AND qual = 'true'
    AND roles && ARRAY['public','anon']::name[];
  IF bad > 0 THEN
    RAISE EXCEPTION 'wide-open public/anon USING(true) policy still present on % table(s)', bad;
  END IF;
END $$;

COMMIT;

-- ============================================================================
-- ROLLBACK (restore prior wide-open state — for emergency use only):
-- BEGIN;
--   DROP POLICY IF EXISTS menu_items_service ON public.menu_items;
--   CREATE POLICY "Service role full access on menu_items" ON public.menu_items FOR ALL USING (true) WITH CHECK (true);
--   GRANT SELECT, INSERT, UPDATE, DELETE ON public.menu_items TO anon, authenticated;
--   -- (repeat per table; recruiters: GRANT INSERT,UPDATE,DELETE back)
-- COMMIT;
-- ============================================================================
