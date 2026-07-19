"""Sales-hierarchy scoping — the BACKEND control plane (independent of RLS).

7-level org tree on sales_reps (role + manager_id + materialized `path` of
dot-joined rep ids). This module resolves the caller's scope and filters any
rep-keyed rows to their subtree. It deliberately does NOT delegate to RLS:
even if a policy regresses (this portal's history: 20260511, 20260522,
20260603 wide-open policies), endpoints that route their rows through these
helpers still enforce the downline boundary. Conversely the RLS plane
(supabase/migrations/20260716_sales_hierarchy.sql) holds if a backend caller
forgets these helpers. Two planes, independent failure modes.

Tested red-first by tests/rls/test_hierarchy_isolation.py.
"""
from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass

from fastapi import Depends, HTTPException

from .auth import ADMIN_EMAILS, require_jwt

logger = logging.getLogger("meridian.api.hierarchy")

_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)

# Rank 1 outranks 7. A manager must strictly outrank their report.
ROLE_LEVELS: dict[str, int] = {
    "admin": 1,
    "vp_sales": 2,
    "regional_manager": 3,
    "district_manager": 4,
    "office_manager": 5,
    "assistant_manager": 6,
    "sales_rep": 7,
}

# Columns that may not exist until the 20260716 migration is applied; every
# fetch falls back to the legacy column set so the API never 500s pre-apply
# (it fails CLOSED: no role/path -> self-only scope).
_HIER_COLS = "id,name,email,role,manager_id,path,level,is_active,portal_context,created_at"
_LEGACY_COLS = "id,name,email,is_active,portal_context,created_at"


@dataclass(frozen=True)
class RepScope:
    rep_id: str | None
    role: str
    path: str | None
    is_admin: bool


def _supabase_env() -> tuple[str, str]:
    url = os.environ.get("SUPABASE_URL", "")
    key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        or os.environ.get("SUPABASE_SERVICE_KEY", "")
    )
    return url, key


async def _service_get(params: dict) -> list[dict]:
    """GET /rest/v1/sales_reps with the service key (scope resolution must not
    itself depend on RLS — it IS the independent plane). Fail closed on error."""
    import httpx

    url, key = _supabase_env()
    if not url or not key:
        return []
    headers = {"Authorization": f"Bearer {key}", "apikey": key}
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(f"{url}/rest/v1/sales_reps", headers=headers, params=params)
            if resp.status_code == 200:
                return resp.json()
            # Pre-migration prod: unknown column -> retry with legacy columns.
            if "select" in params and params["select"] != _LEGACY_COLS:
                resp = await client.get(
                    f"{url}/rest/v1/sales_reps",
                    headers=headers,
                    params={**params, "select": _LEGACY_COLS},
                )
                if resp.status_code == 200:
                    return resp.json()
            logger.warning("hierarchy: sales_reps fetch failed: %s %s", resp.status_code, resp.text[:200])
    except Exception as exc:  # noqa: BLE001 — fail closed, never 500 the caller
        logger.warning("hierarchy: sales_reps fetch error: %s", exc)
    return []


async def _fetch_rep_by_email(email: str) -> dict | None:
    """Test seam: caller's sales_reps row (or None).

    SECURITY: match case-insensitively but EXACTLY. PostgREST `ilike` treats `_`
    and `%` as wildcards, and reps self-signup with an attacker-chosen email
    (`/rep-signup`), so a plain `ilike.<email>` + `rows[0]` would let someone who
    registers `a_min@corp.com` bind their session to `admin@corp.com`'s
    role/path — a privilege escalation, since resolve_scope derives is_admin
    from this row. So we ilike-FETCH then narrow to an exact lowercased compare
    (same pattern as commissions/billing/commission_engine).
    """
    if not email:
        return None
    target = email.strip().lower()
    rows = await _service_get({"email": f"ilike.{email.strip()}", "select": _HIER_COLS, "limit": "20"})
    return next((r for r in (rows or []) if (r.get("email") or "").strip().lower() == target), None)


async def _fetch_reps_under(path: str) -> list[dict]:
    """Test seam: all reps whose path is `path` or a descendant of it."""
    rows = await _service_get({"or": f"(path.eq.{path},path.like.{path}.*)", "select": _HIER_COLS})
    if rows:
        return rows
    # PostgREST `like` uses * wildcards; keep a plain fallback for exotic paths.
    return []


async def resolve_scope(user: dict) -> RepScope:
    """Resolve (role, path) for a JWT user. Admin = role=='admin' OR the email
    allowlist (belt-and-suspenders — the allowlist is NOT removed)."""
    email = (user.get("email") or "").lower()
    allowlisted = email in [e.lower() for e in ADMIN_EMAILS]
    row = await _fetch_rep_by_email(email)
    if not row:
        # No rep row: allowlisted admins keep access; everyone else fails closed.
        return RepScope(rep_id=None, role="admin" if allowlisted else "sales_rep",
                        path=None, is_admin=allowlisted)
    role = row.get("role") or "sales_rep"
    return RepScope(
        rep_id=row.get("id"),
        role=role,
        path=row.get("path"),
        is_admin=(role == "admin" or allowlisted),
    )


async def visible_rep_ids(scope: RepScope) -> set[str] | None:
    """Rep ids whose rows/leads the caller may see.

    None  -> unrestricted (admin)
    set() -> nothing assigned (unknown session; fail closed)
    """
    if scope.is_admin:
        return None
    if not scope.rep_id:
        return set()
    if scope.role == "sales_rep" or not scope.path:
        # Leaf rep, or hierarchy columns not yet migrated: self only (fail closed).
        return {scope.rep_id}
    reps = await _fetch_reps_under(scope.path)
    ids = {r["id"] for r in reps if r.get("id")}
    ids.add(scope.rep_id)
    return ids


def scope_lead_rows(rows: list[dict], allowed: set[str] | None) -> list[dict]:
    """Filter rep-keyed lead rows to the allowed set. Unassigned (rep_id NULL)
    stays visible — matches the RLS plane."""
    if allowed is None:
        return rows
    return [r for r in rows if r.get("rep_id") is None or r.get("rep_id") in allowed]


def scope_roster_rows(rows: list[dict], scope: RepScope, allowed: set[str] | None) -> list[dict]:
    """Filter roster (sales_reps) rows: subtree + the caller's upline chain
    (manager names), never lateral branches. Matches the RLS roster policy."""
    if allowed is None:
        return rows
    keep = set(allowed)
    if scope.path:
        keep |= set(scope.path.split("."))  # path segments ARE the upline ids
    if scope.rep_id:
        keep.add(scope.rep_id)
    return [r for r in rows if r.get("id") in keep]


# ── Role management guards ────────────────────────────────────────────────────


async def require_org_admin(user: dict = Depends(require_jwt)) -> dict:
    """Admin gate for org-tree writes: role=='admin' (DB) OR ADMIN_EMAILS
    allowlist. The allowlist stays as belt-and-suspenders, not the only check."""
    scope = await resolve_scope(user)
    if not scope.is_admin:
        logger.warning("org-admin access denied for %s (role=%s)", user.get("email"), scope.role)
        raise HTTPException(403, "Admin access required")
    return user


def check_assignment(new_role: str, rep_id: str, manager: dict | None) -> None:
    """Validate a role/manager assignment. Raises HTTPException(400) on:
    unknown role, manager not outranking the assignee, or a cycle (the new
    manager's path already contains the assignee). The DB trigger re-checks the
    cycle independently."""
    if new_role not in ROLE_LEVELS:
        raise HTTPException(400, f"Unknown role '{new_role}'")
    if manager is None:
        return
    manager_role = manager.get("role") or "sales_rep"
    if ROLE_LEVELS.get(manager_role, 99) >= ROLE_LEVELS[new_role]:
        raise HTTPException(
            400,
            f"Manager role '{manager_role}' does not outrank assignee role '{new_role}'",
        )
    manager_path = manager.get("path") or ""
    if rep_id and (manager.get("id") == rep_id or f".{manager_path}.".find(f".{rep_id}.") >= 0):
        raise HTTPException(400, "Cycle: the chosen manager is already in this rep's downline")


def validate_uuid(value: str, field: str = "id") -> None:
    if not value or not _UUID_RE.match(value):
        raise HTTPException(400, f"Invalid {field} format")


def build_tree(reps: list[dict], root_ids: set[str] | None = None) -> list[dict]:
    """Nest a flat rep list into a forest ordered by role rank then name."""
    by_id = {r["id"]: {**r, "direct_reports": []} for r in reps if r.get("id")}
    roots: list[dict] = []
    for node in by_id.values():
        parent = by_id.get(node.get("manager_id") or "")
        if parent is not None and (root_ids is None or node["id"] not in root_ids):
            parent["direct_reports"].append(node)
        else:
            roots.append(node)

    def _sort(nodes: list[dict]) -> None:
        nodes.sort(key=lambda n: (ROLE_LEVELS.get(n.get("role") or "sales_rep", 99),
                                  (n.get("name") or "").lower()))
        for n in nodes:
            _sort(n["direct_reports"])

    _sort(roots)
    return roots
