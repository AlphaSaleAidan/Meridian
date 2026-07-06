"""
Agent personality → live Vapi prompt.

Merchants configure a personality in Phone Orders settings (PersonalityPanel):
{formality, upsell, humor, customGreeting, customHold, customClosing,
brandKeywords}. It persists to phone_agent_config.personality (JSONB) and
src/api/routes/vapi_webhook.py renders it into the system prompt / assistant:

  - formality < 0.35 → casual tone line; > 0.7 → professional tone line
  - upsell 'none'    → REPLACES the upsell step (never suggest items);
    'active' → up to two suggestions; 'gentle'/unset → original single upsell
  - humor True       → light-humor line
  - customGreeting   → overrides firstMessage (and the prompt's greet line)
  - customHold / customClosing / brandKeywords → one prompt line each
  - absent / empty personality → prompt byte-for-byte unchanged

Run:  python -m pytest tests/api/test_vapi_personality_prompt.py -v
"""
from __future__ import annotations

import os
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.api.routes import vapi_webhook as vw  # noqa: E402


def _fake_config(**overrides) -> SimpleNamespace:
    """Minimal stand-in for MerchantPhoneConfig as the prompt builder consumes it."""
    data = dict(
        merchant_id="m_test",
        business_name="Midtown Kitchen",
        greeting="Thanks for calling Midtown Kitchen!",
        menu_items=[],
        order_types=["pickup", "delivery"],
        voice="af_bella",
        personality=None,
    )
    data.update(overrides)
    return SimpleNamespace(**data)


BASELINE = vw._system_prompt(_fake_config())


# ── formality variants ───────────────────────────────────────────────

def test_low_formality_adds_casual_line():
    prompt = vw._system_prompt(_fake_config(personality={"formality": 0.2}))
    assert "Keep the tone casual and relaxed." in prompt
    assert "Keep the tone polished and professional." not in prompt


def test_high_formality_adds_professional_line():
    prompt = vw._system_prompt(_fake_config(personality={"formality": 0.9}))
    assert "Keep the tone polished and professional." in prompt
    assert "Keep the tone casual and relaxed." not in prompt


def test_mid_formality_adds_no_tone_line():
    """Balanced formality (0.35–0.7) is the default voice — no extra line."""
    prompt = vw._system_prompt(_fake_config(personality={"formality": 0.5}))
    assert prompt == BASELINE


@pytest.mark.parametrize("bad", [None, "high", [0.1]])
def test_non_numeric_formality_ignored(bad):
    prompt = vw._system_prompt(_fake_config(personality={"formality": bad}))
    assert prompt == BASELINE


# ── upsell step replacement ──────────────────────────────────────────

def test_upsell_none_replaces_upsell_step():
    prompt = vw._system_prompt(_fake_config(personality={"upsell": "none"}))
    assert "Do not upsell — never suggest additional items" in prompt
    assert "ONE natural upsell" not in prompt
    # Step numbering stays intact — 'none' replaces step 3, never deletes it.
    assert "\n3. " in prompt and "\n4. " in prompt


def test_upsell_active_allows_two_suggestions():
    prompt = vw._system_prompt(_fake_config(personality={"upsell": "active"}))
    assert "up to TWO natural suggestions" in prompt
    assert "ONE natural upsell" not in prompt


@pytest.mark.parametrize("value", ["gentle", "", None, "unknown"])
def test_upsell_gentle_or_unset_keeps_original_step(value):
    prompt = vw._system_prompt(_fake_config(personality={"upsell": value}))
    assert prompt == BASELINE


# ── custom greeting override ─────────────────────────────────────────

def test_custom_greeting_overrides_first_message():
    cfg = _fake_config(personality={"customGreeting": "Welcome to the family!"})
    assistant = vw._assistant_for(cfg)
    assert assistant["firstMessage"] == "Welcome to the family!"
    # Prompt's greet line must match what the caller actually heard.
    assert '1. Greet: "Welcome to the family!"' in vw._system_prompt(cfg)


def test_blank_custom_greeting_keeps_standard_greeting():
    cfg = _fake_config(personality={"customGreeting": "   "})
    assert vw._assistant_for(cfg)["firstMessage"] == cfg.greeting
    assert vw._system_prompt(cfg) == BASELINE


# ── humor / hold / closing / brand keywords ──────────────────────────

def test_humor_hold_closing_keywords_render_one_line_each():
    prompt = vw._system_prompt(_fake_config(personality={
        "humor": True,
        "customHold": "One sec while I check on that...",
        "customClosing": "Enjoy your meal!",
        "brandKeywords": ["homemade", "fresh-baked"],
    }))
    assert "Light, tasteful humor is welcome." in prompt
    assert 'When you need a moment say: "One sec while I check on that..."' in prompt
    assert 'End calls with: "Enjoy your meal!"' in prompt
    assert "Work these phrases in naturally when relevant: homemade, fresh-baked" in prompt


def test_humor_false_adds_nothing():
    prompt = vw._system_prompt(_fake_config(personality={"humor": False}))
    assert prompt == BASELINE


def test_empty_brand_keywords_add_nothing():
    prompt = vw._system_prompt(_fake_config(personality={"brandKeywords": ["", "  "]}))
    assert prompt == BASELINE


# ── empty / absent personality → prompt unchanged ────────────────────

@pytest.mark.parametrize("empty", [None, {}, "not-a-dict"])
def test_empty_personality_leaves_prompt_unchanged(empty):
    assert vw._system_prompt(_fake_config(personality=empty)) == BASELINE


def test_config_without_personality_attr_unchanged():
    """Old MerchantPhoneConfig rows (SimpleNamespace without the field)."""
    cfg = _fake_config()
    del cfg.personality
    assert vw._system_prompt(cfg) == BASELINE
    assert vw._assistant_for(cfg)["firstMessage"] == cfg.greeting
