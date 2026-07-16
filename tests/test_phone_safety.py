"""
Phone-activation safety: transfer-loop prevention, per-merchant call cap,
and end-reason telemetry.

Loop invariants:
  1. E.164 normalization treats "(555) 010-0100" and "+15550100100" as the
     same line — the loop checks are format-insensitive.
  2. Onboarding validation rejects a transfer_number that is the merchant's
     own agent DID or ANY agent DID in phone_agent_config; a distinct cell
     passes. (Scenario killed: transfer → store line → *72 full-forward →
     agent DID → infinite loop.)
  3. The Vapi assistant only carries the transferCall tool for a validated
     transfer number; the own-DID case is suppressed even at assembly time.
  4. The loop-guard assistant carries NO tools (no submit_order, no transfer).

Cap invariants:
  5. phone_agent_config.max_call_minutes overrides the env default in
     maxDurationSeconds AND the spoken pacing line; None falls back to the
     global default; 0 = uncapped for that merchant.
  6. The end-of-call overage clamp uses the SAME effective cap — a raised cap
     bills to the raised cap, and the disclosed per-call maximum holds.

Telemetry invariants:
  7. Vapi endedReason values map to the stable disposition buckets
     (cutoff | caller_hangup | agent_hangup | silence | error | other).
"""
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
_PA = str(Path(__file__).resolve().parents[1] / "services" / "phone_agent")
if _PA not in sys.path:
    sys.path.insert(0, _PA)

import src.api.routes.vapi_webhook as vw  # noqa: E402
from src.services.phone_safety import (  # noqa: E402
    map_ended_reason, normalize_e164, same_number, transfer_number_conflict,
)

aio = pytest.mark.asyncio


# ── 1. E.164 normalization ────────────────────────────────────


def test_normalize_e164_variants():
    assert normalize_e164("(555) 010-0100") == "+15550100100"
    assert normalize_e164("555-010-0100") == "+15550100100"
    assert normalize_e164("1 555 010 0100") == "+15550100100"
    assert normalize_e164("+1 555-010-0100") == "+15550100100"
    assert normalize_e164("+15550100100") == "+15550100100"
    assert normalize_e164("") == ""
    assert normalize_e164("   ") == ""
    assert normalize_e164("ext") == ""


def test_same_number_is_format_insensitive():
    assert same_number("(604) 555-1234", "+16045551234")
    assert not same_number("+16045551234", "+16045559999")
    assert not same_number("", "")  # empty never matches anything


# ── 2. onboarding transfer-number validation ──────────────────


class _FleetDB:
    """phone_agent_config lookup stub: `fleet` is the set of agent DIDs."""

    def __init__(self, fleet: set[str]):
        self.fleet = fleet

    async def select(self, table, columns=None, filters=None, limit=None):
        assert table == "phone_agent_config"
        num = (filters or {}).get("phone_number", "").removeprefix("eq.")
        if num in self.fleet:
            return [{"merchant_id": "other-merchant", "phone_number": num}]
        return []


OWN_DID = "+17785550100"
FLEET_DID = "+16475550200"


@aio
async def test_rejects_own_agent_did_even_formatted_differently():
    db = _FleetDB({OWN_DID, FLEET_DID})
    msg = await transfer_number_conflict(db, "(778) 555-0100", OWN_DID)
    assert msg is not None
    # merchant-readable: explains the loop and suggests the safe alternatives
    assert "loop" in msg.lower()
    assert "conditional" in msg.lower() or "busy" in msg.lower()


@aio
async def test_rejects_another_merchants_agent_did():
    db = _FleetDB({OWN_DID, FLEET_DID})
    msg = await transfer_number_conflict(db, FLEET_DID, OWN_DID)
    assert msg is not None
    assert "agent" in msg.lower()


@aio
async def test_accepts_a_distinct_cell():
    db = _FleetDB({OWN_DID, FLEET_DID})
    assert await transfer_number_conflict(db, "+16045551234", OWN_DID) is None
    # empty transfer number is a no-op, not a conflict
    assert await transfer_number_conflict(db, "", OWN_DID) is None


# ── 3/4. Vapi assistant assembly ──────────────────────────────


def _cfg(**over):
    base = dict(
        merchant_id="m1", business_name="Tony's Pizza", business_type="restaurant",
        greeting="", voice="Elliot", language="en", accent="",
        menu_items=[], order_types=["pickup"], business_hours={}, personality=None,
        transfer_number="", phone_number=OWN_DID, special_instructions_enabled=True,
        reservation_config=None, restaurant_brief="",
    )
    base.update(over)
    return SimpleNamespace(**base)


def _tool_types(assistant):
    return [t.get("type") for t in assistant["model"]["tools"]]


def test_transfer_tool_added_for_valid_transfer_number():
    a = vw._assistant_for(_cfg(transfer_number="+16045551234"))
    assert "transferCall" in _tool_types(a)
    tc = next(t for t in a["model"]["tools"] if t.get("type") == "transferCall")
    assert tc["destinations"][0]["number"] == "+16045551234"
    prompt = a["model"]["messages"][0]["content"]
    assert "TRANSFER TO A HUMAN" in prompt
    # no-answer fallback: take a message + promise a callback
    assert "callback" in prompt.lower()


def test_transfer_tool_suppressed_when_transfer_is_own_did():
    a = vw._assistant_for(_cfg(transfer_number="(778) 555-0100"))
    assert _tool_types(a) == ["function"]
    assert "TRANSFER TO A HUMAN" not in a["model"]["messages"][0]["content"]


def test_transfer_tool_absent_without_transfer_number():
    a = vw._assistant_for(_cfg())
    assert _tool_types(a) == ["function"]


def test_handler_override_suppresses_fleet_did_transfer():
    # The assistant-request handler passes "" after the fleet check trips.
    a = vw._assistant_for(_cfg(transfer_number=FLEET_DID), transfer_number="")
    assert _tool_types(a) == ["function"]


def test_loop_guard_assistant_has_no_tools():
    a = vw._loop_guard_assistant(_cfg())
    assert a["model"]["tools"] == []
    prompt = a["model"]["messages"][0]["content"]
    assert "CANNOT take an order" in prompt
    assert "CANNOT transfer" in prompt
    assert "call" in a["firstMessage"].lower()


# ── 5. per-merchant cap threading ─────────────────────────────


def test_default_cap_is_5_minutes(monkeypatch):
    """The 5-minute rule stays (decision 2026-07-16, reverting the brief 8-min
    default): with no env override the module constant must land on 5."""
    import importlib
    monkeypatch.delenv("MERIDIAN_VOICE_MAX_CALL_MIN", raising=False)
    importlib.reload(vw)
    assert vw.VOICE_MAX_CALL_MIN == 5


def test_merchant_cap_overrides_max_duration(monkeypatch):
    monkeypatch.setattr(vw, "VOICE_MAX_CALL_MIN", 8)
    a = vw._assistant_for(_cfg(max_call_minutes=12))
    assert a["maxDurationSeconds"] == 12 * 60 + vw.VOICE_CAP_GRACE_SEC
    # pacing line speaks the merchant's cap, not the global default
    assert "end automatically at 12 minutes" in a["model"]["messages"][0]["content"]


def test_merchant_cap_falls_back_to_env_default(monkeypatch):
    monkeypatch.setattr(vw, "VOICE_MAX_CALL_MIN", 8)
    a = vw._assistant_for(_cfg())  # no max_call_minutes attribute
    assert a["maxDurationSeconds"] == 8 * 60 + vw.VOICE_CAP_GRACE_SEC
    assert "end automatically at 8 minutes" in a["model"]["messages"][0]["content"]
    a2 = vw._assistant_for(_cfg(max_call_minutes=None))
    assert a2["maxDurationSeconds"] == 8 * 60 + vw.VOICE_CAP_GRACE_SEC


def test_merchant_cap_zero_means_uncapped(monkeypatch):
    monkeypatch.setattr(vw, "VOICE_MAX_CALL_MIN", 8)
    a = vw._assistant_for(_cfg(max_call_minutes=0))
    assert "maxDurationSeconds" not in a
    assert "end automatically" not in a["model"]["messages"][0]["content"]


def test_pacing_line_includes_spoken_heads_up(monkeypatch):
    monkeypatch.setattr(vw, "VOICE_MAX_CALL_MIN", 8)
    line = vw._pacing_line(8)
    assert "heads-up" in line
    assert "read your order back" in line


# ── 6. overage clamp uses the effective cap ───────────────────


def test_overage_clamped_to_merchant_cap():
    # 10-min call, 3 included, 8-min cap → billed 5 min (not 7)
    assert vw._overage_minutes(10.0, 3, 8) == 5
    # grace period: cap 8, drop lands at 8.2 min → ceil 9 → still clamped to 5
    assert vw._overage_minutes(8.2, 3, 8) == 5
    # uncapped merchant bills actual overage
    assert vw._overage_minutes(10.0, 3, 0) == 7
    # under the included block → nothing billed
    assert vw._overage_minutes(2.5, 3, 8) == 0
    # cap below included → never negative
    assert vw._overage_minutes(10.0, 3, 2) == 0


def test_effective_cap_min_resolution(monkeypatch):
    monkeypatch.setattr(vw, "VOICE_MAX_CALL_MIN", 8)
    assert vw._effective_cap_min(_cfg(max_call_minutes=12)) == 12
    assert vw._effective_cap_min(_cfg(max_call_minutes=0)) == 0
    assert vw._effective_cap_min(_cfg(max_call_minutes=None)) == 8
    assert vw._effective_cap_min(_cfg()) == 8
    # junk values fall back rather than break billing
    assert vw._effective_cap_min(_cfg(max_call_minutes="12")) == 8
    assert vw._effective_cap_min(_cfg(max_call_minutes=-3)) == 8
    assert vw._effective_cap_min(_cfg(max_call_minutes=True)) == 8


# ── 7. endedReason → disposition mapping ──────────────────────


@pytest.mark.parametrize("reason,expected", [
    ("exceeded-max-duration", "cutoff"),
    ("customer-ended-call", "caller_hangup"),
    ("assistant-ended-call", "agent_hangup"),
    ("assistant-said-end-call-phrase", "agent_hangup"),
    ("silence-timed-out", "silence"),
    ("assistant-error", "error"),
    ("assistant-error-openai-500", "error"),
    ("pipeline-error-deepgram-returning-403", "error"),
    ("some-brand-new-vapi-reason", "other"),
    ("", "other"),
    (None, "other"),
])
def test_map_ended_reason(reason, expected):
    assert map_ended_reason(reason) == expected


def test_had_order_detection():
    with_order = {"artifact": {"messages": [
        {"role": "assistant", "toolCalls": [
            {"function": {"name": "submit_order", "arguments": "{}"}}]},
    ]}}
    without = {"artifact": {"messages": [{"role": "user", "message": "hi"}]}}
    assert vw._had_order(with_order) is True
    assert vw._had_order(without) is False
    assert vw._had_order({}) is None  # undeterminable → NULL, not False
