"""Tests for the phone-agent wrong-order detector (scripts/phone_order_accuracy.py).

The detector answers one question per call: does the order the agent captured
match what the caller actually asked for? These tests pin the behaviour that
matters operationally:

  1. A transcript and order that agree      -> match, not flagged.
  2. "two large lattes" captured as one medium -> flagged with the discrepancy.
  3. A call with no transcript / no order   -> skipped, never judged.
  4. The judge erroring or returning junk   -> that call is skipped, the sweep
                                               survives and still reports.
  5. PII is redacted BEFORE the judge sees anything — caller phone, email and
     customer name never leave the box.

The DeepSeek judge and Supabase are both mocked; no network, no LLM, no DB.

Run:
    /root/Meridian/.venv/bin/python -m pytest tests/api/test_phone_order_accuracy.py -v
"""
import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

import phone_order_accuracy as poa  # noqa: E402


# ─── Fixtures: two real-shaped calls, one clean and one mis-captured. ───

MATCHING_CALL = {
    "call_sid": "CA_match_001",
    "merchant_id": "11111111-1111-1111-1111-111111111111",
    "status": "order_placed",
    "duration_seconds": 74,
    "transcript": [
        {"role": "system", "content": "You are a phone ordering agent."},
        {"role": "assistant", "content": "Thanks for calling Maple Tandoor, what can I get you?"},
        {"role": "user", "content": "Can I get two large lattes please"},
        {"role": "assistant", "content": "Two large lattes. Anything else?"},
        {"role": "user", "content": "That's it"},
    ],
    "order_data": {
        "items": [
            {"name": "Latte", "quantity": 2, "size": "large", "unit_price": 5.0},
        ],
        "total": 11.30,
    },
}

MISMATCHED_CALL = {
    "call_sid": "CA_wrong_002",
    "merchant_id": "11111111-1111-1111-1111-111111111111",
    "status": "order_placed",
    "duration_seconds": 66,
    "transcript": [
        {"role": "assistant", "content": "What can I get you?"},
        {"role": "user", "content": "Two large lattes"},
        {"role": "assistant", "content": "One medium latte, got it."},
    ],
    # The agent mis-heard: 1 medium instead of 2 large.
    "order_data": {
        "items": [
            {"name": "Latte", "quantity": 1, "size": "medium", "unit_price": 4.0},
        ],
        "total": 4.52,
    },
}

MATCH_VERDICT = {
    "order_matches": True,
    "confidence": 0.95,
    "discrepancies": [],
    "summary": "",
}

MISMATCH_VERDICT = {
    "order_matches": False,
    "confidence": 0.9,
    "discrepancies": [
        {
            "type": "wrong_quantity",
            "item": "Latte",
            "expected": "2 large",
            "captured": "1 medium",
            "detail": "Caller asked for two large lattes; one medium was captured.",
        },
        {
            "type": "wrong_size",
            "item": "Latte",
            "expected": "large",
            "captured": "medium",
            "detail": "Size downgraded.",
        },
    ],
    "summary": "Captured 1 medium latte instead of 2 large.",
}


def _judge_returning(*verdicts):
    """A fake DeepSeek.chat that yields each verdict in turn as a JSON message."""
    payloads = [{"content": json.dumps(v)} for v in verdicts]

    async def _chat(client, messages, **kwargs):
        return payloads.pop(0) if payloads else payloads
    return AsyncMock(side_effect=_chat)


def _fake_ds(*verdicts):
    ds = AsyncMock()
    ds.chat = _judge_returning(*verdicts)
    return ds


# ─── 1. Matching order is not flagged. ───

async def test_matching_order_is_not_flagged():
    ds = _fake_ds(MATCH_VERDICT)

    finding = await poa.check_call(
        ds, AsyncMock(), MATCHING_CALL, min_confidence=0.5, dry_run=True
    )

    assert finding is not None
    assert finding["order_matches"] is True
    assert finding["discrepancies"] == []
    assert finding["severity"] == "none"
    assert finding["call_sid"] == "CA_match_001"


# ─── 2. Mis-capture is flagged with the discrepancy. ───

async def test_wrong_quantity_and_size_is_flagged():
    ds = _fake_ds(MISMATCH_VERDICT)

    finding = await poa.check_call(
        ds, AsyncMock(), MISMATCHED_CALL, min_confidence=0.5, dry_run=True
    )

    assert finding["order_matches"] is False
    types = {d["type"] for d in finding["discrepancies"]}
    assert types == {"wrong_quantity", "wrong_size"}
    # Worst discrepancy decides: both are 'medium'.
    assert finding["severity"] == "medium"
    assert "2 large" in finding["discrepancies"][0]["expected"]
    assert finding["order_total"] == 4.52


async def test_missing_item_escalates_to_high_severity():
    verdict = {
        "order_matches": False,
        "confidence": 0.88,
        "discrepancies": [{"type": "missing_item", "item": "Garlic naan",
                           "expected": "1 garlic naan", "captured": "", "detail": ""}],
        "summary": "Garlic naan was never added.",
    }
    ds = _fake_ds(verdict)

    finding = await poa.check_call(
        ds, AsyncMock(), MISMATCHED_CALL, min_confidence=0.5, dry_run=True
    )

    assert finding["severity"] == "high"


async def test_low_confidence_verdict_is_capped_at_low_severity():
    """A judge that isn't sure shouldn't push a call to the top of the queue."""
    unsure = dict(MISMATCH_VERDICT, confidence=0.2)
    ds = _fake_ds(unsure)

    finding = await poa.check_call(
        ds, AsyncMock(), MISMATCHED_CALL, min_confidence=0.5, dry_run=True
    )

    assert finding["order_matches"] is False  # still flagged
    assert finding["severity"] == "low"       # but ranked below confident flags


# ─── 3. Calls with nothing to compare are skipped before the judge runs. ───

async def test_calls_without_transcript_or_order_are_skipped():
    rows = [
        MATCHING_CALL,
        {**MISMATCHED_CALL, "call_sid": "CA_no_transcript", "transcript": []},
        {**MISMATCHED_CALL, "call_sid": "CA_no_order", "order_data": None},
        {**MISMATCHED_CALL, "call_sid": None},  # no natural key
    ]

    response = AsyncMock()
    response.json = lambda: rows
    response.raise_for_status = lambda: None

    with patch.object(poa, "sb", AsyncMock(return_value=response)):
        got = await poa.fetch_orders(AsyncMock(), days=3, limit=100, merchant=None)

    assert [c["call_sid"] for c in got] == ["CA_match_001"]


async def test_empty_transcript_never_reaches_the_judge():
    ds = _fake_ds(MATCH_VERDICT)
    blank = {**MATCHING_CALL, "transcript": []}

    response = AsyncMock()
    response.json = lambda: [blank]
    response.raise_for_status = lambda: None

    with patch.object(poa, "sb", AsyncMock(return_value=response)):
        got = await poa.fetch_orders(AsyncMock(), days=3, limit=100, merchant=None)

    assert got == []
    ds.chat.assert_not_awaited()


# ─── 4. Judge failures are quiet: skipped, sweep survives. ───

async def test_judge_exception_is_swallowed_and_call_skipped():
    ds = AsyncMock()
    ds.chat = AsyncMock(side_effect=RuntimeError("deepseek 500"))

    finding = await poa.check_call(
        ds, AsyncMock(), MISMATCHED_CALL, min_confidence=0.5, dry_run=True
    )

    assert finding is None


async def test_judge_returning_junk_is_skipped():
    ds = AsyncMock()
    ds.chat = AsyncMock(return_value={"content": "I'm sorry, I can't do that."})

    finding = await poa.check_call(
        ds, AsyncMock(), MISMATCHED_CALL, min_confidence=0.5, dry_run=True
    )

    assert finding is None


async def test_persist_failure_does_not_lose_the_finding():
    """A DB write failure is logged, not raised — the finding still comes back."""
    ds = _fake_ds(MISMATCH_VERDICT)

    with patch.object(poa, "upsert_finding", AsyncMock(side_effect=OSError("supabase down"))):
        finding = await poa.check_call(
            ds, AsyncMock(), MISMATCHED_CALL, min_confidence=0.5, dry_run=False
        )

    assert finding is not None
    assert finding["order_matches"] is False


async def test_sweep_reports_when_some_calls_fail():
    """One bad judge call must not take the batch down."""
    good = await poa.check_call(
        _fake_ds(MATCH_VERDICT), AsyncMock(), MATCHING_CALL,
        min_confidence=0.5, dry_run=True,
    )
    bad = await poa.check_call(
        _fake_ds(), AsyncMock(), MISMATCHED_CALL,  # judge returns nothing
        min_confidence=0.5, dry_run=True,
    )

    assert bad is None
    summary = poa.write_report([good], skipped=1, out=Path("/tmp/poa-test-out"))
    assert summary["orders_checked"] == 1
    assert summary["skipped"] == 1
    assert summary["flagged"] == 0


# ─── 5. PII never reaches the judge. ───

async def test_pii_is_redacted_before_the_judge_sees_it():
    call = {
        **MISMATCHED_CALL,
        "transcript": [
            {"role": "user", "content": "Hi it's Sarah, my number is 604-555-0199"},
            {"role": "user", "content": "email me at sarah.chen@example.com"},
            {"role": "user", "content": "Two large lattes"},
        ],
        "order_data": {
            "customer_name": "Sarah Chen",
            "customer_phone": "+16045550199",
            "customer_email": "sarah.chen@example.com",
            "items": [{"name": "Latte", "quantity": 1, "size": "medium"}],
            "special_instructions": "call 604-555-0199 when ready",
            "total": 4.52,
        },
    }

    captured = {}

    async def _chat(client, messages, **kwargs):
        captured["prompt"] = json.dumps(messages)
        return {"content": json.dumps(MISMATCH_VERDICT)}

    ds = AsyncMock()
    ds.chat = AsyncMock(side_effect=_chat)

    await poa.check_call(ds, AsyncMock(), call, min_confidence=0.5, dry_run=True)

    prompt = captured["prompt"]
    assert "604-555-0199" not in prompt
    assert "6045550199" not in prompt
    assert "sarah.chen@example.com" not in prompt
    assert "Sarah Chen" not in prompt          # name key stripped from the order
    assert "[phone]" in prompt and "[email]" in prompt
    assert "Latte" in prompt                    # the actual order still gets judged


def test_scrub_order_strips_identifying_keys_recursively():
    scrubbed = poa.scrub_order({
        "customer": {"name": "Sarah", "phone": "+16045550199"},
        "customer_name": "Sarah Chen",
        "items": [{"name": "Latte", "special_instructions": "text 604-555-0199"}],
        "total": 4.52,
    })

    assert "customer" not in scrubbed
    assert "customer_name" not in scrubbed
    assert scrubbed["items"][0]["name"] == "Latte"   # item names are not PII
    assert "604-555-0199" not in json.dumps(scrubbed)
    assert scrubbed["total"] == 4.52


def test_render_transcript_drops_the_system_prompt():
    """The agent's own instructions are not part of what the caller asked for."""
    rendered = poa.render_transcript(MATCHING_CALL["transcript"])

    assert "You are a phone ordering agent" not in rendered
    assert "CALLER: Can I get two large lattes please" in rendered


# ─── Verdict normalisation edge cases. ───

def test_discrepancies_override_a_contradictory_match_claim():
    """If the judge lists something wrong, the order is not a match."""
    v = poa.normalize_verdict({
        "order_matches": True,
        "confidence": 0.8,
        "discrepancies": [{"type": "extra_item", "item": "Fries"}],
        "summary": "Fries were added but never ordered.",
    })

    assert v["order_matches"] is False


def test_unitemised_mismatch_still_flags_at_low_severity():
    v = poa.normalize_verdict({
        "order_matches": False, "confidence": 0.9,
        "discrepancies": [], "summary": "Something is off.",
    })

    assert v["order_matches"] is False
    assert poa.severity_for(v["order_matches"], v["discrepancies"], 0.9, 0.5) == "low"


def test_unknown_discrepancy_type_is_coerced_not_dropped():
    v = poa.normalize_verdict({
        "order_matches": False, "confidence": 0.7,
        "discrepancies": [{"type": "totally_made_up", "item": "Latte"}],
        "summary": "x",
    })

    assert len(v["discrepancies"]) == 1
    assert v["discrepancies"][0]["type"] in poa.DISCREPANCY_SEVERITY


@pytest.mark.parametrize("bad_confidence", ["not-a-number", None, 5.0, -2])
def test_malformed_confidence_is_clamped(bad_confidence):
    v = poa.normalize_verdict({
        "order_matches": True, "confidence": bad_confidence,
        "discrepancies": [], "summary": "",
    })

    assert 0.0 <= v["confidence"] <= 1.0
