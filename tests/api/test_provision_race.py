"""
Provision-number double-buy race guard.

The historical hole: two concurrent /provision-number calls for the SAME
merchant both read `existing=None`, both buy/claim a DID, and the loser's
number leaks — paid monthly at Telnyx, Vapi-bound, referenced by nothing.

Two layers under test:

1. In-process per-merchant lock: concurrent calls serialize, so the second
   sees the winner's number and returns idempotently (no second buy).
2. Cross-worker/instance safety in _store_provisioned_number_atomic: the
   fresh-provision write is conditional (phone_number is.null / merchant_id
   UNIQUE), the loser returns False, and _lost_race_response unwinds — a pool
   claim flips back to available, a live buy is released at Vapi + Telnyx.

Run:  python -m pytest tests/api/test_provision_race.py -v
"""
from __future__ import annotations

import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.api.routes import phone_dashboard as pd  # noqa: E402


# ── fake Supabase REST layer (only the semantics the code under test uses) ──

class FakeDB:
    def __init__(self):
        self.tables: dict[str, list[dict]] = {"phone_agent_config": [],
                                              "phone_number_pool": []}

    @staticmethod
    def _matches(row: dict, filters: dict[str, str]) -> bool:
        for col, cond in filters.items():
            if cond == "is.null":
                if row.get(col) is not None:
                    return False
            elif cond.startswith("eq."):
                if str(row.get(col)) != cond[3:]:
                    return False
            else:  # pragma: no cover — unsupported filter = test bug
                raise AssertionError(f"unsupported filter {col}={cond}")
        return True

    async def select(self, table, filters=None, limit=None, order=None):
        rows = [r for r in self.tables[table] if self._matches(r, filters or {})]
        return rows[:limit] if limit else rows

    async def update(self, table, data, filters):
        updated = []
        for row in self.tables[table]:
            if self._matches(row, filters):
                row.update(data)
                updated.append(dict(row))
        return updated

    async def insert(self, table, data):
        if table == "phone_agent_config":
            # merchant_id TEXT NOT NULL UNIQUE (migration 20260629)
            if any(r.get("merchant_id") == data.get("merchant_id")
                   for r in self.tables[table]):
                raise RuntimeError("duplicate key value violates unique "
                                   "constraint phone_agent_config_merchant_id_key")
        self.tables[table].append(dict(data))
        return [dict(data)]


def _payload(number: str) -> dict:
    return {"phone_number": number, "phone_number_sid": f"sid-{number}",
            "vapi_phone_number_id": f"vapi-{number}", "updated_at": "2026-07-27T00:00:00Z"}


# ── 1. atomic store: update path ─────────────────────────────────────

@pytest.mark.asyncio
async def test_atomic_update_second_writer_loses():
    db = FakeDB()
    db.tables["phone_agent_config"].append(
        {"merchant_id": "m1", "phone_number": None})
    assert await pd._store_provisioned_number_atomic(
        db, "m1", True, _payload("+15550001111"), require_unassigned=True) is True
    # The row is now assigned — a racing second writer must NOT overwrite.
    assert await pd._store_provisioned_number_atomic(
        db, "m1", True, _payload("+15550002222"), require_unassigned=True) is False
    assert db.tables["phone_agent_config"][0]["phone_number"] == "+15550001111"


@pytest.mark.asyncio
async def test_atomic_insert_second_writer_loses():
    db = FakeDB()
    assert await pd._store_provisioned_number_atomic(
        db, "m2", False, _payload("+15550001111"), require_unassigned=True) is True
    assert await pd._store_provisioned_number_atomic(
        db, "m2", False, _payload("+15550002222"), require_unassigned=True) is False
    rows = db.tables["phone_agent_config"]
    assert len(rows) == 1 and rows[0]["phone_number"] == "+15550001111"


@pytest.mark.asyncio
async def test_force_swap_still_overwrites():
    """require_unassigned=False (explicit swap) keeps legacy overwrite behavior."""
    db = FakeDB()
    db.tables["phone_agent_config"].append(
        {"merchant_id": "m3", "phone_number": "+15550001111"})
    assert await pd._store_provisioned_number_atomic(
        db, "m3", True, _payload("+15550009999"), require_unassigned=False) is True
    assert db.tables["phone_agent_config"][0]["phone_number"] == "+15550009999"


# ── 2. lost-race unwind ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_lost_race_pool_claim_returned_to_pool():
    db = FakeDB()
    db.tables["phone_agent_config"].append(
        {"merchant_id": "m4", "phone_number": "+15550001111"})   # the winner
    db.tables["phone_number_pool"].append(
        {"id": 1, "phone_number": "+15550002222", "status": "assigned",
         "assigned_merchant_id": "m4", "assigned_at": "x"})       # our lost claim
    resp = await pd._lost_race_response(
        db, "m4", "+15550002222", "sid", "vapi-id", from_pool=True)
    assert resp == {"phone_number": "+15550001111", "provisioned": False,
                    "already_existed": True}
    pool_row = db.tables["phone_number_pool"][0]
    assert pool_row["status"] == "available"
    assert pool_row["assigned_merchant_id"] is None


@pytest.mark.asyncio
async def test_lost_race_live_buy_released(monkeypatch):
    released, deleted = [], []

    async def fake_release(number, sid):
        released.append((number, sid))
        return True

    async def fake_delete(vapi_id):
        deleted.append(vapi_id)
        return True

    monkeypatch.setattr(pd, "_telnyx_release", fake_release)
    monkeypatch.setattr(pd, "delete_vapi_number", fake_delete)
    db = FakeDB()
    db.tables["phone_agent_config"].append(
        {"merchant_id": "m5", "phone_number": "+15550001111"})
    resp = await pd._lost_race_response(
        db, "m5", "+15550003333", "sid-3", "vapi-3", from_pool=False)
    assert resp["phone_number"] == "+15550001111"
    assert released == [("+15550003333", "sid-3")]
    assert deleted == ["vapi-3"]


# ── 3. in-process lock: concurrent endpoint calls never double-buy ───

@pytest.mark.asyncio
async def test_concurrent_provision_single_claim(monkeypatch):
    db = FakeDB()
    db.tables["phone_number_pool"] = [
        {"id": 1, "phone_number": "+15068000001", "provider_sid": "s1",
         "vapi_phone_number_id": "v1", "status": "available"},
        {"id": 2, "phone_number": "+15068000002", "provider_sid": "s2",
         "vapi_phone_number_id": "v2", "status": "available"},
    ]

    async def fake_enforce(principal, merchant_id):
        return None

    from src.services import number_pool
    real_claim = number_pool.claim_from_pool
    claims = []

    async def slow_claim(db_, merchant_id):
        # Widen the race window: both requests would be inside the buy section
        # together if the per-merchant lock didn't serialize them.
        await asyncio.sleep(0.05)
        row = await real_claim(db_, merchant_id)
        claims.append(row)
        return row

    monkeypatch.setattr(pd, "get_db", lambda: db)
    monkeypatch.setattr(pd, "enforce_service_member", fake_enforce)
    monkeypatch.setattr(pd, "_validate_merchant_id", lambda m: None)
    monkeypatch.setattr(pd, "TELNYX_API_KEY", "test-key")
    monkeypatch.setattr(number_pool, "claim_from_pool", slow_claim)

    req = pd.ProvisionNumberRequest(merchant_id="m-race")
    r1, r2 = await asyncio.gather(
        pd.provision_number(req, principal=None),
        pd.provision_number(req, principal=None),
    )
    results = sorted([r1, r2], key=lambda r: not r["provisioned"])
    assert results[0]["provisioned"] is True
    assert results[1] == {"phone_number": results[0]["phone_number"],
                          "provisioned": False, "already_existed": True}
    # Exactly ONE pool claim consumed; the second call short-circuited on the
    # existing number (idempotent path) without touching the pool.
    assert len(claims) == 1
    available = [r for r in db.tables["phone_number_pool"]
                 if r["status"] == "available"]
    assert len(available) == 1
