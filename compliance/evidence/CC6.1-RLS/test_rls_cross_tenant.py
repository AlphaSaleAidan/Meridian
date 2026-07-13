"""
Adversarial RLS cross-tenant negative test  —  control CC6.1-RLS.

This is the DELIVERABLE the SOC 2 Charter calls for: prove the *denied path fails*.
It does two things:

  1. SELF-CONTAINED REGRESSION (always runs if a Postgres is reachable):
     builds a minimal replica of the tenant-key shape, installs the *wide-open*
     policy (`FOR ALL USING(true)` with no TO clause) and demonstrates the
     cross-tenant LEAK, then installs the *fixed* service-role-only policy and
     demonstrates the leak is CLOSED — under the non-privileged `authenticated`
     role, with RLS forced. This proves the remediation pattern in
     fix_rls_wideopen.sql actually works.

  2. LIVE INVARIANT (runs only against the real Meridian DB):
     asserts NO permissive public/authenticated `USING(true)` policy remains on
     the sensitive tables. This is the regression guard to wire into CI.

Run:
    RLS_TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/postgres \
        pytest compliance/evidence/CC6.1-RLS/test_rls_cross_tenant.py -v

If RLS_TEST_DATABASE_URL is unset the self-contained test SKIPs (CI must provide a
throwaway Postgres service, as the deleted tests/e2e/test_camera_tenancy_rls.py did).
MERIDIAN_LIVE_DB (read-only creds) enables the live-invariant check.
"""
import os
import uuid
import pytest

psycopg = pytest.importorskip("psycopg")  # psycopg 3

SENSITIVE_TABLES = [
    "vision_cameras", "vision_traffic", "vision_visitors", "vision_visits",
    "phone_agent_config", "phone_call_logs", "phone_orders",
    "schedule_staff", "schedule_shifts", "published_schedules",
    "sms_optout_tracking",
]


def _conn(url_env):
    url = os.environ.get(url_env)
    if not url:
        pytest.skip(f"{url_env} not set")
    return psycopg.connect(url, autocommit=True)


# --------------------------------------------------------------------------- #
# 1. Self-contained regression: leak -> fix -> denied                          #
# --------------------------------------------------------------------------- #
@pytest.fixture
def db():
    conn = _conn("RLS_TEST_DATABASE_URL")
    sch = f"rls_test_{uuid.uuid4().hex[:8]}"
    with conn.cursor() as c:
        c.execute(f"CREATE SCHEMA {sch}")
        c.execute(f"SET search_path TO {sch}")
        # an 'authenticated' role that mimics Supabase's non-privileged API role
        c.execute("DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='authenticated') "
                  "THEN CREATE ROLE authenticated NOLOGIN; END IF; END $$;")
        c.execute(f"GRANT USAGE ON SCHEMA {sch} TO authenticated")
        # minimal replica of a tenant-scoped vision table
        c.execute("CREATE TABLE vision_cameras (id uuid primary key default gen_random_uuid(), "
                  "org_id uuid not null, name text)")
        c.execute("ALTER TABLE vision_cameras ENABLE ROW LEVEL SECURITY")
        c.execute("ALTER TABLE vision_cameras FORCE ROW LEVEL SECURITY")
        c.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON vision_cameras TO authenticated")
        org_a, org_b = uuid.uuid4(), uuid.uuid4()
        c.execute("INSERT INTO vision_cameras (org_id, name) VALUES (%s,'A-cam'),(%s,'B-cam')",
                  (org_a, org_b))
    yield conn, sch, org_a, org_b
    with conn.cursor() as c:
        c.execute(f"DROP SCHEMA {sch} CASCADE")
    conn.close()


def _rows_as_authenticated(conn, sch):
    """Read vision_cameras as the non-privileged authenticated role."""
    with conn.cursor() as c:
        c.execute("SET ROLE authenticated")
        c.execute(f"SET search_path TO {sch}")
        try:
            c.execute("SELECT name FROM vision_cameras ORDER BY name")
            return {r[0] for r in c.fetchall()}
        finally:
            c.execute("RESET ROLE")


def test_wideopen_policy_leaks_then_fix_denies(db):
    conn, sch, org_a, org_b = db
    with conn.cursor() as c:
        c.execute(f"SET search_path TO {sch}")

        # --- ANTI-PATTERN: the live policy, named "service role" but no TO clause
        c.execute('CREATE POLICY "Service role full access on vision_cameras" '
                  "ON vision_cameras FOR ALL USING (true) WITH CHECK (true)")
    leaked = _rows_as_authenticated(conn, sch)
    # an authenticated tenant sees BOTH orgs' cameras — the bug we are remediating
    assert leaked == {"A-cam", "B-cam"}, f"expected cross-tenant leak, got {leaked}"

    with conn.cursor() as c:
        c.execute(f"SET search_path TO {sch}")
        # --- FIX: drop wide-open, restrict to service_role only
        c.execute('DROP POLICY "Service role full access on vision_cameras" ON vision_cameras')
        c.execute("CREATE POLICY vision_cameras_service ON vision_cameras "
                  "FOR ALL TO service_role USING (true) WITH CHECK (true)")
    denied = _rows_as_authenticated(conn, sch)
    # after the fix, the authenticated role sees NOTHING (API mediates via service_role)
    assert denied == set(), f"authenticated must not read any tenant rows, got {denied}"


def test_no_permissive_true_policy_after_fix(db):
    """The invariant fix_rls_wideopen.sql asserts: no public/authenticated USING(true)."""
    conn, sch, org_a, org_b = db
    with conn.cursor() as c:
        c.execute(f"SET search_path TO {sch}")
        c.execute("CREATE POLICY vision_cameras_service ON vision_cameras "
                  "FOR ALL TO service_role USING (true) WITH CHECK (true)")
        c.execute("SELECT count(*) FROM pg_policies WHERE schemaname=%s "
                  "AND tablename='vision_cameras' AND qual='true' "
                  "AND (roles='{public}' OR roles='{authenticated}' OR roles='{anon}')", (sch,))
        assert c.fetchone()[0] == 0


# --------------------------------------------------------------------------- #
# 2. Live invariant against the real Meridian DB (read-only creds)             #
# --------------------------------------------------------------------------- #
def test_live_db_has_no_wideopen_sensitive_policies():
    conn = _conn("MERIDIAN_LIVE_DB")
    offenders = []
    with conn.cursor() as c:
        for t in SENSITIVE_TABLES:
            c.execute("SELECT policyname, roles FROM pg_policies WHERE schemaname='public' "
                      "AND tablename=%s AND qual='true' "
                      "AND (roles='{public}' OR roles='{authenticated}' OR roles='{anon}')", (t,))
            offenders += [(t, p, r) for p, r in c.fetchall()]
    conn.close()
    assert not offenders, (
        "CC6.1-RLS live regression: wide-open USING(true) policies present on "
        f"sensitive tables: {offenders}"
    )
