"""Phase 1 — cross-tenant denial test for the camera streaming data model.

Proves that, under RLS, an authenticated member of business A cannot read business
B's cameras / streams — and that the P0 "FOR ALL USING (true)" hole on vision_cameras
is closed by 20260624_camera_streaming_phase1.sql.

Runs against a real Postgres (the migration uses RLS + auth.uid()). It SKIPS when no
test database is available, so it never blocks CI without infra:

    pip install psycopg[binary]
    TEST_DATABASE_URL=postgresql://localhost/meridian_test pytest tests/e2e/test_camera_tenancy_rls.py

CI: add a postgres service + TEST_DATABASE_URL to execute it (tracked for a later phase).
"""
import os
import pathlib
import uuid

import pytest

psycopg = pytest.importorskip("psycopg")  # skip if driver absent
TEST_DB = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_DB, reason="TEST_DATABASE_URL not set")

MIGRATION = (
    pathlib.Path(__file__).resolve().parents[2]
    / "supabase/migrations/20260624_camera_streaming_phase1.sql"
)

# Minimal scaffolding the migration FKs against + a Supabase-like auth.uid()/authenticated.
SCAFFOLD = """
DROP SCHEMA IF EXISTS auth CASCADE;
CREATE SCHEMA auth;
-- auth.uid() reads the per-session GUC we set below (mirrors Supabase semantics).
CREATE OR REPLACE FUNCTION auth.uid() RETURNS uuid LANGUAGE sql STABLE AS
  $$ SELECT NULLIF(current_setting('request.jwt.claim.sub', true), '')::uuid $$;
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='authenticated') THEN CREATE ROLE authenticated; END IF;
END $$;

CREATE TABLE businesses (id TEXT PRIMARY KEY);
CREATE TABLE organizations (id UUID PRIMARY KEY DEFAULT gen_random_uuid());
CREATE TABLE locations (id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID, name TEXT, state TEXT);
CREATE TABLE business_users (id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id TEXT REFERENCES businesses(id), user_id UUID, is_active BOOLEAN DEFAULT TRUE);
-- the existing camera tables (as they are in prod: org_id TEXT, the P0 'true' policy)
CREATE TABLE vision_cameras (id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id TEXT NOT NULL REFERENCES businesses(id), name TEXT);
CREATE TABLE vision_traffic (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), org_id TEXT NOT NULL REFERENCES businesses(id));
CREATE TABLE vision_visitors (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), org_id TEXT NOT NULL REFERENCES businesses(id));
CREATE TABLE vision_visits (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), org_id TEXT NOT NULL REFERENCES businesses(id));
ALTER TABLE vision_cameras ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role full access on vision_cameras" ON vision_cameras FOR ALL USING (true) WITH CHECK (true);
GRANT USAGE ON SCHEMA public, auth TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO authenticated;
"""


@pytest.fixture()
def conn():
    c = psycopg.connect(TEST_DB, autocommit=True)
    try:
        c.execute(SCAFFOLD)
        c.execute(MIGRATION.read_text())
        yield c
    finally:
        c.execute("RESET ROLE; DROP SCHEMA IF EXISTS auth CASCADE;")
        for t in ("user_overlay_prefs", "stream_tokens", "camera_streams", "camera_sites",
                  "vision_visits", "vision_visitors", "vision_traffic", "vision_cameras",
                  "business_users", "locations", "businesses", "organizations"):
            c.execute(f"DROP TABLE IF EXISTS {t} CASCADE")
        c.close()


def _seed_tenant(conn, biz: str):
    user = uuid.uuid4()
    conn.execute("INSERT INTO businesses(id) VALUES (%s)", (biz,))
    conn.execute("INSERT INTO business_users(business_id, user_id, is_active) VALUES (%s,%s,true)", (biz, user))
    cam = conn.execute("INSERT INTO vision_cameras(org_id, name) VALUES (%s,%s) RETURNING id",
                       (biz, f"cam-{biz}")).fetchone()[0]
    conn.execute("INSERT INTO camera_streams(org_id, camera_id, stream_name) VALUES (%s,%s,%s)",
                 (biz, cam, f"s-{biz}"))
    return user, cam


def _as_user(conn, user):
    conn.execute("SET ROLE authenticated")
    conn.execute("SELECT set_config('request.jwt.claim.sub', %s, false)", (str(user),))


def test_cross_tenant_camera_read_denied(conn):
    user_a, cam_a = _seed_tenant(conn, "biz_A")
    user_b, cam_b = _seed_tenant(conn, "biz_B")

    _as_user(conn, user_a)
    cams = {r[0] for r in conn.execute("SELECT id FROM vision_cameras").fetchall()}
    assert cam_a in cams, "tenant A must see its OWN camera"
    assert cam_b not in cams, "P0: tenant A must NOT see tenant B's camera"

    streams = {r[0] for r in conn.execute("SELECT org_id FROM camera_streams").fetchall()}
    assert streams == {"biz_A"}, f"tenant A must only see its own streams, saw {streams}"


def test_p0_true_policy_removed(conn):
    rows = conn.execute(
        "SELECT count(*) FROM pg_policies WHERE tablename='vision_cameras' AND qual='true'"
    ).fetchone()[0]
    assert rows == 0, "the FOR ALL USING(true) policy must be gone after the migration"
