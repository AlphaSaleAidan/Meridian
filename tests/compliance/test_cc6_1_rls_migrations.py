"""
CC6.1 — Row-level security: migrations may never (re)introduce broad policies.

Static analysis of migrations/*.sql — the change-time complement to the live
pg_policies evidence collector (scripts/compliance/collect_rls_evidence.py).
History: phone_*/schedule_* tables shipped USING(true) policies granted to
anon — readable with the public key (fixed in PR #198). These tests make that
class of regression fail CI before it can reach Supabase.
"""
import re
from pathlib import Path

CONTROL = "CC6.1"

MIGRATIONS = sorted((Path(__file__).parents[2] / "migrations").glob("*.sql"))

# Tables whose policies may legitimately target public/anon (public legal
# documents; content is published by design and rows carry no tenant data).
PUBLIC_POLICY_ALLOWLIST = {"compliance_documents"}

_POLICY_RE = re.compile(
    r"create\s+policy\s+\"?(?P<name>[\w.-]+)\"?\s+on\s+\"?(?:public\.)?(?P<table>\w+)\"?"
    r"(?P<body>.*?);",
    re.IGNORECASE | re.DOTALL,
)
_CREATE_TABLE_RE = re.compile(
    r"create\s+table\s+(?:if\s+not\s+exists\s+)?\"?(?:public\.)?(?P<table>\w+)\"?",
    re.IGNORECASE,
)
_ENABLE_RLS_RE = re.compile(
    r"alter\s+table\s+\"?(?:public\.)?(?P<table>\w+)\"?\s+enable\s+row\s+level\s+security",
    re.IGNORECASE,
)


def _all_sql() -> str:
    return "\n".join(p.read_text() for p in MIGRATIONS)


def test_migrations_exist():
    assert MIGRATIONS, "migrations/ directory is empty — nothing to verify"


# Known migration↔live drift, verified read-only against prod 2026-07-12:
# these tables HAVE relrowsecurity=true live (enabled directly in Supabase)
# but no ENABLE ROW LEVEL SECURITY in migrations/. Backfilling the migrations
# closes the drift and shrinks this set; adding NEW tables here is a CI
# failure by design. swarm_traces is a local SQLite schema (no RLS concept).
KNOWN_RLS_MIGRATION_DRIFT = {
    "checkout_sessions", "payouts", "rep_client_assignments",
    "sales_reps", "voice_ledger", "swarm_traces",
}


def test_every_created_table_enables_rls():
    """Every table created by a migration must enable RLS somewhere in the set."""
    sql = _all_sql()
    created = {m.group("table").lower() for m in _CREATE_TABLE_RE.finditer(sql)}
    rls_enabled = {m.group("table").lower() for m in _ENABLE_RLS_RE.finditer(sql)}
    missing = sorted(created - rls_enabled - KNOWN_RLS_MIGRATION_DRIFT)
    assert not missing, (
        "NEW tables created without ENABLE ROW LEVEL SECURITY anywhere in "
        "migrations/ — Supabase exposes these via PostgREST subject only to "
        "grants:\n  " + "\n  ".join(missing)
    )


def test_known_rls_drift_only_shrinks():
    """When drift is backfilled, remove the table from the known set."""
    sql = _all_sql()
    rls_enabled = {m.group("table").lower() for m in _ENABLE_RLS_RE.finditer(sql)}
    fixed = sorted(KNOWN_RLS_MIGRATION_DRIFT & rls_enabled)
    assert not fixed, (
        "These tables now enable RLS in migrations — remove them from "
        "KNOWN_RLS_MIGRATION_DRIFT so the ratchet tightens:\n  " + "\n  ".join(fixed)
    )


def test_no_broad_policy_for_anon_or_public():
    """No CREATE POLICY may combine anon/public roles with USING (true)."""
    violations = []
    for path in MIGRATIONS:
        for m in _POLICY_RE.finditer(path.read_text()):
            body = m.group("body").lower()
            table = m.group("table").lower()
            if table in PUBLIC_POLICY_ALLOWLIST:
                continue
            to_match = re.search(r"\bto\s+([\w,\s]+?)(?:\busing\b|\bwith\b|$)", body)
            roles = {r.strip() for r in to_match.group(1).split(",")} if to_match else {"public"}
            broad_roles = roles & {"anon", "public", "authenticated"}
            wide_open = re.search(r"using\s*\(\s*true\s*\)", body)
            if broad_roles and wide_open:
                violations.append(f"{path.name}: {m.group('name')} ON {table} TO {sorted(broad_roles)}")
    assert not violations, (
        "USING(true) policies granted to anon/public/authenticated — this is "
        "the exact shape of the PR #198 incident (tenant data readable with "
        "the public key):\n  " + "\n  ".join(violations)
    )


def test_no_grants_to_anon_on_sensitive_tables():
    """Migrations must not GRANT on sensitive tables to anon."""
    sensitive = {
        "phone_agent_config", "phone_orders", "phone_call_logs",
        "leads", "us_leads", "business_users", "checkout_sessions",
        "sales_rep_commissions", "email_send_log",
    }
    grant_re = re.compile(
        r"grant\s+[\w,\s]+\s+on\s+(?:table\s+)?\"?(?:public\.)?(\w+)\"?\s+to\s+([\w,\s]+);",
        re.IGNORECASE,
    )
    violations = []
    for path in MIGRATIONS:
        for m in grant_re.finditer(path.read_text()):
            table, roles = m.group(1).lower(), m.group(2).lower()
            if table in sensitive and "anon" in roles:
                violations.append(f"{path.name}: GRANT ON {table} TO {roles.strip()}")
    assert not violations, (
        "GRANT to anon on sensitive tables:\n  " + "\n  ".join(violations)
    )
