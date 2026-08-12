"""Peer-visible aggregate Leaderboard.

  GET /api/leaderboard → ALL active reps in the caller's portal_context, with
                         ONLY leaderboard-safe fields.

Why this exists: the 20260716 hierarchy scoping (#334 — RLS `reps_select_scoped`
+ backend `scope_roster_rows`) correctly scopes ROSTER DATA to self + downline
+ upline. But the portal Leaderboard tab rendered from that same scoped roster,
so a leaf rep saw a board of one. Leaderboards are peer-visible by nature;
sensitive data is not. The split:

  * Roster / Team Management (emails, phones, commission rates, lead rows)
    stays on the scoped endpoints (/api/canada/team, /api/us/team) — unchanged.
  * The board comes from HERE: a service-role query (the scoped RLS plane would
    collapse the board again), safe because of the RESPONSE SHAPE, not row
    filtering. Exposed per rep: id, name, role, deals_won, deals_open,
    total_mrr. NO emails, NO phones, NO lead rows, NO commission details.

Aggregation is one reps fetch + one leads fetch per portal table (grouped
in-process by rep_id) — never a per-rep N+1.

Tested by tests/api/test_leaderboard.py.
"""
from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Depends, HTTPException

from .. import hierarchy
from ..auth import ADMIN_EMAILS, require_jwt

logger = logging.getLogger("meridian.api.leaderboard")

router = APIRouter(prefix="/api/leaderboard", tags=["leaderboard"])

# Stage buckets mirror the portal UI (computeTeamStats in the Team pages):
# won = signed MRR counts toward the board; open = live pipeline; closed_lost
# counts toward neither.
WON_STAGES = frozenset({"customer_walkthrough", "pos_connected", "closed_won"})
LOST_STAGE = "closed_lost"

# portal_context → (sales_reps filter, leads tables to aggregate)
_PORTAL_REPS_FILTER = {"canada": "in.(canada,all)", "us": "in.(us,all)"}
_PORTAL_LEAD_TABLES = {"canada": ("canada_leads",), "us": ("us_leads",)}
_ALL_LEAD_TABLES = ("canada_leads", "us_leads")

# Explicit field allowlist — serialization is the security boundary here, so
# the response is built ONLY from these keys (tested: no email/phone ever).
_REPS_COLS = "id,name,role,portal_context,is_active,region"
_REPS_COLS_NO_REGION = "id,name,role,portal_context,is_active"  # pre-20260812 (no region column)
_REPS_COLS_LEGACY = "id,name,portal_context,is_active"  # pre-20260716 (no role column)
_LEADS_COLS = "rep_id,stage,monthly_value"


def _service_env() -> tuple[str, str]:
    url = os.environ.get("SUPABASE_URL", "")
    key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        or os.environ.get("SUPABASE_SERVICE_KEY", "")
    )
    return url, key


async def _resolve_portal(user: dict) -> tuple[str | None, str | None, str | None]:
    """(portal_context, caller rep_id, caller region). 403 for sessions with no
    rep profile — the board is for reps, and an unknown session must fail
    closed."""
    email = (user.get("email") or "").lower()
    caller = await hierarchy._fetch_rep_by_email(email)
    if caller:
        return (
            (caller.get("portal_context") or "all"),
            caller.get("id"),
            (caller.get("region") or None),
        )
    if email in [e.lower() for e in ADMIN_EMAILS]:
        # Allowlisted admin without a rep row: cross-portal board.
        return "all", None, None
    raise HTTPException(403, "No sales rep profile for this account")


@router.get("")
async def get_leaderboard(user: dict = Depends(require_jwt)):
    """Aggregate board for the caller's portal. Requires a valid rep JWT."""
    import httpx

    portal, caller_rep_id, caller_region = await _resolve_portal(user)

    # Region members (20260812) have no leaderboard — their territory opted
    # out (Odyssey). Return an explicitly-disabled empty board rather than a
    # board of strangers; the portal hides the tab, this is the backstop.
    if caller_region:
        return {
            "leaderboard": [],
            "disabled": True,
            "portal": portal,
            "viewer": {"rep_id": caller_rep_id, "region": caller_region},
        }

    supabase_url, service_key = _service_env()
    if not supabase_url or not service_key:
        raise HTTPException(503, "Supabase not configured")
    headers = {"Authorization": f"Bearer {service_key}", "apikey": service_key}

    reps_params: dict[str, str] = {"select": _REPS_COLS, "is_active": "eq.true"}
    reps_filter = _PORTAL_REPS_FILTER.get(portal or "")
    if reps_filter:
        reps_params["portal_context"] = reps_filter
    lead_tables = _PORTAL_LEAD_TABLES.get(portal or "", _ALL_LEAD_TABLES)

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{supabase_url}/rest/v1/sales_reps", headers=headers, params=reps_params
        )
        if resp.status_code != 200:
            # Pre-20260812 prod: region column unknown → drop it.
            resp = await client.get(
                f"{supabase_url}/rest/v1/sales_reps",
                headers=headers,
                params={**reps_params, "select": _REPS_COLS_NO_REGION},
            )
        if resp.status_code != 200:
            # Pre-20260716 prod: role column unknown → legacy column set.
            resp = await client.get(
                f"{supabase_url}/rest/v1/sales_reps",
                headers=headers,
                params={**reps_params, "select": _REPS_COLS_LEGACY},
            )
        if resp.status_code != 200:
            logger.error("leaderboard: reps fetch failed: %s %s", resp.status_code, resp.text[:200])
            raise HTTPException(503, "Leaderboard temporarily unavailable")
        rep_rows = resp.json()

        # One aggregate pass per portal leads table (rep_id GROUP BY done
        # in-process; PostgREST aggregates are not enabled on this project).
        lead_rows: list[dict] = []
        for table in lead_tables:
            lresp = await client.get(
                f"{supabase_url}/rest/v1/{table}",
                headers=headers,
                params={"select": _LEADS_COLS, "rep_id": "not.is.null"},
            )
            if lresp.status_code == 200:
                lead_rows.extend(lresp.json())
            else:
                logger.warning(
                    "leaderboard: %s fetch failed: %s %s", table, lresp.status_code, lresp.text[:200]
                )

    stats: dict[str, dict[str, int]] = {}
    for row in lead_rows:
        rep_id = row.get("rep_id")
        if not rep_id:
            continue
        agg = stats.setdefault(rep_id, {"deals_won": 0, "deals_open": 0, "total_mrr": 0})
        stage = row.get("stage") or ""
        if stage in WON_STAGES:
            agg["deals_won"] += 1
            agg["total_mrr"] += round(float(row.get("monthly_value") or 0))
        elif stage != LOST_STAGE:
            agg["deals_open"] += 1

    board = []
    for rep in rep_rows:
        rep_id = rep.get("id")
        if not rep_id:
            continue
        # Region members never appear on the portal board (their territory is
        # walled off; Odyssey additionally has boards disabled outright).
        if rep.get("region"):
            continue
        agg = stats.get(rep_id, {"deals_won": 0, "deals_open": 0, "total_mrr": 0})
        # Allowlist serialization — never spread the DB row into the response.
        board.append({
            "id": rep_id,
            "name": rep.get("name") or "",
            "role": rep.get("role") or "sales_rep",
            "deals_won": agg["deals_won"],
            "deals_open": agg["deals_open"],
            "total_mrr": agg["total_mrr"],
        })

    board.sort(key=lambda r: (-r["total_mrr"], -r["deals_won"], r["name"].lower()))
    return {
        "leaderboard": board,
        "portal": portal,
        "viewer": {"rep_id": caller_rep_id},
    }
