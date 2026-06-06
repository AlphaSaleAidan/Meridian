"""Tiered model routing for the Meridian swarm (masterplan Phase 3).

Wraps the existing LiteLLM latency router with a tier concept
(lightweight / standard / heavy_reasoning) and one-step confidence
escalation. See ``tiered_router`` for the public surface.
"""
from .tiered_router import (
    TIER_HEAVY,
    TIER_LIGHT,
    TIER_STANDARD,
    DEFAULT_TIER,
    is_low_confidence,
    model_group_for_tier,
    next_tier_up,
    resolve_tier,
    tier_model_list,
)

__all__ = [
    "TIER_LIGHT",
    "TIER_STANDARD",
    "TIER_HEAVY",
    "DEFAULT_TIER",
    "resolve_tier",
    "model_group_for_tier",
    "next_tier_up",
    "is_low_confidence",
    "tier_model_list",
]
