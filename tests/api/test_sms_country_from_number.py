"""
Per-country SMS from-number selection.

All outbound SMS used to send from the single US DID in TELNYX_PHONE_NUMBER,
which has no 10DLC registration — US→US messages queue at the carrier forever.
Canada and the US share +1, so the destination country has to be read off the
NANP area code, not the dial prefix.

Covers:
  1. src.sms.from_number.sms_from_number: US destination → default, Canadian
     destination with TELNYX_PHONE_NUMBER_CA set → the Canadian DID, Canadian
     destination without the env → default, garbage/blank input → default.
  2. Both central send paths (services/phone_agent/sms_checkout for pay-link +
     receipts, src/sms/client for invoices + alerts) put the selected number in
     the Telnyx `from` field, and drop messaging_profile_id when a
     country-specific DID is used (it lives on its own profile).

Run:  python -m pytest tests/api/test_sms_country_from_number.py -v
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "services", "phone_agent")
    ),
)
os.environ.setdefault("ENCRYPTION_KEY", "0" * 64)

import sms_checkout  # noqa: E402
import src.sms.client as sms_client  # noqa: E402
from src.sms.from_number import (  # noqa: E402
    is_canadian_destination,
    sms_from_number,
)

aio = pytest.mark.asyncio

US_FROM = "+16185550100"
CA_FROM = "+15145550199"


class _Resp:
    status_code = 200
    text = ""

    def json(self):
        return {"data": {"id": "msg_1"}}


class _Client:
    def __init__(self):
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, json=None, headers=None, timeout=None):
        self.calls.append(json)
        return _Resp()


# ─── helper ───────────────────────────────────────────────────
def test_us_destination_keeps_default(monkeypatch):
    monkeypatch.setenv("TELNYX_PHONE_NUMBER_CA", CA_FROM)
    # 212 New York, 415 San Francisco, 618 southern Illinois
    for dest in ("+12125550123", "+14155550123", "+16185550123"):
        assert sms_from_number(dest, US_FROM) == US_FROM
        assert is_canadian_destination(dest) is False


def test_canadian_destination_uses_ca_number(monkeypatch):
    monkeypatch.setenv("TELNYX_PHONE_NUMBER_CA", CA_FROM)
    # 514 Montreal, 604 Vancouver, 416 Toronto, 902 Halifax, 236 BC overlay
    for dest in ("+15145550123", "+16045550123", "+14165550123",
                 "+19025550123", "+12365550123"):
        assert sms_from_number(dest, US_FROM) == CA_FROM
        assert is_canadian_destination(dest) is True


def test_canadian_destination_falls_back_without_env(monkeypatch):
    monkeypatch.delenv("TELNYX_PHONE_NUMBER_CA", raising=False)
    assert sms_from_number("+15145550123", US_FROM) == US_FROM
    # Blank/whitespace env is treated as unset, not as an empty from-number.
    monkeypatch.setenv("TELNYX_PHONE_NUMBER_CA", "   ")
    assert sms_from_number("+15145550123", US_FROM) == US_FROM


def test_unparseable_destination_falls_back(monkeypatch):
    monkeypatch.setenv("TELNYX_PHONE_NUMBER_CA", CA_FROM)
    for dest in ("", "   ", "not a phone", "+1", "+15145", "+445145550123",
                 "+15145550123456789", None):
        assert sms_from_number(dest, US_FROM) == US_FROM


def test_accepts_unnormalized_canadian_shapes(monkeypatch):
    monkeypatch.setenv("TELNYX_PHONE_NUMBER_CA", CA_FROM)
    for dest in ("(514) 555-0123", "514-555-0123", "15145550123", "5145550123"):
        assert sms_from_number(dest, US_FROM) == CA_FROM


def test_default_comes_from_env_when_not_passed(monkeypatch):
    monkeypatch.setenv("TELNYX_PHONE_NUMBER", US_FROM)
    monkeypatch.delenv("TELNYX_PHONE_NUMBER_CA", raising=False)
    assert sms_from_number("+12125550123") == US_FROM


# ─── phone_agent send path (pay link + receipts) ──────────────
@aio
async def test_checkout_sms_sends_from_ca_number(monkeypatch):
    monkeypatch.setenv("TELNYX_API_KEY", "k")
    monkeypatch.setenv("TELNYX_PHONE_NUMBER", US_FROM)
    monkeypatch.setenv("TELNYX_PHONE_NUMBER_CA", CA_FROM)
    monkeypatch.setenv("TELNYX_MESSAGING_PROFILE_ID", "prof_us")
    client = _Client()
    monkeypatch.setattr(sms_checkout.httpx, "AsyncClient", lambda *a, **k: client)

    res = await sms_checkout.send_sms("+15145550123", "Pay here: https://x/p/1")

    assert res["sent"] is True
    assert client.calls[0]["from"] == CA_FROM
    # The CA DID is on its own messaging profile — don't pin the US one.
    assert "messaging_profile_id" not in client.calls[0]


@aio
async def test_checkout_sms_us_keeps_default_and_profile(monkeypatch):
    monkeypatch.setenv("TELNYX_API_KEY", "k")
    monkeypatch.setenv("TELNYX_PHONE_NUMBER", US_FROM)
    monkeypatch.setenv("TELNYX_PHONE_NUMBER_CA", CA_FROM)
    monkeypatch.setenv("TELNYX_MESSAGING_PROFILE_ID", "prof_us")
    client = _Client()
    monkeypatch.setattr(sms_checkout.httpx, "AsyncClient", lambda *a, **k: client)

    await sms_checkout.send_sms("+12125550123", "Pay here: https://x/p/1")

    assert client.calls[0]["from"] == US_FROM
    assert client.calls[0]["messaging_profile_id"] == "prof_us"


@aio
async def test_checkout_sms_unset_ca_env_is_unchanged(monkeypatch):
    monkeypatch.setenv("TELNYX_API_KEY", "k")
    monkeypatch.setenv("TELNYX_PHONE_NUMBER", US_FROM)
    monkeypatch.delenv("TELNYX_PHONE_NUMBER_CA", raising=False)
    monkeypatch.setenv("TELNYX_MESSAGING_PROFILE_ID", "prof_us")
    client = _Client()
    monkeypatch.setattr(sms_checkout.httpx, "AsyncClient", lambda *a, **k: client)

    await sms_checkout.send_sms("+15145550123", "Pay here: https://x/p/1")

    assert client.calls[0]["from"] == US_FROM
    assert client.calls[0]["messaging_profile_id"] == "prof_us"


# ─── src/sms send path (invoices + alerts) ────────────────────
@aio
async def test_invoice_sms_sends_from_ca_number(monkeypatch):
    monkeypatch.setenv("TELNYX_PHONE_NUMBER_CA", CA_FROM)
    monkeypatch.setattr(sms_client, "TELNYX_API_KEY", "k")
    monkeypatch.setattr(sms_client, "TELNYX_FROM", US_FROM)
    monkeypatch.setattr(sms_client, "TELNYX_PROFILE_ID", "prof_us")
    client = _Client()
    monkeypatch.setattr(sms_client.httpx, "AsyncClient", lambda *a, **k: client)

    res = await sms_client.send_sms("+16045550123", "invoice ready")

    assert res["sent"] is True
    assert client.calls[0]["from"] == CA_FROM
    assert "messaging_profile_id" not in client.calls[0]


@aio
async def test_invoice_sms_us_keeps_default_and_profile(monkeypatch):
    monkeypatch.setenv("TELNYX_PHONE_NUMBER_CA", CA_FROM)
    monkeypatch.setattr(sms_client, "TELNYX_API_KEY", "k")
    monkeypatch.setattr(sms_client, "TELNYX_FROM", US_FROM)
    monkeypatch.setattr(sms_client, "TELNYX_PROFILE_ID", "prof_us")
    client = _Client()
    monkeypatch.setattr(sms_client.httpx, "AsyncClient", lambda *a, **k: client)

    await sms_client.send_sms("+12125550123", "invoice ready")

    assert client.calls[0]["from"] == US_FROM
    assert client.calls[0]["messaging_profile_id"] == "prof_us"
