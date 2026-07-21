"""
Telnyx→Vapi number binding + pool (all-Telnyx, no Twilio).

Layers:
  1. vapi_provisioning.import_telnyx_number: gates on VAPI_PRIVATE_KEY +
     VAPI_TELNYX_CREDENTIAL_ID, sends provider=telnyx + credentialId + dynamic
     server (no static assistant), never raises on network/HTTP errors.
  2. number_pool.buy_into_pool / claim_from_pool: buy+bind ahead of time,
     rollback on partial failure, atomic claim.
  3. provision_number: claims a ready pool number first (instant); on an empty
     pool it live-buys at Telnyx + binds to Vapi, releasing + 502-ing if the
     bind fails (never a dead line).
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
os.environ.setdefault("ENCRYPTION_KEY", "0" * 64)

import src.services.vapi_provisioning as vp  # noqa: E402
import src.services.number_pool as npool  # noqa: E402
from src.api.routes import phone_dashboard as pd  # noqa: E402

aio = pytest.mark.asyncio


class _Resp:
    def __init__(self, status, data=None, text=""):
        self.status_code = status
        self._d = data if data is not None else {}
        self.text = text or ""

    def json(self):
        return self._d


class _Client:
    def __init__(self, *, post=None):
        self._post = post
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, json=None, headers=None):
        self.calls.append(("POST", url, json, headers))
        return self._post


# ─── client: Telnyx import ────────────────────────────────────
@aio
async def test_telnyx_import_noops_without_credential(monkeypatch):
    monkeypatch.setenv("VAPI_PRIVATE_KEY", "vk")
    monkeypatch.delenv("VAPI_TELNYX_CREDENTIAL_ID", raising=False)
    assert vp.vapi_telnyx_enabled() is False
    assert await vp.import_telnyx_number("+15551230000") is None


@aio
async def test_telnyx_import_sends_provider_credential_and_dynamic_server(monkeypatch):
    monkeypatch.setenv("VAPI_PRIVATE_KEY", "vk")
    monkeypatch.setenv("VAPI_TELNYX_CREDENTIAL_ID", "cred_123")
    monkeypatch.setenv("VAPI_SERVER_SECRET", "shh")
    monkeypatch.setenv("MEDIA_STREAM_HOST", "api.meridian.tips")
    client = _Client(post=_Resp(201, {"id": "vapi_ph_9"}))
    monkeypatch.setattr(vp.httpx, "AsyncClient", lambda timeout=None: client)

    out = await vp.import_telnyx_number("+15551230000", name="Thai Place")
    assert out == "vapi_ph_9"
    _, url, body, headers = client.calls[0]
    assert url.endswith("/phone-number")
    assert body["provider"] == "telnyx"
    assert body["number"] == "+15551230000"
    assert body["credentialId"] == "cred_123"
    assert body["server"]["url"] == "https://api.meridian.tips/api/vapi/webhook"
    assert body["server"]["secret"] == "shh"
    assert "assistantId" not in body
    assert headers["Authorization"] == "Bearer vk"


@aio
async def test_telnyx_import_returns_none_on_http_error(monkeypatch):
    monkeypatch.setenv("VAPI_PRIVATE_KEY", "vk")
    monkeypatch.setenv("VAPI_TELNYX_CREDENTIAL_ID", "cred_123")
    monkeypatch.setattr(vp.httpx, "AsyncClient",
                        lambda timeout=None: _Client(post=_Resp(400, {}, "bad")))
    assert await vp.import_telnyx_number("+15551230000") is None


# ─── pool ─────────────────────────────────────────────────────
class _PoolDB:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.inserted = []
        self.updated = []

    async def select(self, table, cols=None, filters=None, order=None, limit=None):
        st = (filters or {}).get("status", "").replace("eq.", "")
        rows = [r for r in self.rows if r.get("status") == st] if st else list(self.rows)
        return rows[:limit] if limit else rows

    async def insert(self, table, payload):
        self.inserted.append(payload)
        self.rows.append({**payload, "id": f"row{len(self.rows)}"})
        return [payload]

    async def update(self, table, patch, filters=None):
        rid = (filters or {}).get("id", "").replace("eq.", "")
        want_status = (filters or {}).get("status", "").replace("eq.", "")
        for r in self.rows:
            if r.get("id") == rid and (not want_status or r.get("status") == want_status):
                r.update(patch)
                self.updated.append((rid, patch))
                return [r]
        return []


def _patch_telnyx(monkeypatch, *, search_seq, import_result="vapi_x", release_sink=None):
    it = iter(search_seq)
    async def fake_search(country, area): return next(it, None)
    async def fake_purchase(number): return {"phone_number": number, "sid": "ord"}
    async def fake_import(number, name=""):
        return import_result(number) if callable(import_result) else import_result
    async def fake_release(number, sid):
        if release_sink is not None:
            release_sink.append(number)
        return True
    monkeypatch.setattr("src.api.routes.phone_dashboard._telnyx_search", fake_search)
    monkeypatch.setattr("src.api.routes.phone_dashboard._telnyx_purchase", fake_purchase)
    monkeypatch.setattr("src.api.routes.phone_dashboard._telnyx_release", fake_release)
    monkeypatch.setattr("src.services.vapi_provisioning.import_telnyx_number", fake_import)
    monkeypatch.setattr("src.services.vapi_provisioning.vapi_telnyx_enabled", lambda: True)


@aio
async def test_buy_into_pool_buys_binds_and_records(monkeypatch):
    db = _PoolDB()
    monkeypatch.setattr("src.db.get_db", lambda: db, raising=False)
    _patch_telnyx(monkeypatch,
                  search_seq=["+15068017376", "+15068017672", "+15068018168"],
                  import_result=lambda n: "vapi_" + n[-4:])

    res = await npool.buy_into_pool(3, country="CA")
    assert res["added"] == 3 and res["failed"] == 0
    assert len(db.inserted) == 3
    assert all(r["status"] == "available" and r["provider"] == "telnyx"
               and r["vapi_phone_number_id"] for r in db.inserted)


@aio
async def test_buy_into_pool_rolls_back_on_bind_failure(monkeypatch):
    db = _PoolDB()
    monkeypatch.setattr("src.db.get_db", lambda: db, raising=False)
    released = []
    _patch_telnyx(monkeypatch, search_seq=["+15068017376"],
                  import_result=None, release_sink=released)

    res = await npool.buy_into_pool(1)
    assert res["added"] == 0 and res["failed"] == 1
    assert released == ["+15068017376"]
    assert db.inserted == []


@aio
async def test_claim_from_pool_is_atomic(monkeypatch):
    db = _PoolDB(rows=[
        {"id": "row0", "status": "available", "phone_number": "+1500",
         "provider_sid": "o0", "vapi_phone_number_id": "v0", "created_at": "1"},
    ])
    claimed = await npool.claim_from_pool(db, "biz_abc")
    assert claimed["phone_number"] == "+1500"
    assert db.rows[0]["status"] == "assigned"
    assert db.rows[0]["assigned_merchant_id"] == "biz_abc"
    assert await npool.claim_from_pool(db, "biz_xyz") is None


# ─── provision_number: pool-first then live buy ───────────────
class _ConfigDB(_PoolDB):
    def __init__(self, pool_rows=None, config_rows=None):
        super().__init__(rows=pool_rows or [])
        self.config = config_rows or []

    async def select(self, table, cols=None, filters=None, order=None, limit=None):
        if table == "phone_agent_config":
            return list(self.config)
        return await super().select(table, cols, filters, order, limit)

    async def insert(self, table, payload):
        if table == "phone_agent_config":
            self.config.append(payload)
            return [payload]
        return await super().insert(table, payload)

    async def update(self, table, patch, filters=None):
        if table == "phone_agent_config":
            self.config_updated = patch
            return [patch]
        return await super().update(table, patch, filters)


def _wire_provision(monkeypatch, db):
    async def ok(principal, mid): return None
    monkeypatch.setattr(pd, "enforce_service_member", ok)
    monkeypatch.setattr(pd, "get_db", lambda: db)
    monkeypatch.setattr(pd, "TELNYX_API_KEY", "tk")
    monkeypatch.setattr("src.services.number_pool.get_db", lambda: db, raising=False)


@aio
async def test_provision_claims_from_pool_first(monkeypatch):
    db = _ConfigDB(
        pool_rows=[{"id": "row0", "status": "available", "phone_number": "+1POOL",
                    "provider_sid": "o0", "vapi_phone_number_id": "vpool", "created_at": "1"}],
        config_rows=[])
    _wire_provision(monkeypatch, db)

    req = pd.ProvisionNumberRequest(merchant_id="biz_" + "a" * 16)
    out = await pd.provision_number(req, principal={"kind": "service"})

    assert out["from_pool"] is True and out["phone_number"] == "+1POOL"
    assert out["vapi_bound"] is True
    assert db.rows[0]["status"] == "assigned"


@aio
async def test_provision_live_buys_when_pool_empty(monkeypatch):
    db = _ConfigDB(pool_rows=[], config_rows=[])
    _wire_provision(monkeypatch, db)
    monkeypatch.setattr(pd, "vapi_telnyx_enabled", lambda: True)
    async def fake_search(c, a): return "+15068017376"
    async def fake_purchase(n): return {"phone_number": n, "sid": "ord_live"}
    async def fake_import(n, name=""): return "vapi_live"
    monkeypatch.setattr(pd, "_telnyx_search", fake_search)
    monkeypatch.setattr(pd, "_telnyx_purchase", fake_purchase)
    monkeypatch.setattr(pd, "import_telnyx_number", fake_import)

    req = pd.ProvisionNumberRequest(merchant_id="biz_" + "b" * 16)
    out = await pd.provision_number(req, principal={"kind": "service"})

    assert out["from_pool"] is False
    assert out["phone_number"] == "+15068017376" and out["vapi_bound"] is True


@aio
async def test_provision_releases_and_502s_on_bind_failure(monkeypatch):
    db = _ConfigDB(pool_rows=[], config_rows=[])
    _wire_provision(monkeypatch, db)
    monkeypatch.setattr(pd, "vapi_telnyx_enabled", lambda: True)
    released = []
    async def fake_search(c, a): return "+15068017376"
    async def fake_purchase(n): return {"phone_number": n, "sid": "ord_live"}
    async def fake_import(n, name=""): return None
    async def fake_release(n, sid):
        released.append(n)
        return True
    monkeypatch.setattr(pd, "_telnyx_search", fake_search)
    monkeypatch.setattr(pd, "_telnyx_purchase", fake_purchase)
    monkeypatch.setattr(pd, "import_telnyx_number", fake_import)
    monkeypatch.setattr(pd, "_telnyx_release", fake_release)

    req = pd.ProvisionNumberRequest(merchant_id="biz_" + "c" * 16)
    with pytest.raises(pd.HTTPException) as exc:
        await pd.provision_number(req, principal={"kind": "service"})
    assert exc.value.status_code == 502
    assert released == ["+15068017376"]
    assert db.config == []
