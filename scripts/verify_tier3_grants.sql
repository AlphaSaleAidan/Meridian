-- ============================================================================
-- verify_tier3_grants.sql — expected vs actual `authenticated` grants
-- Companion to migrations/045_tier3_authenticated_grants.sql.
--
-- Read-only. Run against prod (Supabase SQL editor, or:
--   psql "$SUPABASE_DB_URL" -f scripts/verify_tier3_grants.sql
-- or the Management API SQL endpoint — browser User-Agent required or
-- Cloudflare 403s with "error code: 1010").
--
-- Section 1: PASS/FAIL per expected grant (should be all PASS after 045).
-- Section 2: full actual grant matrix for the regression's table set.
-- Section 3: REVIEW — tables with user-JWT write paths in the repo whose
--            policies could NOT be verified statically; a human must decide.
-- ============================================================================

-- ── 1. Expected vs actual ───────────────────────────────────────────────────
WITH expected(tbl, priv, should_have) AS (
  VALUES
    -- granted by 045 (see migration header for file:line evidence)
    ('canada_leads',               'SELECT', true),
    ('canada_leads',               'INSERT', true),
    ('canada_leads',               'UPDATE', true),
    ('canada_leads',               'DELETE', true),
    ('sales_reps',                 'SELECT', true),
    ('sales_reps',                 'INSERT', true),
    ('sales_reps',                 'UPDATE', true),
    ('business_users',             'SELECT', true),
    ('business_users',             'INSERT', true),
    ('sla_signatures',             'SELECT', true),
    ('sla_signatures',             'INSERT', true),
    ('schedule_uploads',           'SELECT', true),
    ('schedule_uploads',           'INSERT', true),
    ('schedule_uploads',           'UPDATE', true),
    ('inventory_document_uploads', 'SELECT', true),
    ('inventory_document_uploads', 'INSERT', true),
    -- must NOT be held (no authenticated-reachable policy / widens access)
    ('sales_reps',                 'DELETE', false),
    ('business_users',             'UPDATE', false),
    ('business_users',             'DELETE', false),
    ('sla_signatures',             'UPDATE', false),
    ('sla_signatures',             'DELETE', false),
    ('schedule_uploads',           'DELETE', false),
    ('inventory_document_uploads', 'UPDATE', false),
    ('inventory_document_uploads', 'DELETE', false),
    -- pre-existing repo grants that must still hold (Tier 1/2-era fixes)
    ('us_leads',                   'SELECT', true),
    ('us_leads',                   'INSERT', true),
    ('us_leads',                   'UPDATE', true),
    ('us_leads',                   'DELETE', true),
    ('rep_training_progress',      'INSERT', true),
    ('rep_training_progress',      'UPDATE', true),
    ('rep_conduct_signatures',     'INSERT', true)
)
SELECT
  e.tbl,
  e.priv,
  e.should_have AS expected,
  a.actual,
  CASE
    WHEN a.actual IS NULL             THEN 'NO SUCH TABLE'
    WHEN a.actual = e.should_have     THEN 'PASS'
    ELSE 'FAIL'
  END AS status
FROM expected e
CROSS JOIN LATERAL (
  SELECT CASE WHEN to_regclass(format('public.%I', e.tbl)) IS NULL THEN NULL
              ELSE has_table_privilege('authenticated', format('public.%I', e.tbl), e.priv)
         END AS actual
) a
ORDER BY status DESC, e.tbl, e.priv;

-- ── 2. Actual grant matrix (regression table set + neighbors) ───────────────
SELECT table_name,
       string_agg(privilege_type, ', ' ORDER BY privilege_type) AS authenticated_grants
FROM information_schema.role_table_grants
WHERE grantee = 'authenticated'
  AND table_schema = 'public'
  AND table_name IN (
    'canada_leads', 'sales_reps', 'business_users', 'sla_signatures',
    'schedule_uploads', 'inventory_document_uploads', 'us_leads',
    'rep_training_progress', 'rep_conduct_signatures',
    'businesses', 'business_locations', 'organizations', 'products',
    'schedule_staff', 'spaces', 'space_zones',
    'security_events', 'support_tickets', 'pos_waitlist',
    'website_analytics', 'website_orders'
  )
GROUP BY table_name
ORDER BY table_name;

-- ── 3. REVIEW — statically unverifiable, human decision required ────────────
-- These tables have user-JWT write call sites in the repo but either no
-- in-repo policy DDL or a policy that excludes `authenticated`. 045 does NOT
-- grant on them. Inspect the live policies below and decide per table:
--
--   organizations       update  frontend/src/pages/canada/merchant/MerchantOnboardingWizard.tsx:300
--                               (no in-repo DDL — dashboard-created)
--   products            upsert  frontend/src/pages/us/portal/USCustomerOnboardingWizard.tsx:386,
--                               canada/portal/CanadaCustomerOnboardingWizard.tsx:384,
--                               customer/CustomerOnboardingWizard.tsx:397 (no in-repo DDL)
--   business_locations  upsert/insert/update
--                               USCustomerOnboardingWizard.tsx:222,
--                               MerchantOnboardingWizard.tsx:312/:314,
--                               CanadaCustomerOnboardingWizard.tsx:220
--                               (only repo policy is locations_select — writes
--                               need a policy before a grant means anything)
--   schedule_staff      insert  frontend/src/pages/customer/CustomerOnboardingWizard.tsx:436
--                               (policy is service_role-only since 20260628 —
--                               this client write is a latent bug)
--   spaces/space_zones  delete/insert  frontend/src/lib/spaces-service.ts:347/:205
--                               (SELECT-only for authenticated by design, CC6.1
--                               — migrations/024_spaces_org_isolation.sql)
--   businesses          (no direct write path; SECURITY DEFINER RPCs; ad-hoc
--                               2026-06-07 INSERT,UPDATE grant may exist in prod)
SELECT tablename, policyname, cmd, roles, qual, with_check
FROM pg_policies
WHERE schemaname = 'public'
  AND tablename IN ('organizations', 'products', 'business_locations',
                    'schedule_staff', 'spaces', 'space_zones', 'businesses')
ORDER BY tablename, cmd, policyname;

-- RLS must be ON for every table we grant on (a grant with RLS off = full table
-- access). Expect rowsecurity = true for all rows returned here.
SELECT relname, relrowsecurity AS rls_enabled, relforcerowsecurity AS rls_forced
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
  AND relname IN ('canada_leads', 'sales_reps', 'business_users',
                  'sla_signatures', 'schedule_uploads', 'inventory_document_uploads')
ORDER BY relname;
