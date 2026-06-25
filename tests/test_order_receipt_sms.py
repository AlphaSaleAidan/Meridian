"""
Order-receipt SMS — logic coverage for the phone agent.

Mocks httpx so no network. Pins: receipt formatting (qty/size/total), the
safe early-return when from/to/key is missing (NO send attempted), the exact
Telnyx payload, messaging-profile passthrough, and never-raises behaviour.
"""
import sys
import types
from pathlib import Path

import pytest

_DIR = str(Path(__file__).resolve().parents[1] / "services" / "phone_agent")
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)

import sms_receipt as sr  # noqa: E402

aio = pytest.mark.asyncio


class _Cfg:
    business_name = "Tap Room"
    phone_number = "+17823585534"


def test_receipt_text_qty_size_total():
    order = {"items": [
        {"name": "Cheeseburger", "quantity": 2, "unit_price": 9.5},
        {"name": "Cola", "quantity": 1, "price": 3.0, "size": "Large"},
    ]}
    txt = sr.order_receipt_text(order, _Cfg())
    assert "Tap Room — your order:" in txt
    assert "2x Cheeseburger" in txt
    assert "1x Cola (Large)" in txt
    # 2*9.5 + 1*3.0 = 22.00
    assert "Total: $22.00" in txt
    assert txt.endswith("Thanks for ordering by phone!")


def test_receipt_text_no_prices_omits_total():
    txt = sr.order_receipt_text({"items": [{"name": "Water", "quantity": 1}]}, _Cfg())
    assert "Total:" not in txt
    assert "1x Water" in txt


def _spy_httpx(monkeypatch):
    """Install a fake httpx whose AsyncClient.post records the call."""
    calls = []

    class _Resp:
        status_code = 200

    class _Client:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, json=None, headers=None):
            calls.append({"url": url, "json": json, "headers": headers})
            return _Resp()

    fake = types.ModuleType("httpx")
    fake.AsyncClient = _Client
    monkeypatch.setitem(sys.modules, "httpx", fake)
    return calls


@aio
async def test_send_skips_without_credentials(monkeypatch):
    calls = _spy_httpx(monkeypatch)
    monkeypatch.delenv("TELNYX_API_KEY", raising=False)
    monkeypatch.delenv("TELNYX_PHONE_NUMBER", raising=False)
    # no key, no from -> must NOT attempt a send
    await sr.send_order_sms("+16044175584", "hi", frm="")
    assert calls == [], "should not call Telnyx without credentials"


@aio
async def test_send_builds_correct_payload(monkeypatch):
    calls = _spy_httpx(monkeypatch)
    monkeypatch.setenv("TELNYX_API_KEY", "KEYabc")
    monkeypatch.setenv("TELNYX_MESSAGING_PROFILE_ID", "prof-1")
    await sr.send_order_sms("+16044175584", "your order", frm="+17823585534")
    assert len(calls) == 1
    c = calls[0]
    assert c["url"] == "https://api.telnyx.com/v2/messages"
    assert c["json"]["from"] == "+17823585534"  # merchant DID wins over env
    assert c["json"]["to"] == "+16044175584"
    assert c["json"]["text"] == "your order"
    assert c["json"]["messaging_profile_id"] == "prof-1"
    assert c["headers"]["Authorization"] == "Bearer KEYabc"


@aio
async def test_send_falls_back_to_env_from(monkeypatch):
    calls = _spy_httpx(monkeypatch)
    monkeypatch.setenv("TELNYX_API_KEY", "KEYabc")
    monkeypatch.setenv("TELNYX_PHONE_NUMBER", "+15555550100")
    monkeypatch.delenv("TELNYX_MESSAGING_PROFILE_ID", raising=False)
    await sr.send_order_sms("+16044175584", "your order")  # no frm passed
    assert calls[0]["json"]["from"] == "+15555550100"
    assert "messaging_profile_id" not in calls[0]["json"]


@aio
async def test_send_never_raises_on_http_error(monkeypatch):
    monkeypatch.setenv("TELNYX_API_KEY", "KEYabc")
    monkeypatch.setenv("TELNYX_PHONE_NUMBER", "+15555550100")

    class _Boom:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, *a, **k):
            raise RuntimeError("network down")

    fake = types.ModuleType("httpx")
    fake.AsyncClient = _Boom
    monkeypatch.setitem(sys.modules, "httpx", fake)
    # must swallow the error — a failed text never breaks the call/order
    await sr.send_order_sms("+16044175584", "your order")
