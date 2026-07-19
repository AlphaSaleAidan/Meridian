"""
Multi-Location Hub — Workstream 5 (Command tier).

RED-first tests pinning the four security/isolation invariants from the spec
(docs/multi-location-hub-journey.md §7):

  1. Membership isolation — an identity sees ONLY orgs it is a member of.
  2. Org-switch re-scoping — switching to org B never validates against org A's
     data; a jump to a non-member org is denied (no A<->B leakage).
  3. Command-tier server-side gate — a non-Command org gets 403; tier resolves
     from the org record / locked billing contract, never the body.
  4. Push-down ownership filter — a push applies ONLY to selected branches the
     identity owns/administers; unowned targets are dropped.

Plus the tier resolver's pure predicate and the aggregation math.

Run:  python -m pytest tests/test_multi_location_hub.py -v
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.billing import tiers  # noqa: E402
from src.api import hub_service  # noqa: E402

aio = pytest.mark.asyncio


class MockDB:
    """Table-keyed fixture db. `select` filters by user_id/org_id/merchant_id so
    isolation is actually exercised (not just canned). Records upserts."""

    def __init__(self, tables: dict | None = None):
        self.tables = tables or {}
        self.upserts: list[tuple] = []
        # per-org stat fixtures for the aggregation path
        self.daily = {}          # org_id -> list[dict]
        self.phone_orders = {}   # org_id -> list[dict]
        self.phone_calls = {}    # org_id -> list[dict]

    @staticmethod
    def _match(row: dict, filters: dict | None) -> bool:
        if not filters:
            return True
        for k, v in filters.items():
            if k == "select":
                continue
            if isinstance(v, str) and v.startswith("eq."):
                want = v[3:]
                have = row.get(k)
                if want == "true":
                    if have is not True:
                        return False
                elif want == "false":
                    if have is not False:
                        return False
                elif str(have) != want:
                    return False
            elif isinstance(v, str) and v.startswith("in.("):
                allowed = v[len("in.("):-1].split(",")
                if str(row.get(k)) not in allowed:
                    return False
            elif isinstance(v, str) and v == "is.null":
                if row.get(k) is not None:
                    return False
        return True

    async def select(self, table, columns="*", filters=None, order=None,
                     limit=None, offset=None):
        rows = [r for r in self.tables.get(table, []) if self._match(r, filters)]
        if limit:
            rows = rows[:limit]
        return [dict(r) for r in rows]

    async def upsert(self, table, data, on_conflict="", return_data=True):
        self.upserts.append((table, dict(data), on_conflict))
        self.tables.setdefault(table, [])
        # emulate conflict-merge on the conflict keys
        keys = [k.strip() for k in on_conflict.split(",")] if on_conflict else []
        if keys:
            for r in self.tables[table]:
                if all(r.get(k) == data.get(k) for k in keys):
                    r.update(data)
                    return [dict(r)]
        self.tables[table].append(dict(data))
        return [dict(data)]

    async def get_daily_revenue(self, org_id, days=30):
        return self.daily.get(org_id, [])

    async def get_phone_orders(self, org_id, days=30, limit=500):
        return self.phone_orders.get(org_id, [])

    async def get_phone_call_logs(self, org_id, days=30, limit=500):
        return self.phone_calls.get(org_id, [])


# ── 0. Tier resolver pure predicate ──────────────────────────────────────────


def test_command_predicate_enterprise_account_tier():
    # businesses.plan_tier == 'enterprise' (sales `command` maps here) = Command
    assert tiers._is_command_value("enterprise", None) is True


def test_command_predicate_billing_command_tier():
    # locked contract plan_tier == 'command' = Command, even if account tier lags
    assert tiers._is_command_value("growth", "command") is True


def test_command_predicate_non_command_is_false():
    assert tiers._is_command_value("growth", "premium") is False
    assert tiers._is_command_value("starter", None) is False
    assert tiers._is_command_value(None, None) is False


@aio
async def test_resolver_fails_closed_on_non_command():
    db = MockDB(tables={
        "businesses": [{"id": "biz_A", "plan_tier": "growth"}],
        "merchant_billing_terms": [{"merchant_id": "biz_A", "plan_tier": "premium"}],
    })
    assert (await tiers.resolve_org_command_tier(db, "biz_A")) is False


@aio
async def test_resolver_true_for_enterprise():
    db = MockDB(tables={"businesses": [{"id": "biz_A", "plan_tier": "enterprise"}]})
    assert (await tiers.resolve_org_command_tier(db, "biz_A")) is True


# ── 1. Membership isolation ──────────────────────────────────────────────────


@aio
async def test_identity_sees_only_own_orgs():
    db = MockDB(tables={
        "identity_org_memberships": [
            {"user_id": "u1", "org_id": "biz_A", "role": "owner", "is_owner": True, "is_active": True},
            {"user_id": "u1", "org_id": "biz_B", "role": "manager", "is_owner": False, "is_active": True},
            {"user_id": "u2", "org_id": "biz_C", "role": "owner", "is_owner": True, "is_active": True},
        ],
        "businesses": [
            {"id": "biz_A", "name": "Alpha", "plan_tier": "enterprise", "status": "active"},
            {"id": "biz_B", "name": "Beta", "plan_tier": "growth", "status": "active"},
            {"id": "biz_C", "name": "Gamma", "plan_tier": "enterprise", "status": "active"},
        ],
    })
    orgs = await hub_service.list_identity_orgs(db, "u1")
    got = {o["org_id"] for o in orgs}
    assert got == {"biz_A", "biz_B"}          # u1's orgs only
    assert "biz_C" not in got                  # u2's org NOT visible


# ── 2. Org-switch re-scoping (no A<->B leakage) ──────────────────────────────


@aio
async def test_switch_to_member_org_ok():
    db = MockDB(tables={
        "identity_org_memberships": [
            {"user_id": "u1", "org_id": "biz_A", "role": "owner", "is_owner": True, "is_active": True},
        ],
    })
    res = await hub_service.assert_org_switchable(db, "u1", "biz_A")
    assert res["org_id"] == "biz_A"


@aio
async def test_switch_to_non_member_org_denied():
    # u1 is a member of biz_A only. Attempting to jump to biz_C (u2's) must be
    # denied — the switch can never re-scope to another tenant.
    db = MockDB(tables={
        "identity_org_memberships": [
            {"user_id": "u1", "org_id": "biz_A", "role": "owner", "is_owner": True, "is_active": True},
            {"user_id": "u2", "org_id": "biz_C", "role": "owner", "is_owner": True, "is_active": True},
        ],
    })
    with pytest.raises(PermissionError):
        await hub_service.assert_org_switchable(db, "u1", "biz_C")


@aio
async def test_connect_requires_provable_control():
    # Body claims biz_C but u1 doesn't own it and has no business_users row →
    # PermissionError, and NOTHING is written (no self-granted membership).
    db = MockDB(tables={
        "businesses": [{"id": "biz_C", "owner_user_id": "u2"}],
        "business_users": [],
    })
    with pytest.raises(PermissionError):
        await hub_service.verify_and_link_org(db, "u1", "biz_C")
    assert db.upserts == []


@aio
async def test_connect_owner_links_and_records_owner_role():
    db = MockDB(tables={
        "businesses": [{"id": "biz_A", "owner_user_id": "u1"}],
        "business_users": [],
    })
    res = await hub_service.verify_and_link_org(db, "u1", "biz_A")
    assert res["is_owner"] is True and res["role"] == "owner"
    assert any(t == "identity_org_memberships" for (t, _, _) in db.upserts)


# ── 3. Command-tier server-side gate ─────────────────────────────────────────


@aio
async def test_hub_gate_403_for_non_command(monkeypatch):
    import src.api.routes.hub as hub
    db = MockDB(tables={
        "businesses": [{"id": "biz_A", "owner_user_id": "u1", "plan_tier": "growth"}],
        "business_users": [],
        "identity_org_memberships": [],
    })
    monkeypatch.setattr(hub, "get_db", lambda: db)
    user = {"id": "u1", "email": "owner@example.com"}
    with pytest.raises(Exception) as e:
        await hub.require_command_hub(org_id="biz_A", user=user)
    assert "403" in str(e.value) or "Command" in str(e.value)


@aio
async def test_hub_gate_allows_command_owner(monkeypatch):
    import src.api.routes.hub as hub
    db = MockDB(tables={
        "businesses": [{"id": "biz_A", "owner_user_id": "u1", "plan_tier": "enterprise"}],
        "business_users": [],
        "identity_org_memberships": [],
    })
    monkeypatch.setattr(hub, "get_db", lambda: db)
    user = {"id": "u1", "email": "owner@example.com"}
    ctx = await hub.require_command_hub(org_id="biz_A", user=user)
    assert ctx["user_id"] == "u1" and ctx["hub_org_id"] == "biz_A"


@aio
async def test_hub_gate_403_for_non_member_even_if_command(monkeypatch):
    # biz_A is Command tier but belongs to u2; u1 must still get 403.
    import src.api.routes.hub as hub
    db = MockDB(tables={
        "businesses": [{"id": "biz_A", "owner_user_id": "u2", "plan_tier": "enterprise"}],
        "business_users": [],
        "identity_org_memberships": [],
    })
    monkeypatch.setattr(hub, "get_db", lambda: db)
    user = {"id": "u1", "email": "intruder@example.com"}
    with pytest.raises(Exception) as e:
        await hub.require_command_hub(org_id="biz_A", user=user)
    assert "403" in str(e.value) or "member" in str(e.value)


# ── 4. Push-down ownership filter ────────────────────────────────────────────


@aio
async def test_push_down_applies_only_to_owned_branches():
    # u1 owns biz_A (owner) and administers biz_B (admin); biz_C belongs to u2.
    db = MockDB(tables={
        "identity_org_memberships": [
            {"user_id": "u1", "org_id": "biz_A", "role": "owner", "is_active": True},
            {"user_id": "u1", "org_id": "biz_B", "role": "admin", "is_active": True},
            {"user_id": "u1", "org_id": "biz_D", "role": "viewer", "is_active": True},
            {"user_id": "u2", "org_id": "biz_C", "role": "owner", "is_active": True},
        ],
    })
    res = await hub_service.push_down(
        db, "u1", "chatbot_config",
        payload={"greeting": "Welcome to the franchise!"},
        target_org_ids=["biz_A", "biz_B", "biz_C", "biz_D"],
    )
    by_org = {r["org_id"]: r["status"] for r in res["results"]}
    assert by_org["biz_A"] == "applied"            # owner
    assert by_org["biz_B"] == "applied"            # admin
    assert by_org["biz_C"] == "skipped_not_owned"  # not u1's org
    assert by_org["biz_D"] == "skipped_not_owned"  # viewer cannot push
    # only the two owned branches were written
    written = {d["merchant_id"] for (t, d, _) in db.upserts if t == "phone_agent_config"}
    assert written == {"biz_A", "biz_B"}


@aio
async def test_push_down_fee_respects_command_floor():
    db = MockDB(tables={
        "identity_org_memberships": [
            {"user_id": "u1", "org_id": "biz_A", "role": "owner", "is_active": True},
        ],
    })
    res = await hub_service.push_down(
        db, "u1", "phone_fee_override",
        payload={"order_fee_cents": 10},          # below Command floor of 45
        target_org_ids=["biz_A"],
    )
    assert res["results"][0]["status"] == "error"
    assert db.upserts == []                         # nothing written below floor


@aio
async def test_push_down_stub_type_reports_not_implemented():
    db = MockDB(tables={
        "identity_org_memberships": [
            {"user_id": "u1", "org_id": "biz_A", "role": "owner", "is_active": True},
        ],
    })
    res = await hub_service.push_down(
        db, "u1", "schedule_template", payload={}, target_org_ids=["biz_A"],
    )
    assert res["results"][0]["status"] == "not_implemented"


@aio
async def test_push_down_unknown_type_raises():
    db = MockDB(tables={})
    with pytest.raises(ValueError):
        await hub_service.push_down(db, "u1", "bogus", payload={}, target_org_ids=["biz_A"])


# ── Aggregation math (unified overview) ──────────────────────────────────────


@aio
async def test_overview_aggregates_across_owned_orgs_only():
    db = MockDB(tables={
        "identity_org_memberships": [
            {"user_id": "u1", "org_id": "biz_A", "role": "owner", "is_owner": True, "is_active": True},
            {"user_id": "u1", "org_id": "biz_B", "role": "manager", "is_owner": False, "is_active": True},
            {"user_id": "u2", "org_id": "biz_C", "role": "owner", "is_owner": True, "is_active": True},
        ],
        "businesses": [
            {"id": "biz_A", "name": "Alpha", "plan_tier": "enterprise", "status": "active"},
            {"id": "biz_B", "name": "Beta", "plan_tier": "growth", "status": "active"},
            {"id": "biz_C", "name": "Gamma", "plan_tier": "enterprise", "status": "active"},
        ],
    })
    db.daily = {
        "biz_A": [{"total_revenue_cents": 1000, "transaction_count": 5}],
        "biz_B": [{"total_revenue_cents": 500, "transaction_count": 2}],
        "biz_C": [{"total_revenue_cents": 99999, "transaction_count": 999}],  # u2 — must NOT count
    }
    db.phone_calls = {"biz_A": [{}, {}], "biz_B": [{}], "biz_C": [{}] * 50}

    ov = await hub_service.aggregate_overview(db, "u1", days=30)
    assert ov["location_count"] == 2
    assert ov["totals"]["revenue_cents"] == 1500          # A + B only, NOT C
    assert ov["totals"]["transaction_count"] == 7
    assert ov["totals"]["phone_call_count"] == 3
    got = {loc["org_id"] for loc in ov["locations"]}
    assert got == {"biz_A", "biz_B"}
