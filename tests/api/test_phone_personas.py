"""
Character personas — selectable character types with premium ElevenLabs voices.

The persona layer (services/phone_agent/personas.py + vapi_webhook wiring) is
STRICTLY additive: personality.character selects a persona that swaps the
voice, default greeting, and appends a PERSONA block — everything else in the
composed assistant (call flow, menu, upsell brief hook, guards) is unchanged,
and no character / any error serves the legacy path byte-for-byte.

Run:  python -m pytest tests/api/test_phone_personas.py -v
"""
from __future__ import annotations

import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pytest  # noqa: E402

from src.api.routes import vapi_webhook as vw  # noqa: E402  (adds phone_agent to sys.path)
import personas  # noqa: E402


def _config(**over):
    base = dict(
        merchant_id="m-test",
        business_name="Testaurant",
        greeting="Thanks for calling Testaurant!",
        voice="af_bella",
        menu_items=[{"name": "Cheese Pizza", "price": 10.0}],
        order_types=["pickup"],
        personality=None,
        language="en",
    )
    base.update(over)
    return SimpleNamespace(**base)


# ── registry integrity ────────────────────────────────────────────────

REQUIRED_KEYS = {"label", "tagline", "catchphrase", "voice", "greeting", "block"}


def test_registry_shape_and_cast():
    assert set(personas.PERSONAS) >= {"vinny", "mel", "rosie", "priya",
                                      "jacques", "carlos", "sam", "mei"}
    for pid, p in personas.PERSONAS.items():
        missing = REQUIRED_KEYS - set(p)
        assert not missing, f"{pid} missing {missing}"
        assert p["voice"]["provider"] == "11labs", pid
        assert p["voice"]["voiceId"], pid
        assert "{business}" in p["greeting"], pid
        assert p["block"].strip(), pid


def test_persona_block_carries_shared_product_rules():
    for pid, p in personas.PERSONAS.items():
        block = personas.persona_block(p)
        assert "PLAIN TALK" in block, pid
        assert "8th grader" in block, pid
        assert "TODAY'S UPSELL PRIORITIES" in block, pid
        assert "family-friendly" in block, pid


def test_get_persona_unknown_and_empty():
    assert personas.get_persona("vinny") is not None
    assert personas.get_persona("  VINNY ") is not None  # normalized
    assert personas.get_persona("not-a-character") is None
    assert personas.get_persona("") is None
    assert personas.get_persona(None) is None
    assert personas.get_persona(42) is None


# ── webhook wiring ────────────────────────────────────────────────────

def test_character_swaps_voice_to_11labs():
    cfg = _config(personality={"character": "vinny"})
    a = vw._assistant_for(cfg)
    assert a["voice"]["provider"] == "11labs"
    assert a["voice"]["voiceId"] == "burt"


def test_no_character_keeps_legacy_voice():
    a = vw._assistant_for(_config())
    assert a["voice"] == {"provider": "vapi", "voiceId": "Savannah"}  # af_bella


def test_unknown_character_falls_back_to_legacy_voice():
    a = vw._assistant_for(_config(personality={"character": "zzz-nope"}))
    assert a["voice"] == {"provider": "vapi", "voiceId": "Savannah"}


def test_character_appends_persona_block_and_keeps_flow():
    cfg = _config(personality={"character": "mel"})
    a = vw._assistant_for(cfg)
    prompt = a["model"]["messages"][0]["content"]
    assert "PERSONA — MEL" in prompt
    assert "CALL FLOW" in prompt          # legacy flow intact
    assert "GUARD RULES" in prompt        # guards intact
    assert "MENU:" in prompt              # menu intact
    assert "submit_order" in prompt


def test_no_character_prompt_unchanged():
    plain = vw._assistant_for(_config())["model"]["messages"][0]["content"]
    assert "PERSONA —" not in plain


def test_persona_greeting_used_when_no_custom_greeting():
    cfg = _config(personality={"character": "mel"})
    a = vw._assistant_for(cfg)
    assert "Mel here" in a["firstMessage"]
    assert "Testaurant" in a["firstMessage"]


def test_custom_greeting_beats_persona_greeting():
    cfg = _config(personality={"character": "mel",
                               "customGreeting": "Custom hello!"})
    a = vw._assistant_for(cfg)
    assert a["firstMessage"] == "Custom hello!"


def test_upsell_brief_hook_survives_persona(monkeypatch):
    # The smart-upsell block and persona block must coexist in one prompt.
    monkeypatch.setattr(vw, "_smart_upsell_block",
                        lambda config: "\n\nTODAY'S UPSELL PRIORITIES:\n- Coke")
    cfg = _config(personality={"character": "vinny"})
    prompt = vw._assistant_for(cfg)["model"]["messages"][0]["content"]
    assert "TODAY'S UPSELL PRIORITIES" in prompt
    assert "PERSONA — VINNY" in prompt


def test_demo_config_leads_with_vinny():
    from merchant_config import _demo_config
    cfg = _demo_config("demo")
    assert (cfg.personality or {}).get("character") == "vinny"
    a = vw._assistant_for(cfg)
    assert a["voice"]["provider"] == "11labs"
    # Disclosure survives via customGreeting.
    assert "nothin' gets charged" in a["firstMessage"]
