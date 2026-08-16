"""Cancellation recovery — matching, ranking, exclusive holds, and the chain.

Run:
    python -m pytest tests/test_booking_waitlist.py -v

The assertions that matter most:
  * a no-show history outranks a big spend (turning up beats spending)
  * with no history at all, order is arrival time and says so
  * the offer HOLDS the slot, and a failed notification releases it
  * an expired offer rolls down to the next guest without anyone touching it
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("ENCRYPTION_KEY", "0" * 64)

from src.services import booking_waitlist as wl  # noqa: E402
from src.services.booking_store import SlotTaken  # noqa: E402

NOW = datetime(2026, 9, 14, 16, 0, tzinfo=timezone.utc)
SLOT_START = datetime(2026, 9, 14, 23, 0, tzinfo=timezone.utc)   # 7pm Toronto
SLOT_END = datetime(2026, 9, 15, 0, 30, tzinfo=timezone.utc)


def _entry(eid, name, phone, party=2, **over):
    base = {
        "id": eid, "merchant_id": "m1", "customer_name": name,
        "customer_phone": phone, "party_size": party,
        "window_start": "2026-09-14T21:00:00+00:00",
        "window_end": "2026-09-15T03:00:00+00:00",
        "min_notice_minutes": 60, "status": "waiting", "offer_count": 0,
        "created_at": "2026-09-14T10:00:00+00:00",
    }
    base.update(over)
    return base


def _cancelled(**over):
    base = {
        "id": "bk-cancelled", "merchant_id": "m1", "resource_id": "res-1",
        "starts_at": SLOT_START.isoformat(), "ends_at": SLOT_END.isoformat(),
        "duration_minutes": 90, "party_size": 2,
    }
    base.update(over)
    return base


class StubStore:
    def __init__(self, entries=None, collide=False):
        self.entries = entries or []
        self.collide = collide
        self.created: list[dict] = []
        self.updates: list[tuple[str, dict]] = []
        self.waitlist_updates: list[tuple[str, dict]] = []
        self.bookings: dict[str, dict] = {}

    async def list_waitlist(self, merchant_id, status="waiting"):
        return [e for e in self.entries if e.get("status") == status]

    async def update_waitlist(self, entry_id, fields):
        self.waitlist_updates.append((str(entry_id), fields))
        for e in self.entries:
            if str(e["id"]) == str(entry_id):
                e.update(fields)
        return {}

    async def find_waitlist_by_claim(self, merchant_id, code):
        for e in self.entries:
            if str(e.get("claim_code", "")).lower() == code.strip().lower() \
                    and e.get("status") == "offered":
                return e
        return None

    async def expired_offers(self, now_iso):
        out = []
        for e in self.entries:
            if e.get("status") != "offered":
                continue
            exp = e.get("offer_expires_at")
            if exp and exp < now_iso:
                out.append(e)
        return out

    async def create_booking(self, fields):
        if self.collide:
            raise SlotTaken()
        row = {**fields, "id": f"hold-{len(self.created) + 1}"}
        self.created.append(row)
        self.bookings[row["id"]] = row
        return row

    async def get_booking(self, booking_id):
        return self.bookings.get(str(booking_id))

    async def update_booking(self, booking_id, fields):
        self.updates.append((str(booking_id), fields))
        row = self.bookings.get(str(booking_id), {"id": booking_id})
        row.update(fields)
        self.bookings[str(booking_id)] = row
        return row

    async def list_resources(self, merchant_id, active_only=True):
        return [{"id": "res-1", "seats": 4, "name": "Table 1"}]


@pytest.fixture
def wired(monkeypatch):
    """Patch the store, merchant config, history and SMS in one place."""
    sms: list[tuple[str, str]] = []

    def _setup(entries=None, *, enabled=True, collide=False, history=None,
               sms_ok=True):
        store = StubStore(entries=entries, collide=collide)
        monkeypatch.setattr(wl, "get_booking_store", lambda: store)

        async def _config(merchant_id):
            return {"business_name": "Maple Tandoor",
                    "business_timezone": "America/Toronto",
                    "waitlist_enabled": enabled,
                    "waitlist_offer_minutes": 15}

        monkeypatch.setattr(wl, "_merchant_config", _config)

        async def _history(merchant_id, phones):
            base = {p: {"spend_cents": 0, "completed": 0, "no_shows": 0}
                    for p in phones}
            base.update(history or {})
            return base

        monkeypatch.setattr(wl, "_guest_history", _history)

        async def _send(phone, message):
            sms.append((phone, message))
            return {"sent": sms_ok}

        import src.sms.client as client
        monkeypatch.setattr(client, "send_sms", _send)
        return store

    _setup.sms = sms  # type: ignore[attr-defined]
    return _setup


# ─── Ranking ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_a_no_show_history_outranks_a_big_spender(wired):
    """Turning up beats spending. Someone who burned the merchant twice cost
    them the slot twice."""
    wired(history={
        "+1555000001": {"spend_cents": 80000, "completed": 2, "no_shows": 2},
        "+1555000002": {"spend_cents": 6000, "completed": 3, "no_shows": 0},
    })
    entries = [_entry("a", "Big Spender", "+1555000001"),
               _entry("b", "Reliable", "+1555000002")]

    ranked = await wl.rank_candidates("m1", entries)
    assert ranked[0]["customer_name"] == "Reliable"
    assert "no-show" in ranked[1]["_reason"]


@pytest.mark.asyncio
async def test_with_no_history_order_is_arrival_and_says_so(wired):
    """Never invent a score. If we know nothing, be honest that it's a queue."""
    wired()
    entries = [
        _entry("a", "First", "+1555000001", party=1,
               created_at="2026-09-14T09:00:00+00:00"),
        _entry("b", "Second", "+1555000002", party=1,
               created_at="2026-09-14T11:00:00+00:00"),
    ]

    ranked = await wl.rank_candidates("m1", entries)
    assert [e["customer_name"] for e in ranked] == ["First", "Second"]
    # Party size is a real signal, so a party of one is the only case with
    # genuinely nothing to go on — and then we say so rather than invent a score.
    assert ranked[0]["_reason"] == "first in the queue"


def test_score_reason_is_human_readable():
    score, reason = wl._score(
        {"party_size": 4},
        {"spend_cents": 24000, "completed": 3, "no_shows": 0})
    assert "3 past visits" in reason
    assert "$240 spent before" in reason
    assert "party of 4" in reason
    assert score > 0


def test_spend_has_diminishing_returns():
    """A $4,000 guest should not outrank everyone forever."""
    _s1, _ = wl._score({}, {"spend_cents": 100000, "completed": 0, "no_shows": 0})
    s2, _ = wl._score({}, {"spend_cents": 400000, "completed": 0, "no_shows": 0})
    assert s2 <= 20.0, "spend contribution must be capped"


# ─── Matching ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_only_guests_whose_window_contains_the_slot_match(wired):
    store = wired([
        _entry("inside", "Fits", "+1555000001"),
        _entry("early", "Wants lunch", "+1555000002",
               window_start="2026-09-14T15:00:00+00:00",
               window_end="2026-09-14T18:00:00+00:00"),
    ])
    matched = await wl.matching_entries("m1", SLOT_START, SLOT_END, 4, now=NOW)
    assert [e["id"] for e in matched] == ["inside"]


@pytest.mark.asyncio
async def test_a_party_too_big_for_the_table_does_not_match(wired):
    wired([_entry("big", "Eight of us", "+1555000001", party=8)])
    matched = await wl.matching_entries("m1", SLOT_START, SLOT_END, 4, now=NOW)
    assert matched == []


@pytest.mark.asyncio
async def test_guests_own_notice_floor_is_respected(wired):
    """Someone who wants 7pm does not want a text at 6:40 about 7pm."""
    wired([_entry("fussy", "Needs warning", "+1555000001",
                  min_notice_minutes=480)])
    # NOW is 7 hours before the slot; they asked for 8.
    matched = await wl.matching_entries("m1", SLOT_START, SLOT_END, 4, now=NOW)
    assert matched == []


@pytest.mark.asyncio
async def test_a_guest_already_offered_three_times_is_left_alone(wired):
    wired([_entry("pestered", "Enough", "+1555000001", offer_count=3)])
    matched = await wl.matching_entries("m1", SLOT_START, SLOT_END, 4, now=NOW)
    assert matched == []


# ─── The offer ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_recovery_holds_the_slot_and_texts_the_best_guest(wired):
    store = wired([_entry("a", "Dana Reid", "+15551234567")])
    result = await wl.recover_slot("m1", _cancelled(), now=NOW)

    assert result["offered"] is True
    # The hold is a REAL booking in 'offered' status — that is what makes the
    # offer exclusive under the exclusion constraint.
    hold = store.created[0]
    assert hold["status"] == "offered"
    assert hold["resource_id"] == "res-1"
    assert hold["waitlist_id"] == "a"

    phone, body = wired.sms[-1]
    assert phone == "+15551234567"
    assert "7 PM" in body and "Maple Tandoor" in body
    assert "15 minutes" in body


@pytest.mark.asyncio
async def test_the_offer_records_why_that_guest_was_chosen(wired):
    store = wired([_entry("a", "Dana", "+15551234567")])
    await wl.recover_slot("m1", _cancelled(), now=NOW)
    _eid, fields = store.waitlist_updates[0]
    assert fields["status"] == "offered"
    assert fields["rank_reason"]
    assert len(fields["claim_code"]) == wl.CLAIM_LENGTH


@pytest.mark.asyncio
async def test_disabled_merchants_are_never_texted(wired):
    """Outbound on the merchant's behalf is theirs to opt into."""
    wired([_entry("a", "Dana", "+15551234567")], enabled=False)
    result = await wl.recover_slot("m1", _cancelled(), now=NOW)
    assert result == {"offered": False, "reason": "disabled"}
    assert wired.sms == []


@pytest.mark.asyncio
async def test_a_slot_already_retaken_offers_nothing(wired):
    """Someone booked it between the cancellation and the sweep."""
    wired([_entry("a", "Dana", "+15551234567")], collide=True)
    result = await wl.recover_slot("m1", _cancelled(), now=NOW)
    assert result["offered"] is False


@pytest.mark.asyncio
async def test_a_failed_text_releases_the_hold_instead_of_sitting_on_it(wired):
    """Holding a table for someone we could not reach serves nobody."""
    store = wired([_entry("a", "Dana", "+15551234567")], sms_ok=False)
    result = await wl.recover_slot("m1", _cancelled(), now=NOW)
    assert result["offered"] is False
    released = [f for _b, f in store.updates if f.get("status") == "cancelled"]
    assert released, "the hold must be released"


@pytest.mark.asyncio
async def test_a_past_slot_is_not_recovered(wired):
    wired([_entry("a", "Dana", "+15551234567")])
    past = _cancelled(starts_at="2026-09-13T23:00:00+00:00",
                      ends_at="2026-09-14T00:30:00+00:00")
    result = await wl.recover_slot("m1", past, now=NOW)
    assert result == {"offered": False, "reason": "in the past"}


@pytest.mark.asyncio
async def test_recovery_never_raises_into_the_cancellation(wired):
    """Cancelling must succeed even when recovery is broken."""
    store = wired([_entry("a", "Dana", "+15551234567")])

    async def _boom(*a, **kw):
        raise RuntimeError("everything is on fire")

    store.list_waitlist = _boom  # type: ignore[assignment]
    result = await wl.recover_slot("m1", _cancelled(), now=NOW)
    assert result == {"offered": False, "reason": "error"}


# ─── Claim and the chain ──────────────────────────────────────

@pytest.mark.asyncio
async def test_claiming_converts_the_hold_into_a_confirmed_booking(wired):
    store = wired([_entry("a", "Dana", "+15551234567")])
    await wl.recover_slot("m1", _cancelled(), now=NOW)
    code = store.entries[0]["claim_code"]

    booking = await wl.claim("m1", code.lower())
    assert booking["status"] == "confirmed"
    assert store.entries[0]["status"] == "booked"


@pytest.mark.asyncio
async def test_claiming_puts_the_booking_in_the_merchants_own_calendar(wired, monkeypatch):
    """The recovery is worthless to a merchant who cannot see it.

    The table frees up, we text the next guest, they take it — and if this
    push is missing, the shop's Square calendar still shows 7pm empty and
    nobody sets that table. The HOLD is deliberately not pushed (see claim());
    the claim is the moment it becomes a real booking.
    """
    pushed: list[tuple[str, str]] = []
    import src.services.booking_agent as ba
    monkeypatch.setattr(ba, "_spawn_push",
                        lambda m, row: pushed.append((m, row.get("status"))))

    store = wired([_entry("a", "Dana", "+15551234567")])
    await wl.recover_slot("m1", _cancelled(), now=NOW)
    assert pushed == [], "a held offer must not reach their calendar"

    await wl.claim("m1", store.entries[0]["claim_code"])
    assert pushed == [("m1", "confirmed")]


@pytest.mark.asyncio
async def test_an_expired_code_cannot_be_claimed(wired):
    store = wired([_entry("a", "Dana", "+15551234567",
                          status="offered", claim_code="WX7Y",
                          offer_expires_at="2020-01-01T00:00:00+00:00",
                          offer_booking_id="hold-1")])
    assert await wl.claim("m1", "WX7Y") is None


@pytest.mark.asyncio
async def test_an_unknown_code_claims_nothing(wired):
    wired([_entry("a", "Dana", "+15551234567")])
    assert await wl.claim("m1", "ZZZZ") is None


@pytest.mark.asyncio
async def test_an_expired_offer_rolls_down_to_the_next_guest(wired):
    """The chain: one cancellation walks the ranked list without anyone
    touching it."""
    store = wired([
        _entry("a", "Ignored Me", "+1555000001", status="offered",
               claim_code="AAAA", offered_at="2026-09-14T15:50:00+00:00",
               offer_expires_at="2026-09-14T16:05:00+00:00",
               offer_booking_id="hold-1", offer_count=1),
        _entry("b", "Next Up", "+1555000002"),
    ])
    store.bookings["hold-1"] = _cancelled(id="hold-1")

    result = await wl.expire_offers(now=datetime(2026, 9, 14, 16, 30,
                                                 tzinfo=timezone.utc))
    assert result["expired"] == 1
    assert result["reoffered"] == 1
    # The second guest got the text.
    assert wired.sms[-1][0] == "+1555000002"


@pytest.mark.asyncio
async def test_an_unanswered_offer_returns_the_guest_to_waiting(wired):
    """Not 'expired' — they never answered, and offer_count already caps how
    many times we bother them."""
    store = wired([_entry("a", "Quiet", "+1555000001", status="offered",
                          claim_code="AAAA", offered_at="2026-09-14T15:50:00+00:00",
                          offer_expires_at="2026-09-14T16:05:00+00:00",
                          offer_booking_id="hold-1", offer_count=1)])
    store.bookings["hold-1"] = _cancelled(id="hold-1")
    await wl.expire_offers(now=datetime(2026, 9, 14, 16, 30, tzinfo=timezone.utc))
    assert store.entries[0]["status"] == "waiting"


def test_claim_codes_avoid_ambiguous_characters():
    """The code gets read aloud by a synthetic voice and repeated by a human."""
    for _ in range(200):
        code = wl.generate_claim_code()
        assert len(code) == wl.CLAIM_LENGTH
        assert not set(code) & set("O0I1S5")


def test_outbound_voice_is_gated_off_until_the_carrier_supports_it():
    """Flipping it on before a Telnyx outbound voice profile exists produces
    silent failures."""
    assert wl.VOICE_ENABLED is False
