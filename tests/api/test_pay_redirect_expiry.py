"""Short-link (/p/{code}) must not bounce customers to a dead Stripe page for a
finished/expired checkout session — it shows a branded status page instead."""

import pytest

from src.api.routes import pay_redirect as pr


class _FakeDB:
    def __init__(self, row):
        self._row = row

    async def select(self, *a, **k):
        return [self._row] if self._row else []


async def _call(monkeypatch, row):
    monkeypatch.setattr(pr, "get_db", lambda: _FakeDB(row))
    return await pr.pay_redirect("abcd1234")


@pytest.mark.asyncio
async def test_open_session_redirects(monkeypatch):
    resp = await _call(monkeypatch, {"checkout_url": "https://checkout.stripe.com/x", "status": "open"})
    assert resp.status_code == 303
    assert resp.headers["location"] == "https://checkout.stripe.com/x"


@pytest.mark.asyncio
async def test_completed_session_shows_paid_page(monkeypatch):
    resp = await _call(monkeypatch, {"checkout_url": "https://checkout.stripe.com/x", "status": "complete"})
    assert resp.status_code == 200  # branded "already paid", not a redirect


@pytest.mark.asyncio
async def test_expired_session_shows_expired_page(monkeypatch):
    resp = await _call(monkeypatch, {"checkout_url": "https://checkout.stripe.com/x", "status": "expired"})
    assert resp.status_code == 410  # gone, branded — no bounce to dead Stripe URL
