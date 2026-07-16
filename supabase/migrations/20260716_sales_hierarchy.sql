-- ============================================================================
-- 7-level sales hierarchy: role + manager_id + materialized path on sales_reps,
-- scoped-downline RLS on canada_leads / sales_reps / commissions / payouts.
--
-- Idempotent. NOT applied automatically — apply with a Supabase snapshot in
-- place, coordinated with the main session. Tested by
-- tests/rls/hierarchy_policies.test.sql (red-first; see its header).
--
-- Design notes
--  * path = dot-joined rep UUIDs from root to self ('root.mid.leaf'),
--    maintained by trigger with a cycle guard; descendant paths cascade on
--    reparent. Prefix scans use the text_pattern_ops index.
--  * JOIN KEY: policies resolve the caller via auth.email() -> sales_reps.email.
--    auth.uid() != sales_reps.id in this schema (rep rows are created by the
--    backend independently of Supabase auth signup) — the email join is the
--    pattern proven by 20260628_canada_leads_rep_isolation.sql. rep_path_for(uid)
--    is still provided for id-keyed callers (e.g. mapping a lead's rep_id to a
--    path without recursive policy evaluation).
--  * Helpers are SECURITY DEFINER so policies on sales_reps can consult
--    sales_reps without recursively evaluating their own policies.
--  * us_leads policies are intentionally NOT touched here: the backend plane
--    (src/api/hierarchy.py) enforces subtree scoping for the US portal.
--  * Two independent planes: these policies + the backend filters. The backend
--    never relies on RLS; RLS never relies on the backend.
--
-- ROLLBACK: drop the four policies created below and re-create the 20260512
-- "reps_select"/"reps_update"/"reps_delete" policies; the added columns are
-- additive and safe to leave in place. No data is deleted by this migration.
-- ============================================================================

-- ── 1. Columns ────────────────────────────────────────────────────────────────

ALTER TABLE sales_reps ADD COLUMN IF NOT EXISTS role TEXT NOT NULL DEFAULT 'sales_rep';
ALTER TABLE sales_reps ADD COLUMN IF NOT EXISTS manager_id UUID;
ALTER TABLE sales_reps ADD COLUMN IF NOT EXISTS path TEXT;
ALTER TABLE sales_reps ADD COLUMN IF NOT EXISTS level INT;

DO $$ BEGIN
  ALTER TABLE sales_reps ADD CONSTRAINT sales_reps_role_check CHECK (role IN (
    'admin', 'vp_sales', 'regional_manager', 'district_manager',
    'office_manager', 'assistant_manager', 'sales_rep'
  ));
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE sales_reps ADD CONSTRAINT sales_reps_manager_fk
    FOREIGN KEY (manager_id) REFERENCES sales_reps(id) ON DELETE SET NULL;
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

CREATE INDEX IF NOT EXISTS idx_sales_reps_path ON sales_reps (path text_pattern_ops);
CREATE INDEX IF NOT EXISTS idx_sales_reps_manager ON sales_reps (manager_id);

-- ── 2. Role → level ───────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION sales_rep_role_level(r text) RETURNS int
LANGUAGE sql IMMUTABLE AS $$
  SELECT CASE r
    WHEN 'admin'             THEN 1
    WHEN 'vp_sales'          THEN 2
    WHEN 'regional_manager'  THEN 3
    WHEN 'district_manager'  THEN 4
    WHEN 'office_manager'    THEN 5
    WHEN 'assistant_manager' THEN 6
    ELSE 7  -- sales_rep
  END
$$;

-- ── 3. Materialized-path trigger with cycle guard ─────────────────────────────

CREATE OR REPLACE FUNCTION sales_reps_maintain_path() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
  parent_path text;
BEGIN
  NEW.level := sales_rep_role_level(NEW.role);
  IF NEW.manager_id IS NULL THEN
    NEW.path := NEW.id::text;
  ELSE
    IF NEW.manager_id = NEW.id THEN
      RAISE EXCEPTION 'sales_reps: a rep cannot be their own manager (%)', NEW.id;
    END IF;
    SELECT path INTO parent_path FROM sales_reps WHERE id = NEW.manager_id;
    IF parent_path IS NULL THEN
      RAISE EXCEPTION 'sales_reps: manager % not found or has no path yet', NEW.manager_id;
    END IF;
    -- Cycle guard: the new manager's path must not already contain this rep.
    IF ('.' || parent_path || '.') LIKE ('%.' || NEW.id::text || '.%') THEN
      RAISE EXCEPTION 'sales_reps: cycle — % is in the downline of %', NEW.manager_id, NEW.id;
    END IF;
    NEW.path := parent_path || '.' || NEW.id::text;
  END IF;
  RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS trg_sales_reps_path ON sales_reps;
CREATE TRIGGER trg_sales_reps_path
  BEFORE INSERT OR UPDATE OF manager_id, role ON sales_reps
  FOR EACH ROW EXECUTE FUNCTION sales_reps_maintain_path();

-- Reparent cascade: one prefix-rewrite fixes the whole subtree; the recursive
-- firing then finds zero stale rows (depth guard is belt-and-suspenders).
CREATE OR REPLACE FUNCTION sales_reps_cascade_path() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  UPDATE sales_reps
     SET path = NEW.path || substr(path, length(OLD.path) + 1)
   WHERE path LIKE OLD.path || '.%';
  RETURN NULL;
END $$;

DROP TRIGGER IF EXISTS trg_sales_reps_cascade_path ON sales_reps;
CREATE TRIGGER trg_sales_reps_cascade_path
  AFTER UPDATE OF path, manager_id ON sales_reps
  FOR EACH ROW
  WHEN (OLD.path IS DISTINCT FROM NEW.path AND pg_trigger_depth() < 3)
  EXECUTE FUNCTION sales_reps_cascade_path();

-- Privileged-column guard (independent of the RLS UPDATE policy below — a
-- second, separately-failing control): a non-admin session must never change
-- role / manager_id / path / level / commission_rate / is_active, even if a
-- future policy regression re-widens UPDATE. Service-role and admin sessions
-- pass. current_rep_role() is defined further down; pg resolves at call time.
CREATE OR REPLACE FUNCTION sales_reps_guard_privileged_cols() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF current_user IN ('service_role', 'postgres', 'supabase_admin') THEN
    RETURN NEW;
  END IF;
  IF current_rep_role() = 'admin' THEN
    RETURN NEW;
  END IF;
  IF NEW.role            IS DISTINCT FROM OLD.role
     OR NEW.manager_id   IS DISTINCT FROM OLD.manager_id
     OR NEW.path         IS DISTINCT FROM OLD.path
     OR NEW.level        IS DISTINCT FROM OLD.level
     OR NEW.commission_rate IS DISTINCT FROM OLD.commission_rate
     OR NEW.is_active    IS DISTINCT FROM OLD.is_active THEN
    RAISE EXCEPTION 'sales_reps: only admins may change role/manager/commission/active';
  END IF;
  RETURN NEW;
END $$;

-- ── 4. RLS helpers (SECURITY DEFINER: no recursive policy evaluation) ─────────

CREATE OR REPLACE FUNCTION rep_path_for(uid uuid) RETURNS text
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT path FROM sales_reps WHERE id = uid
$$;

CREATE OR REPLACE FUNCTION current_rep_id() RETURNS uuid
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT id FROM sales_reps WHERE lower(email) = lower(auth.email()) LIMIT 1
$$;

CREATE OR REPLACE FUNCTION current_rep_path() RETURNS text
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT path FROM sales_reps WHERE lower(email) = lower(auth.email()) LIMIT 1
$$;

CREATE OR REPLACE FUNCTION current_rep_role() RETURNS text
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT role FROM sales_reps WHERE lower(email) = lower(auth.email()) LIMIT 1
$$;

REVOKE ALL ON FUNCTION rep_path_for(uuid), current_rep_id(), current_rep_path(), current_rep_role() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION rep_path_for(uuid), current_rep_id(), current_rep_path(), current_rep_role()
  TO authenticated, service_role;

-- Guard trigger references current_rep_role(), so it is created after it.
DROP TRIGGER IF EXISTS trg_sales_reps_guard_cols ON sales_reps;
CREATE TRIGGER trg_sales_reps_guard_cols
  BEFORE UPDATE ON sales_reps
  FOR EACH ROW EXECUTE FUNCTION sales_reps_guard_privileged_cols();

-- ── 5. Backfill ───────────────────────────────────────────────────────────────
-- Admin allowlist (mirrors src/api/auth.py ADMIN_EMAILS) → role='admin'.
-- Everyone else keeps sales_rep, manager NULL, path = own id.

UPDATE sales_reps SET role = 'admin'
 WHERE lower(email) IN (
   'apierce@alphasale.co',
   'aidanpierce72@gmail.com',
   'aidanpierce@meridian.tips',
   'cheungenochmgmt@gmail.com',
   'aidanvietnguyen@gmail.com'
 ) AND role IS DISTINCT FROM 'admin';

UPDATE sales_reps
   SET path = id::text, level = sales_rep_role_level(role)
 WHERE path IS NULL;

-- ── 6. Policies ───────────────────────────────────────────────────────────────

-- sales_reps roster: admin sees all; everyone else sees self + downline subtree
-- + upline chain names (their managers). Replaces the 20260512 wide-open
-- "any authenticated user sees all" policy.
DROP POLICY IF EXISTS "reps_select" ON sales_reps;
DROP POLICY IF EXISTS "reps_select_scoped" ON sales_reps;
CREATE POLICY "reps_select_scoped" ON sales_reps FOR SELECT TO authenticated
  USING (
    current_rep_role() = 'admin'
    OR lower(email) = lower(auth.email())
    OR (current_rep_path() IS NOT NULL AND path LIKE current_rep_path() || '.%')  -- downline
    OR (current_rep_path() IS NOT NULL AND current_rep_path() LIKE path || '.%')  -- upline chain
  );

-- sales_reps UPDATE: was "any authenticated user can update ANY row" — with the
-- new role column that is a straight privilege-escalation vector. Scope to
-- admin-or-self; the privileged-column trigger above independently blocks a
-- self-update from touching role/manager/commission/active (settings pages
-- only write name/phone/location).
DROP POLICY IF EXISTS "reps_update" ON sales_reps;
DROP POLICY IF EXISTS "reps_update_scoped" ON sales_reps;
CREATE POLICY "reps_update_scoped" ON sales_reps FOR UPDATE TO authenticated
  USING (current_rep_role() = 'admin' OR lower(email) = lower(auth.email()))
  WITH CHECK (current_rep_role() = 'admin' OR lower(email) = lower(auth.email()));

-- sales_reps DELETE: admin only (reject/remove flows run through the backend
-- service role anyway).
DROP POLICY IF EXISTS "reps_delete" ON sales_reps;
DROP POLICY IF EXISTS "reps_delete_admin" ON sales_reps;
CREATE POLICY "reps_delete_admin" ON sales_reps FOR DELETE TO authenticated
  USING (current_rep_role() = 'admin');

-- sales_reps INSERT: keep the self-provision path (sales-auth.tsx inserts the
-- caller's own row) but stop arbitrary-identity / pre-elevated inserts.
DROP POLICY IF EXISTS "reps_insert" ON sales_reps;
DROP POLICY IF EXISTS "reps_insert_self" ON sales_reps;
CREATE POLICY "reps_insert_self" ON sales_reps FOR INSERT TO authenticated
  WITH CHECK (
    lower(email) = lower(auth.email())
    AND role = 'sales_rep'
    AND manager_id IS NULL
  );

-- canada_leads: ADDITIVE manager policy. The per-rep own-lead policies from
-- 20260628 stay in force (permissive policies OR together). Managers (any role
-- above sales_rep) read leads owned by reps strictly inside their subtree;
-- admins read all. Writes stay owner-only (unchanged).
DROP POLICY IF EXISTS "Managers can read downline leads" ON canada_leads;
CREATE POLICY "Managers can read downline leads" ON canada_leads FOR SELECT TO authenticated
  USING (
    current_rep_role() = 'admin'
    OR (
      current_rep_role() IS NOT NULL
      AND current_rep_role() <> 'sales_rep'
      AND rep_id IS NOT NULL
      AND rep_path_for(rep_id) LIKE current_rep_path() || '.%'
    )
  );

-- commissions / payouts: downline read (rollup skeleton only — no commission
-- math is added; calculate_commission() remains uncalled by design). Guarded:
-- these tables live in migrations/010 and may not exist on every environment.
DO $$
BEGIN
  IF to_regclass('public.commissions') IS NOT NULL THEN
    EXECUTE 'ALTER TABLE public.commissions ENABLE ROW LEVEL SECURITY';
    EXECUTE 'DROP POLICY IF EXISTS commissions_downline_read ON public.commissions';
    EXECUTE $p$CREATE POLICY commissions_downline_read ON public.commissions FOR SELECT TO authenticated
      USING (
        current_rep_role() = 'admin'
        OR rep_id = current_rep_id()
        OR (
          current_rep_role() IS NOT NULL
          AND current_rep_role() <> 'sales_rep'
          AND rep_path_for(rep_id) LIKE current_rep_path() || '.%'
        )
      )$p$;
  END IF;
  IF to_regclass('public.payouts') IS NOT NULL THEN
    EXECUTE 'ALTER TABLE public.payouts ENABLE ROW LEVEL SECURITY';
    EXECUTE 'DROP POLICY IF EXISTS payouts_downline_read ON public.payouts';
    EXECUTE $p$CREATE POLICY payouts_downline_read ON public.payouts FOR SELECT TO authenticated
      USING (
        current_rep_role() = 'admin'
        OR rep_id = current_rep_id()
        OR (
          current_rep_role() IS NOT NULL
          AND current_rep_role() <> 'sales_rep'
          AND rep_path_for(rep_id) LIKE current_rep_path() || '.%'
        )
      )$p$;
  END IF;
END $$;
