"""Shared phone/SMS/card session store.

Covers the two states this ships in: no REDIS_URL (Railway today) where every
path must stay on the in-process dicts, and a Redis-backed store where sessions
round-trip, TTLs are set per namespace, card captures are encrypted at rest, and
any Redis failure degrades to the dict instead of raising into a live call.
"""
import asyncio
import json
import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("ENCRYPTION_KEY", "0" * 64)

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "services" / "phone_agent"))
sys.path.insert(0, str(_ROOT))

import session_store as ss  # noqa: E402
from session_store import (  # noqa: E402
    NS_CAPTURES,
    NS_SESSIONS,
    NS_SMS_SESSIONS,
    SessionStore,
)


# ─── Tiny async Redis stand-in (fakeredis is not a project dependency) ────────

class FakeRedis:
    """Just the surface SessionStore uses: get/set/delete/expire/ping/aclose."""

    def __init__(self):
        self.data: dict[str, str] = {}
        self.ttls: dict[str, int] = {}
        self.fail_on: set[str] = set()      # method names that should blow up
        self.ping_ok = True

    def _check(self, op: str):
        if op in self.fail_on:
            raise ConnectionError(f"fake redis {op} down")

    async def get(self, key):
        self._check("get")
        return self.data.get(key)

    async def set(self, key, value, ex=None):
        self._check("set")
        self.data[key] = value
        if ex is not None:
            self.ttls[key] = ex
        return True

    async def delete(self, key):
        self._check("delete")
        self.data.pop(key, None)
        self.ttls.pop(key, None)
        return 1

    async def expire(self, key, ttl):
        self._check("expire")
        if key not in self.data:
            return False
        self.ttls[key] = ttl
        return True

    async def ping(self):
        self._check("ping")
        return self.ping_ok

    async def aclose(self):
        return None

    # test helper — Redis would drop the key itself once the TTL elapsed
    def expire_now(self, key):
        self.data.pop(key, None)
        self.ttls.pop(key, None)


def _store(client=None, url="redis://fake"):
    return SessionStore(url=url, client=client)


def _run(coro):
    return asyncio.run(coro)


SESSION = {
    "messages": [{"role": "user", "content": "two large pepperoni"}],
    "ts": 1_700_000_000.0,
    "merchant_id": "m-1",
    "capture": "record",
    "empty_count": 0,
    "tax_rate": 0.13,
}

CAPTURE = {
    "call_sid": "CA-1",
    "order_ref": "MRD-1",
    "merchant_id": "m-1",
    "amount_cents": 1798,
    "caller_phone": "+15551234567",
    "pan": "4242424242424242",
    "expiry": "1230",
    "cvv": "123",
    "postal": "90210",
    "attempts": 0,
    "created": 1_700_000_000.0,
}


# ─── No REDIS_URL: the default path is the dict path ─────────────────────────

def test_no_redis_url_is_not_shared(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    store = SessionStore()
    assert store.shared is False
    assert _run(store.ping()) is False


def test_no_redis_url_round_trips_in_process():
    store = _store(url="")
    assert _run(store.set(NS_SESSIONS, "CA-1", SESSION)) is False  # never hit Redis
    assert _run(store.get(NS_SESSIONS, "CA-1")) == SESSION
    _run(store.delete(NS_SESSIONS, "CA-1"))
    assert _run(store.get(NS_SESSIONS, "CA-1")) is None


def test_no_redis_url_expires_in_process(monkeypatch):
    store = _store(url="")
    monkeypatch.setattr(ss.time, "time", lambda: 1000.0)
    _run(store.set(NS_CAPTURES, "CA-1", CAPTURE))
    monkeypatch.setattr(ss.time, "time", lambda: 1000.0 + ss.ttl_for(NS_CAPTURES) + 1)
    assert _run(store.get(NS_CAPTURES, "CA-1")) is None


# ─── Redis-backed round trips ────────────────────────────────────────────────

@pytest.mark.parametrize("namespace,value", [
    (NS_SESSIONS, SESSION),
    (NS_SMS_SESSIONS, {"messages": [], "ts": 1.0, "order_placed": False,
                       "config": {"merchant_id": "m-1", "business_name": "Nom"}}),
    (NS_CAPTURES, CAPTURE),
])
def test_round_trip_per_namespace(namespace, value):
    fake = FakeRedis()
    store = _store(fake)
    assert _run(store.set(namespace, "k", value)) is True
    assert _run(store.get(namespace, "k")) == value


def test_delete_removes_from_redis():
    fake = FakeRedis()
    store = _store(fake)
    _run(store.set(NS_SESSIONS, "CA-1", SESSION))
    _run(store.delete(NS_SESSIONS, "CA-1"))
    assert fake.data == {}
    assert _run(store.get(NS_SESSIONS, "CA-1")) is None


def test_missing_key_reads_none():
    assert _run(_store(FakeRedis()).get(NS_SESSIONS, "nope")) is None


def test_empty_key_is_a_noop():
    fake = FakeRedis()
    store = _store(fake)
    assert _run(store.set(NS_SESSIONS, "", SESSION)) is False
    assert _run(store.get(NS_SESSIONS, "")) is None
    assert fake.data == {}


# ─── TTLs ────────────────────────────────────────────────────────────────────

def test_ttl_defaults_match_the_in_module_constants():
    # phone.SESSION_TTL, sms_order.SESSION_TTL, card_on_phone._CAPTURE_TTL
    assert ss.ttl_for(NS_SESSIONS) == 600
    assert ss.ttl_for(NS_SMS_SESSIONS) == 1800
    assert ss.ttl_for(NS_CAPTURES) == 300


def test_ttl_is_env_overridable(monkeypatch):
    monkeypatch.setenv("SMS_SESSION_TTL", "7200")
    assert ss.ttl_for(NS_SMS_SESSIONS) == 7200
    monkeypatch.setenv("SMS_SESSION_TTL", "not-a-number")
    assert ss.ttl_for(NS_SMS_SESSIONS) == 1800


def test_each_namespace_writes_its_own_ttl():
    fake = FakeRedis()
    store = _store(fake)
    for ns in (NS_SESSIONS, NS_SMS_SESSIONS, NS_CAPTURES):
        _run(store.set(ns, "k", {"ts": 1.0}))
    assert [fake.ttls[k] for k in sorted(fake.ttls)] == [
        ss.ttl_for(NS_CAPTURES), ss.ttl_for(NS_SESSIONS), ss.ttl_for(NS_SMS_SESSIONS),
    ]


def test_expired_key_reads_as_missing():
    fake = FakeRedis()
    store = _store(fake)
    _run(store.set(NS_SESSIONS, "CA-1", SESSION))
    fake.expire_now(next(iter(fake.data)))
    assert _run(store.get(NS_SESSIONS, "CA-1")) is None


def test_touch_extends_the_ttl():
    fake = FakeRedis()
    store = _store(fake)
    _run(store.set(NS_SESSIONS, "CA-1", SESSION))
    key = next(iter(fake.data))
    fake.ttls[key] = 5
    assert _run(store.touch(NS_SESSIONS, "CA-1")) is True
    assert fake.ttls[key] == ss.ttl_for(NS_SESSIONS)


# ─── PCI: card captures are encrypted at rest ────────────────────────────────

def test_capture_is_encrypted_at_rest():
    fake = FakeRedis()
    store = _store(fake)
    _run(store.set(NS_CAPTURES, "CA-1", CAPTURE))
    stored = next(iter(fake.data.values()))

    assert stored != json.dumps(CAPTURE)
    assert stored.startswith("v1:")                 # AES-256-GCM envelope
    for secret in (CAPTURE["pan"], CAPTURE["cvv"], CAPTURE["expiry"],
                   CAPTURE["postal"], CAPTURE["pan"][-4:]):
        assert secret not in stored
    assert "pan" not in stored and "cvv" not in stored   # not even the field names
    assert _run(store.get(NS_CAPTURES, "CA-1")) == CAPTURE


def test_sessions_are_not_encrypted():
    """Only the card namespace pays the encryption cost."""
    fake = FakeRedis()
    _run(_store(fake).set(NS_SESSIONS, "CA-1", SESSION))
    assert json.loads(next(iter(fake.data.values()))) == SESSION


def test_captures_stay_in_process_without_an_encryption_key(monkeypatch):
    monkeypatch.delenv("ENCRYPTION_KEY", raising=False)
    fake = FakeRedis()
    store = _store(fake)
    assert _run(store.set(NS_CAPTURES, "CA-1", CAPTURE)) is False
    assert fake.data == {}                            # never written in the clear
    assert _run(store.get(NS_CAPTURES, "CA-1")) == CAPTURE  # still usable locally
    # Sessions are unaffected — only the card namespace is gated on the key.
    assert _run(store.set(NS_SESSIONS, "CA-1", SESSION)) is True


def test_undecryptable_capture_reads_as_missing():
    fake = FakeRedis()
    store = _store(fake)
    _run(store.set(NS_CAPTURES, "CA-1", CAPTURE))
    key = next(iter(fake.data))
    fake.data[key] = "v1:garbage:garbage:garbage"
    assert _run(store.get(NS_CAPTURES, "CA-1")) is None


def test_corrupt_session_reads_as_missing():
    fake = FakeRedis()
    store = _store(fake)
    _run(store.set(NS_SESSIONS, "CA-1", SESSION))
    fake.data[next(iter(fake.data))] = "{not json"
    assert _run(store.get(NS_SESSIONS, "CA-1")) is None


# ─── Fail-open ───────────────────────────────────────────────────────────────

def test_redis_failing_mid_call_serves_the_in_process_copy():
    """Redis dies between two webhooks of the same call: the write lands in the
    dict and the next read finds it there rather than raising."""
    fake = FakeRedis()
    store = _store(fake)
    fake.fail_on.update({"set", "get"})
    assert _run(store.set(NS_SESSIONS, "CA-1", SESSION)) is False
    assert _run(store.get(NS_SESSIONS, "CA-1")) == SESSION


def test_redis_get_failure_without_a_local_copy_is_a_miss():
    fake = FakeRedis()
    store = _store(fake)
    _run(store.set(NS_SESSIONS, "CA-1", SESSION))
    fake.fail_on.add("get")
    assert _run(store.get(NS_SESSIONS, "CA-1")) is None   # no local copy, no raise


def test_redis_set_failure_keeps_the_value_in_process():
    fake = FakeRedis()
    store = _store(fake)
    fake.fail_on.add("set")
    assert _run(store.set(NS_SESSIONS, "CA-1", SESSION)) is False
    fake.fail_on.clear()
    assert _run(store.get(NS_SESSIONS, "CA-1")) == SESSION  # served from the dict


def test_redis_delete_and_touch_failures_do_not_raise():
    fake = FakeRedis()
    store = _store(fake)
    _run(store.set(NS_SESSIONS, "CA-1", SESSION))
    fake.fail_on.update({"delete", "expire"})
    assert _run(store.delete(NS_SESSIONS, "CA-1")) is False
    assert _run(store.touch(NS_SESSIONS, "CA-1")) is False


def test_unserializable_value_keeps_the_call_alive():
    fake = FakeRedis()
    store = _store(fake)
    value = {"ts": 1.0, "client": object()}
    assert _run(store.set(NS_SESSIONS, "CA-1", value)) is False
    assert fake.data == {}
    assert _run(store.get(NS_SESSIONS, "CA-1")) == value


def test_ping_reports_redis_health():
    fake = FakeRedis()
    assert _run(_store(fake).ping()) is True
    fake.fail_on.add("ping")
    assert _run(_store(fake).ping()) is False


def test_unreachable_redis_url_degrades_instead_of_raising(monkeypatch):
    store = SessionStore(url="not-a-redis-url")
    assert store.shared is True
    assert _run(store.ping()) is False
    assert _run(store.set(NS_SESSIONS, "CA-1", SESSION)) is False
    assert _run(store.get(NS_SESSIONS, "CA-1")) == SESSION   # in-process fallback
