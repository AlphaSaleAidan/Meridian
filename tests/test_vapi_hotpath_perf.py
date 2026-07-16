"""
VAPI ASSISTANT-REQUEST HOT PATH — round-trip budget coverage.

The time between pickup and the agent's greeting is Supabase round-trips; the
perf-audit fix caps the path at ≤4 SEQUENTIAL stages by (a) sharing one httpx
client, (b) gathering menu_items + merchant_menus, and (c) gathering the
loop-guard + transfer fleet checks. This file pins:

  1. assistant-request issues ≤4 sequential query stages (concurrent requests
     inside one gather count as ONE stage) and exactly 6 total queries for a
     merchant with a caller id and a transfer number configured.
  2. Fail-open contracts survive the gather: a loop-guard error still serves
     the NORMAL assistant; a fleet-check error KEEPS the configured transfer.
  3. end-of-call passes the resolved config through to _record_call_ending —
     the merchant is never re-resolved for telemetry.

Pattern mirrors tests/test_menu_agent_path.py: direct calls, asyncio.run.

Run:  python -m pytest tests/test_vapi_hotpath_perf.py -v
"""
from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("ENCRYPTION_KEY", "0" * 64)

_PHONE_AGENT_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "services", "phone_agent"))
if _PHONE_AGENT_DIR not in sys.path:
    sys.path.insert(0, _PHONE_AGENT_DIR)

import merchant_config as mc  # noqa: E402
from src.api.routes import vapi_webhook as vw  # noqa: E402

MID = "biz_hotpath_0001"
DIALED = "+15550001111"
CALLER = "+15550002222"
TRANSFER = "+15550003333"

CONFIG_ROW = {
    "merchant_id": MID,
    "business_name": "Hot Path Pizza",
    "phone_number": DIALED,
    "greeting": "Thanks for calling Hot Path Pizza!",
    "active": True,
    "menu_items": [{"name": "Slice", "price": 4.0}],
    "transfer_number": TRANSFER,
}


def _run(coro):
    return asyncio.run(coro)


class _Resp:
    def __init__(self, data):
        self.status_code = 200
        self._data = data

    def json(self):
        return self._data


class FakeSupabaseClient:
    """Stands in for the module-level shared httpx client.

    Counts SEQUENTIAL stages: a get() that starts while no other get() is in
    flight opens a new stage; gathered (concurrent) requests share one stage.
    """

    is_closed = False

    def __init__(self):
        self.calls: list[tuple[str, dict]] = []
        self.stages = 0
        self._inflight = 0

    async def get(self, url, params=None, headers=None):
        params = params or {}
        self.calls.append((url.rsplit("/rest/v1/", 1)[-1], dict(params)))
        if self._inflight == 0:
            self.stages += 1
        self._inflight += 1
        try:
            # Yield twice so concurrently-gathered requests enter before we
            # return — otherwise every request would look sequential.
            await asyncio.sleep(0)
            await asyncio.sleep(0)
            return self._respond(url, params)
        finally:
            self._inflight -= 1

    def _respond(self, url, params):
        table = url.rsplit("/rest/v1/", 1)[-1]
        if table == "phone_agent_config":
            phone = (params.get("phone_number") or "")
            if phone:
                if phone[3:] == DIALED:  # strip "eq."
                    return _Resp([{"merchant_id": MID}])
                return _Resp([])  # caller / transfer are not agent DIDs
            return _Resp([dict(CONFIG_ROW)])
        # menu_items / merchant_menus: no store rows → JSONB fallback.
        return _Resp([])


class _FakeRequest:
    def __init__(self, payload):
        self._payload = payload
        self.headers = {"x-vapi-secret": "test-secret"}

    async def json(self):
        return self._payload


def _assistant_request_payload():
    return {"message": {
        "type": "assistant-request",
        "call": {
            "phoneNumber": {"number": DIALED},
            "customer": {"number": CALLER},
        },
    }}


def _patch_hotpath(monkeypatch, fake):
    monkeypatch.setattr(mc, "SUPABASE_URL", "https://fake.supabase.co")
    monkeypatch.setattr(mc, "SUPABASE_KEY", "test-key")
    monkeypatch.setattr(mc, "_get_http_client", lambda: fake)
    monkeypatch.setattr(vw, "VAPI_SERVER_SECRET", "test-secret")
    # Keep the optional gates out of the picture (their envs are unset in CI,
    # but pin it so this test never depends on the environment).
    monkeypatch.setattr(vw, "TELNYX_FALLBACK_NUMBER", "")
    monkeypatch.setattr(vw, "VOICE_BALANCE_FLOOR_CENTS", None)


# ── 1. round-trip budget ─────────────────────────────────────────────────

def test_assistant_request_is_at_most_4_sequential_stages(monkeypatch):
    fake = FakeSupabaseClient()
    _patch_hotpath(monkeypatch, fake)

    res = _run(vw.vapi_webhook(_FakeRequest(_assistant_request_payload())))

    assert "assistant" in res
    assert res["assistant"]["name"] == "Hot Path Pizza — Order Taker"
    # transfer number is clean → transferCall tool present.
    tool_types = [t.get("type") for t in res["assistant"]["model"]["tools"]]
    assert "transferCall" in tool_types

    # dialed-DID lookup, config, (menu_items ∥ merchant_menus),
    # (loop-guard ∥ fleet check) — 6 queries in ≤4 sequential stages.
    assert len(fake.calls) == 6, fake.calls
    assert fake.stages <= 4, (
        f"assistant-request took {fake.stages} sequential stages "
        f"(budget 4): {fake.calls}")


# ── 2. fail-open contracts survive the gather ────────────────────────────

def test_loop_guard_error_serves_normal_assistant(monkeypatch):
    fake = FakeSupabaseClient()
    _patch_hotpath(monkeypatch, fake)

    async def _boom(caller, dialed, config):
        raise RuntimeError("loop check boom")
    monkeypatch.setattr(vw, "_is_loop_caller", _boom)

    res = _run(vw.vapi_webhook(_FakeRequest(_assistant_request_payload())))

    # Loop check blew up → NORMAL order-taker assistant, not the message-taker.
    assert res["assistant"]["name"] == "Hot Path Pizza — Order Taker"


def test_fleet_check_error_keeps_transfer(monkeypatch):
    fake = FakeSupabaseClient()
    _patch_hotpath(monkeypatch, fake)

    real = mc.get_merchant_by_phone

    async def _boom_on_transfer(number):
        if number == TRANSFER:
            raise RuntimeError("fleet check boom")
        return await real(number)
    monkeypatch.setattr(mc, "get_merchant_by_phone", _boom_on_transfer)

    res = _run(vw.vapi_webhook(_FakeRequest(_assistant_request_payload())))

    tool_types = [t.get("type") for t in res["assistant"]["model"]["tools"]]
    assert "transferCall" in tool_types  # error → keep the configured transfer


def test_loop_caller_still_gets_message_taker(monkeypatch):
    fake = FakeSupabaseClient()
    _patch_hotpath(monkeypatch, fake)
    payload = _assistant_request_payload()
    # Caller IS the dialed agent DID → loop guard must trip (sync same_number
    # path, no DB) and serve the message-taker.
    payload["message"]["call"]["customer"]["number"] = DIALED

    res = _run(vw.vapi_webhook(_FakeRequest(payload)))

    assert res["assistant"]["name"] == "Hot Path Pizza — Message Taker"


# ── 3. end-of-call: config passed through, never re-resolved ─────────────

def test_record_call_ending_uses_passed_config(monkeypatch):
    fake = FakeSupabaseClient()
    _patch_hotpath(monkeypatch, fake)

    inserted: list[tuple[str, dict]] = []

    class _FakeDB:
        async def select(self, table, columns="*", filters=None, order=None, limit=None):
            return []

        async def insert(self, table, row):
            inserted.append((table, row))
            return [row]

    import src.db as db_mod
    monkeypatch.setattr(db_mod, "_db_instance", _FakeDB())

    config = mc._demo_config(MID)
    _run(vw._record_call_ending(
        {"call": {}}, "call_123", "customer-ended-call", 42, config=config))

    assert fake.calls == []  # passed-through config → zero Supabase reads
    assert inserted and inserted[0][0] == "voice_call_endings"
    assert inserted[0][1]["merchant_id"] == MID
    assert inserted[0][1]["duration_seconds"] == 42
