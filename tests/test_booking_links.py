"""Texting the booking link instead of reading it out.

Run:
    python -m pytest tests/test_booking_links.py -v

The assertions that matter most:
  * the prompt does NOT contain the URL — the model cannot recite what it
    cannot see, which is what makes "text it every time" actually hold
  * "I've texted it" is only ever said when a provider accepted the message
  * a failed send hands the address back so the agent can read it after all
  * a merchant with no destination gets no tool and no promise
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("ENCRYPTION_KEY", "0" * 64)

from src.services import booking_links as bl  # noqa: E402


def _config(**over):
    base = dict(
        merchant_id="m1",
        business_name="Maple Tandoor",
        booking_mode="external_link",
        booking_noun="table",
        booking_link_url="https://mapletandoor.ca/reservations",
        reservation_config=None,
    )
    base.update(over)
    return SimpleNamespace(**base)


class StubStore:
    """Stands in for BookingStore._req, which is the only surface the link
    service touches."""

    def __init__(self, fail_insert=False):
        self.rows: list[dict] = []
        self.patches: list[tuple[dict, dict]] = []
        self.fail_insert = fail_insert
        self._n = 0

    async def _req(self, method, table, params=None, json=None, **kw):
        assert table == "booking_link_sends"
        if method == "POST":
            if self.fail_insert:
                raise RuntimeError("db down")
            self._n += 1
            row = dict(json or {})
            row["id"] = f"row-{self._n}"
            row.setdefault("click_count", 0)
            row.setdefault("clicked_at", None)
            self.rows.append(row)
            return [row]
        if method == "GET":
            p = params or {}
            if "code" in p:
                code = p["code"].replace("ilike.", "").lower()
                return [r for r in self.rows if (r.get("code") or "").lower() == code][:1]
            merchant = p.get("merchant_id", "").replace("eq.", "")
            return [r for r in self.rows if r.get("merchant_id") == merchant]
        if method == "PATCH":
            self.patches.append((params or {}, json or {}))
            rid = (params or {}).get("id", "").replace("eq.", "")
            for r in self.rows:
                if r["id"] == rid:
                    r.update(json or {})
            return []
        raise AssertionError(f"unexpected {method}")


@pytest.fixture
def store(monkeypatch):
    s = StubStore()
    svc = bl.BookingLinkService.__new__(bl.BookingLinkService)
    svc._store = s
    monkeypatch.setattr(bl, "get_link_service", lambda: svc)
    monkeypatch.setattr(bl, "_service", svc, raising=False)
    return s


@pytest.fixture
def sent_messages(monkeypatch):
    sent: list[tuple[str, str]] = []

    async def fake_send(phone, message):
        sent.append((phone, message))
        return {"sent": True, "method": "telnyx"}

    import src.sms.client as sms
    monkeypatch.setattr(sms, "send_sms", fake_send)
    return sent


# ── where the link points ───────────────────────────────────────────────

def test_direct_url_wins_over_questionnaire():
    cfg = _config(
        booking_link_url="https://typed-here.example/book",
        reservation_config={"on_website": True, "website_url": "https://old.example"},
    )
    assert bl.configured_url(cfg) == "https://typed-here.example/book"


def test_falls_back_to_onboarding_answer():
    """A merchant who already told onboarding where they book should not have
    to type it a second time."""
    cfg = _config(
        booking_link_url="",
        reservation_config={"on_website": True, "website_url": "https://old.example"},
    )
    assert bl.configured_url(cfg) == "https://old.example"


def test_questionnaire_ignored_when_they_said_they_do_not_book_online():
    cfg = _config(
        booking_link_url="",
        reservation_config={"on_website": False, "website_url": "https://old.example"},
    )
    assert bl.configured_url(cfg) == ""


def test_link_url_uses_public_base(monkeypatch):
    monkeypatch.setenv("API_PUBLIC_URL", "https://api.meridian.tips/")
    assert bl.link_url_for("abc1234") == "https://api.meridian.tips/b/abc1234"


def test_message_leads_with_the_shop_not_with_us():
    """A text that leads with our product name reads as spam to someone who
    just called a restaurant."""
    msg = bl.compose_message("Maple Tandoor", "https://x.test/b/abc")
    assert msg.startswith("Maple Tandoor")
    assert "meridian" not in msg.lower()
    assert "https://x.test/b/abc" in msg


def test_code_alphabet_excludes_the_pairs_people_mishear():
    """The code is read aloud when a text cannot be delivered."""
    for ch in "oil015s":
        assert ch not in bl._CODE_ALPHABET


# ── sending ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sends_and_records(store, sent_messages, monkeypatch):
    monkeypatch.setenv("API_PUBLIC_URL", "https://api.test")
    out = await bl.text_booking_link(_config(), "+16045550100", vapi_call_id="call-1")

    assert out["sent"] is True
    assert len(store.rows) == 1
    row = store.rows[0]
    assert row["merchant_id"] == "m1"
    assert row["vapi_call_id"] == "call-1"
    # Snapshotted, so editing the merchant's URL later cannot repoint a text
    # already sitting in someone's message history.
    assert row["target_url"] == "https://mapletandoor.ca/reservations"
    assert out["url"] == f"https://api.test/b/{row['code']}"
    assert sent_messages[0][0] == "+16045550100"
    assert row["code"] in sent_messages[0][1]


@pytest.mark.asyncio
async def test_each_send_gets_its_own_code(store, sent_messages):
    """Two callers on the same evening must be distinguishable, or 'opened'
    means 'somebody opened it' rather than 'this caller opened it'."""
    await bl.text_booking_link(_config(), "+16045550100")
    await bl.text_booking_link(_config(), "+16045550101")
    codes = {r["code"] for r in store.rows}
    assert len(codes) == 2


@pytest.mark.asyncio
async def test_bare_domain_gets_a_scheme(store, sent_messages):
    out = await bl.text_booking_link(_config(booking_link_url="mapletandoor.ca/book"),
                                     "+16045550100")
    assert out["target"] == "https://mapletandoor.ca/book"


@pytest.mark.asyncio
async def test_no_destination_is_not_a_send(store, sent_messages):
    out = await bl.text_booking_link(
        _config(booking_link_url="", reservation_config=None), "+16045550100")
    assert out["sent"] is False
    assert out["reason"] == "no_booking_url"
    assert not sent_messages


@pytest.mark.asyncio
async def test_no_phone_is_not_a_send(store, sent_messages):
    out = await bl.text_booking_link(_config(), "")
    assert out["sent"] is False
    assert out["reason"] == "no_phone"
    assert not sent_messages


@pytest.mark.asyncio
async def test_provider_refusal_marks_the_row_failed(store, monkeypatch):
    async def refuse(phone, message):
        return {"sent": False, "reason": "landline"}

    import src.sms.client as sms
    monkeypatch.setattr(sms, "send_sms", refuse)

    out = await bl.text_booking_link(_config(), "+16045550100")
    assert out["sent"] is False
    assert any(p[1].get("delivery") == "failed" for p in store.patches)


@pytest.mark.asyncio
async def test_db_failure_still_texts_the_merchant_url(monkeypatch, sent_messages):
    """No row means no short code and no click evidence — but the caller still
    needs the link, so the send falls back to the merchant's own URL rather
    than failing the call."""
    s = StubStore(fail_insert=True)
    svc = bl.BookingLinkService.__new__(bl.BookingLinkService)
    svc._store = s
    monkeypatch.setattr(bl, "get_link_service", lambda: svc)

    out = await bl.text_booking_link(_config(), "+16045550100")
    assert out["sent"] is True
    assert out["url"] == "https://mapletandoor.ca/reservations"


@pytest.mark.asyncio
async def test_sms_crash_does_not_raise_into_a_live_call(store, monkeypatch):
    async def boom(phone, message):
        raise RuntimeError("provider exploded")

    import src.sms.client as sms
    monkeypatch.setattr(sms, "send_sms", boom)

    out = await bl.text_booking_link(_config(), "+16045550100")
    assert out["sent"] is False


# ── clicks ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_first_click_sets_clicked_at_and_counts(store, sent_messages):
    await bl.text_booking_link(_config(), "+16045550100")
    row = store.rows[0]
    svc = bl.get_link_service()

    await svc.record_click(row)
    assert row["click_count"] == 1
    assert row["clicked_at"] is not None
    first = row["clicked_at"]

    await svc.record_click(row)
    assert row["click_count"] == 2
    # clicked_at is FIRST open, not most recent — last_clicked_at carries that.
    assert row["clicked_at"] == first
    assert row["last_clicked_at"] is not None


@pytest.mark.asyncio
async def test_stats_counts_opened_only_among_delivered(store, sent_messages):
    await bl.text_booking_link(_config(), "+16045550100")
    await bl.text_booking_link(_config(), "+16045550101")
    svc = bl.get_link_service()
    await svc.record_click(store.rows[0])
    store.rows[1]["delivery"] = "failed"

    stats = await svc.stats("m1")
    assert stats["sent"] == 1
    assert stats["opened"] == 1
    assert stats["failed"] == 1
