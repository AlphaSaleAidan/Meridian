"""Deposits: what gets asked for, and what gets taken.

Run:
    python -m pytest tests/test_booking_deposits.py -v

The assertions that matter most:
  * a flat amount beats a percentage, because typing an amount is deliberate
  * a percentage of an unpriced service is nothing, never a guess
  * the amount is COPIED onto the booking, so a price rise cannot change what
    a customer already agreed to
  * money is only ever captured from an explicit no-show — never a timer
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("ENCRYPTION_KEY", "0" * 64)

from src.services import booking_deposits as dep  # noqa: E402


class StubStore:
    def __init__(self):
        self.updates: list[tuple[str, dict]] = []
        self.cancelled: list[tuple[str, str]] = []
        self.rows: list[dict] = []
        self.cfg_rows: list[dict] = []

    async def update_booking(self, booking_id, fields):
        self.updates.append((booking_id, fields))
        return {"id": booking_id, **fields}

    async def cancel_booking(self, booking_id, reason=""):
        self.cancelled.append((booking_id, reason))
        return {"id": booking_id, "status": "cancelled"}

    async def _req(self, method, table, params=None, json=None, **kw):
        if table == "phone_agent_config":
            return self.cfg_rows
        return self.rows


def _stub_module(monkeypatch, name: str, **attrs):
    """Install a fake flat-import module (the phone rail is imported flat —
    `from payment_links import ...` — so tests provide it via sys.modules)."""
    import types
    mod = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(mod, key, value)
    monkeypatch.setitem(sys.modules, name, mod)
    return mod


def _stub_checkout_rail(monkeypatch, url="https://checkout.stripe.com/c/pay/cs_test_1"):
    async def fake_get_config(merchant_id):
        return object()

    async def fake_checkout(booking, cfg, cents, **kw):
        return {"url": url, "method": "stripe", "session_id": "cs_test_1"}

    _stub_module(monkeypatch, "merchant_config", get_merchant_config=fake_get_config)
    _stub_module(monkeypatch, "payment_links", create_deposit_checkout=fake_checkout)
    return url


@pytest.fixture
def svc(monkeypatch):
    store = StubStore()
    s = dep.DepositService.__new__(dep.DepositService)
    s._store = store
    monkeypatch.setattr(dep, "get_deposit_service", lambda: s)
    s.store = store  # type: ignore[attr-defined]
    return s


def _booking(**over):
    base = {
        "id": "bk-1", "merchant_id": "m1", "customer_phone": "+16045550100",
        "deposit_status": "none", "deposit_cents": None,
    }
    base.update(over)
    return base


# ── how much ────────────────────────────────────────────────────────────

def test_flat_amount_wins_over_percentage():
    """Typing an amount is the more deliberate act; a percentage is usually
    left over from a template."""
    service = {"deposit_cents": 2500, "deposit_percent": 50, "price_cents": 20000}
    assert dep.required_cents(service) == 2500


def test_percentage_is_taken_from_the_price():
    assert dep.required_cents({"deposit_percent": 25, "price_cents": 40000}) == 10000


def test_percentage_of_an_unpriced_service_is_nothing():
    """Guessing a base would invent a charge the merchant never set."""
    assert dep.required_cents({"deposit_percent": 50, "price_cents": None}) == 0


def test_no_deposit_configured_is_zero():
    assert dep.required_cents({"price_cents": 20000}) == 0
    assert dep.required_cents(None) == 0


def test_spoken_line_names_the_amount_and_the_policy():
    line = dep.describe(5000, "Refundable up to 24 hours before")
    assert "$50" in line
    assert "Refundable up to 24 hours before." in line
    assert dep.describe(0) == ""


# ── asking ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_requesting_marks_the_booking_and_texts_the_stripe_link(svc, monkeypatch):
    sent: list[tuple[str, str]] = []

    async def fake_send(phone, message):
        sent.append((phone, message))
        return {"sent": True}

    import src.sms.client as sms
    monkeypatch.setattr(sms, "send_sms", fake_send)
    url = _stub_checkout_rail(monkeypatch)

    out = await svc.request(_booking(), 5000)
    assert out["sent"] is True
    assert out["url"] == url
    assert svc.store.updates[0][1]["deposit_status"] == "requested"
    assert svc.store.updates[0][1]["deposit_cents"] == 5000
    assert "$50" in sent[0][1]
    assert url in sent[0][1]


@pytest.mark.asyncio
async def test_zero_deposit_asks_for_nothing(svc):
    out = await svc.request(_booking(), 0)
    assert out["sent"] is False
    assert out["reason"] == "no_deposit_required"
    assert svc.store.updates == []


@pytest.mark.asyncio
async def test_no_phone_requests_nothing(svc):
    """With no way to deliver the link, nothing is requested — a 'requested'
    row the customer never heard about would be cancelled by the sweep
    through no fault of theirs."""
    out = await svc.request(_booking(customer_phone=""), 5000)
    assert out["sent"] is False
    assert out["reason"] == "no_phone"
    assert svc.store.updates == []


@pytest.mark.asyncio
async def test_no_checkout_no_request_never_a_dead_link(svc, monkeypatch):
    """Stripe down → the deposit is skipped entirely, the booking untouched.
    The old /pay/deposit fallback texted a URL with no page behind it."""
    async def fake_get_config(merchant_id):
        return object()

    async def broken_checkout(booking, cfg, cents, **kw):
        raise RuntimeError("stripe_not_configured")

    _stub_module(monkeypatch, "merchant_config", get_merchant_config=fake_get_config)
    _stub_module(monkeypatch, "payment_links", create_deposit_checkout=broken_checkout)

    out = await svc.request(_booking(), 5000)
    assert out["sent"] is False
    assert out["reason"] == "checkout_unavailable"
    assert svc.store.updates == []


@pytest.mark.asyncio
async def test_unsendable_sms_waives_instead_of_arming_the_sweep(svc, monkeypatch):
    """The link never reached them, so the sweep must not cancel their
    booking over a deposit they were never asked for."""
    async def fake_send(phone, message):
        return {"sent": False, "reason": "carrier_rejected"}

    import src.sms.client as sms
    monkeypatch.setattr(sms, "send_sms", fake_send)
    _stub_checkout_rail(monkeypatch)

    out = await svc.request(_booking(), 5000)
    assert out["sent"] is False
    assert svc.store.updates[0][1]["deposit_status"] == "requested"
    assert svc.store.updates[1][1]["deposit_status"] == "waived"


# ── taking and giving back ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_capture_only_from_a_held_deposit(svc):
    out = await svc.capture(_booking(deposit_status="requested"))
    assert out["captured"] is False
    assert svc.store.updates == []


@pytest.mark.asyncio
async def test_capture_records_why(svc):
    out = await svc.capture(_booking(deposit_status="held", deposit_cents=5000))
    assert out["captured"] is True
    fields = svc.store.updates[0][1]
    assert fields["deposit_status"] == "captured"
    assert fields["cancel_reason"] == "no_show"


@pytest.mark.asyncio
async def test_release_gives_it_back(svc):
    out = await svc.release(_booking(deposit_status="held", deposit_cents=5000))
    assert out["released"] is True
    assert svc.store.updates[0][1]["deposit_status"] == "refunded"


@pytest.mark.asyncio
async def test_releasing_nothing_is_not_an_error(svc):
    out = await svc.release(_booking(deposit_status="none"))
    assert out["released"] is False


@pytest.mark.asyncio
async def test_expired_requests_are_returned_not_acted_on(svc):
    """The query reports; the sweep decides whether the slot goes back."""
    svc.store.rows = [{"id": "bk-9", "deposit_status": "requested"}]
    rows = await svc.expired_requests(60)
    assert rows and rows[0]["id"] == "bk-9"
    # Nothing was cancelled, captured or written.
    assert svc.store.updates == []


# ── the sweep ───────────────────────────────────────────────────────────

def _stub_sweep_aftermath(monkeypatch, sms_log=None):
    async def noop(*a, **kw):
        return {}

    async def fake_send(phone, message):
        if sms_log is not None:
            sms_log.append((phone, message))
        return {"sent": True}

    _stub_module(monkeypatch, "src.services.booking_sync", withdraw_booking=noop)
    _stub_module(monkeypatch, "src.services.booking_waitlist", recover_slot=noop)
    import src.sms.client as sms
    monkeypatch.setattr(sms, "send_sms", fake_send)


@pytest.mark.asyncio
async def test_sweep_releases_only_past_the_merchants_own_window(svc, monkeypatch):
    """One merchant holds 30 minutes, the other the 60-minute default. A row
    40 minutes old is released for the first and kept for the second."""
    now = datetime(2026, 9, 3, 12, 0, tzinfo=timezone.utc)
    stale = (now - timedelta(minutes=40)).isoformat()
    svc.store.rows = [
        {"id": "bk-a", "merchant_id": "m-short", "deposit_status": "requested",
         "deposit_requested_at": stale, "customer_phone": "+16045550100"},
        {"id": "bk-b", "merchant_id": "m-long", "deposit_status": "requested",
         "deposit_requested_at": stale, "customer_phone": "+16045550101"},
    ]
    svc.store.cfg_rows = [{"merchant_id": "m-short", "deposit_hold_minutes": 30}]
    texts: list[tuple[str, str]] = []
    _stub_sweep_aftermath(monkeypatch, texts)

    out = await dep.run_deposit_sweep(now=now)
    assert out == {"released": 1, "kept": 1}
    assert svc.store.cancelled == [("bk-a", "deposit not paid in time")]
    assert svc.store.updates[0][1]["deposit_status"] == "failed"
    assert texts and texts[0][0] == "+16045550100"


@pytest.mark.asyncio
async def test_sweep_never_captures(svc, monkeypatch):
    """Releasing a slot is not taking money — the sweep must never write
    'captured'; that word is reserved for an explicit human no-show."""
    now = datetime(2026, 9, 3, 12, 0, tzinfo=timezone.utc)
    svc.store.rows = [
        {"id": "bk-a", "merchant_id": "m1", "deposit_status": "requested",
         "deposit_requested_at": (now - timedelta(hours=3)).isoformat(),
         "customer_phone": ""},
    ]
    _stub_sweep_aftermath(monkeypatch)

    await dep.run_deposit_sweep(now=now)
    assert all(f.get("deposit_status") != "captured"
               for _, f in svc.store.updates)
