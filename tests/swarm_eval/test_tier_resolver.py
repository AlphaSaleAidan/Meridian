"""Masterplan Phase 3 — tier resolver + one-step confidence escalation.

These tests pin the *routing* contract added on top of the existing LiteLLM
latency router, without touching any provider network or ML dependency:

  1. Pure tier helpers (``resolve_tier``/``model_group_for_tier``/
     ``next_tier_up``/``is_low_confidence``) behave per the ladder spec.
  2. ``_call_api`` targets the model-group for the agent's resolved tier.
  3. ``_call_llm`` escalates *exactly once* to the next tier up on a
     low-confidence answer, never escalates a confident answer, and never
     escalates past the top tier.
  4. The resolved tier is threaded into the trace record.

The LiteLLM Router is replaced with an in-process fake, so these run fast and
offline (no API keys, no litellm install needed at call time).
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.ai import llm_layer
from src.ai.routing import (
    DEFAULT_TIER,
    TIER_HEAVY,
    TIER_LIGHT,
    TIER_STANDARD,
    is_low_confidence,
    model_group_for_tier,
    next_tier_up,
    resolve_tier,
)


# ── pure helpers ──────────────────────────────────────────────────────────
def test_resolve_tier_known_and_unknown():
    assert resolve_tier("CommercialDirector") == TIER_HEAVY
    assert resolve_tier("InsightGenerator") == TIER_STANDARD
    # Unknown agents degrade safely to the default tier, never error.
    assert resolve_tier("TotallyUnknownAgent") == DEFAULT_TIER
    assert resolve_tier(None) == DEFAULT_TIER


def test_model_group_for_tier():
    assert model_group_for_tier(TIER_LIGHT) == "meridian-t1"
    assert model_group_for_tier(TIER_STANDARD) == "meridian-t2"
    assert model_group_for_tier(TIER_HEAVY) == "meridian-t3"
    # Unrecognized → default group.
    assert model_group_for_tier("nonsense") == model_group_for_tier(DEFAULT_TIER)
    assert model_group_for_tier(None) == model_group_for_tier(DEFAULT_TIER)


def test_next_tier_up_ladder():
    assert next_tier_up(TIER_LIGHT) == TIER_STANDARD
    assert next_tier_up(TIER_STANDARD) == TIER_HEAVY
    # Already at the top → no further escalation.
    assert next_tier_up(TIER_HEAVY) is None
    assert next_tier_up("nonsense") is None


def test_is_low_confidence_cases():
    assert is_low_confidence(None) is True          # parse/router failure
    assert is_low_confidence({}) is True            # empty
    assert is_low_confidence({"confidence": 0.2}) is True
    assert is_low_confidence({"confidence": 0.9}) is False
    # No confidence field on a real object → treated as confident.
    assert is_low_confidence({"insights": []}) is False
    # Garbage confidence value → don't escalate (fail safe to confident).
    assert is_low_confidence({"confidence": "high"}) is False


# ── fakes ─────────────────────────────────────────────────────────────────
def _resp(content: str, model: str = "groq/llama-3.3-70b-versatile"):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        model=model,
        _hidden_params={},
        usage={"prompt_tokens": 1, "completion_tokens": 2},
    )


class _FakeRouter:
    """Records the ``model`` group of every acompletion call and returns a
    response produced by ``responder(model_group)``."""

    def __init__(self, responder):
        self.models: list[str] = []
        self._responder = responder

    async def acompletion(self, **kwargs):
        group = kwargs["model"]
        self.models.append(group)
        return _resp(self._responder(group))


def _install_router(monkeypatch, responder) -> _FakeRouter:
    fake = _FakeRouter(responder)
    monkeypatch.setattr(llm_layer, "_get_router", lambda: fake)
    return fake


# ── _call_api tier targeting ──────────────────────────────────────────────
def test_call_api_targets_resolved_tier_group(monkeypatch):
    fake = _install_router(monkeypatch, lambda g: json.dumps({"ok": True}))

    # Heavy agent → t3 group.
    out = asyncio.run(llm_layer._call_api([{"role": "user", "content": "hi"}],
                                          agent_name="CommercialDirector"))
    assert out == {"ok": True}
    assert fake.models == ["meridian-t3"]


def test_call_api_default_tier_for_unknown_agent(monkeypatch):
    fake = _install_router(monkeypatch, lambda g: json.dumps({"ok": True}))
    asyncio.run(llm_layer._call_api([{"role": "user", "content": "hi"}],
                                    agent_name="UnknownAgent"))
    # DEFAULT_TIER is standard → t2.
    assert fake.models == [model_group_for_tier(DEFAULT_TIER)]
    assert fake.models == ["meridian-t2"]


# ── _call_llm escalation ──────────────────────────────────────────────────
def test_call_llm_escalates_once_on_low_confidence(monkeypatch):
    # t2 answers low-confidence; t3 answers confident.
    def responder(group):
        if group == "meridian-t2":
            return json.dumps({"confidence": 0.1, "answer": "weak"})
        return json.dumps({"confidence": 0.95, "answer": "strong"})

    fake = _install_router(monkeypatch, responder)
    out = asyncio.run(llm_layer._call_llm([{"role": "user", "content": "hi"}],
                                          agent_name="InsightGenerator"))
    # Standard → escalate one step to heavy. Exactly two calls, second at t3.
    assert fake.models == ["meridian-t2", "meridian-t3"]
    assert out["answer"] == "strong"


def test_call_llm_no_escalation_when_confident(monkeypatch):
    fake = _install_router(monkeypatch, lambda g: json.dumps({"answer": "fine"}))
    out = asyncio.run(llm_layer._call_llm([{"role": "user", "content": "hi"}],
                                          agent_name="InsightGenerator"))
    # No confidence field ⇒ treated confident ⇒ single call, no escalation.
    assert fake.models == ["meridian-t2"]
    assert out["answer"] == "fine"


def test_call_llm_no_escalation_at_top_tier(monkeypatch):
    # Heavy agent gives a low-confidence answer, but there's no tier above it.
    fake = _install_router(monkeypatch, lambda g: json.dumps({"confidence": 0.05}))
    asyncio.run(llm_layer._call_llm([{"role": "user", "content": "hi"}],
                                    agent_name="CommercialDirector"))
    assert fake.models == ["meridian-t3"]  # no second call


def test_call_llm_escalation_bounded_to_one_step(monkeypatch):
    # Both tiers answer low-confidence: escalation must still fire only once.
    fake = _install_router(monkeypatch, lambda g: json.dumps({"confidence": 0.1}))
    asyncio.run(llm_layer._call_llm([{"role": "user", "content": "hi"}],
                                    agent_name="InsightGenerator"))
    assert fake.models == ["meridian-t2", "meridian-t3"]


# ── trace records carry the tier ──────────────────────────────────────────
def test_tier_is_recorded_in_trace(monkeypatch):
    _install_router(monkeypatch, lambda g: json.dumps({"answer": "fine"}))
    captured: list[dict] = []
    monkeypatch.setattr(llm_layer, "_trace_record",
                        lambda **kw: captured.append(kw))

    asyncio.run(llm_layer._call_llm([{"role": "user", "content": "hi"}],
                                    agent_name="CommercialDirector"))
    assert captured, "no trace recorded"
    assert captured[-1]["tier"] == TIER_HEAVY
    assert captured[-1]["agent_name"] == "CommercialDirector"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
