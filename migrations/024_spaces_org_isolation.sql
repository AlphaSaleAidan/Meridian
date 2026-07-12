-- CC6.1 — close cross-tenant read on spaces / space_zones.
--
-- Both tables carried a `USING (true)` SELECT policy granted to `authenticated`,
-- so ANY logged-in user could read EVERY merchant's 3D-scan metadata and zone
-- analytics (traffic, dwell, revenue-per-sqft) with their own JWT. This is the
-- same class of finding as the phone_*/schedule_* fix in #198, caught by the
-- SOC 2 RLS evidence collector (scripts/compliance/collect_rls_evidence.py).
--
-- Fix: replace the wide-open SELECT policies with the org-scoped member
-- isolation already used on the vision_* tables — a user sees a row only when
-- they are an active member of that row's org. `authenticated` holds SELECT
-- only (no INSERT/UPDATE/DELETE grant), so writes are unaffected; the frontend
-- read path (spaces-service.ts: select .eq('org_id'|'space_id')) is unchanged
-- except that RLS now enforces the membership the client filter assumes.
--
-- space_zones has no org_id of its own; it inherits scope through its parent
-- space (space_id -> spaces.org_id).

-- ── spaces ───────────────────────────────────────────────────────────
DROP POLICY IF EXISTS spaces_authenticated_read ON public.spaces;

CREATE POLICY spaces_member_isolation
  ON public.spaces FOR SELECT
  TO authenticated
  USING (
    org_id IN (
      SELECT business_users.business_id
      FROM public.business_users
      WHERE business_users.user_id = auth.uid()
        AND business_users.is_active IS TRUE
    )
  );

-- ── space_zones ──────────────────────────────────────────────────────
DROP POLICY IF EXISTS space_zones_authenticated_read ON public.space_zones;

CREATE POLICY space_zones_member_isolation
  ON public.space_zones FOR SELECT
  TO authenticated
  USING (
    space_id IN (
      SELECT s.id
      FROM public.spaces s
      WHERE s.org_id IN (
        SELECT business_users.business_id
        FROM public.business_users
        WHERE business_users.user_id = auth.uid()
          AND business_users.is_active IS TRUE
      )
    )
  );

-- service_role ALL policies (spaces_service / space_zones_service) are left in
-- place — the backend keeps full access via the service key. The legacy
-- `merchant_isolation` policy on spaces (org_id = auth.uid()::text) is inert
-- (no matching grant path for writes; superseded for reads) and is left
-- untouched to keep this change minimal; a follow-up may drop it.
