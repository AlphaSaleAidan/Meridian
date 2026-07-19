-- ============================================================================
-- 045 — Tier 3: restore lost `authenticated` write GRANTs (June 2026 regression)
-- ============================================================================
--
-- ROOT CAUSE (same class as supabase/migrations/20260603_fix_us_leads_grants.sql):
-- a June 2026 Supabase regression stripped the `authenticated` role's table-level
-- INSERT/UPDATE/DELETE grants on ~12 tables while their RLS policies survived.
-- Under RLS the base GRANT is checked BEFORE the policy, so every user-JWT write
-- fails with SQLSTATE 42501 "permission denied for table <t>" -> backend HTTP 500.
-- (42501 always means the GRANT is missing; "new row violates row-level security
-- policy" is the error you get when the GRANT exists but the policy denies.)
--
-- HISTORY:
--   * Tier 1+2 were restored ad hoc on 2026-06-07 via the Supabase Management
--     API SQL endpoint (never codified as a repo migration). The only in-repo
--     precedent is 20260603_fix_us_leads_grants.sql (us_leads).
--   * rep_training_progress / rep_conduct_signatures self-grant in
--     supabase/migrations/20260707_rep_training_course.sql (post-regression).
--   * This migration is the Tier-3 restore AND codifies the 2026-06-07 ad-hoc
--     grants that overlap it, so repo state == intended prod state.
--
-- METHOD (static analysis of this repo @ origin/main 1671f123):
-- every table written through a user JWT (frontend supabase-js client, or a
-- backend route that forwards the caller's Bearer token to PostgREST), granted
-- ONLY the verbs that an `authenticated`-reachable RLS policy actually allows.
--
-- TABLE x VERB x EVIDENCE (write path -> policy):
--
-- canada_leads          SELECT, INSERT, UPDATE, DELETE
--   writes: frontend/src/lib/canada-leads-service.ts:219 (insert), :253/:268
--           (update), :284 (delete);
--           frontend/src/pages/canada/portal/CanadaPortalCreateCustomerPage.tsx:652 (insert)
--   policies: supabase/migrations/20260628_canada_leads_rep_isolation.sql
--             SELECT:30 UPDATE:43 DELETE:59 INSERT:71 (all rep-scoped)
--
-- sales_reps            SELECT, INSERT, UPDATE  (NO DELETE — see below)
--   writes: frontend/src/lib/sales-auth.tsx:88 (insert — rep application);
--           frontend/src/pages/us/portal/USPortalSettingsPage.tsx:53,
--           us/portal/USPortalOnboardingPage.tsx:93,
--           canada/portal/CanadaPortalSettingsPage.tsx:45,
--           canada/portal/CanadaPortalOnboardingPage.tsx:93 (update)
--   policies: supabase/migrations/20260512_sales_reps_table.sql
--             SELECT:28 INSERT:36 UPDATE:44
--   DELETE deliberately NOT granted: reps_delete (:52) is `auth.uid() IS NOT
--   NULL` — any logged-in user could delete any rep. No user-JWT delete path
--   exists in the repo (rep rejection goes through the backend service key,
--   src/api/routes/canada.py rep-reject). Granting DELETE would open real
--   access; withholding it keeps delete service-role-only.
--
-- business_users        SELECT, INSERT
--   writes: frontend/src/pages/us/portal/USCustomerOnboardingWizard.tsx:422,
--           canada/portal/CanadaCustomerOnboardingWizard.tsx:420 (insert)
--   policies: supabase/migrations/20260429_001_business_accounts.sql
--             business_users_select:165 business_users_insert:171 (owner-scoped)
--   No UPDATE/DELETE policy exists -> not granted.
--
-- sla_signatures        SELECT, INSERT
--   writes (backend, forwarded user JWT): src/api/routes/us.py:523 and
--           src/api/routes/canada.py:575 (POST /rest/v1/sla_signatures with
--           Authorization: Bearer <user_token>; the 2026-06-07 incident —
--           /api/canada/sign-sla 500'd exactly here).
--           SELECT is required because both posts send
--           `Prefer: return=representation` (INSERT ... RETURNING).
--   policies: supabase/migrations/20260529_sla_signatures.sql
--             sla_signatures_owner_read:31 sla_signatures_authenticated_insert:39
--   No UPDATE/DELETE policy -> not granted (signatures are immutable).
--
-- schedule_uploads      SELECT, INSERT, UPDATE
--   writes: frontend/src/pages/us/portal/USCustomerOnboardingWizard.tsx:446,
--           canada/portal/CanadaCustomerOnboardingWizard.tsx:444,
--           customer/CustomerOnboardingWizard.tsx:461 (insert)
--   policies: supabase/migrations/20260516_schedule_uploads.sql
--             select_owner:68 insert_owner:72 update_owner:76 (owner-scoped)
--   UPDATE has no current frontend call site but is included to codify the
--   2026-06-07 ad-hoc prod grant (schedule_uploads INSERT,UPDATE) under its
--   owner-scoped policy.
--
-- inventory_document_uploads  SELECT, INSERT
--   writes: frontend/src/pages/MarginsPage.tsx:42,
--           us/portal/USCustomerOnboardingWizard.tsx:393,
--           canada/portal/CanadaCustomerOnboardingWizard.tsx:391 (insert)
--   policies: supabase/migrations/20260516_inventory_document_uploads.sql
--             SELECT:21 INSERT:26 (org-scoped) — no UPDATE/DELETE policy.
--
-- EXCLUDED ON PURPOSE (do not "fix" these here):
--   * us_leads, cpa_* — already granted in repo (20260603_fix_us_leads_grants.sql,
--     migrations/025_cpa_taxes_expenses.sql).
--   * rep_training_progress, rep_conduct_signatures — granted in
--     20260707_rep_training_course.sql.
--   * businesses — no direct user-JWT table write in the current repo; creation
--     goes through SECURITY DEFINER RPCs (create_business_for_user /
--     provision_business, 20260429_002_deal_flow.sql:127-131). The 2026-06-07
--     ad-hoc INSERT,UPDATE grant remains in prod; codify if/when a direct
--     client write path returns.
--   * business_locations — frontend writes EXIST (USCustomerOnboardingWizard.tsx:222
--     upsert, MerchantOnboardingWizard.tsx:312/314, CanadaCustomerOnboardingWizard.tsx:220)
--     but the ONLY repo policy is locations_select (20260429_001:177). With RLS
--     deny-by-default a write GRANT here is inert until a write policy exists;
--     granting now would be dead weight that springs to life if someone later
--     adds a wide policy. Needs a policy decision first — see
--     scripts/verify_tier3_grants.sql REVIEW section.
--   * organizations (MerchantOnboardingWizard.tsx:300 update), products
--     (3 wizard upserts) — tables have NO in-repo DDL or policies (dashboard-
--     created); verbs cannot be verified statically. REVIEW section.
--   * schedule_staff — frontend insert at CustomerOnboardingWizard.tsx:436, but
--     20260628_fix_phone_schedule_rls_anon_exposure.sql:46 made its only policy
--     service_role-scoped. A grant would be inert + misleading. That client
--     write is a latent bug to fix separately.
--   * spaces / space_zones — frontend delete/insert exist (spaces-service.ts:347,
--     :205) but migrations/024_spaces_org_isolation.sql deliberately keeps
--     `authenticated` SELECT-only (CC6.1). Do not regrant writes.
--   * security_events, support_tickets, pos_waitlist, website_analytics,
--     website_orders and the 42-table broader list — no user-JWT write path in
--     this repo; per-table triage 2026-06-07 says HOLD/REVIEW.
--
-- APPLY: cannot be run from this environment (no prod access). Run via the
-- Supabase SQL editor, `supabase db push`, or the Management API SQL endpoint
--   POST https://api.supabase.com/v1/projects/kbuzufjxwflrutowwnfl/database/query
-- (send a browser User-Agent or Cloudflare 403s). Then run
-- scripts/verify_tier3_grants.sql and eyeball expected-vs-actual.
--
-- Idempotent: GRANT is additive and safe to re-run. The DO block below aborts
-- the transaction if any expected grant is missing afterwards.
-- ============================================================================

BEGIN;

GRANT SELECT, INSERT, UPDATE, DELETE ON public.canada_leads               TO authenticated;
GRANT SELECT, INSERT, UPDATE         ON public.sales_reps                 TO authenticated;
GRANT SELECT, INSERT                 ON public.business_users             TO authenticated;
GRANT SELECT, INSERT                 ON public.sla_signatures             TO authenticated;
GRANT SELECT, INSERT, UPDATE         ON public.schedule_uploads           TO authenticated;
GRANT SELECT, INSERT                 ON public.inventory_document_uploads TO authenticated;

-- ── Verification: assert every expected grant actually exists ───────────────
DO $$
DECLARE
  exp record;
  missing text := '';
  unexpected text := '';
BEGIN
  FOR exp IN
    SELECT * FROM (VALUES
      ('canada_leads',               'SELECT'), ('canada_leads',               'INSERT'),
      ('canada_leads',               'UPDATE'), ('canada_leads',               'DELETE'),
      ('sales_reps',                 'SELECT'), ('sales_reps',                 'INSERT'),
      ('sales_reps',                 'UPDATE'),
      ('business_users',             'SELECT'), ('business_users',             'INSERT'),
      ('sla_signatures',             'SELECT'), ('sla_signatures',             'INSERT'),
      ('schedule_uploads',           'SELECT'), ('schedule_uploads',           'INSERT'),
      ('schedule_uploads',           'UPDATE'),
      ('inventory_document_uploads', 'SELECT'), ('inventory_document_uploads', 'INSERT')
    ) AS t(tbl, priv)
  LOOP
    IF NOT has_table_privilege('authenticated', format('public.%I', exp.tbl), exp.priv) THEN
      missing := missing || format(' %s:%s', exp.tbl, exp.priv);
    END IF;
  END LOOP;

  IF missing <> '' THEN
    RAISE EXCEPTION '045 verification failed — missing authenticated grants:%', missing;
  END IF;

  -- Negative direction (guards must fail closed, both directions asserted):
  -- these verbs have NO authenticated-reachable policy, or granting them would
  -- widen access (sales_reps DELETE). Warn — do not abort — so pre-existing
  -- prod drift is surfaced for review instead of wedging the migration.
  FOR exp IN
    SELECT * FROM (VALUES
      ('sales_reps',                 'DELETE'),
      ('business_users',             'UPDATE'), ('business_users',             'DELETE'),
      ('sla_signatures',             'UPDATE'), ('sla_signatures',             'DELETE'),
      ('schedule_uploads',           'DELETE'),
      ('inventory_document_uploads', 'UPDATE'), ('inventory_document_uploads', 'DELETE')
    ) AS t(tbl, priv)
  LOOP
    IF has_table_privilege('authenticated', format('public.%I', exp.tbl), exp.priv) THEN
      unexpected := unexpected || format(' %s:%s', exp.tbl, exp.priv);
    END IF;
  END LOOP;

  IF unexpected <> '' THEN
    RAISE WARNING '045 drift — authenticated holds grants this migration did not intend (review + consider REVOKE):%', unexpected;
  END IF;

  RAISE NOTICE '045 tier3 authenticated grants verified OK';
END $$;

COMMIT;

-- ── ROLLBACK (exact inverse — run manually if this must be reverted) ────────
-- BEGIN;
-- REVOKE SELECT, INSERT, UPDATE, DELETE ON public.canada_leads               FROM authenticated;
-- REVOKE SELECT, INSERT, UPDATE         ON public.sales_reps                 FROM authenticated;
-- REVOKE SELECT, INSERT                 ON public.business_users             FROM authenticated;
-- REVOKE SELECT, INSERT                 ON public.sla_signatures             FROM authenticated;
-- REVOKE SELECT, INSERT, UPDATE         ON public.schedule_uploads           FROM authenticated;
-- REVOKE SELECT, INSERT                 ON public.inventory_document_uploads FROM authenticated;
-- COMMIT;
-- WARNING: rolling back re-breaks every live path listed in the header
-- (canada leads CRUD, rep signup/settings, onboarding wizards, SLA signing —
-- 42501 -> HTTP 500) AND revokes SELECT the portals rely on for reads, which
-- is BROADER than the pre-migration regressed state (regression left SELECT
-- intact). If you only want to undo the write restore, revoke the write verbs:
--   REVOKE INSERT, UPDATE, DELETE ON public.canada_leads     FROM authenticated;
--   REVOKE INSERT, UPDATE  ON public.sales_reps              FROM authenticated;
--   REVOKE INSERT          ON public.business_users          FROM authenticated;
--   REVOKE INSERT          ON public.sla_signatures          FROM authenticated;
--   REVOKE INSERT, UPDATE  ON public.schedule_uploads        FROM authenticated;
--   REVOKE INSERT          ON public.inventory_document_uploads FROM authenticated;
