"""
Voice smoothness upgrades — speech-plan tuning + menu-aware upsells.

1. MERIDIAN_VOICE_SPEECH_TUNING (default OFF): flag off, the assistant
   payload carries no startSpeakingPlan/stopSpeakingPlan keys (byte-identical
   rollout safety — an unknown key on Vapi's side would fail every call).
   Flag on: numWords=2 barge-in guard + smart endpointing, LiveKit for EN,
   Vapi's own model for multilingual merchants.

2. Upsell guidance is menu-aware in every pack: the agent is told to name a
   specific item from the MENU, never a vague "anything else?".

Run:  python -m pytest tests/api/test_vapi_speech_tuning.py -v
"""
from __future__ import annotations

import os
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.api.routes import vapi_webhook as vw  # noqa: E402
from script_pack_defs import PACK_DEFS  # noqa: E402

PACK_IDS = sorted(PACK_DEFS)


def _cfg(**overrides) -> SimpleNamespace:
    data = dict(
        merchant_id="m_tune",
        business_name="Tuning Diner",
        greeting="Thanks for calling Tuning Diner!",
        menu_items=[{"name": "Burger", "price": 9.0}, {"name": "Coke", "price": 3.0}],
        order_types=["pickup", "delivery"],
        voice="af_bella",
        personality=None,
    )
    data.update(overrides)
    return SimpleNamespace(**data)


# ── 1. speech-plan tuning flag ───────────────────────────────────────

def test_flag_off_no_speech_plan_keys(monkeypatch):
    """Flag off: the assistant payload is unchanged."""
    monkeypatch.setattr(vw, "VOICE_SPEECH_TUNING", False)
    a = vw._assistant_for(_cfg())
    assert "startSpeakingPlan" not in a
    assert "stopSpeakingPlan" not in a


def test_flag_on_speech_plans_present(monkeypatch):
    monkeypatch.setattr(vw, "VOICE_SPEECH_TUNING", True)
    a = vw._assistant_for(_cfg())
    assert a["startSpeakingPlan"] == {
        "waitSeconds": 0.4,
        "smartEndpointingPlan": {"provider": "livekit"},
    }
    assert a["stopSpeakingPlan"] == {
        "numWords": 2,
        "voiceSeconds": 0.2,
        "backoffSeconds": 1.0,
    }


def test_flag_on_multilingual_uses_vapi_endpointing(monkeypatch):
    monkeypatch.setattr(vw, "VOICE_SPEECH_TUNING", True)
    a = vw._assistant_for(_cfg(language="multi"))
    assert a["startSpeakingPlan"]["smartEndpointingPlan"] == {"provider": "vapi"}


def test_flag_on_keeps_core_assistant_shape(monkeypatch):
    """Tuning keys are additive — tools, model, voice, cap are untouched."""
    monkeypatch.setattr(vw, "VOICE_SPEECH_TUNING", True)
    monkeypatch.setattr(vw, "VOICE_MAX_CALL_MIN", 5)
    a = vw._assistant_for(_cfg())
    assert a["model"]["provider"] == "openai"
    assert any(t.get("function", {}).get("name") == "submit_order"
               for t in a["model"]["tools"] if t.get("type") == "function")
    assert a["maxDurationSeconds"] == 5 * 60 + vw.VOICE_CAP_GRACE_SEC


# ── 2. menu-aware upsells in every pack ──────────────────────────────

@pytest.mark.parametrize("pack_id", PACK_IDS)
def test_pack_default_upsell_names_menu_item(pack_id):
    prompt = vw._system_prompt(_cfg(script_pack=pack_id))
    assert "from the MENU" in prompt


@pytest.mark.parametrize("pack_id", PACK_IDS)
def test_active_upsell_names_menu_item(pack_id):
    prompt = vw._system_prompt(_cfg(script_pack=pack_id,
                                    personality={"upsell": "active"}))
    assert "from the MENU" in prompt
    assert "up to TWO natural suggestions" in prompt


# ── 3. shared delivery guidelines land in every pack ─────────────────

@pytest.mark.parametrize("pack_id", PACK_IDS)
def test_delivery_guidelines_in_guideline_section(pack_id):
    prompt = vw._system_prompt(_cfg(script_pack=pack_id))
    guidelines = prompt.split("HARD RULES")[0]
    assert "Vary your acknowledgments" in guidelines
    assert "Ask ONE thing at a time" in guidelines
