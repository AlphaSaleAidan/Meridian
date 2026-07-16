-- ============================================================================
-- RED-FIRST RLS fixture tests — 7-level sales hierarchy, scoped downlines.
-- Plane 1 of 2 (Postgres RLS). Plane 2 (backend API scoping) lives in
-- tests/rls/test_hierarchy_isolation.py and is tested independently.
--
-- REQUIRES a live postgres (CI-with-postgres or local docker). Run order:
--
--   createdb rls_test   # or a scratch postgres:16 container
--   psql -v ON_ERROR_STOP=1 -f tests/rls/_pg_auth_stub.sql
--   psql -v ON_ERROR_STOP=1 -f supabase/migrations/20260512_sales_reps_table.sql
--   psql -v ON_ERROR_STOP=1 -f supabase/migrations/20260507_canada_leads.sql
--   psql -v ON_ERROR_STOP=1 -f supabase/migrations/20260628_canada_leads_rep_isolation.sql
--   psql -v ON_ERROR_STOP=1 -f tests/rls/_us_leads_stub.sql                       -- prod us_leads has no in-repo CREATE migration
--   psql -v ON_ERROR_STOP=1 -f supabase/migrations/20260628_us_leads_rep_isolation.sql
--   psql -v ON_ERROR_STOP=1 -f supabase/migrations/20260716_sales_hierarchy.sql   -- policies under test (canada + roster)
--   psql -v ON_ERROR_STOP=1 -f supabase/migrations/20260717_us_leads_downline_read.sql  -- policies under test (US downline)
--   psql -v ON_ERROR_STOP=1 -f tests/rls/hierarchy_policies.test.sql
--
-- Written BEFORE 20260716_sales_hierarchy.sql exists: with only the baseline
-- migrations applied this file FAILS (columns/policies missing), which is the
-- red state. It passes once the hierarchy migration is applied. The us_leads
-- cases were added the same red-first way for 20260717_us_leads_downline_read:
-- with only 20260628 applied, the "manager sees downline US lead" assertion
-- FAILS (own-leads-only), and passes once 20260717 is applied.
--
-- Every guard is asserted in BOTH directions (allowed ✓ / denied ✓).
--
-- Fixture tree (paths are dot-joined rep UUIDs):
--   admin  (role admin)
--   vp     (role vp_sales)
--     ├── dm1 (district_manager) ── rep1 (sales_rep)
--     └── dm2 (district_manager) ── rep2 (sales_rep)
-- ============================================================================

\set ON_ERROR_STOP on

BEGIN;

-- ── Fixture (inserted as superuser; trigger computes path/level) ─────────────
INSERT INTO sales_reps (id, name, email, role, is_active) VALUES
  ('aaaaaaaa-0000-4000-8000-000000000001', 'Admin',  'admin@rls.test', 'admin', true),
  ('bbbbbbbb-0000-4000-8000-000000000002', 'VP',     'vp@rls.test',    'vp_sales', true);

INSERT INTO sales_reps (id, name, email, role, manager_id, is_active) VALUES
  ('cccccccc-0000-4000-8000-000000000003', 'DM One', 'dm1@rls.test', 'district_manager', 'bbbbbbbb-0000-4000-8000-000000000002', true),
  ('eeeeeeee-0000-4000-8000-000000000005', 'DM Two', 'dm2@rls.test', 'district_manager', 'bbbbbbbb-0000-4000-8000-000000000002', true);

INSERT INTO sales_reps (id, name, email, role, manager_id, is_active) VALUES
  ('dddddddd-0000-4000-8000-000000000004', 'Rep One', 'rep1@rls.test', 'sales_rep', 'cccccccc-0000-4000-8000-000000000003', true),
  ('ffffffff-0000-4000-8000-000000000006', 'Rep Two', 'rep2@rls.test', 'sales_rep', 'eeeeeeee-0000-4000-8000-000000000005', true);

-- Trigger sanity: materialized paths were computed
DO $$
BEGIN
  IF (SELECT path FROM sales_reps WHERE email = 'rep1@rls.test')
     <> 'bbbbbbbb-0000-4000-8000-000000000002.cccccccc-0000-4000-8000-000000000003.dddddddd-0000-4000-8000-000000000004' THEN
    RAISE EXCEPTION 'FAIL: materialized path not maintained by trigger (got %)',
      (SELECT path FROM sales_reps WHERE email = 'rep1@rls.test');
  END IF;
  RAISE NOTICE 'PASS: trigger maintains materialized path';
END $$;

INSERT INTO canada_leads (id, business_name, contact_name, contact_email, rep_id) VALUES
  ('11111111-0000-4000-8000-000000000001', 'Branch1 Pizza',   'P One', 'p1@biz.test', 'dddddddd-0000-4000-8000-000000000004'),
  ('22222222-0000-4000-8000-000000000002', 'Branch2 Cafe',    'P Two', 'p2@biz.test', 'ffffffff-0000-4000-8000-000000000006'),
  ('33333333-0000-4000-8000-000000000003', 'Unassigned Deli', 'P Nil', 'p3@biz.test', NULL);

-- US mirror fixture (same tree, us_leads table — 20260717 policy under test)
INSERT INTO us_leads (id, business_name, rep_id) VALUES
  ('44444444-0000-4000-8000-000000000004', 'US Branch1 Diner',    'dddddddd-0000-4000-8000-000000000004'),
  ('55555555-0000-4000-8000-000000000005', 'US Branch2 Grill',    'ffffffff-0000-4000-8000-000000000006'),
  ('66666666-0000-4000-8000-000000000006', 'US Unassigned Truck', NULL);

-- ── Persona: dm1 (manager) ───────────────────────────────────────────────────
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claims', '{"email":"dm1@rls.test","role":"authenticated"}', true);

DO $$
DECLARE n int;
BEGIN
  -- direction 1: manager CAN read own-subtree lead
  SELECT count(*) INTO n FROM canada_leads WHERE id = '11111111-0000-4000-8000-000000000001';
  IF n <> 1 THEN RAISE EXCEPTION 'FAIL: manager cannot see own-subtree lead'; END IF;
  RAISE NOTICE 'PASS: manager sees own-subtree lead';

  -- direction 2: manager CANNOT read sibling-branch lead
  SELECT count(*) INTO n FROM canada_leads WHERE id = '22222222-0000-4000-8000-000000000002';
  IF n <> 0 THEN RAISE EXCEPTION 'FAIL: sibling-branch lead visible to manager'; END IF;
  RAISE NOTICE 'PASS: sibling-branch lead hidden from manager';

  -- cross-branch WRITE blocked (0 rows affected)
  UPDATE canada_leads SET notes = 'stolen' WHERE id = '22222222-0000-4000-8000-000000000002';
  GET DIAGNOSTICS n = ROW_COUNT;
  IF n <> 0 THEN RAISE EXCEPTION 'FAIL: cross-branch UPDATE affected % row(s)', n; END IF;
  RAISE NOTICE 'PASS: cross-branch write blocked';

  -- roster: subtree + upline visible, sibling branch hidden
  SELECT count(*) INTO n FROM sales_reps WHERE email = 'rep1@rls.test';
  IF n <> 1 THEN RAISE EXCEPTION 'FAIL: manager cannot see downline rep in roster'; END IF;
  SELECT count(*) INTO n FROM sales_reps WHERE email = 'vp@rls.test';
  IF n <> 1 THEN RAISE EXCEPTION 'FAIL: manager cannot see upline chain in roster'; END IF;
  SELECT count(*) INTO n FROM sales_reps WHERE email IN ('dm2@rls.test', 'rep2@rls.test');
  IF n <> 0 THEN RAISE EXCEPTION 'FAIL: sibling branch visible in roster (% rows)', n; END IF;
  RAISE NOTICE 'PASS: roster scoped to subtree + upline';

  -- ── us_leads (20260717 mirror policy) — BOTH directions ──
  -- direction 1: manager CAN read own-subtree US lead
  SELECT count(*) INTO n FROM us_leads WHERE id = '44444444-0000-4000-8000-000000000004';
  IF n <> 1 THEN RAISE EXCEPTION 'FAIL: manager cannot see own-subtree US lead'; END IF;
  RAISE NOTICE 'PASS: manager sees own-subtree US lead';

  -- direction 2: manager CANNOT read sibling-branch US lead
  SELECT count(*) INTO n FROM us_leads WHERE id = '55555555-0000-4000-8000-000000000005';
  IF n <> 0 THEN RAISE EXCEPTION 'FAIL: sibling-branch US lead visible to manager'; END IF;
  RAISE NOTICE 'PASS: sibling-branch US lead hidden from manager';

  -- downline read is READ-ONLY: manager UPDATE on downline US lead affects 0 rows
  UPDATE us_leads SET notes = 'manager-write' WHERE id = '44444444-0000-4000-8000-000000000004';
  GET DIAGNOSTICS n = ROW_COUNT;
  IF n <> 0 THEN RAISE EXCEPTION 'FAIL: manager WROTE a downline US lead (% row(s)) — 20260717 must be SELECT-only', n; END IF;
  RAISE NOTICE 'PASS: US downline read is read-only (writes stay owner-only)';

  -- privilege escalation: manager cannot self-promote via direct UPDATE
  UPDATE sales_reps SET role = 'admin' WHERE email = 'dm1@rls.test';
  RAISE EXCEPTION 'FAIL: non-admin self-promoted to admin via sales_reps UPDATE';
EXCEPTION
  WHEN raise_exception THEN
    IF SQLERRM LIKE 'FAIL:%' THEN RAISE; END IF;
    RAISE NOTICE 'PASS: self-promotion blocked (%)', SQLERRM;
END $$;

RESET ROLE;

-- ── Persona: rep1 (leaf rep) ─────────────────────────────────────────────────
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claims', '{"email":"rep1@rls.test","role":"authenticated"}', true);

DO $$
DECLARE n int;
BEGIN
  SELECT count(*) INTO n FROM canada_leads WHERE id = '11111111-0000-4000-8000-000000000001';
  IF n <> 1 THEN RAISE EXCEPTION 'FAIL: rep cannot see own lead'; END IF;
  SELECT count(*) INTO n FROM canada_leads WHERE id = '22222222-0000-4000-8000-000000000002';
  IF n <> 0 THEN RAISE EXCEPTION 'FAIL: rep sees another rep''s lead'; END IF;
  RAISE NOTICE 'PASS: rep sees only self (both directions)';

  -- a leaf rep gets NO manager-subtree widening
  SELECT count(*) INTO n FROM sales_reps WHERE email IN ('dm2@rls.test', 'rep2@rls.test');
  IF n <> 0 THEN RAISE EXCEPTION 'FAIL: leaf rep sees lateral branch in roster'; END IF;
  RAISE NOTICE 'PASS: leaf rep roster limited to own chain';

  -- us_leads: leaf rep stays self-only under the additive 20260717 policy
  SELECT count(*) INTO n FROM us_leads WHERE id = '44444444-0000-4000-8000-000000000004';
  IF n <> 1 THEN RAISE EXCEPTION 'FAIL: rep cannot see own US lead'; END IF;
  SELECT count(*) INTO n FROM us_leads WHERE id = '55555555-0000-4000-8000-000000000005';
  IF n <> 0 THEN RAISE EXCEPTION 'FAIL: rep sees another rep''s US lead (20260717 widened leaf reps)'; END IF;
  RAISE NOTICE 'PASS: US leaf rep sees only self (both directions)';
END $$;

RESET ROLE;

-- ── Persona: admin ───────────────────────────────────────────────────────────
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claims', '{"email":"admin@rls.test","role":"authenticated"}', true);

DO $$
DECLARE n int;
BEGIN
  SELECT count(*) INTO n FROM canada_leads;
  IF n <> 3 THEN RAISE EXCEPTION 'FAIL: admin sees % leads, expected all 3', n; END IF;
  SELECT count(*) INTO n FROM us_leads;
  IF n <> 3 THEN RAISE EXCEPTION 'FAIL: admin sees % US leads, expected all 3', n; END IF;
  SELECT count(*) INTO n FROM sales_reps;
  IF n <> 6 THEN RAISE EXCEPTION 'FAIL: admin sees % reps, expected all 6', n; END IF;
  RAISE NOTICE 'PASS: admin sees the full forest';
END $$;

RESET ROLE;

-- ── Cycle guard (trigger plane) ──────────────────────────────────────────────
DO $$
BEGIN
  -- vp reports to their own grand-descendant rep1 → must be rejected
  UPDATE sales_reps SET manager_id = 'dddddddd-0000-4000-8000-000000000004'
   WHERE id = 'bbbbbbbb-0000-4000-8000-000000000002';
  RAISE EXCEPTION 'FAIL: cycle accepted (vp now managed by own descendant)';
EXCEPTION
  WHEN raise_exception THEN
    IF SQLERRM LIKE 'FAIL:%' THEN RAISE; END IF;
    RAISE NOTICE 'PASS: cycle guard rejected descendant-as-manager (%)', SQLERRM;
END $$;

-- ── Reparent cascade: moving dm2 under dm1 rewrites rep2''s path ─────────────
DO $$
DECLARE p text;
BEGIN
  UPDATE sales_reps SET manager_id = 'cccccccc-0000-4000-8000-000000000003'
   WHERE id = 'eeeeeeee-0000-4000-8000-000000000005';
  SELECT path INTO p FROM sales_reps WHERE id = 'ffffffff-0000-4000-8000-000000000006';
  IF p <> 'bbbbbbbb-0000-4000-8000-000000000002.cccccccc-0000-4000-8000-000000000003.eeeeeeee-0000-4000-8000-000000000005.ffffffff-0000-4000-8000-000000000006' THEN
    RAISE EXCEPTION 'FAIL: descendant path not cascaded on reparent (got %)', p;
  END IF;
  RAISE NOTICE 'PASS: reparent cascades descendant paths';
END $$;

ROLLBACK;

\echo 'hierarchy_policies.test.sql: ALL ASSERTIONS PASSED (transaction rolled back)'
