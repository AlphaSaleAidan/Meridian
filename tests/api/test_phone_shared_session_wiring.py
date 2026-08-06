"""Wiring between the phone/SMS webhooks and the shared session store.

The store itself is covered in test_phone_session_store.py. This file covers the
seams: the decorators that hydrate/write-back around a webhook, and the startup
guard that decides whether multiple uvicorn workers are safe.

The rule under test throughout: with no REDIS_URL the decorators are
pass-throughs and the in-process dicts behave exactly as they always have.
"""
from __future__ import annotations

import asyncio
import dataclasses
import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("ENCRYPTION_KEY", "0" * 64)

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "services" / "phone_agent"))
sys.path.insert(0, str(_ROOT))

import card_on_phone as cop  # noqa: E402
import session_store as ss  # noqa: E402
from session_store import NS_CAPTURES, NS_SESSIONS, NS_SMS_SESSIONS, SessionStore  # noqa: E402
from src.api.routes import phone  # noqa: E402


def _run(coro):
    return asyncio.run(coro)


class FakeForm(dict):
    pass


class FakeRequest:
    """Only what the decorators touch: an awaitable, cached form."""

    def __init__(self, **fields):
        self._form = FakeForm(fields)
        self.form_calls = 0

    async def form(self):
        self.form_calls += 1
        return self._form


class LocalStore(SessionStore):
    """A store that reports as shared but keeps everything in-process, so the
    decorators run their Redis code path without needing a Redis."""

    def __init__(self):
        super().__init__(url="redis://test")

    def _namespace_shared(self, namespace):  # noqa: D102
        return False


@pytest.fixture
def shared_store(monkeypatch):
    store = LocalStore()
    monkeypatch.setattr(phone, "get_session_store", lambda: store)
    monkeypatch.setattr(phone, "_SESSION_STORE_AVAILABLE", True)
    yield store


@pytest.fixture(autouse=True)
def clean_dicts():
    phone._sessions.clear()
    cop._captures.clear()
    yield
    phone._sessions.clear()
    cop._captures.clear()


# ─── Off by default ──────────────────────────────────────────────────────────

def test_decorator_is_a_pass_through_without_redis(monkeypatch):
    monkeypatch.setattr(phone, "get_session_store", lambda: SessionStore(url=""))
    calls = []

    @phone._shared_state()
    async def handler(request):
        calls.append(request)
        phone._sessions["CA-1"] = {"ts": 1.0}
        return "twiml"

    request = FakeRequest(CallSid="CA-1")
    assert _run(handler(request)) == "twiml"
    assert calls == [request]
    assert request.form_calls == 0          # not even parsed when store is off
    assert phone._sessions["CA-1"] == {"ts": 1.0}


def test_decorator_preserves_the_handler_signature():
    assert phone.twilio_voice.__name__ == "twilio_voice"
    assert phone.pay_zip.__name__ == "pay_zip"


# ─── Hydrate / write-back ────────────────────────────────────────────────────

def test_session_written_back_after_the_handler(shared_store):
    @phone._shared_state()
    async def handler(request):
        phone._sessions["CA-1"] = {"ts": 5.0, "messages": []}
        return "ok"

    assert _run(handler(FakeRequest(CallSid="CA-1"))) == "ok"
    assert _run(shared_store.get(NS_SESSIONS, "CA-1")) == {"ts": 5.0, "messages": []}


def test_session_loaded_before_the_handler_runs(shared_store):
    """The webhook lands on a worker that never saw this call."""
    _run(shared_store.set(NS_SESSIONS, "CA-1", {"ts": 1.0, "merchant_id": "m-1"}))
    seen = {}

    @phone._shared_state()
    async def handler(request):
        seen.update(phone._sessions.get("CA-1", {}))
        return "ok"

    _run(handler(FakeRequest(CallSid="CA-1")))
    assert seen == {"ts": 1.0, "merchant_id": "m-1"}


def test_deleting_the_session_clears_it_from_the_store(shared_store):
    _run(shared_store.set(NS_SESSIONS, "CA-1", {"ts": 1.0}))

    @phone._shared_state()
    async def handler(request):
        phone._sessions.pop("CA-1", None)     # what a call-ending handler does
        return "hangup"

    _run(handler(FakeRequest(CallSid="CA-1")))
    assert _run(shared_store.get(NS_SESSIONS, "CA-1")) is None


def test_write_back_runs_even_when_the_handler_raises(shared_store):
    @phone._shared_state()
    async def handler(request):
        phone._sessions["CA-1"] = {"ts": 9.0}
        raise ValueError("boom")

    with pytest.raises(ValueError):
        _run(handler(FakeRequest(CallSid="CA-1")))
    assert _run(shared_store.get(NS_SESSIONS, "CA-1")) == {"ts": 9.0}


def test_no_call_sid_skips_the_store(shared_store):
    @phone._shared_state()
    async def handler(request):
        return "ok"

    assert _run(handler(FakeRequest(From="+15551234567"))) == "ok"


def test_store_failure_does_not_break_the_handler(shared_store, monkeypatch):
    async def boom(*a, **kw):
        raise ConnectionError("redis gone")

    monkeypatch.setattr(shared_store, "get", boom)
    monkeypatch.setattr(shared_store, "set", boom)

    @phone._shared_state()
    async def handler(request):
        phone._sessions["CA-1"] = {"ts": 3.0}
        return "twiml"

    assert _run(handler(FakeRequest(CallSid="CA-1"))) == "twiml"
    assert phone._sessions["CA-1"] == {"ts": 3.0}   # the call carries on locally


# ─── Card captures ───────────────────────────────────────────────────────────

def test_capture_round_trips_through_the_store(shared_store):
    @phone._shared_state(captures=True)
    async def collect(request):
        cap = cop.start_capture("CA-1", order_ref="MRD-1", merchant_id="m-1",
                                amount_cents=1798)
        cap.pan = "4242424242424242"
        return "ok"

    _run(collect(FakeRequest(CallSid="CA-1")))
    stored = _run(shared_store.get(NS_CAPTURES, "CA-1"))
    assert stored["pan"] == "4242424242424242"
    assert stored["order_ref"] == "MRD-1"

    # Next keypad webhook, different worker: the dict is empty until we hydrate.
    cop._captures.clear()
    seen = {}

    @phone._shared_state(captures=True)
    async def next_digit(request):
        cap = cop.get_capture("CA-1")
        seen["pan"] = cap.pan if cap else None
        return "ok"

    _run(next_digit(FakeRequest(CallSid="CA-1")))
    assert seen["pan"] == "4242424242424242"


def test_cleared_capture_is_removed_from_the_store(shared_store):
    _run(shared_store.set(NS_CAPTURES, "CA-1",
                          dataclasses.asdict(cop.CardCapture(call_sid="CA-1", pan="4242"))))

    @phone._shared_state(captures=True)
    async def finish(request):
        cop.clear_capture("CA-1")
        return "ok"

    _run(finish(FakeRequest(CallSid="CA-1")))
    assert _run(shared_store.get(NS_CAPTURES, "CA-1")) is None


def test_malformed_stored_capture_is_ignored(shared_store):
    _run(shared_store.set(NS_CAPTURES, "CA-1", {"not_a_field": 1}))
    seen = {}

    @phone._shared_state(captures=True)
    async def handler(request):
        seen["cap"] = cop.get_capture("CA-1")
        return "ok"

    _run(handler(FakeRequest(CallSid="CA-1")))
    assert seen["cap"] is None


def test_expired_capture_stays_expired_across_workers(shared_store, monkeypatch):
    """TTL is carried by CardCapture.created, so a capture read back from the
    store expires on the same clock it always did."""
    stale = cop.CardCapture(call_sid="CA-1", pan="4242")
    stale.created = 0.0
    _run(shared_store.set(NS_CAPTURES, "CA-1", dataclasses.asdict(stale)))
    seen = {}

    @phone._shared_state(captures=True)
    async def handler(request):
        seen["cap"] = cop.get_capture("CA-1")
        return "ok"

    _run(handler(FakeRequest(CallSid="CA-1")))
    assert seen["cap"] is None


# ─── SMS sessions ────────────────────────────────────────────────────────────

def _sms_module():
    import sms_order
    return sms_order


def test_sms_decorator_is_a_pass_through_without_redis(monkeypatch):
    sms_order = _sms_module()
    monkeypatch.setattr(sms_order, "get_session_store", lambda: SessionStore(url=""))
    sms_order._sms_sessions.clear()

    @sms_order._shared_sms_session
    async def handler(request):
        sms_order._sms_sessions["+1222:+1333"] = {"ts": 1.0}
        return "twiml"

    request = FakeRequest(To="+1222", From="+1333")
    assert _run(handler(request)) == "twiml"
    assert request.form_calls == 0
    assert sms_order._sms_sessions == {"+1222:+1333": {"ts": 1.0}}


def test_sms_session_round_trips_with_its_merchant_config(monkeypatch):
    sms_order = _sms_module()
    store = LocalStore()
    monkeypatch.setattr(sms_order, "get_session_store", lambda: store)
    sms_order._sms_sessions.clear()

    config = sms_order.MerchantPhoneConfig(
        merchant_id="m-1", business_name="Nom Nom", business_type="restaurant",
        phone_number="+1222", greeting="hi", voice="alloy", language="en",
        active=True, menu_items=[{"name": "pizza", "price": 12.0}],
        pos_system="square", pos_access_token="tok", pos_location_id="loc",
        business_hours={}, after_hours_message="", max_concurrent_calls=5,
        order_types=["pickup"], special_instructions_enabled=True,
        transfer_number="", pos_webhook_url="", sms_checkout_enabled=True,
        sms_ordering_enabled=True,
    )

    @sms_order._shared_sms_session
    async def handler(request):
        sms_order._sms_sessions["+1222:+1333"] = {
            "messages": [{"role": "user", "content": "menu"}],
            "system": "prompt", "config": config,
            "customer_phone": "+1333", "merchant_phone": "+1222",
            "ts": 1.0, "order_placed": False,
        }
        return "ok"

    _run(handler(FakeRequest(To="+1222", From="+1333")))

    # Stored JSON-safe...
    wire = _run(store.get(NS_SMS_SESSIONS, "+1222:+1333"))
    assert wire["config"]["business_name"] == "Nom Nom"

    # ...and rehydrated as a real MerchantPhoneConfig on the next worker.
    sms_order._sms_sessions.clear()
    seen = {}

    @sms_order._shared_sms_session
    async def next_text(request):
        seen["session"] = sms_order._sms_sessions.get("+1222:+1333")
        return "ok"

    _run(next_text(FakeRequest(To="+1222", From="+1333")))
    restored = seen["session"]
    assert isinstance(restored["config"], sms_order.MerchantPhoneConfig)
    assert restored["config"] == config
    assert restored["messages"] == [{"role": "user", "content": "menu"}]


def test_sms_session_with_a_stale_config_shape_starts_fresh(monkeypatch):
    """A deploy that changes MerchantPhoneConfig must not 500 an inbound text."""
    sms_order = _sms_module()
    store = LocalStore()
    monkeypatch.setattr(sms_order, "get_session_store", lambda: store)
    sms_order._sms_sessions.clear()
    _run(store.set(NS_SMS_SESSIONS, "+1222:+1333",
                   {"ts": 1.0, "config": {"field_that_no_longer_exists": 1}}))
    seen = {}

    @sms_order._shared_sms_session
    async def handler(request):
        seen["session"] = sms_order._sms_sessions.get("+1222:+1333")
        return "ok"

    assert _run(handler(FakeRequest(To="+1222", From="+1333"))) == "ok"
    assert seen["session"] is None


# ─── Multi-worker startup guard ──────────────────────────────────────────────

def _app():
    from src.api import app as app_module
    return app_module


@pytest.mark.parametrize("workers", ["0", "1", ""])
def test_single_worker_always_starts(monkeypatch, workers):
    app_module = _app()
    monkeypatch.delenv("MERIDIAN_ALLOW_MULTI_WORKER", raising=False)
    monkeypatch.setenv("WEB_CONCURRENCY", workers)
    monkeypatch.setattr(sys, "argv", ["uvicorn"])
    _run(app_module._assert_single_worker())      # no raise


def test_multi_worker_refused_without_a_shared_store(monkeypatch):
    app_module = _app()
    monkeypatch.delenv("MERIDIAN_ALLOW_MULTI_WORKER", raising=False)
    monkeypatch.setenv("WEB_CONCURRENCY", "4")
    monkeypatch.setattr(sys, "argv", ["uvicorn"])

    async def unhealthy():
        return False
    monkeypatch.setattr(app_module, "_shared_session_store_healthy", unhealthy)

    with pytest.raises(RuntimeError, match="Refusing to start with 4 workers"):
        _run(app_module._assert_single_worker())


def test_multi_worker_allowed_when_redis_answers(monkeypatch):
    app_module = _app()
    monkeypatch.delenv("MERIDIAN_ALLOW_MULTI_WORKER", raising=False)
    monkeypatch.setenv("WEB_CONCURRENCY", "4")
    monkeypatch.setattr(sys, "argv", ["uvicorn"])

    async def healthy():
        return True
    monkeypatch.setattr(app_module, "_shared_session_store_healthy", healthy)

    _run(app_module._assert_single_worker())      # no raise


def test_redis_url_alone_does_not_unlock_multi_worker(monkeypatch):
    """A REDIS_URL pointing at nothing must still refuse — otherwise we trade a
    loud startup failure for calls dying mid-conversation."""
    app_module = _app()
    monkeypatch.delenv("MERIDIAN_ALLOW_MULTI_WORKER", raising=False)
    monkeypatch.setenv("WEB_CONCURRENCY", "2")
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:6399/0")
    monkeypatch.setattr(sys, "argv", ["uvicorn"])
    ss.reset_session_store(SessionStore(url="not-a-redis-url"))
    try:
        with pytest.raises(RuntimeError, match="Refusing to start with 2 workers"):
            _run(app_module._assert_single_worker())
    finally:
        ss.reset_session_store(None)


def test_explicit_override_still_wins(monkeypatch):
    app_module = _app()
    monkeypatch.setenv("MERIDIAN_ALLOW_MULTI_WORKER", "1")
    monkeypatch.setenv("WEB_CONCURRENCY", "8")
    monkeypatch.setattr(sys, "argv", ["uvicorn"])
    _run(app_module._assert_single_worker())      # no raise


def test_worker_count_read_from_argv(monkeypatch):
    app_module = _app()
    monkeypatch.delenv("WEB_CONCURRENCY", raising=False)
    monkeypatch.setattr(sys, "argv", ["uvicorn", "--workers", "3"])
    assert app_module._configured_workers() == 3
    monkeypatch.setattr(sys, "argv", ["uvicorn", "-w", "2"])
    assert app_module._configured_workers() == 2
    monkeypatch.setattr(sys, "argv", ["uvicorn"])
    assert app_module._configured_workers() == 0
