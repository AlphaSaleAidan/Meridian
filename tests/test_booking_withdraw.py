"""Taking a cancelled booking back off the merchant's own calendar.

Run:
    python -m pytest tests/test_booking_withdraw.py -v

Why this exists: push_booking mirrored our bookings INTO the merchant's
calendar and nothing ever took them back out. Both adapters implemented
cancel_booking; no caller ever reached it. A caller who cancelled by phone
stayed on the shop's Square calendar for ever, so staff held a table for
someone who was not coming and the owner deleted it by hand — our product
making their day longer.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("ENCRYPTION_KEY", "0" * 64)

from src.services import booking_sync as sync  # noqa: E402
from src.services.booking_providers.base import Capabilities  # noqa: E402


class StubProvider:
    def __init__(self, *, can_cancel=True, raises=False, result=True):
        self.capabilities = Capabilities(
            summary="stub", read_busy=True, write_booking=True,
            cancel_booking=can_cancel,
        )
        self.calls: list[str] = []
        self.raises = raises
        self.result = result

    async def cancel_booking(self, connection, provider_booking_id):
        if self.raises:
            raise RuntimeError("square is down")
        self.calls.append(provider_booking_id)
        return self.result


class StubStore:
    def __init__(self, connections):
        self._connections = connections

    async def list_connections(self, merchant_id):
        return self._connections


def _booking(**over):
    base = {
        "id": "bk-1", "merchant_id": "m1",
        "provider": "square_appointments", "provider_booking_id": "sq-123",
    }
    base.update(over)
    return base


def _connection(**over):
    base = {"id": "conn-1", "merchant_id": "m1",
            "provider": "square_appointments", "status": "connected"}
    base.update(over)
    return base


@pytest.fixture
def wired(monkeypatch):
    """Returns a setter so each test picks its own provider + connections."""
    state: dict = {}

    def setup(provider, connections):
        state["provider"] = provider
        monkeypatch.setattr(sync, "get_provider", lambda key: provider)
        monkeypatch.setattr(sync, "get_booking_store",
                            lambda: StubStore(connections))
        return provider

    monkeypatch.setattr(sync, "_mark_error", lambda *a, **k: _noop())
    return setup


async def _noop():
    return None


@pytest.mark.asyncio
async def test_withdraws_from_the_connected_provider(wired):
    provider = wired(StubProvider(), [_connection()])
    assert await sync.withdraw_booking("m1", _booking()) is True
    assert provider.calls == ["sq-123"]


@pytest.mark.asyncio
async def test_nothing_pushed_means_nothing_to_withdraw(wired):
    """A booking that never reached their calendar must not send a cancel for
    an id that does not exist there."""
    provider = wired(StubProvider(), [_connection()])
    assert await sync.withdraw_booking("m1", _booking(provider_booking_id="")) is False
    assert await sync.withdraw_booking("m1", _booking(provider=None)) is False
    assert provider.calls == []


@pytest.mark.asyncio
async def test_skips_providers_that_cannot_cancel(wired):
    """An .ics feed is read-only — there is nothing on their side to remove."""
    provider = wired(StubProvider(can_cancel=False), [_connection()])
    assert await sync.withdraw_booking("m1", _booking()) is False
    assert provider.calls == []


@pytest.mark.asyncio
async def test_skips_a_disconnected_connection(wired):
    provider = wired(StubProvider(), [_connection(status="error")])
    assert await sync.withdraw_booking("m1", _booking()) is False
    assert provider.calls == []


@pytest.mark.asyncio
async def test_ignores_a_connection_for_a_different_provider(wired):
    provider = wired(StubProvider(), [_connection(provider="google_calendar")])
    assert await sync.withdraw_booking("m1", _booking()) is False
    assert provider.calls == []


@pytest.mark.asyncio
async def test_provider_outage_is_swallowed(wired):
    """The booking is ALREADY cancelled in our database when this runs. A
    failure here is a stale entry in their calendar, never an uncancelled
    booking, and must not raise into the caller's phone call."""
    wired(StubProvider(raises=True), [_connection()])
    assert await sync.withdraw_booking("m1", _booking()) is False


@pytest.mark.asyncio
async def test_store_failure_is_swallowed(monkeypatch):
    class Broken:
        async def list_connections(self, merchant_id):
            raise RuntimeError("db down")

    monkeypatch.setattr(sync, "get_provider", lambda key: StubProvider())
    monkeypatch.setattr(sync, "get_booking_store", lambda: Broken())
    assert await sync.withdraw_booking("m1", _booking()) is False
