"""
Agent personality → in-app test-call prompt.

The wizard's interactive test call (POST /api/phone/test-chat) must express
the same personality settings as the live Vapi agent, otherwise merchants
tune the PersonalityPanel, run a test call, and hear no difference.
_build_test_prompt reuses vapi_webhook's renderers:

  - customGreeting overrides the standard greeting line
  - upsell 'none' → hard no-upsell rule; 'active' → up to two suggestions;
    'gentle' → single suggestion; unset → no upsell rule (pre-field prompt)
  - formality / humor / customHold / customClosing / brandKeywords → one
    prompt line each
  - absent / empty personality → prompt byte-for-byte unchanged

Run:  python -m pytest tests/api/test_phone_test_chat_personality.py -v
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.api.routes.phone_dashboard import TestChatRequest, _build_test_prompt  # noqa: E402


def _req(**kwargs) -> TestChatRequest:
    return TestChatRequest(
        merchant_id="00000000-0000-0000-0000-000000000000",
        messages=[{"role": "user", "content": "hi"}],
        business_name="Testaurant",
        greeting="Thanks for calling Testaurant!",
        menu_items=[{"name": "Burger", "price": 9.5, "category": "food"}],
        order_types=["pickup"],
        **kwargs,
    )


def test_no_personality_prompt_unchanged():
    """Unset personality must not add or change a single character."""
    assert _build_test_prompt(_req()) == _build_test_prompt(_req(personality=None))
    assert _build_test_prompt(_req()) == _build_test_prompt(_req(personality={}))
    prompt = _build_test_prompt(_req())
    assert "upsell" not in prompt.lower()
    assert 'Open with a greeting like: "Thanks for calling Testaurant!"' in prompt


def test_custom_greeting_overrides():
    prompt = _build_test_prompt(_req(personality={"customGreeting": "Yo, Testaurant here!"}))
    assert 'Open with a greeting like: "Yo, Testaurant here!"' in prompt
    assert "Thanks for calling Testaurant!" not in prompt


def test_upsell_none_renders_hard_rule():
    prompt = _build_test_prompt(_req(personality={"upsell": "none"}))
    assert "Do not upsell" in prompt


def test_upsell_active_allows_two():
    prompt = _build_test_prompt(_req(personality={"upsell": "active"}))
    assert "TWO natural suggestions" in prompt


def test_upsell_gentle_single_suggestion():
    prompt = _build_test_prompt(_req(personality={"upsell": "gentle"}))
    assert "ONE natural upsell" in prompt


def test_style_lines_render():
    prompt = _build_test_prompt(_req(personality={
        "formality": 0.9,
        "humor": True,
        "customHold": "One sec, checking that for you.",
        "customClosing": "See you soon!",
        "brandKeywords": ["farm-fresh", "family-owned"],
    }))
    assert "polished and professional" in prompt
    assert "humor" in prompt.lower()
    assert 'One sec, checking that for you.' in prompt
    assert 'End calls with: "See you soon!"' in prompt
    assert "farm-fresh, family-owned" in prompt


def test_casual_formality():
    prompt = _build_test_prompt(_req(personality={"formality": 0.1}))
    assert "casual and relaxed" in prompt
