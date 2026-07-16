-- Minimal us_leads shim for scratch-postgres RLS tests.
--
-- Prod's us_leads table predates the in-repo migration history (no CREATE
-- TABLE migration exists for it — 20260522_us_leads_rls.sql and later files
-- only manage policies). This stub creates just the columns those policies
-- reference (rep_id ownership + the fields the fixture asserts on) so
-- 20260628_us_leads_rep_isolation.sql and 20260717_us_leads_downline_read.sql
-- can run unmodified against a scratch postgres:16.
--
-- Apply AFTER 20260512_sales_reps_table.sql (rep_id FK), BEFORE the us_leads
-- policy migrations. See tests/rls/hierarchy_policies.test.sql for run order.

CREATE TABLE IF NOT EXISTS us_leads (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  business_name text NOT NULL,
  stage text NOT NULL DEFAULT 'prospecting',
  monthly_value integer NOT NULL DEFAULT 0,
  notes text DEFAULT '',
  rep_id uuid REFERENCES sales_reps(id),
  created_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE us_leads ENABLE ROW LEVEL SECURITY;

-- Prod carries direct grants for these roles (RLS is the gate); mirror that so
-- the 20260628 REVOKE-from-anon is exercised meaningfully.
GRANT SELECT, INSERT, UPDATE, DELETE ON us_leads TO authenticated, service_role;
GRANT SELECT ON us_leads TO anon;
