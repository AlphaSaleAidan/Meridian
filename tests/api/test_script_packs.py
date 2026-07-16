"""
Script packs — per-vertical, time-optimized call scripts (flag-gated).

Two contracts under test:

1. ZERO DEFAULT CHANGE (byte identity): a merchant whose
   phone_agent_config.script_pack is NULL / absent / '' / 'legacy' / unknown
   gets the EXACT pre-pack generic prompt. Proven against golden snapshots
   (golden_vapi_legacy_prompts.json) captured from the prompt builder BEFORE
   the pack layer existed. Any error inside the pack layer must also fall
   back to the legacy prompt (fail-legacy).

2. PACK COMPOSITION: packs render as CONVERSATION GUIDELINES (principles the
   agent adapts — not a numbered script) plus non-negotiable HARD RULES:
   read-back + confirmation before submit_order, the pay-link line, the
   shared safety protections, and the weak-spot rules (pay-now, group
   orders). Every merchant-level block (personality style, reservations,
   transfer, menu link, cap pacing, menu + sold-out) renders identically in
   every pack, and merchant upsell personality overrides the pack's policy.

Run:  python -m pytest tests/api/test_script_packs.py -v
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.api.routes import vapi_webhook as vw  # noqa: E402  (adds phone_agent to sys.path)
import script_packs  # noqa: E402
from script_pack_defs import PACK_DEFS  # noqa: E402

GOLDEN = json.loads(
    (Path(__file__).parent / "golden_vapi_legacy_prompts.json").read_text()
)
PACK_IDS = sorted(PACK_DEFS)


def _cfg(**overrides) -> SimpleNamespace:
    """The exact fixture the golden snapshots were captured with."""
    data = dict(
        merchant_id="m_gold",
        business_name="Golden Diner",
        greeting="Thanks for calling Golden Diner!",
        menu_items=[
            {"name": "Cheese Pizza", "sizes": ["medium", "large"],
             "size_prices": {"medium": 14, "large": 18}, "topping_price": 2.0,
             "modifications": ["pepperoni", "mushroom"]},
            {"name": "Garlic Bread", "price": 6.0},
            {"name": "Coke", "price": 3.0, "sizes": ["small", "large"]},
            {"name": "Mystery Item"},
        ],
        order_types=["pickup", "delivery", "dine_in"],
        voice="af_bella",
        personality=None,
    )
    data.update(overrides)
    return SimpleNamespace(**data)


def _full_cfg(**overrides) -> SimpleNamespace:
    return _cfg(
        personality={"formality": 0.9, "upsell": "active", "humor": True,
                     "customGreeting": "Welcome to the family!",
                     "customHold": "One sec...", "customClosing": "Ciao!",
                     "brandKeywords": ["wood-fired"]},
        reservation_config={"on_website": True, "website_url": "https://x.test/book"},
        sold_out_items=["Calzone"],
        menu_public_url="https://meridian.tips/m/golden",
        max_call_minutes=5,
        **overrides,
    )


@pytest.fixture(autouse=True)
def _pin_env_cap(monkeypatch):
    """The goldens were captured with the 5-minute default cap."""
    monkeypatch.setattr(vw, "VOICE_MAX_CALL_MIN", 5)


# ── 1. byte identity: NULL pack == pre-pack prompt ───────────────────

def test_golden_plain_byte_identical():
    assert vw._system_prompt(_cfg()) == GOLDEN["plain"]


def test_golden_full_blocks_byte_identical():
    """Personality + reservations + sold-out + menu link + cap + transfer."""
    assert vw._system_prompt(_full_cfg(), transfer_number="+15551234567") == GOLDEN["full"]


def test_golden_merchant_cap_byte_identical():
    assert vw._system_prompt(_cfg(max_call_minutes=4)) == GOLDEN["capped_no_personality"]


@pytest.mark.parametrize("value", [None, "", "  ", "legacy", "LEGACY", "Legacy",
                                   "no_such_pack", 42, {"id": "efficient_v1"}])
def test_null_blank_legacy_unknown_pack_all_byte_identical(value):
    assert vw._system_prompt(_cfg(script_pack=value)) == GOLDEN["plain"]


def test_config_without_script_pack_attr_byte_identical():
    """Old MerchantPhoneConfig rows (no script_pack field at all)."""
    cfg = _cfg()
    assert not hasattr(cfg, "script_pack")
    assert vw._system_prompt(cfg) == GOLDEN["plain"]


def test_pack_layer_crash_falls_back_to_legacy(monkeypatch):
    """Fail-legacy: an exploding pack composer must never change a live call."""
    def boom(pack_id, config, transfer_number):
        raise RuntimeError("pack layer exploded")
    monkeypatch.setattr(vw, "_pack_system_prompt", boom)
    assert vw._system_prompt(_cfg(script_pack="efficient_v1")) == GOLDEN["plain"]


# ── 2. pack selection ────────────────────────────────────────────────

@pytest.mark.parametrize("raw,expected", [
    (None, None), ("", None), ("legacy", None), ("  LEGACY ", None),
    ("typo_v9", None), (7, None), (["efficient_v1"], None),
    ("efficient_v1", "efficient_v1"), (" Pizzeria_V1 ", "pizzeria_v1"),
    ("cafe_quickserve_v1", "cafe_quickserve_v1"), ("indian_v1", "indian_v1"),
])
def test_resolve_pack_id(raw, expected):
    assert script_packs.resolve_pack_id(raw) == expected


def test_list_packs_legacy_control_first():
    packs = script_packs.list_packs()
    assert packs[0]["id"] == "legacy"
    assert packs[0]["status"] == "control"
    ids = [p["id"] for p in packs]
    assert len(ids) == len(set(ids))
    assert set(ids) == {"legacy", *PACK_IDS}
    for p in packs:
        assert p["label"] and p["recommend"] and p["version"]
        assert p["status"] in ("control", "pending", "beat_baseline", "not_ready")


# ── 3. pack composition keeps every merchant-level block ─────────────

@pytest.mark.parametrize("pack_id", PACK_IDS)
def test_pack_keeps_shared_safety_and_merchant_blocks(pack_id):
    prompt = vw._system_prompt(
        _full_cfg(script_pack=pack_id, language="multi"),
        transfer_number="+15551234567",
    )
    # Skeleton — guidelines the agent adapts, plus non-negotiable hard rules
    assert prompt.startswith("You are the AI phone order-taker for Golden Diner.")
    assert "CONVERSATION GUIDELINES (principles to adapt naturally" in prompt
    assert "HARD RULES (never bend these" in prompt
    # No prescriptive numbered flow in pack prompts (guidelines, not scripts)
    assert "CALL FLOW (follow this order every time):" not in prompt
    assert not any(ln[:3] in ("1. ", "2. ", "3. ") for ln in prompt.splitlines())
    # Non-negotiables — read-back+confirm before submit, pay-link line,
    # and the same safety protections as the legacy GUARD RULES block
    assert "Call submit_order ONLY after the caller confirms" in prompt
    assert "I've sent a secure payment link to your phone" in prompt
    assert "- Delivery without an address → ask for the address before calling submit_order." in prompt
    assert "- Off-menu items → say so warmly and suggest a similar item." in prompt
    assert "- Mishear → ask the caller to repeat just THAT item; never restart the order from scratch." in prompt
    assert "- Frustrated caller → brief apology" in prompt
    # Merchant-level blocks
    assert "STYLE:" in prompt                                    # personality
    assert "RESERVATIONS:" in prompt                             # reservation config
    assert "TRANSFER TO A HUMAN:" in prompt                      # transfer number
    assert "MENU:" in prompt and "Cheese Pizza: medium $14 / large $18" in prompt
    assert "SOLD OUT TODAY" in prompt and "- Calzone" in prompt
    assert "https://meridian.tips/m/golden" in prompt            # menu link
    assert "Calls end automatically at 5 minutes." in prompt     # cap pacing
    # customGreeting override flows into the pack's greeting guideline
    assert 'Welcome to the family!"' in prompt
    # Weak-spot hard rules (pay-now + group orders)
    assert "pay now or pay over the phone" in prompt
    assert "Group orders:" in prompt


@pytest.mark.parametrize("pack_id", PACK_IDS)
def test_pack_order_type_priority_before_readback(pack_id):
    """The whole point: establishing order type is prioritized EARLY in the
    guidelines, ahead of the read-back guidance."""
    prompt = vw._system_prompt(_cfg(script_pack=pack_id))
    guidelines = prompt.split("HARD RULES")[0]
    type_pos = guidelines.find("pickup, delivery")
    readback_pos = guidelines.find("read-back")
    assert 0 < type_pos < readback_pos


@pytest.mark.parametrize("pack_id", PACK_IDS)
def test_merchant_upsell_none_overrides_pack(pack_id):
    prompt = vw._system_prompt(_cfg(script_pack=pack_id,
                                    personality={"upsell": "none"}))
    assert "Do not upsell — never suggest additional items" in prompt
    guidelines_after = prompt.split("Do not upsell")[1].split("HARD RULES")[0]
    assert "upsell" not in guidelines_after.lower().replace("do not upsell", "")
    assert "suggestion" not in guidelines_after.lower()


@pytest.mark.parametrize("pack_id", PACK_IDS)
def test_merchant_upsell_active_overrides_pack(pack_id):
    prompt = vw._system_prompt(_cfg(script_pack=pack_id,
                                    personality={"upsell": "active"}))
    assert "up to TWO natural suggestions" in prompt


def test_multilingual_line_only_when_language_multi():
    with_multi = vw._system_prompt(_cfg(script_pack="indian_v1", language="multi"))
    without = vw._system_prompt(_cfg(script_pack="indian_v1", language="en"))
    assert "Hindi or Punjabi" in with_multi
    assert "Hindi or Punjabi" not in without


def test_pack_prompt_differs_from_legacy():
    """Sanity: selecting a pack actually changes the conversation guidance."""
    for pack_id in PACK_IDS:
        assert vw._system_prompt(_cfg(script_pack=pack_id)) != GOLDEN["plain"]


def test_packs_without_transfer_or_soldout_render_clean():
    prompt = vw._system_prompt(_cfg(script_pack="efficient_v1",
                                    order_types=["pickup", "delivery"]))
    assert "TRANSFER TO A HUMAN" not in prompt
    assert "SOLD OUT TODAY" not in prompt
    assert "RESERVATIONS:" not in prompt


def test_pack_reservation_block_terminated_with_newline():
    """Legacy runs RESERVATIONS straight into the next guard line (byte-
    preserved there); packs must terminate the block cleanly."""
    prompt = vw._system_prompt(_cfg(script_pack="efficient_v1"))
    assert "the notes.- " not in prompt
    assert "RESERVATIONS:" in prompt


# ── 4. save-path validation (PhoneConfigRequest) ─────────────────────

def test_config_request_accepts_known_and_legacy_pack_ids():
    from src.api.routes.phone_dashboard import PhoneConfigRequest
    for value in ("legacy", "", "efficient_v1", "PIZZERIA_V1 "):
        req = PhoneConfigRequest(merchant_id="biz_" + "a" * 16, script_pack=value)
        assert req.script_pack == value.strip().lower()
    assert PhoneConfigRequest(merchant_id="biz_" + "a" * 16).script_pack is None


def test_config_request_rejects_unknown_pack_id():
    from pydantic import ValidationError
    from src.api.routes.phone_dashboard import PhoneConfigRequest
    with pytest.raises(ValidationError):
        PhoneConfigRequest(merchant_id="biz_" + "a" * 16, script_pack="no_such_pack")
