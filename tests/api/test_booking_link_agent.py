"""The phone-agent side of texted booking links: prompt, tools, handler.

Run:
    python -m pytest tests/api/test_booking_link_agent.py -v

The load-bearing test here is test_prompt_never_contains_the_url. Everything
else is arrangement; that one is the mechanism. A model that can see the
address will eventually read it out no matter how firmly the prompt tells it
not to, so the address is simply absent and the tool is the only exit.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("ENCRYPTION_KEY", "0" * 64)

from src.api.routes import vapi_webhook as vw  # noqa: E402

URL = "https://mapletandoor.ca/reservations"


def _config(**over):
    base = dict(
        merchant_id="m1",
        business_name="Maple Tandoor",
        business_timezone="America/Vancouver",
        booking_mode="external_link",
        booking_noun="table",
        booking_link_url=URL,
        reservation_config=None,
        waitlist_enabled=False,
    )
    base.update(over)
    return SimpleNamespace(**base)


# ── mode detection ──────────────────────────────────────────────────────

def test_link_mode_requires_a_destination():
    """A link mode with nowhere to send anyone is an agent promising a text it
    cannot deliver, so it stays off."""
    assert vw._link_mode(_config()) is True
    assert vw._link_mode(_config(booking_link_url="")) is False


def test_link_mode_is_not_native_mode():
    assert vw._link_mode(_config(booking_mode="native")) is False
    assert vw._booking_enabled(_config()) is False


def test_off_merchants_get_neither():
    cfg = _config(booking_mode="off")
    assert vw._link_mode(cfg) is False
    assert vw._booking_tools(cfg) == []


# ── the prompt ──────────────────────────────────────────────────────────

def test_prompt_never_contains_the_url():
    block = vw._link_booking_block(_config())
    assert URL not in block
    assert "mapletandoor" not in block.lower()


def test_prompt_forbids_reading_the_address_and_forbids_asking_first():
    block = vw._link_booking_block(_config()).lower()
    assert "never say the web address out loud" in block
    assert "do not ask whether they" in block
    assert "text_booking_link" in block


def test_prompt_uses_the_merchant_noun():
    assert "tables" in vw._link_booking_block(_config(booking_noun="table"))
    assert "appointments" in vw._link_booking_block(_config(booking_noun="appointment"))


def test_reservation_block_routes_link_merchants_to_the_link_block():
    block = vw._reservation_block(_config(), ["reservation"])
    assert "text_booking_link" in block
    assert URL not in block


def test_existing_merchants_are_untouched():
    """booking_mode 'off' with the old questionnaire answer keeps the original
    spoken-URL wording, byte for byte — that is every merchant in production."""
    cfg = _config(
        booking_mode="off",
        booking_link_url="",
        reservation_config={"on_website": True, "website_url": URL},
    )
    block = vw._reservation_block(cfg, ["reservation"])
    assert f"book online at {URL}" in block
    assert "text_booking_link" not in block


# ── tools ───────────────────────────────────────────────────────────────

def test_link_mode_gets_exactly_one_tool():
    tools = vw._booking_tools(_config())
    names = [t["function"]["name"] for t in tools]
    assert names == ["text_booking_link"]


def test_link_mode_does_not_get_the_booking_engine_tools():
    """Offering check_availability to a merchant whose calendar lives
    elsewhere would let the agent promise times nobody is holding."""
    names = [t["function"]["name"] for t in vw._booking_tools(_config())]
    assert "check_availability" not in names
    assert "book_reservation" not in names


def test_phone_argument_is_optional():
    tool = vw._TEXT_BOOKING_LINK_TOOL["function"]
    assert tool["parameters"]["required"] == []


# ── the handler ─────────────────────────────────────────────────────────

class LinkSpy(list):
    """Records each send attempt; `result` is what the service pretends to
    return, so a test can flip success to failure mid-fixture."""
    result: dict = {}


@pytest.fixture
def link_calls(monkeypatch):
    spy = LinkSpy()
    spy.result = {"sent": True, "url": "https://api.test/b/abc1234",
                  "target": URL, "reason": ""}

    async def fake(config, to_phone, *, vapi_call_id="", request_base=""):
        spy.append({"phone": to_phone, "call_id": vapi_call_id})
        return spy.result

    monkeypatch.setattr("src.services.booking_links.text_booking_link", fake)
    return spy


@pytest.mark.asyncio
async def test_defaults_to_the_number_they_called_from(link_calls):
    await vw._handle_booking_tool(
        "text_booking_link", {}, _config(), caller_phone="+16045550100",
        vapi_call_id="call-9",
    )
    assert link_calls[0] == {"phone": "+16045550100", "call_id": "call-9"}


@pytest.mark.asyncio
async def test_explicit_phone_overrides_caller_id(link_calls):
    await vw._handle_booking_tool(
        "text_booking_link", {"phone": "+16045559999"}, _config(),
        caller_phone="+16045550100",
    )
    assert link_calls[0]["phone"] == "+16045559999"


@pytest.mark.asyncio
async def test_success_tells_the_agent_not_to_read_it_out(link_calls):
    out = await vw._handle_booking_tool(
        "text_booking_link", {}, _config(), caller_phone="+16045550100")
    assert "texted" in out.lower()
    assert "do not read the address out" in out.lower()


@pytest.mark.asyncio
async def test_failed_send_hands_back_the_address_to_read(link_calls):
    """The one situation where speaking a URL is the right answer."""
    link_calls.result = {"sent": False, "url": "", "target": URL,
                         "reason": "landline"}
    out = await vw._handle_booking_tool(
        "text_booking_link", {}, _config(), caller_phone="+16045550100")
    assert URL in out
    assert "could not be delivered" in out.lower()
    assert "call them back" in out.lower()


@pytest.mark.asyncio
async def test_no_phone_asks_for_one_rather_than_claiming_success(link_calls):
    link_calls.result = {"sent": False, "url": "", "target": URL,
                         "reason": "no_phone"}
    out = await vw._handle_booking_tool("text_booking_link", {}, _config())
    assert "ask them for a mobile number" in out.lower()
    assert "texted" not in out.lower()


@pytest.mark.asyncio
async def test_stale_assistant_cannot_text_for_a_merchant_who_turned_it_off(link_calls):
    """A Vapi assistant cached with the tool must not keep working after the
    merchant clears their URL."""
    out = await vw._handle_booking_tool(
        "text_booking_link", {}, _config(booking_link_url=""),
        caller_phone="+16045550100")
    assert "can't send a booking link" in out.lower()
    assert not link_calls
