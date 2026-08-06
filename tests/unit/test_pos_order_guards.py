"""
Tests for the layered guards in create_pos_order.

The plan moved from sandbox Square to live production credentials on
2026-06-04. Under the sandbox plan, a bug that fired a Square call hit
fake money. Under the live-creds plan, "no money risk on the demo
path" rests entirely on the correctness of the guard logic. These
tests exercise that guard from the populated-token side, so the claim
is tested rather than asserted.

What we're proving:

  1. NULL / empty token + empty system → logs-only (existing behaviour).
  2. Populated token + demo_safe=True   → logs-only (new guard layer 2).
  3. Populated token + POS_ORDERS_DISABLED env → logs-only (killswitch).
  4. Populated token + clean config     → Square call attempted.

Plus a few targeted edge cases:
  - Whitespace-only token treated as empty.
  - Square configured without location_id refused before HTTP fires.

The Square branch is mocked at services.phone_agent.pos_connector
._create_square_order so the test never makes real HTTP calls.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

# Sidecar path injection mirrors how main.py / sms_order.py load it.
_PHONE_AGENT_DIR = (
    Path(__file__).resolve().parents[2] / "services" / "phone_agent"
)
if str(_PHONE_AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(_PHONE_AGENT_DIR))

import pos_connector  # noqa: E402


SAMPLE_ORDER = {
    "customer_name": "Test Caller",
    "order_type": "pickup",
    "items": [{"name": "Cheeseburger", "quantity": 1}],
    "caller_phone": "+14165551234",
}

# A token-shaped string. Length and structure don't matter; only that
# the guard sees it as "present" (truthy after .strip()).
POPULATED_TOKEN = "EAAAxx_fake_square_token_for_test_only"
LOCATION_ID = "L_FAKE_LOCATION"


# ──────────────────────────────────────────────────────────────────────
# Layer 1 — POS_ORDERS_DISABLED killswitch
# ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pos_orders_disabled_killswitch_blocks_populated_config(monkeypatch):
    """POS_ORDERS_DISABLED=1 overrides everything else, even a clean
    populated config that would otherwise fire."""
    monkeypatch.setenv("POS_ORDERS_DISABLED", "1")

    with patch.object(pos_connector, "_create_square_order", new=AsyncMock()) as fake_square:
        result = await pos_connector.create_pos_order(
            order=SAMPLE_ORDER,
            pos_system="square",
            access_token=POPULATED_TOKEN,
            location_id=LOCATION_ID,
            demo_safe=False,
        )

    assert result == {"success": False, "reason": "pos_orders_disabled"}
    fake_square.assert_not_called()


# ──────────────────────────────────────────────────────────────────────
# Layer 2 — demo_safe per-merchant flag
# ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_demo_safe_blocks_populated_token(monkeypatch):
    """The load-bearing test: a demo merchant whose pos_access_token has
    been populated (by accidental OAuth, paste error, etc.) STILL does
    not fire a live Square call."""
    monkeypatch.delenv("POS_ORDERS_DISABLED", raising=False)

    with patch.object(pos_connector, "_create_square_order", new=AsyncMock()) as fake_square:
        result = await pos_connector.create_pos_order(
            order=SAMPLE_ORDER,
            pos_system="square",
            access_token=POPULATED_TOKEN,
            location_id=LOCATION_ID,
            demo_safe=True,
        )

    assert result == {"success": False, "reason": "demo_safe"}
    fake_square.assert_not_called()


@pytest.mark.asyncio
async def test_demo_safe_default_false_does_not_block(monkeypatch):
    """Real merchants (demo_safe defaults to False) are NOT incorrectly
    blocked by the new guard."""
    monkeypatch.delenv("POS_ORDERS_DISABLED", raising=False)

    with patch.object(
        pos_connector,
        "_create_square_order",
        new=AsyncMock(return_value={"success": True, "pos_order_id": "sq_test"}),
    ) as fake_square:
        result = await pos_connector.create_pos_order(
            order=SAMPLE_ORDER,
            pos_system="square",
            access_token=POPULATED_TOKEN,
            location_id=LOCATION_ID,
            # demo_safe omitted — should default to False
        )

    assert result == {"success": True, "pos_order_id": "sq_test"}
    fake_square.assert_called_once()


# ──────────────────────────────────────────────────────────────────────
# Layer 3 — input sanitisation (NULL / whitespace tokens)
# ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_empty_token_returns_logs_only(monkeypatch):
    monkeypatch.delenv("POS_ORDERS_DISABLED", raising=False)

    with patch.object(pos_connector, "_create_square_order", new=AsyncMock()) as fake_square:
        result = await pos_connector.create_pos_order(
            order=SAMPLE_ORDER,
            pos_system="square",
            access_token="",
            location_id=LOCATION_ID,
        )

    assert result == {"success": False, "reason": "no_pos_configured"}
    fake_square.assert_not_called()


@pytest.mark.asyncio
async def test_whitespace_token_treated_as_empty(monkeypatch):
    """A token of `   ` would pass `if not access_token` because non-empty
    strings are truthy. The .strip() in the new guard catches it."""
    monkeypatch.delenv("POS_ORDERS_DISABLED", raising=False)

    with patch.object(pos_connector, "_create_square_order", new=AsyncMock()) as fake_square:
        result = await pos_connector.create_pos_order(
            order=SAMPLE_ORDER,
            pos_system="square",
            access_token="   \t  ",
            location_id=LOCATION_ID,
        )

    assert result == {"success": False, "reason": "no_pos_configured"}
    fake_square.assert_not_called()


@pytest.mark.asyncio
async def test_empty_pos_system_returns_logs_only(monkeypatch):
    monkeypatch.delenv("POS_ORDERS_DISABLED", raising=False)

    with patch.object(pos_connector, "_create_square_order", new=AsyncMock()) as fake_square:
        result = await pos_connector.create_pos_order(
            order=SAMPLE_ORDER,
            pos_system="",
            access_token=POPULATED_TOKEN,
            location_id=LOCATION_ID,
        )

    assert result == {"success": False, "reason": "no_pos_configured"}
    fake_square.assert_not_called()


# ──────────────────────────────────────────────────────────────────────
# Layer 4 — POS-specific requirements
# ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_square_without_location_id_refused(monkeypatch):
    """Square requires location_id. Refusing before HTTP fires beats
    relying on Square to return a clean 400."""
    monkeypatch.delenv("POS_ORDERS_DISABLED", raising=False)

    with patch.object(pos_connector, "_create_square_order", new=AsyncMock()) as fake_square:
        result = await pos_connector.create_pos_order(
            order=SAMPLE_ORDER,
            pos_system="square",
            access_token=POPULATED_TOKEN,
            location_id="",
        )

    assert result == {"success": False, "reason": "square_missing_location_id"}
    fake_square.assert_not_called()


# ──────────────────────────────────────────────────────────────────────
# Layer ordering — killswitch beats demo_safe beats logs-only
# ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_killswitch_takes_precedence_over_demo_safe(monkeypatch):
    monkeypatch.setenv("POS_ORDERS_DISABLED", "1")

    result = await pos_connector.create_pos_order(
        order=SAMPLE_ORDER,
        pos_system="square",
        access_token=POPULATED_TOKEN,
        location_id=LOCATION_ID,
        demo_safe=True,
    )

    assert result == {"success": False, "reason": "pos_orders_disabled"}


# ──────────────────────────────────────────────────────────────────────
# Square payload correctness — currency must be uppercase ISO
# ──────────────────────────────────────────────────────────────────────

class _CapturingClient:
    """Minimal httpx.AsyncClient stand-in that records the POST payload."""

    def __init__(self, calls):
        self._calls = calls

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, url, json=None, headers=None, timeout=None):
        self._calls.append(json)

        class _Res:
            status_code = 200

            @staticmethod
            def json():
                return {"order": {"id": "sq-test-1"}}

        return _Res()


@pytest.mark.asyncio
async def test_square_currency_is_uppercased(monkeypatch):
    """The normalizer carries lowercase currency ("usd"/"cad" — Stripe's
    convention); Square's Currency enum is uppercase ISO and 400s
    (INVALID_ENUM_VALUE) on the raw value, killing every kitchen ticket.
    The connector must uppercase at the Square boundary."""
    calls: list = []
    monkeypatch.setattr(
        pos_connector.httpx, "AsyncClient", lambda: _CapturingClient(calls)
    )

    result = await pos_connector._create_square_order(
        order={
            "merchant_id": "m1",
            "currency": "cad",
            "customer_name": "Test",
            "order_type": "pickup",
            "items": [{"name": "Samosa", "quantity": 1, "unit_price": 5.0}],
        },
        access_token="tok",
        location_id="LOC1",
    )

    assert result["success"] is True
    assert calls[0]["order"]["line_items"][0]["base_price_money"]["currency"] == "CAD"


@pytest.mark.asyncio
async def test_square_currency_defaults_to_usd_when_absent(monkeypatch):
    calls: list = []
    monkeypatch.setattr(
        pos_connector.httpx, "AsyncClient", lambda: _CapturingClient(calls)
    )

    await pos_connector._create_square_order(
        order={
            "merchant_id": "m1",
            "customer_name": "Test",
            "order_type": "pickup",
            "items": [{"name": "Samosa", "quantity": 1, "unit_price": 5.0}],
        },
        access_token="tok",
        location_id="LOC1",
    )

    assert calls[0]["order"]["line_items"][0]["base_price_money"]["currency"] == "USD"
