"""Masterplan Phase 4 — agent registry contract + drift gate.

Runs the standalone validator (``scripts/validate_agents.py``) inside pytest so
CI fails when:
  * a new BaseAgent subclass is added without a registry row,
  * a registry row's class/module no longer resolves,
  * a row's ``model_tier`` is invalid or inconsistent with ``calls_llm``.

Also pins that the registry actually drives the router via
``registry_loader`` — the whole point of Phase 4 is that the YAML, not the
in-code seed map, is the source of truth for routing tiers.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from scripts import validate_agents
from src.ai.routing import resolve_tier
from src.ai.routing.registry_loader import (
    load_registry_tiers,
    parse_registry,
    registry_tier_map,
)
from src.ai.routing.tiered_router import TIER_HEAVY, TIER_STANDARD, VALID_TIERS


def test_registry_passes_validator():
    """The committed registry must have zero validation errors."""
    errors = validate_agents.validate()
    assert errors == [], "agent registry validation failed:\n" + "\n".join(errors)


def test_registry_has_rows():
    rows = parse_registry()
    assert len(rows) >= 40, f"expected the full fleet, got {len(rows)} rows"


def test_llm_rows_have_valid_model_tier():
    for row in parse_registry():
        if row.get("calls_llm"):
            assert row.get("model_tier") in VALID_TIERS, row
        else:
            assert row.get("model_tier") is None, row


def test_registry_drives_router_tiers():
    """After loading the registry, resolve_tier reflects the YAML assignments."""
    applied = load_registry_tiers()
    assert applied, "registry produced no tier assignments"
    # Spot-check both ends of the ladder from the committed registry.
    assert registry_tier_map().get("CrossReferenceOrchestrator") == TIER_HEAVY
    assert resolve_tier("CrossReferenceOrchestrator") == TIER_HEAVY
    assert resolve_tier("InsightGenerator") == TIER_STANDARD


def test_voice_bot_never_heavy():
    """Latency-critical phone loop must never route to the slow heavy tier."""
    tiers = registry_tier_map()
    assert tiers.get("PipecatVoiceBot") == TIER_STANDARD


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
