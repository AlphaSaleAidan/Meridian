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
        self.rows: list[dict] = []

    async def update_booking(self, booking_id, fields):
        self.updates.append((booking_id, fields))
        return {"id": booking_id, **fields}

    async def _req(self, method, table, params=None, json=None, **kw):
        return self.rows


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
async def test_requesting_marks_the_booking_and_texts(svc, monkeypatch):
    sent: list[tuple[str, str]] = []

    async def fake_send(phone, message):
        sent.append((phone, message))
        return {"sent": True}

    import src.sms.client as sms
    monkeypatch.setattr(sms, "send_sms", fake_send)

    class Links:
        async def record_send(self, *a, **kw):
            return {"id": "row-1", "code": "abc1234"}

    monkeypatch.setattr("src.services.booking_links.get_link_service", lambda: Links())
    monkeypatch.setenv("API_PUBLIC_URL", "https://api.test")

    out = await svc.request(_booking(), 5000)
    assert out["sent"] is True
    assert svc.store.updates[0][1]["deposit_status"] == "requested"
    assert svc.store.updates[0][1]["deposit_cents"] == 5000
    assert "$50" in sent[0][1]


@pytest.mark.asyncio
async def test_zero_deposit_asks_for_nothing(svc):
    out = await svc.request(_booking(), 0)
    assert out["sent"] is False
    assert out["reason"] == "no_deposit_required"
    assert svc.store.updates == []


@pytest.mark.asyncio
async def test_no_phone_leaves_it_requested_not_paid(svc):
    """A booking we cannot chase must not quietly read as settled."""
    out = await svc.request(_booking(customer_phone=""), 5000)
    assert out["sent"] is False
    assert out["reason"] == "no_phone"
    assert svc.store.updates[0][1]["deposit_status"] == "requested"


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
    """The sweep reports; a human decides whether the slot goes back."""
    svc.store.rows = [{"id": "bk-9", "deposit_status": "requested"}]
    rows = await svc.expired_requests(60)
    assert rows and rows[0]["id"] == "bk-9"
    # Nothing was cancelled, captured or written.
    assert svc.store.updates == []
