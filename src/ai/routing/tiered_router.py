"""Tiered model routing (masterplan Phase 3).

This module sits *on top of* the existing LiteLLM latency router in
``llm_layer.py`` — it does not replace it. It adds three things the
masterplan asks for:

1. A tier concept (``lightweight`` / ``standard`` / ``heavy_reasoning``)
   that maps an agent to a LiteLLM model-group, so cheap/simple work
   stops going to the most expensive model that merely answers fastest.
2. A model-group builder that keeps the *existing* per-tier provider
   failover intact (latency-based routing within a tier group).
3. Helpers for one-step confidence escalation (a low-confidence T1/T2
   answer retries once at the next tier up, capped at one step).

The free provider chain stays free; tiers only reorder preference within
the providers already wired in ``llm_layer._get_router``.
"""
from __future__ import annotations

import os

# Tier identifiers (kept as plain strings so they serialize cleanly into
# the registry YAML, the trace table, and agent class attributes).
TIER_LIGHT = "lightweight"
TIER_STANDARD = "standard"
TIER_HEAVY = "heavy_reasoning"

DEFAULT_TIER = TIER_STANDARD

# Escalation ladder, cheapest → most capable. ``next_tier_up`` walks this.
_TIER_LADDER = [TIER_LIGHT, TIER_STANDARD, TIER_HEAVY]

VALID_TIERS = frozenset(_TIER_LADDER)

# LiteLLM model_name groups, one per tier. The legacy single group
# ("meridian-llm") is preserved for back-compat callers.
LEGACY_GROUP = "meridian-llm"
_TIER_GROUP = {
    TIER_LIGHT: "meridian-t1",
    TIER_STANDARD: "meridian-t2",
    TIER_HEAVY: "meridian-t3",
}

# Seed tier assignments for the ~7 LLM-calling agents (from the Phase 0
# agent registry). Populated/overridden at runtime by ``load_agent_tiers``
# once ``agents/registry.yaml`` exists (Phase 4). Keys are matched against
# the recorded ``agent_name`` (BaseAgent.name or the class name).
_AGENT_TIERS: dict[str, str] = {
    # Orchestration / synthesis → strongest reasoning.
    "CommercialDirector": TIER_HEAVY,
    "commercial_director": TIER_HEAVY,
    "cross_reference_orchestrator": TIER_HEAVY,
    # Generation agents → standard.
    "InsightGenerator": TIER_STANDARD,
    "ForecastNarrativeGenerator": TIER_STANDARD,
    "ReportGenerator": TIER_STANDARD,
    "CanadaRulesGenerator": TIER_STANDARD,
    "enhance_insights": TIER_STANDARD,
    "ClineAgent": TIER_STANDARD,
    # Voice is latency-sensitive but needs coherent dialogue → standard
    # (Groq 70b is fast); never route the live phone loop to the slow
    # heavy tier.
    "PipecatVoiceBot": TIER_STANDARD,
}


def load_agent_tiers(mapping: dict[str, str]) -> None:
    """Merge externally-sourced tier assignments (e.g. parsed from
    ``agents/registry.yaml``) over the built-in seed map. Invalid tiers
    are ignored rather than raising, so a malformed registry can never
    take the call path down."""
    for name, tier in (mapping or {}).items():
        if tier in VALID_TIERS:
            _AGENT_TIERS[name] = tier


def resolve_tier(agent_name: str | None) -> str:
    """Resolve an agent name to its tier. Unknown agents get
    ``DEFAULT_TIER`` so a missing registry entry degrades safely to
    standard routing instead of erroring."""
    if not agent_name:
        return DEFAULT_TIER
    return _AGENT_TIERS.get(agent_name, DEFAULT_TIER)


def model_group_for_tier(tier: str | None) -> str:
    """Map a tier to its LiteLLM model-group name, falling back to the
    default tier's group for anything unrecognized."""
    return _TIER_GROUP.get(tier or DEFAULT_TIER, _TIER_GROUP[DEFAULT_TIER])


def next_tier_up(tier: str | None) -> str | None:
    """Return the next-more-capable tier, or ``None`` if already at the
    top (or unknown). Used to bound confidence escalation to one step."""
    try:
        idx = _TIER_LADDER.index(tier)  # type: ignore[arg-type]
    except ValueError:
        return None
    if idx + 1 < len(_TIER_LADDER):
        return _TIER_LADDER[idx + 1]
    return None


def is_low_confidence(result: dict | None, threshold: float = 0.45) -> bool:
    """Decide whether a call's result warrants escalating one tier up.

    Low-confidence signals (any one triggers escalation):
      * ``None`` / empty result (parse failure or schema-invalid output —
        ``llm_layer`` already returns ``None`` in those cases);
      * an explicit self-reported ``confidence`` below ``threshold``.

    A normal successful JSON object with no confidence field is treated as
    confident, so escalation only fires on genuine trouble and stays
    cost-bounded."""
    if not result:
        return True
    conf = result.get("confidence")
    if conf is None:
        return False
    try:
        return float(conf) < threshold
    except (TypeError, ValueError):
        return False


def _provider_params() -> dict[str, dict]:
    """Return litellm_params for each wired provider, keyed by a short
    handle. Only providers whose API key is present are included — this
    mirrors ``llm_layer._get_router`` exactly so tiers never reference a
    provider that the base router wouldn't have."""
    p: dict[str, dict] = {}
    if os.environ.get("DEEPSEEK_API_KEY"):
        p["deepseek"] = {
            "model": "deepseek/deepseek-chat",
            "api_key": os.environ["DEEPSEEK_API_KEY"],
            "api_base": "https://api.deepseek.com/v1",
        }
    if os.environ.get("SAMBANOVA_API_KEY"):
        p["sambanova"] = {
            "model": "openai/Meta-Llama-3.1-405B-Instruct",
            "api_key": os.environ["SAMBANOVA_API_KEY"],
            "api_base": "https://api.sambanova.ai/v1",
        }
    if os.environ.get("GROQ_API_KEY"):
        p["groq"] = {
            "model": "groq/llama-3.3-70b-versatile",
            "api_key": os.environ["GROQ_API_KEY"],
        }
    if os.environ.get("CEREBRAS_API_KEY"):
        p["cerebras"] = {
            "model": "openai/llama3.1-70b",
            "api_key": os.environ["CEREBRAS_API_KEY"],
            "api_base": "https://api.cerebras.ai/v1",
        }
    if os.environ.get("OPENAI_API_KEY"):
        p["openai_mini"] = {
            "model": "gpt-4o-mini",
            "api_key": os.environ["OPENAI_API_KEY"],
        }
        p["openai"] = {
            "model": "gpt-4o",
            "api_key": os.environ["OPENAI_API_KEY"],
        }
    return p


# Provider preference order per tier (best-suited first). Latency-based
# routing then picks the fastest *available* member, so this is a
# preference/cost ordering, not a hard sequence.
_TIER_PREFERENCE = {
    TIER_HEAVY: ["deepseek", "sambanova", "openai"],
    TIER_STANDARD: ["groq", "cerebras", "sambanova", "deepseek", "openai_mini"],
    TIER_LIGHT: ["cerebras", "groq", "openai_mini"],
}


def tier_model_list() -> list[dict]:
    """Build the LiteLLM ``model_list`` covering all tier groups plus the
    legacy group. Returns ``[]`` when no provider keys are set (callers
    treat that as "no router available" and fall back to local/direct)."""
    providers = _provider_params()
    if not providers:
        return []

    model_list: list[dict] = []
    # Per-tier groups, in preference order, skipping providers not wired.
    for tier, handles in _TIER_PREFERENCE.items():
        group = _TIER_GROUP[tier]
        members = [h for h in handles if h in providers]
        # If a tier ends up empty (e.g. only OpenAI wired), fall back to
        # every available provider so the group is never unroutable.
        if not members:
            members = list(providers.keys())
        for h in members:
            model_list.append({"model_name": group, "litellm_params": dict(providers[h])})

    # Legacy group: every provider, preserving the original behavior for
    # callers that don't pass a tier.
    for h in providers.values():
        model_list.append({"model_name": LEGACY_GROUP, "litellm_params": dict(h)})

    return model_list
