-- Stand-in tables for tests/rls/tier3_grants.test.sql (pattern: _us_leads_stub.sql).
-- Minimal columns, no FKs — these fixtures exist purely so GRANT/REVOKE state
-- can be asserted on a scratch postgres:16.
--
-- Apply AFTER tests/rls/_pg_auth_stub.sql (needs the `authenticated` role).
-- The auth stub sets Supabase-style ALTER DEFAULT PRIVILEGES (grant-all), so
-- after creating the tables this file REVOKES the write verbs from
-- `authenticated` — reproducing the June-2026 regressed prod state exactly
-- (write grants stripped, SELECT left intact) = the red state for the test.

CREATE TABLE IF NOT EXISTS public.canada_leads               (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), rep_id uuid);
CREATE TABLE IF NOT EXISTS public.sales_reps                 (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), email text, is_active boolean);
CREATE TABLE IF NOT EXISTS public.business_users             (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), business_id text, user_id uuid);
CREATE TABLE IF NOT EXISTS public.sla_signatures             (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), org_id text, signed_at timestamptz DEFAULT now());
CREATE TABLE IF NOT EXISTS public.schedule_uploads           (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), org_id text, status text);
CREATE TABLE IF NOT EXISTS public.inventory_document_uploads (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), org_id uuid);

ALTER TABLE public.canada_leads               ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sales_reps                 ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.business_users             ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sla_signatures             ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.schedule_uploads           ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.inventory_document_uploads ENABLE ROW LEVEL SECURITY;

-- ── Reproduce the regression: strip write grants, keep SELECT ───────────────
REVOKE INSERT, UPDATE, DELETE ON public.canada_leads               FROM authenticated;
REVOKE INSERT, UPDATE, DELETE ON public.sales_reps                 FROM authenticated;
REVOKE INSERT, UPDATE, DELETE ON public.business_users             FROM authenticated;
REVOKE INSERT, UPDATE, DELETE ON public.sla_signatures             FROM authenticated;
REVOKE INSERT, UPDATE, DELETE ON public.schedule_uploads           FROM authenticated;
REVOKE INSERT, UPDATE, DELETE ON public.inventory_document_uploads FROM authenticated;
-- anon should hold nothing on these tables at all
REVOKE ALL ON public.canada_leads, public.sales_reps, public.business_users,
              public.sla_signatures, public.schedule_uploads,
              public.inventory_document_uploads FROM anon;
