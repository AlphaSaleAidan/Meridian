"""
Vapi phone-number binding — the fix that makes a provisioned DID actually ring
the agent.

Two layers:
  1. vapi_provisioning client: import/delete/list gate on VAPI_PRIVATE_KEY,
     send the right body (server URL + secret, no static assistant), and never
     raise on network/HTTP errors.
  2. provision_number wiring: when binding is enabled, a purchased Twilio number
     is imported into Vapi and its id stored; a FAILED import releases the
     Twilio number and 502s (never strands a paid, dead line); a swap releases
     the old Vapi binding.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
os.environ.setdefault("ENCRYPTION_KEY", "0" * 64)

import src.services.vapi_provisioning as vp  # noqa: E402
from src.api.routes import phone_dashboard as pd  # noqa: E402

aio = pytest.mark.asyncio


# ─── fake httpx ───────────────────────────────────────────────
class _Resp:
    def __init__(self, status, data=None, text=""):
        self.status_code = status
        self._d = data if data is not None else {}
        self.text = text or ""

    def json(self):
        return self._d


class _Client:
    def __init__(self, *, post=None, delete=None, get=None):
        self._post, self._delete, self._get = post, delete, get
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, json=None, headers=None):
        self.calls.append(("POST", url, json, headers))
        return self._post

    async def delete(self, url, headers=None):
        self.calls.append(("DELETE", url, headers))
        return self._delete

    async def get(self, url, headers=None):
        self.calls.append(("GET", url, headers))
        return self._get


def _patch_httpx(monkeypatch, client):
    monkeypatch.setattr(vp.httpx, "AsyncClient", lambda timeout=None: client)
    return client


# ─── client: gating ───────────────────────────────────────────
@aio
async def test_import_noops_without_key(monkeypatch):
    monkeypatch.delenv("VAPI_PRIVATE_KEY", raising=False)
    assert vp.vapi_binding_enabled() is False
    res = await vp.import_twilio_number("+15551230000", twilio_account_sid="AC",
                                        twilio_auth_token="tok")
    assert res is None


@aio
async def test_import_sends_dynamic_server_body_and_returns_id(monkeypatch):
    monkeypatch.setenv("VAPI_PRIVATE_KEY", "vk_test")
    monkeypatch.setenv("VAPI_SERVER_SECRET", "shh")
    monkeypatch.setenv("MEDIA_STREAM_HOST", "api.meridian.tips")
    client = _patch_httpx(monkeypatch, _Client(post=_Resp(201, {"id": "vapi_ph_1"})))
    res = await vp.import_twilio_number("+15551230000", twilio_account_sid="AC123",
                                        twilio_auth_token="tok", name="Thai Place")
    assert res == "vapi_ph_1"
    _, url, body, headers = client.calls[0]
    assert url.endswith("/phone-number")
    assert body["provider"] == "twilio"
    assert body["number"] == "+15551230000"
    assert body["twilioAccountSid"] == "AC123"
    # dynamic routing: server URL + secret, NO static assistant
    assert body["server"]["url"] == "https://api.meridian.tips/api/vapi/webhook"
    assert body["server"]["secret"] == "shh"
    assert "assistantId" not in body and "squadId" not in body
    assert headers["Authorization"] == "Bearer vk_test"


@aio
async def test_import_returns_none_on_http_error(monkeypatch):
    monkeypatch.setenv("VAPI_PRIVATE_KEY", "vk_test")
    _patch_httpx(monkeypatch, _Client(post=_Resp(400, {}, "bad number")))
    res = await vp.import_twilio_number("+15551230000", twilio_account_sid="AC",
                                        twilio_auth_token="tok")
    assert res is None


@aio
async def test_import_returns_none_on_network_error(monkeypatch):
    monkeypatch.setenv("VAPI_PRIVATE_KEY", "vk_test")

    class _Boom(_Client):
        async def post(self, *a, **k):
            raise vp.httpx.ConnectError("down")
    _patch_httpx(monkeypatch, _Boom(post=None))
    res = await vp.import_twilio_number("+1555", twilio_account_sid="AC",
                                        twilio_auth_token="tok")
    assert res is None


@aio
async def test_delete_true_on_2xx_and_404(monkeypatch):
    monkeypatch.setenv("VAPI_PRIVATE_KEY", "vk_test")
    _patch_httpx(monkeypatch, _Client(delete=_Resp(200)))
    assert await vp.delete_vapi_number("vapi_ph_1") is True
    _patch_httpx(monkeypatch, _Client(delete=_Resp(404)))
    assert await vp.delete_vapi_number("gone") is True
    _patch_httpx(monkeypatch, _Client(delete=_Resp(500, {}, "err")))
    assert await vp.delete_vapi_number("x") is False


# ─── provision_number wiring ──────────────────────────────────
class _FakeDB:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.updated = []
        self.inserted = []

    async def select(self, table, filters=None, limit=None):
        return list(self.rows)

    async def update(self, table, payload, filters=None):
        self.updated.append(payload)
        return [payload]

    async def insert(self, table, payload):
        self.inserted.append(payload)
        return [payload]


def _wire_provision(monkeypatch, db, *, purchase_sid="SID_NEW",
                    import_result="vapi_ph_new", released=None):
    monkeypatch.setattr(pd, "PHONE_PROVIDER", "twilio")
    monkeypatch.setattr(pd, "TWILIO_SID", "AC_main")
    monkeypatch.setattr(pd, "TWILIO_TOKEN", "tok_main")
    monkeypatch.setattr(pd, "get_db", lambda: db)

    async def fake_enforce(principal, mid):
        return None
    monkeypatch.setattr(pd, "enforce_service_member", fake_enforce)

    async def fake_search(country, area):
        return "+15557778888"
    monkeypatch.setattr(pd, "_twilio_search", fake_search)

    async def fake_purchase(number, name):
        return {"phone_number": number, "sid": purchase_sid}
    monkeypatch.setattr(pd, "_twilio_purchase", fake_purchase)

    monkeypatch.setattr(pd, "vapi_binding_enabled", lambda: True)

    import_calls = []

    async def fake_import(number, *, twilio_account_sid, twilio_auth_token, name=""):
        import_calls.append(number)
        return import_result
    monkeypatch.setattr(pd, "import_twilio_number", fake_import)

    release_calls = []

    async def fake_release(sid):
        release_calls.append(sid)
        return True
    monkeypatch.setattr(pd, "_twilio_release", fake_release)

    del_calls = []

    async def fake_del(vid):
        del_calls.append(vid)
        return True
    monkeypatch.setattr(pd, "delete_vapi_number", fake_del)

    return import_calls, release_calls, del_calls


@aio
async def test_provision_binds_to_vapi_and_stores_id(monkeypatch):
    db = _FakeDB(rows=[])
    imports, releases, dels = _wire_provision(monkeypatch, db)
    req = pd.ProvisionNumberRequest(merchant_id="biz_" + "a" * 16, country="CA")

    out = await pd.provision_number(req, principal={"sub": "svc"})

    assert out["provisioned"] is True and out["vapi_bound"] is True
    assert imports == ["+15557778888"]
    assert db.inserted and db.inserted[0]["vapi_phone_number_id"] == "vapi_ph_new"
    assert releases == []  # success → no rollback


@aio
async def test_provision_rolls_back_when_vapi_import_fails(monkeypatch):
    db = _FakeDB(rows=[])
    imports, releases, dels = _wire_provision(monkeypatch, db, import_result=None)
    req = pd.ProvisionNumberRequest(merchant_id="biz_" + "b" * 16, country="CA")

    with pytest.raises(pd.HTTPException) as exc:
        await pd.provision_number(req, principal={"sub": "svc"})

    assert exc.value.status_code == 502
    assert releases == ["SID_NEW"], "failed bind must release the Twilio number"
    assert db.inserted == [] and db.updated == [], "no dead number stored"


@aio
async def test_swap_releases_old_vapi_binding(monkeypatch):
    db = _FakeDB(rows=[{"phone_number": "+15550001111",
                        "phone_number_sid": "SID_OLD",
                        "vapi_phone_number_id": "vapi_ph_old"}])
    imports, releases, dels = _wire_provision(monkeypatch, db)
    req = pd.ProvisionNumberRequest(merchant_id="biz_" + "c" * 16, country="CA", force=True)

    out = await pd.provision_number(req, principal={"sub": "svc"})

    assert out["provisioned"] is True
    assert dels == ["vapi_ph_old"], "old Vapi binding released on swap"
    assert "SID_OLD" in releases


@aio
async def test_provision_store_tolerates_missing_vapi_column(monkeypatch):
    class _PickyDB(_FakeDB):
        async def insert(self, table, payload):
            if "vapi_phone_number_id" in payload:
                raise RuntimeError('column "vapi_phone_number_id" does not exist')
            self.inserted.append(payload)
            return [payload]
    db = _PickyDB(rows=[])
    _wire_provision(monkeypatch, db)
    req = pd.ProvisionNumberRequest(merchant_id="biz_" + "d" * 16, country="CA")

    out = await pd.provision_number(req, principal={"sub": "svc"})

    assert out["provisioned"] is True
    assert db.inserted and "vapi_phone_number_id" not in db.inserted[0]
