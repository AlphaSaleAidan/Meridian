"""
Meridian → Foundry lead bridge — src/services/foundry_bridge.py.

  1. Interest detector: website/CRM phrasing matches; POS/analytics phrasing —
     including "online ordering", which is Meridian's own product — does not.
  2. Env-gated: without FOUNDRY_INBOUND_URL/KEY the bridge is inert (no HTTP).
  3. Happy path: website-shaped row → POST with the shared-key header and the
     Foundry inbound payload shape; Canada source maps to meridian-quote-canada.
  4. Transport failure → False, never raises (prospect's response is sacred).

Run:  python -m pytest tests/services/test_foundry_bridge.py -v
"""
from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import httpx  # noqa: E402
import pytest  # noqa: E402

from src.services import foundry_bridge  # noqa: E402


def _run(coro):
    return asyncio.run(coro)


def _row(**overrides) -> dict:
    row = {
        "business_name": "Maple Tandoor",
        "full_name": "Priya N",
        "email": "priya@example.com",
        "phone": "+12368324333",
        "preferred_date": "2026-08-11",
        "preferred_window": "morning",
        "notes": "We need a new website for the restaurant",
        "source": "us-landing",
    }
    row.update(overrides)
    return row


# ── 1. interest detector ─────────────────────────────────────


@pytest.mark.parametrize(
    "notes",
    [
        "we need a new website",
        "Our web site is ancient",
        "looking for a landing page",
        "help with web design",
        "want an online store",
        "ecommerce setup",
        "e-commerce setup",
        "need a custom CRM for my reps",
    ],
)
def test_website_phrasing_matches(notes):
    assert foundry_bridge.is_website_interest(notes)


@pytest.mark.parametrize(
    "notes",
    [
        "",
        "interested in the phone agent",
        "POS analytics demo please",
        "want online ordering for my restaurant",  # Meridian product, not a build
        "call me about pricing",
    ],
)
def test_non_website_phrasing_does_not_match(notes):
    assert not foundry_bridge.is_website_interest(notes)


# ── 2. env gate ──────────────────────────────────────────────


def test_inert_without_env(monkeypatch):
    monkeypatch.delenv("FOUNDRY_INBOUND_URL", raising=False)
    monkeypatch.delenv("FOUNDRY_INBOUND_KEY", raising=False)

    def _no_http(*a, **k):  # any HTTP attempt is a test failure
        raise AssertionError("bridge must not call out without env")

    monkeypatch.setattr(httpx, "AsyncClient", _no_http)
    assert _run(foundry_bridge.forward_quote_lead(_row())) is False


def test_non_website_row_never_forwards(monkeypatch):
    monkeypatch.setenv("FOUNDRY_INBOUND_URL", "https://foundry.test/inbound")
    monkeypatch.setenv("FOUNDRY_INBOUND_KEY", "k")

    def _no_http(*a, **k):
        raise AssertionError("non-website lead must not be forwarded")

    monkeypatch.setattr(httpx, "AsyncClient", _no_http)
    row = _row(notes="POS analytics demo please")
    assert _run(foundry_bridge.forward_quote_lead(row)) is False


# ── 3. happy path ────────────────────────────────────────────


class FakeResponse:
    def __init__(self, status_code=200, body=None, text=""):
        self.status_code = status_code
        self._body = body or {"leadId": "lead-1"}
        self.text = text

    def json(self):
        return self._body


class FakeClient:
    """Records the POST the bridge makes."""

    calls: list[dict] = []
    response: FakeResponse = FakeResponse()
    raise_exc: Exception | None = None

    def __init__(self, timeout=None):
        self.timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, url, json=None, headers=None):
        if FakeClient.raise_exc is not None:
            raise FakeClient.raise_exc
        FakeClient.calls.append({"url": url, "json": json, "headers": headers})
        return FakeClient.response


@pytest.fixture(autouse=True)
def _reset_fake_client():
    FakeClient.calls = []
    FakeClient.response = FakeResponse()
    FakeClient.raise_exc = None
    yield


def test_forwards_website_lead_with_key_header(monkeypatch):
    monkeypatch.setenv("FOUNDRY_INBOUND_URL", "https://foundry.test/inbound")
    monkeypatch.setenv("FOUNDRY_INBOUND_KEY", "sekret")
    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)

    assert _run(foundry_bridge.forward_quote_lead(_row())) is True
    assert len(FakeClient.calls) == 1
    call = FakeClient.calls[0]
    assert call["url"] == "https://foundry.test/inbound"
    assert call["headers"] == {"x-foundry-inbound-key": "sekret"}
    payload = call["json"]
    assert payload["company"] == "Maple Tandoor"
    assert payload["contactName"] == "Priya N"
    assert payload["email"] == "priya@example.com"
    assert payload["phone"] == "+12368324333"
    assert payload["source"] == "meridian-quote-us"
    assert "Preferred call window: 2026-08-11 morning" in payload["notes"]


def test_canada_source_maps_to_canada(monkeypatch):
    monkeypatch.setenv("FOUNDRY_INBOUND_URL", "https://foundry.test/inbound")
    monkeypatch.setenv("FOUNDRY_INBOUND_KEY", "sekret")
    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)

    _run(foundry_bridge.forward_quote_lead(_row(source="canada-landing")))
    assert FakeClient.calls[0]["json"]["source"] == "meridian-quote-canada"


def test_missing_phone_key_omitted(monkeypatch):
    monkeypatch.setenv("FOUNDRY_INBOUND_URL", "https://foundry.test/inbound")
    monkeypatch.setenv("FOUNDRY_INBOUND_KEY", "sekret")
    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)

    _run(foundry_bridge.forward_quote_lead(_row(phone="")))
    assert "phone" not in FakeClient.calls[0]["json"]


# ── 4. failure isolation ─────────────────────────────────────


def test_transport_error_returns_false(monkeypatch):
    monkeypatch.setenv("FOUNDRY_INBOUND_URL", "https://foundry.test/inbound")
    monkeypatch.setenv("FOUNDRY_INBOUND_KEY", "sekret")
    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
    FakeClient.raise_exc = httpx.ConnectTimeout("boom")

    assert _run(foundry_bridge.forward_quote_lead(_row())) is False


def test_rejection_returns_false(monkeypatch):
    monkeypatch.setenv("FOUNDRY_INBOUND_URL", "https://foundry.test/inbound")
    monkeypatch.setenv("FOUNDRY_INBOUND_KEY", "sekret")
    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
    FakeClient.response = FakeResponse(status_code=400, body={}, text="invalid lead")

    assert _run(foundry_bridge.forward_quote_lead(_row())) is False
