"""
Cancel → reclaim the phone number to the pool for reassignment, and don't serve
a cancelled/inactive merchant's calls.

  release_to_pool: unassigns the DID from the merchant (clears phone_number +
  active=false), returns the number to the pool available (upsert-or-insert so
  live-bought numbers with no pool row are covered), and KEEPS the Telnyx DID +
  Vapi binding so a new merchant can be handed the same number.

  vapi_webhook inactive gate: a positively-resolved real merchant with
  active=False gets the "not active" assistant (no orders); the demo fallback
  (active=True) is never gated.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("ENCRYPTION_KEY", "0" * 64)

import src.services.number_pool as npool  # noqa: E402

aio = pytest.mark.asyncio


class _DB:
    def __init__(self, config=None, pool=None):
        self.config = config or []
        self.pool = pool or []
        self.updates = []
        self.inserts = []

    async def select(self, table, cols=None, filters=None, order=None, limit=None):
        if table == "phone_agent_config":
            return list(self.config)
        if table == "phone_number_pool":
            num = (filters or {}).get("phone_number", "").replace("eq.", "")
            return [r for r in self.pool if r.get("phone_number") == num][:1]
        return []

    async def update(self, table, patch, filters=None):
        self.updates.append((table, patch, filters))
        if table == "phone_number_pool":
            rid = (filters or {}).get("id", "").replace("eq.", "")
            for r in self.pool:
                if r.get("id") == rid:
                    r.update(patch)
        if table == "phone_agent_config":
            for r in self.config:
                r.update(patch)
        return [patch]

    async def insert(self, table, payload):
        self.inserts.append((table, payload))
        if table == "phone_number_pool":
            self.pool.append({**payload, "id": f"p{len(self.pool)}"})
        return [payload]


@aio
async def test_reclaim_existing_pool_row_goes_available_and_config_cleared():
    db = _DB(
        config=[{"merchant_id": "biz_x", "phone_number": "+1500", "active": True,
                 "vapi_phone_number_id": "v1", "phone_number_sid": "o1"}],
        pool=[{"id": "p0", "phone_number": "+1500", "status": "assigned",
               "assigned_merchant_id": "biz_x"}])
    out = await npool.release_to_pool(db, "biz_x")

    assert out["phone_number"] == "+1500"
    assert db.pool[0]["status"] == "available"
    assert db.pool[0]["assigned_merchant_id"] is None
    # merchant config: number cleared + agent off
    cfg = db.config[0]
    assert cfg["phone_number"] is None and cfg["active"] is False
    assert cfg["vapi_phone_number_id"] is None


@aio
async def test_reclaim_live_bought_number_inserts_pool_row():
    # merchant had a live-bought number that never had a pool row
    db = _DB(
        config=[{"merchant_id": "biz_y", "phone_number": "+1777", "active": True,
                 "vapi_phone_number_id": "v9", "phone_number_sid": "o9"}],
        pool=[])
    out = await npool.release_to_pool(db, "biz_y")

    assert out["phone_number"] == "+1777"
    assert len(db.pool) == 1
    row = db.pool[0]
    assert row["status"] == "available" and row["phone_number"] == "+1777"
    assert row["vapi_phone_number_id"] == "v9"  # binding preserved for reassignment


@aio
async def test_reclaim_noop_when_no_number():
    db = _DB(config=[{"merchant_id": "biz_z", "phone_number": None, "active": False}])
    assert await npool.release_to_pool(db, "biz_z") is None
    assert db.inserts == [] and db.pool == []


@aio
async def test_reclaim_noop_when_no_config():
    db = _DB(config=[])
    assert await npool.release_to_pool(db, "biz_missing") is None


# ── vapi_webhook inactive gate ────────────────────────────────
def _cfg(merchant_id, active):
    from types import SimpleNamespace
    return SimpleNamespace(merchant_id=merchant_id, active=active, voice="", business_name="X")


def test_inactive_gate_logic():
    """Mirror the gate predicate: real merchant + active False → gated; demo or
    active True → not gated."""
    def gated(cfg):
        mid = getattr(cfg, "merchant_id", "") or ""
        return bool(mid and mid != "demo" and getattr(cfg, "active", True) is False)

    assert gated(_cfg("biz_x", False)) is True        # cancelled real merchant
    assert gated(_cfg("biz_x", True)) is False         # active merchant
    assert gated(_cfg("demo", False)) is False         # demo never gated
    assert gated(_cfg("", False)) is False             # unresolved never gated
