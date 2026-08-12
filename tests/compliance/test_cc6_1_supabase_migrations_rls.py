"""
CC6.1 — Row-level security: the ACTIVE supabase/migrations/ set must not leave any
sensitive table cross-tenant/anon readable after a fresh `supabase db push`.

WHY THIS FILE EXISTS (separate from test_cc6_1_rls_migrations.py):
  test_cc6_1_rls_migrations.py scans the LEGACY top-level `migrations/` directory.
  The live schema is built from `supabase/migrations/` — a different, larger set that
  the legacy test never sees. This file closes that blind spot for the specific
  wide-open exposures called out in the SOC 2 REMEDIATION-MAP (DB-1/DB-2/DB-3 and the
  vision R1 config-drift), by computing the NET end-state of the ordered migration
  set (policies created minus dropped) rather than grepping single files.

Model: policies are applied in filename (== chronological) order. A later
DROP POLICY removes an earlier CREATE; a later CREATE with the same name replaces it.
The test asserts the surviving policy set contains no `USING(true)` policy that
applies to a broad role (anon/public/authenticated) on the sensitive tables, and
that the intended scoped/authenticated read policies survive.
"""
import re
from pathlib import Path

CONTROL = "CC6.1"

SUPABASE_MIGRATIONS = sorted(
    (Path(__file__).resolve().parents[2] / "supabase" / "migrations").glob("*.sql")
)

# Tables that carried the "Service role full access ... USING(true)" boilerplate and
# hold tenant data or PII.
#
# Security model after the full migration set is applied:
#   * anon / public USING(true) -> NEVER allowed on ANY sensitive table (the public
#     anon-key exposure vector). This is the hard invariant.
#   * authenticated USING(true) -> allowed ONLY on the two tables the logged-in Space
#     tab reads directly via the Supabase client (spaces, space_zones). Every other
#     sensitive table is backend-only (service_role) and must NOT expose an
#     authenticated read policy.
SENSITIVE_TABLES = {
    # DB-1 (already fixed on main by 20260628_fix_phone_schedule_rls_anon_exposure.sql)
    "phone_agent_config", "phone_call_logs", "phone_orders",
    "schedule_staff", "schedule_shifts", "published_schedules",
    # DB-2 / DB-3 (fixed by 20260719_fix_wideopen_rls_email_spaces.sql)
    "email_send_log", "space_processing_jobs", "spaces", "space_zones",
    # Vision R1 config-drift (fixed by 20260719_vision_rls_backport_wideopen_drop.sql)
    "vision_cameras", "vision_traffic", "vision_visitors", "vision_visits",
    # SR auto dialer (20260812_autodialer.sql) — rep/lead PII: scoped authenticated
    # SELECT only (realtime), service_role writes; dialer_dnc backend-only.
    "dialer_sessions", "dialer_calls", "dialer_callbacks", "dialer_dnc",
}

# The only sensitive tables where an `authenticated USING(true)` read policy is
# intentional (logged-in Space tab, verified in frontend/src/lib/spaces-service.ts).
AUTHENTICATED_READ_ALLOWED = {"spaces", "space_zones"}

# CREATE POLICY <name> ON <table> <body-up-to-semicolon>
_CREATE_POLICY_RE = re.compile(
    r"create\s+policy\s+\"?(?P<name>[\w .-]+?)\"?\s+on\s+\"?(?:public\.)?(?P<table>\w+)\"?"
    r"(?P<body>.*?);",
    re.IGNORECASE | re.DOTALL,
)
# DROP POLICY [IF EXISTS] <name> ON <table>
_DROP_POLICY_RE = re.compile(
    r"drop\s+policy\s+(?:if\s+exists\s+)?\"?(?P<name>[\w .-]+?)\"?\s+on\s+\"?(?:public\.)?(?P<table>\w+)\"?",
    re.IGNORECASE,
)


def _roles_of(body: str) -> set[str]:
    """Roles a policy applies to. No TO clause => {public}."""
    to_match = re.search(r"\bto\s+([\w,\s]+?)(?:\busing\b|\bwith\b|\bfor\b|$)", body, re.IGNORECASE)
    if not to_match:
        return {"public"}
    return {r.strip().lower() for r in to_match.group(1).split(",") if r.strip()}


def _is_wide_open(body: str) -> bool:
    return bool(re.search(r"using\s*\(\s*true\s*\)", body, re.IGNORECASE))


def _resolve_final_policies() -> dict[tuple[str, str], dict]:
    """
    Replay CREATE/DROP POLICY across the ordered migration set (skipping SQL comment
    lines and rollback blocks) and return the surviving policies keyed by
    (table, policy_name).
    """
    surviving: dict[tuple[str, str], dict] = {}
    for path in SUPABASE_MIGRATIONS:
        # Strip -- comment lines so commented rollback blocks are ignored.
        raw = path.read_text()
        active = "\n".join(
            line for line in raw.splitlines() if not line.lstrip().startswith("--")
        )
        # Interleave create/drop in source order.
        events = []
        for m in _CREATE_POLICY_RE.finditer(active):
            events.append((m.start(), "create", m))
        for m in _DROP_POLICY_RE.finditer(active):
            events.append((m.start(), "drop", m))
        for _, kind, m in sorted(events, key=lambda e: e[0]):
            table = m.group("table").lower()
            name = m.group("name").strip().lower()
            key = (table, name)
            if kind == "drop":
                surviving.pop(key, None)
            else:
                body = m.group("body")
                surviving[key] = {
                    "file": path.name,
                    "table": table,
                    "name": name,
                    "roles": _roles_of(body),
                    "wide_open": _is_wide_open(body),
                }
    return surviving


def test_supabase_migrations_present():
    assert SUPABASE_MIGRATIONS, "supabase/migrations/ is empty — nothing to verify"


def test_no_surviving_anon_wideopen_policy_on_sensitive_tables():
    """
    HARD INVARIANT: after the full ordered migration set is applied, NO sensitive table
    may retain a USING(true) policy reachable by anon or public. This is the exact shape
    of the anon-key exposure (DB-1/DB-2/DB-3) and the vision cross-tenant drift.
    """
    anon_public = {"anon", "public"}
    violations = []
    for info in _resolve_final_policies().values():
        if info["table"] not in SENSITIVE_TABLES:
            continue
        if info["wide_open"] and (info["roles"] & anon_public):
            violations.append(
                f"{info['file']}: policy '{info['name']}' ON {info['table']} "
                f"TO {sorted(info['roles'] & anon_public)} USING(true)"
            )
    assert not violations, (
        "Surviving USING(true) policies reachable by anon/public on sensitive tables "
        "after the full migration set — tenant data readable with the public anon key:\n  "
        + "\n  ".join(sorted(violations))
    )


def test_no_authenticated_wideopen_on_backend_only_tables():
    """
    Backend-only sensitive tables (everything except the Space-tab tables) must NOT
    expose an `authenticated USING(true)` read policy — reads go through the service_role
    backend, so a logged-in user must not be able to read them directly.
    """
    violations = []
    for info in _resolve_final_policies().values():
        table = info["table"]
        if table not in SENSITIVE_TABLES or table in AUTHENTICATED_READ_ALLOWED:
            continue
        if info["wide_open"] and "authenticated" in info["roles"]:
            violations.append(
                f"{info['file']}: policy '{info['name']}' ON {table} "
                f"TO authenticated USING(true)"
            )
    assert not violations, (
        "authenticated USING(true) read policy on a backend-only sensitive table — a "
        "logged-in user could read all tenants' rows directly:\n  "
        + "\n  ".join(sorted(violations))
    )


def test_spaces_authenticated_read_path_preserved():
    """
    The logged-in Space tab reads spaces/space_zones via the Supabase client. The fix
    must PRESERVE that path (explicit authenticated SELECT policy) — regression guard
    against the 42501 incident where tightening RLS broke a live user-JWT path.
    """
    final = _resolve_final_policies()
    for table in ("spaces", "space_zones"):
        # An authenticated SELECT policy must survive for this table.
        auth_policies = [
            info for info in final.values()
            if info["table"] == table and "authenticated" in info["roles"]
        ]
        assert auth_policies, (
            f"{table}: no surviving authenticated read policy — the logged-in Space tab "
            f"would lose read access (grant/RLS regression risk)."
        )


def test_vision_member_isolation_survives():
    """
    Vision tables must end up with the membership-scoped read policy (not wide-open,
    not the dead auth.uid() policy). Proves the R1 backport codifies live prod scoping.
    """
    final = _resolve_final_policies()
    for table in ("vision_cameras", "vision_traffic", "vision_visitors", "vision_visits"):
        iso = [
            info for info in final.values()
            if info["table"] == table and info["name"].endswith("_member_isolation")
        ]
        assert iso, (
            f"{table}: no surviving *_member_isolation policy — org scoping not codified "
            f"in migrations; a fresh db push could leave the table cross-tenant readable."
        )
        # And it must NOT be wide-open.
        for info in iso:
            assert not info["wide_open"], (
                f"{table}: member_isolation policy is USING(true) — not actually scoped."
            )
