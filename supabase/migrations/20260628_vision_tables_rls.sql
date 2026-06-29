-- Vision tables RLS hardening
--
-- Context: 20260516_vision_cameras.sql originally created vision_cameras,
-- vision_traffic, vision_visitors, vision_visits with wide-open FOR ALL
-- USING(true) policies. A LATER migration already replaced those with
-- per-org `vision_*_member_isolation` SELECT policies (scoped TO authenticated,
-- org_id IN the caller's business_users memberships). So in production these
-- tables are ALREADY org-isolated for authenticated users, and anon has NO
-- matching policy (RLS denies anon reads).
--
-- The only residual exposure was a leftover `GRANT SELECT ... TO anon` on each
-- table — harmless on its own (RLS still denies anon with no anon policy) but
-- unnecessary attack surface. This migration removes it (defense in depth).
--
-- It deliberately does NOT touch the `vision_*_member_isolation` policies — they
-- are the correct, current org-scoping, and the backend reads/writes via the
-- service_role key (which bypasses RLS) regardless. No frontend code reads these
-- tables via the Supabase anon/authenticated client.
--
-- This file reflects exactly what was applied to prod on 2026-06-28.
-- ============================================================================

BEGIN;

-- Remove the redundant anon read grant (the only residual vector) -------------
REVOKE SELECT ON public.vision_cameras  FROM anon;
REVOKE SELECT ON public.vision_traffic  FROM anon;
REVOKE SELECT ON public.vision_visitors FROM anon;
REVOKE SELECT ON public.vision_visits   FROM anon;

-- Assert no anon/public-applicable policy exists (org isolation is the only read path).
DO $$
DECLARE bad int;
BEGIN
  SELECT count(*) INTO bad FROM pg_policies
  WHERE schemaname = 'public'
    AND tablename IN ('vision_cameras', 'vision_traffic', 'vision_visitors', 'vision_visits')
    AND roles && ARRAY['anon', 'public']::name[];
  IF bad > 0 THEN
    RAISE EXCEPTION 'vision RLS: % anon/public-applicable policies present (expected 0)', bad;
  END IF;
END $$;

COMMIT;

-- ============================================================================
-- ROLLBACK (if ever needed): restore the anon read grant.
-- BEGIN;
-- GRANT SELECT ON public.vision_cameras  TO anon;
-- GRANT SELECT ON public.vision_traffic  TO anon;
-- GRANT SELECT ON public.vision_visitors TO anon;
-- GRANT SELECT ON public.vision_visits   TO anon;
-- COMMIT;
-- ============================================================================
