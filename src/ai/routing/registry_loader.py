"""Load ``agents/registry.yaml`` and apply its model-tier assignments to the
tiered router (masterplan Phase 4).

This is the seam that makes the registry — not the in-code seed map in
``tiered_router._AGENT_TIERS`` — the source of truth for routing. It is
deliberately fail-soft: a missing or malformed registry leaves the seed map
in place rather than taking the LLM call path down (``load_agent_tiers``
already ignores invalid tiers).
"""
from __future__ import annotations

import logging
import os
from functools import lru_cache

from .tiered_router import load_agent_tiers

logger = logging.getLogger("meridian.ai.routing.registry")

# agents/registry.yaml lives at the repo root: src/ai/routing/ → ../../../
_DEFAULT_REGISTRY = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "agents", "registry.yaml"
)


def parse_registry(path: str | None = None) -> list[dict]:
    """Return the raw agent rows from the registry, or ``[]`` on any failure."""
    target = path or os.environ.get("MERIDIAN_AGENT_REGISTRY") or _DEFAULT_REGISTRY
    try:
        import yaml
    except ImportError:
        logger.debug("PyYAML not installed — registry tiers not applied")
        return []
    try:
        with open(target, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
    except FileNotFoundError:
        logger.debug("agent registry not found at %s", target)
        return []
    except Exception as e:  # malformed YAML, perms, etc.
        logger.warning("agent registry parse failed (%s) — using seed tiers", e)
        return []
    agents = data.get("agents")
    return agents if isinstance(agents, list) else []


def registry_tier_map(path: str | None = None) -> dict[str, str]:
    """Build ``{agent_name: model_tier}`` for every LLM-calling registry row."""
    mapping: dict[str, str] = {}
    for row in parse_registry(path):
        if not isinstance(row, dict):
            continue
        if row.get("calls_llm") and row.get("name") and row.get("model_tier"):
            mapping[str(row["name"])] = str(row["model_tier"])
    return mapping


@lru_cache(maxsize=1)
def load_registry_tiers(path: str | None = None) -> dict[str, str]:
    """Merge registry model-tiers over the seed map (idempotent, cached).

    Returns the mapping that was applied so callers can log/inspect it.
    """
    mapping = registry_tier_map(path)
    if mapping:
        load_agent_tiers(mapping)
        logger.info("Applied %d model-tier assignments from agent registry", len(mapping))
    return mapping
