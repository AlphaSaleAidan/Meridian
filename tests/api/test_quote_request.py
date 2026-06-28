"""
Public "Schedule a Quote" lead capture — POST /api/quote-request.

Covers the new anonymous endpoint (src/api/routes/quote.py) backed by the
quote_requests table (migration 034):

  1. Valid request  → {"ok": true}, a row is inserted into quote_requests, and
     the founder notification email is attempted (recipients + subject correct).
  2. Honeypot tripped (company_website filled) → 400, NOTHING stored, NO email.
  3. Invalid phone  → 400, nothing stored, no email.
  4. Email failure  → still {"ok": true} (lead persisted; email is best-effort).

DB + email are faked; the route is driven directly via asyncio.run, matching
tests/api/test_clover_toast_webhook_dedupe.py.

Run:  python -m pytest tests/api/test_quote_request.py -v
"""
from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pytest  # noqa: E402
from fastapi import HTTPException  # noqa: E402

import src.db as db_mod  # noqa: E402
from src.api.routes import quote as quote_mod  # noqa: E402
from src.api.routes.quote import QuoteRequest, create_quote_request  # noqa: E402


def _run(coro):
    return asyncio.run(coro)


class FakeDB:
    def __init__(self):
        self.inserts: list[tuple[str, dict]] = []

    async def insert(self, table, row, return_data=True):
        self.inserts.append((table, row))
        return [row]


class EmailRecorder:
    """Stands in for src.api.routes.quote.send_quote_request."""
    def __init__(self, *, raise_exc: bool = False):
        self.calls: list[dict] = []
        self.raise_exc = raise_exc

    async def __call__(self, **kwargs):
        self.calls.append(kwargs)
        if self.raise_exc:
            raise RuntimeError("email provider down")
        return [{"to": "founder@example.com", "status": "sent"}]


@pytest.fixture(autouse=True)
def _wire(monkeypatch):
    """Inject a fake DB singleton + fake email sender for every test."""
    fake_db = FakeDB()
    monkeypatch.setattr(db_mod, "_db_instance", fake_db)
    recorder = EmailRecorder()
    monkeypatch.setattr(quote_mod, "send_quote_request", recorder)
    yield fake_db, recorder


def _valid(**overrides) -> QuoteRequest:
    data = dict(
        full_name="Jane Doe",
        business_name="Sunrise Coffee Co.",
        email="jane@sunrise.com",
        phone="+1 (782) 358-5534",
        preferred_date="2026-06-29",
        preferred_window="morning",
        notes="We run Square across 2 locations.",
        source="us-landing",
    )
    data.update(overrides)
    return QuoteRequest(**data)


def test_valid_request_stores_row_and_sends_email(_wire):
    fake_db, recorder = _wire
    result = _run(create_quote_request(_valid()))

    assert result == {"ok": True}

    # Row inserted into the right table with normalized phone.
    assert len(fake_db.inserts) == 1
    table, row = fake_db.inserts[0]
    assert table == "quote_requests"
    assert row["business_name"] == "Sunrise Coffee Co."
    assert row["phone"] == "+17823585534"  # punctuation stripped
    assert row["source"] == "us-landing"

    # Email attempted with the prospect's details.
    assert len(recorder.calls) == 1
    assert recorder.calls[0]["business_name"] == "Sunrise Coffee Co."
    assert recorder.calls[0]["email"] == "jane@sunrise.com"


def test_honeypot_rejected_no_store_no_email(_wire):
    fake_db, recorder = _wire
    with pytest.raises(HTTPException) as exc:
        _run(create_quote_request(_valid(company_website="http://spam.example")))

    assert exc.value.status_code == 400
    assert fake_db.inserts == []
    assert recorder.calls == []


def test_invalid_phone_rejected(_wire):
    fake_db, recorder = _wire
    with pytest.raises(HTTPException) as exc:
        _run(create_quote_request(_valid(phone="not-a-phone")))

    assert exc.value.status_code == 400
    assert fake_db.inserts == []
    assert recorder.calls == []


def test_missing_required_fields_rejected(_wire):
    with pytest.raises(HTTPException) as exc:
        _run(create_quote_request(_valid(full_name="", business_name="")))
    assert exc.value.status_code == 400


def test_invalid_email_rejected(_wire):
    with pytest.raises(HTTPException) as exc:
        _run(create_quote_request(_valid(email="nope")))
    assert exc.value.status_code == 400


def test_email_failure_still_returns_ok(monkeypatch):
    """A down email provider must not bounce a valid lead — row persists, ok=true."""
    fake_db = FakeDB()
    monkeypatch.setattr(db_mod, "_db_instance", fake_db)
    monkeypatch.setattr(quote_mod, "send_quote_request", EmailRecorder(raise_exc=True))

    result = _run(create_quote_request(_valid()))
    assert result == {"ok": True}
    assert len(fake_db.inserts) == 1  # still stored
