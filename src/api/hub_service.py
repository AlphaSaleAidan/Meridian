"""
Multi-Location Hub — service layer (framework-independent, unit-testable).

Owns the hub's core logic so the route (src/api/routes/hub.py) stays a thin
HTTP shell:

  - list_identity_orgs        which orgs an identity belongs to (switcher)
  - verify_and_link_org       connect: prove membership, upsert the hub edge
  - assert_org_switchable     jump: validate the identity may switch to org
  - aggregate_overview        unified stats across the identity's orgs
  - push_down                 deploy a config change to selected OWNED branches

Every function derives the acting identity's org set from the SESSION identity
(user_id), never from a caller-supplied list. `org_id` inputs are validated
against that set before anything is read or written — no cross-org leakage.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

logger = logging.getLogger("meridian.hub")

# ── Push-down config-type registry (extensible pattern) ──────────────────────
# Each handler: async (db, org_id, payload) -> None (raises on failure).
# Register a new config type here + add its id to the frontend push-down form.


async def _push_phone_fee_override(db, org_id: str, payload: dict) -> None:
    """Set the per-order Meridian fee override on a branch's phone_agent_config.

    Respects the Command floor (45¢) — a value below the floor is rejected so a
    push can never drop a branch below its tier redline.
    """
    cents = payload.get("order_fee_cents")
    if cents is None or not isinstance(cents, int) or cents < 0:
        raise ValueError("order_fee_cents must be a non-negative integer")
    COMMAND_FEE_FLOOR_CENTS = 45
    if cents < COMMAND_FEE_FLOOR_CENTS:
        raise ValueError(f"order_fee_cents {cents} below Command floor {COMMAND_FEE_FLOOR_CENTS}")
    await db.upsert(
        "phone_agent_config",
        {"merchant_id": org_id, "order_fee_cents": cents, "updated_at": _now_iso()},
        on_conflict="merchant_id",
    )


async def _push_chatbot_config(db, org_id: str, payload: dict) -> None:
    """Set the phone/website agent greeting (chatbot config) on a branch."""
    greeting = payload.get("greeting")
    if not isinstance(greeting, str) or not greeting.strip():
        raise ValueError("greeting must be a non-empty string")
    row = {"merchant_id": org_id, "greeting": greeting.strip(), "updated_at": _now_iso()}
    # Optional voice/language passthrough when supplied.
    if isinstance(payload.get("voice"), str) and payload["voice"].strip():
        row["voice"] = payload["voice"].strip()
    if isinstance(payload.get("language"), str) and payload["language"].strip():
        row["language"] = payload["language"].strip()
    await db.upsert("phone_agent_config", row, on_conflict="merchant_id")


async def _push_not_implemented(db, org_id: str, payload: dict) -> None:
    raise NotImplementedError("config type registered but not wired in v1")


# config_type -> handler. Stubbed types raise NotImplementedError so the shared
# endpoint reports them per-branch instead of silently no-oping.
PUSH_DOWN_HANDLERS = {
    "phone_fee_override": _push_phone_fee_override,   # wired
    "chatbot_config": _push_chatbot_config,           # wired
    "pricing_table": _push_not_implemented,           # stub
    "schedule_template": _push_not_implemented,       # stub
    "phone_agent_voice": _push_not_implemented,       # stub
}

# Hub roles allowed to push config down to a branch.
_PUSH_ROLES = {"owner", "admin"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Membership resolution ────────────────────────────────────────────────────


async def list_identity_orgs(db, user_id: str) -> list[dict]:
    """Return the orgs the identity belongs to, for the hub switcher.

    Source of truth = identity_org_memberships (active rows for THIS user_id),
    joined to businesses for display. The membership rows are written only after
    server-side verification, and RLS restricts SELECT to the caller's own rows,
    so this can never surface another identity's orgs.
    """
    if not user_id:
        return []
    memberships = await db.select(
        "identity_org_memberships",
        columns="org_id,role,is_owner",
        filters={"user_id": f"eq.{user_id}", "is_active": "eq.true"},
    )
    if not memberships:
        return []

    by_org = {m["org_id"]: m for m in memberships if m.get("org_id")}
    org_ids = list(by_org.keys())
    if not org_ids:
        return []

    # PostgREST in.(a,b,c) filter for the display join.
    in_filter = "in.(" + ",".join(org_ids) + ")"
    bizrows = await db.select(
        "businesses",
        columns="id,name,plan_tier,status,business_type",
        filters={"id": in_filter},
    )
    biz_by_id = {b["id"]: b for b in bizrows}

    out = []
    for oid, m in by_org.items():
        b = biz_by_id.get(oid, {})
        out.append({
            "org_id": oid,
            "name": b.get("name", ""),
            "plan_tier": b.get("plan_tier"),
            "status": b.get("status"),
            "role": m.get("role"),
            "is_owner": bool(m.get("is_owner")),
        })
    out.sort(key=lambda r: (not r["is_owner"], r["name"].lower()))
    return out


async def _identity_controls_org(db, user_id: str, org_id: str) -> tuple[bool, bool]:
    """Independently verify the identity controls the org (NOT from any body list).

    Returns (controls, is_owner):
      - owner:  businesses.owner_user_id == user_id
      - member: active business_users row (user_id, business_id, is_active)
    """
    if not user_id or not org_id:
        return (False, False)
    owner = await db.select(
        "businesses",
        columns="id",
        filters={"id": f"eq.{org_id}", "owner_user_id": f"eq.{user_id}"},
        limit=1,
    )
    if owner:
        return (True, True)
    member = await db.select(
        "business_users",
        columns="user_id",
        filters={
            "business_id": f"eq.{org_id}",
            "user_id": f"eq.{user_id}",
            "is_active": "eq.true",
        },
        limit=1,
    )
    return (bool(member), False)


async def verify_and_link_org(db, user_id: str, org_id: str) -> dict:
    """CONNECT: prove the identity controls org_id, then upsert the hub edge.

    The org_id comes from the request body but the identity comes from the
    session; we NEVER trust the body's claim of ownership — we re-derive it from
    businesses.owner_user_id / business_users. If the identity doesn't control
    the org, we raise PermissionError and write nothing.
    """
    controls, is_owner = await _identity_controls_org(db, user_id, org_id)
    if not controls:
        raise PermissionError("identity is not a member/owner of this org")

    role = "owner" if is_owner else "manager"
    await db.upsert(
        "identity_org_memberships",
        {
            "user_id": user_id,
            "org_id": org_id,
            "role": role,
            "is_owner": is_owner,
            "is_active": True,
            "connected_at": _now_iso(),
        },
        on_conflict="user_id,org_id",
    )
    return {"org_id": org_id, "role": role, "is_owner": is_owner, "linked": True}


async def assert_org_switchable(db, user_id: str, org_id: str) -> dict:
    """JUMP: validate the identity may switch to org_id.

    Membership is checked against the identity's OWN membership rows. Switching
    to an org the identity is not a member of raises PermissionError — so a jump
    can never re-scope the session to another tenant's data.
    """
    if not org_id:
        raise ValueError("org_id required")
    rows = await db.select(
        "identity_org_memberships",
        columns="org_id,role,is_owner",
        filters={
            "user_id": f"eq.{user_id}",
            "org_id": f"eq.{org_id}",
            "is_active": "eq.true",
        },
        limit=1,
    )
    if not rows:
        raise PermissionError("identity is not a member of the target org")
    m = rows[0]
    return {"org_id": org_id, "role": m.get("role"), "is_owner": bool(m.get("is_owner"))}


# ── Unified overview ─────────────────────────────────────────────────────────


async def aggregate_overview(db, user_id: str, days: int = 30) -> dict:
    """Aggregate stats across ALL orgs the identity belongs to.

    Reuses the existing per-org stat queries and sums/compares across the
    identity's own orgs only. The org list comes from list_identity_orgs (session
    identity), never a caller-supplied list.
    """
    orgs = await list_identity_orgs(db, user_id)
    per_location = []
    total_revenue = 0
    total_orders = 0
    total_calls = 0

    for org in orgs:
        oid = org["org_id"]
        daily = await db.get_daily_revenue(oid, days=days)
        rev = sum((r.get("total_revenue_cents") or 0) for r in daily)
        txns = sum((r.get("transaction_count") or 0) for r in daily)

        phone_orders = await db.get_phone_orders(oid, days=days)
        call_logs = await db.get_phone_call_logs(oid, days=days)
        n_phone_orders = len(phone_orders or [])
        n_calls = len(call_logs or [])

        total_revenue += rev
        total_orders += txns
        total_calls += n_calls

        per_location.append({
            "org_id": oid,
            "name": org.get("name", ""),
            "plan_tier": org.get("plan_tier"),
            "revenue_cents": rev,
            "transaction_count": txns,
            "phone_order_count": n_phone_orders,
            "phone_call_count": n_calls,
        })

    per_location.sort(key=lambda r: r["revenue_cents"], reverse=True)
    return {
        "window_days": days,
        "location_count": len(orgs),
        "totals": {
            "revenue_cents": total_revenue,
            "transaction_count": total_orders,
            "phone_call_count": total_calls,
        },
        "locations": per_location,
    }


# ── Franchise push-down ──────────────────────────────────────────────────────


async def push_down(
    db,
    user_id: str,
    config_type: str,
    payload: dict,
    target_org_ids: list[str],
) -> dict:
    """Deploy a config change to SELECTED branches the identity owns/administers.

    - config_type must be a registered PUSH_DOWN_HANDLERS key.
    - target_org_ids is filtered to only orgs the identity has an active
      owner/admin membership for (from identity_org_memberships). Unowned targets
      are dropped as 'skipped_not_owned' — never applied.
    - Each surviving target gets a per-branch result so the UI can show a
      per-branch confirmation.
    """
    handler = PUSH_DOWN_HANDLERS.get(config_type)
    if handler is None:
        raise ValueError(f"unknown config_type: {config_type}")
    if not target_org_ids:
        return {"config_type": config_type, "results": []}

    # The identity's OWN administerable orgs (owner/admin role, active).
    memberships = await db.select(
        "identity_org_memberships",
        columns="org_id,role",
        filters={"user_id": f"eq.{user_id}", "is_active": "eq.true"},
    )
    admin_orgs = {
        m["org_id"] for m in (memberships or [])
        if m.get("org_id") and (m.get("role") in _PUSH_ROLES)
    }

    results = []
    for oid in target_org_ids:
        if oid not in admin_orgs:
            results.append({"org_id": oid, "status": "skipped_not_owned"})
            continue
        try:
            await handler(db, oid, payload)
            results.append({"org_id": oid, "status": "applied"})
        except NotImplementedError:
            results.append({"org_id": oid, "status": "not_implemented"})
        except Exception as exc:  # noqa: BLE001 — per-branch failure isolation
            logger.warning("push-down %s failed for org=%s: %s", config_type, oid, exc)
            results.append({"org_id": oid, "status": "error", "detail": str(exc)})

    return {"config_type": config_type, "results": results}
