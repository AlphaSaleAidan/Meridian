"""
Vapi voice mapping — merchant-picked agent voice reaches the live call.

Merchants store kokoro-style voice ids (af_bella, am_adam, ...) via
POST /api/phone/config into phone_agent_config.voice. The Vapi pipeline
(src/api/routes/vapi_webhook.py) previously hardcoded voiceId "Elliot";
it now maps the stored id to a Vapi native voice via KOKORO_TO_VAPI.

Covers:
  1. Every UI voice id (the 8 VOICE_OPTIONS values) maps to a non-empty
     Vapi voice string.
  2. Unknown / empty / missing voice → "Elliot" (previous default).
  3. _assistant_for(config) emits the mapped voiceId when config.voice is
     set, and "Elliot" when it isn't — config is the loading seam
     (_resolve_config returns it), so a fake config drives the assertion.

Run:  python -m pytest tests/api/test_vapi_voice_mapping.py -v
"""
from __future__ import annotations

import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pytest  # noqa: E402

from src.api.routes import vapi_webhook as vw  # noqa: E402

# Must stay in lockstep with frontend/src/lib/phone-orders-demo-data.ts VOICE_OPTIONS.
UI_VOICE_IDS = [
    "af_bella",
    "af_sarah",
    "af_nicole",
    "bf_emma",
    "am_adam",
    "am_michael",
    "am_echo",
    "bm_george",
]

EXPECTED = {
    "af_bella": "Savannah",
    "af_sarah": "Layla",
    "af_nicole": "Naina",
    "bf_emma": "Emma",
    "am_adam": "Sid",
    "am_michael": "Elliot",
    "am_echo": "Kai",
    "bm_george": "Neil",
}


def _fake_config(**overrides) -> SimpleNamespace:
    """Minimal stand-in for MerchantPhoneConfig as _assistant_for consumes it."""
    data = dict(
        merchant_id="m_test",
        business_name="Midtown Kitchen",
        greeting="Thanks for calling Midtown Kitchen!",
        menu_items=[],
        order_types=["pickup", "delivery"],
        voice="af_bella",
    )
    data.update(overrides)
    return SimpleNamespace(**data)


# ── 1. every UI id resolves to a valid Vapi voice ────────────────────

@pytest.mark.parametrize("voice_id", UI_VOICE_IDS)
def test_every_ui_voice_id_maps_to_vapi_voice(voice_id):
    assert voice_id in vw.KOKORO_TO_VAPI
    mapped = vw._vapi_voice(voice_id)
    assert isinstance(mapped, str) and mapped
    assert mapped == EXPECTED[voice_id]


def test_mapping_covers_exactly_the_ui_ids():
    """No stale/extra ids drift into the mapping without the UI knowing."""
    assert set(vw.KOKORO_TO_VAPI) == set(UI_VOICE_IDS)


# ── 2. unknown / empty → Elliot ──────────────────────────────────────

@pytest.mark.parametrize("bad", ["", None, "kokoro_unknown", "am_echo2", "  "])
def test_unknown_or_empty_voice_falls_back_to_elliot(bad):
    assert vw._vapi_voice(bad) == "Elliot"


# ── 3. _assistant_for wires the merchant's voice into the payload ────

def test_assistant_uses_merchant_voice():
    assistant = vw._assistant_for(_fake_config(voice="af_sarah"))
    assert assistant["voice"] == {"provider": "vapi", "voiceId": "Layla"}


def test_assistant_defaults_to_elliot_without_voice():
    cfg = _fake_config()
    del cfg.voice  # config row with no voice field at all
    assistant = vw._assistant_for(cfg)
    assert assistant["voice"] == {"provider": "vapi", "voiceId": "Elliot"}


def test_assistant_defaults_to_elliot_on_empty_or_unknown_voice():
    for bad in ("", "not_a_voice"):
        assistant = vw._assistant_for(_fake_config(voice=bad))
        assert assistant["voice"] == {"provider": "vapi", "voiceId": "Elliot"}


def test_assistant_payload_otherwise_intact():
    """Voice fix must not disturb the rest of the assistant payload."""
    cfg = _fake_config(voice="bm_george")
    assistant = vw._assistant_for(cfg)
    assert assistant["name"] == "Midtown Kitchen — Order Taker"
    assert assistant["firstMessage"] == cfg.greeting
    assert assistant["transcriber"] == {"provider": "deepgram", "model": "nova-3"}
    assert assistant["model"]["provider"] == "openai"
    assert assistant["model"]["tools"] == [vw._SUBMIT_ORDER_TOOL]
    assert assistant["endCallFunctionEnabled"] is True
