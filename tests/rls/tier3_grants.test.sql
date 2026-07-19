-- ============================================================================
-- RED-FIRST grant tests — Tier-3 `authenticated` write-GRANT restore (045).
--
-- Written against migrations/045_tier3_authenticated_grants.sql. Asserts the
-- GRANT layer only; the policy layer for these tables is asserted in prod via
-- scripts/verify_tier3_grants.sql (grants and policies are independent control
-- planes — under RLS, PG checks the table GRANT first, then the policy).
--
-- REQUIRES a live postgres (scratch postgres:16 container). Run order:
--
--   psql -v ON_ERROR_STOP=1 -f tests/rls/_pg_auth_stub.sql
--   psql -v ON_ERROR_STOP=1 -f tests/rls/_tier3_stub.sql
--   psql -v ON_ERROR_STOP=1 -f tests/rls/tier3_grants.test.sql      -- RED: fails
--   psql -v ON_ERROR_STOP=1 -f migrations/045_tier3_authenticated_grants.sql
--   psql -v ON_ERROR_STOP=1 -f tests/rls/tier3_grants.test.sql      -- GREEN
--
-- The stub tables are created by superuser with no grants — exactly the
-- June-2026 regressed prod state — so this file FAILS before 045 is applied
-- (red) and passes after (green).
--
-- Every guard is asserted in BOTH directions: verbs 045 must grant (allowed ✓)
-- and verbs 045 must NOT grant (denied ✓ — e.g. sales_reps DELETE, which would
-- let any logged-in user delete reps under the permissive reps_delete policy).
-- ============================================================================

\set ON_ERROR_STOP on

DO $$
DECLARE
  exp record;
  failures text := '';
BEGIN
  -- Direction 1 — must be granted after 045
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
      failures := failures || format(E'\n  MISSING grant: %s %s', exp.tbl, exp.priv);
    END IF;
  END LOOP;

  -- Direction 2 — must NOT be granted (no authenticated-reachable policy, or
  -- the only policy is wide enough that the grant would open real access)
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
      failures := failures || format(E'\n  UNEXPECTED grant: %s %s', exp.tbl, exp.priv);
    END IF;
  END LOOP;

  IF failures <> '' THEN
    RAISE EXCEPTION 'tier3_grants.test.sql FAILED:%', failures;
  END IF;

  RAISE NOTICE 'tier3_grants.test.sql PASSED (16 granted + 8 withheld verified)';
END $$;

-- Behavioral probe, denied direction: with RLS on and no DELETE grant, a
-- delete as `authenticated` must die at the GRANT layer (42501), regardless of
-- any policy. Proves the withheld verb is a real control, not decoration.
DO $$
BEGIN
  SET LOCAL ROLE authenticated;
  BEGIN
    DELETE FROM public.sales_reps;
    RAISE EXCEPTION 'tier3_grants.test.sql FAILED: authenticated could DELETE sales_reps';
  EXCEPTION
    WHEN insufficient_privilege THEN
      RAISE NOTICE 'denied ✓ — sales_reps DELETE blocked at grant layer (42501)';
  END;
  RESET ROLE;
END $$;
