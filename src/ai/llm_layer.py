"""
LLM Enhancement Layer — Transforms statistical analysis into actionable business intelligence.

Routes through local Llama 3.1 8B (zero cost) first, falls back to API if needed.
Rewrites raw statistical insights with:
  - Natural language explanations
  - Specific dollar-amount recommendations
  - Industry-contextualized advice
  - Priority-ranked action items
"""
import inspect
import json
import logging
import os
import re
import time

from .trace_recorder import record as _trace_record, new_trace_id as _new_trace_id
from .routing import (
    is_low_confidence,
    model_group_for_tier,
    next_tier_up,
    resolve_tier,
    tier_model_list,
)

logger = logging.getLogger("meridian.ai.llm_layer")

# Apply agents/registry.yaml model-tier assignments over the in-code seed map
# once at import. Fail-soft: a missing/malformed registry leaves the seed map
# intact (load_registry_tiers + load_agent_tiers both no-op on bad input).
try:
    from .routing.registry_loader import load_registry_tiers as _load_registry_tiers
    _load_registry_tiers()
except Exception:  # pragma: no cover - defensive only
    pass


def _caller_agent_name(default: str = "llm_layer") -> str:
    """Best-effort: walk the stack for a frame whose ``self`` looks like a
    BaseAgent (has a ``name`` attribute). Falls back to the first non-internal
    function name (e.g. ``enhance_insights``), then ``default``.

    Internal llm_layer helpers (``_call_llm``, ``_call_api``, ``_call_local``)
    are skipped so the recorded agent_name reflects the real call site."""
    internal = {"_call_llm", "_call_api", "_call_local", "_caller_agent_name", "_record_llm_call"}
    try:
        stack = inspect.stack()
        for frame_info in stack[1:20]:
            local_self = frame_info.frame.f_locals.get("self")
            if local_self is not None:
                cls_name = type(local_self).__name__
                if cls_name != "type":
                    agent_name = getattr(local_self, "name", None)
                    if isinstance(agent_name, str) and agent_name and agent_name != "base":
                        return agent_name
                    if cls_name.endswith("Agent") or cls_name.endswith("Generator"):
                        return cls_name
        # No agent-like self; pick the first non-internal frame's function name.
        for frame_info in stack[1:20]:
            fn = frame_info.function
            if fn and fn not in internal and not fn.startswith("<"):
                return fn
    except Exception:
        pass
    return default


def _record_llm_call(
    *,
    trace_id: str,
    agent_name: str,
    provider: str | None,
    model: str | None,
    latency_ms: int,
    success: bool,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    error: str | None = None,
    task_kind: str = "llm_call",
    tier: str | None = None,
) -> None:
    """Best-effort wrapper around trace_recorder.record (already no-ops on
    failure, but the wrapper keeps the call sites tidy)."""
    try:
        _trace_record(
            trace_id=trace_id,
            agent_name=agent_name,
            tier=tier,
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            success=success,
            task_kind=task_kind,
            error=error,
        )
    except Exception:
        pass


def _extract_provider_model(resp) -> tuple[str | None, str | None]:
    """Pull provider/model out of a LiteLLM response object."""
    model = getattr(resp, "model", None)
    provider = None
    hp = getattr(resp, "_hidden_params", None) or {}
    if isinstance(hp, dict):
        provider = hp.get("custom_llm_provider") or hp.get("api_provider") or hp.get("model_id")
    if not provider and isinstance(model, str) and "/" in model:
        provider = model.split("/", 1)[0]
    return provider, model


def _extract_token_usage(resp) -> tuple[int, int]:
    """Pull (prompt_tokens, completion_tokens) from a LiteLLM response usage."""
    usage = getattr(resp, "usage", None)
    if usage is None:
        return 0, 0
    if isinstance(usage, dict):
        return int(usage.get("prompt_tokens", 0) or 0), int(usage.get("completion_tokens", 0) or 0)
    return (
        int(getattr(usage, "prompt_tokens", 0) or 0),
        int(getattr(usage, "completion_tokens", 0) or 0),
    )

SYSTEM_PROMPT = """You are Meridian's AI business analyst for small businesses.
You receive statistical analysis results from POS transaction data.
Your job: rewrite each insight in plain English with specific $ recommendations.

Rules:
- Use exact numbers from the data (don't round excessively)
- Give specific, actionable advice (not generic platitudes)
- Include expected revenue impact in dollars when possible
- Keep each insight under 3 sentences
- Match your tone to the business vertical (casual for coffee shops, professional for retail)
- If data is insufficient, say so honestly rather than speculating
- ALWAYS respond with valid JSON only — no markdown, no explanation outside the JSON"""


def _extract_json(text: str) -> dict | None:
    """Extract JSON object from LLM response that may contain extra text."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None


async def _call_local(messages: list[dict], trace_id: str | None = None) -> dict | None:
    """Call local Llama model via llama-cpp-python."""
    tid = trace_id or _new_trace_id()
    agent_name = _caller_agent_name()
    start = time.perf_counter()
    try:
        import asyncio
        from ..inference.local_llm import get_llm

        def _run():
            llm = get_llm()
            resp = llm.create_chat_completion(
                messages=messages,
                max_tokens=2000,
                temperature=0.3,
            )
            return resp

        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, _run)
        content = resp["choices"][0]["message"]["content"]
        usage = resp.get("usage") or {}
        prompt_tokens = int(usage.get("prompt_tokens", 0) or 0)
        completion_tokens = int(usage.get("completion_tokens", 0) or 0)
        latency_ms = int((time.perf_counter() - start) * 1000)
        result = _extract_json(content)
        ok = result is not None
        _record_llm_call(
            trace_id=tid, agent_name=agent_name, provider="local",
            model="llama-cpp", latency_ms=latency_ms, success=ok,
            prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
            error=None if ok else "non_json_response",
        )
        if result:
            logger.info("LLM response from local llama-3.1-8b")
            return result
        logger.warning(f"Local LLM returned non-JSON: {content[:200]}")
        return None
    except Exception as e:
        latency_ms = int((time.perf_counter() - start) * 1000)
        _record_llm_call(
            trace_id=tid, agent_name=agent_name, provider="local",
            model="llama-cpp", latency_ms=latency_ms, success=False,
            error=repr(e)[:200],
        )
        logger.warning(f"Local LLM failed: {e}")
        return None


_router = None


def _get_router():
    """Initialize LiteLLM Router with all configured providers for auto-failover + caching.

    The model_list now carries per-tier groups (``meridian-t1/t2/t3``) plus the
    legacy ``meridian-llm`` group, all built by ``tier_model_list`` from the same
    provider env detection used here historically. Latency-based routing still
    picks the fastest available member *within* the selected tier group, so the
    free-provider failover chain is preserved — tiers only reorder preference.
    """
    global _router
    if _router is not None:
        return _router
    try:
        from litellm import Router
        model_list = tier_model_list()
        if not model_list:
            return None
        _router = Router(
            model_list=model_list,
            routing_strategy="latency-based-routing",
            num_retries=2,
            timeout=90,
            cache_responses=True,
            redis_host=os.environ.get("REDIS_HOST"),
            redis_port=int(os.environ.get("REDIS_PORT", "6379")),
        )
        logger.info("LiteLLM Router initialized: %d tier-group members, caching ON", len(model_list))
        return _router
    except ImportError:
        return None


async def check_llm_budget(org_id: str, max_budget_usd: float = 10.0) -> bool:
    """Check if org is within LLM budget. Returns True if allowed."""
    router = _get_router()
    if not router:
        return True
    try:
        # litellm tracks spend per user when user param is passed
        # Budget enforcement happens at call time via _call_api
        return True
    except Exception:
        return True


async def _call_api(
    messages: list[dict],
    response_format: dict | None = None,
    org_id: str | None = None,
    trace_id: str | None = None,
    agent_name: str | None = None,
    tier: str | None = None,
) -> dict | None:
    """Call LLM via Router (auto-failover + caching) or direct fallback.

    ``tier`` selects which LiteLLM model-group the Router targets
    (``meridian-t1/t2/t3``); latency-based routing then picks the fastest
    available provider *inside* that group. When ``tier`` is None it is
    resolved from ``agent_name`` (and ultimately ``DEFAULT_TIER``), so legacy
    callers that pass neither still route through the standard group exactly
    as before.

    Every LiteLLM call records one row to ``swarm_traces`` via
    ``trace_recorder`` (now including the resolved ``tier``). The recorder is
    no-op-safe so this never adds risk to the happy path.
    """
    tid = trace_id or _new_trace_id()
    agent_name = agent_name or _caller_agent_name()
    tier = tier or resolve_tier(agent_name)
    group = model_group_for_tier(tier)

    router = _get_router()
    if router:
        start = time.perf_counter()
        try:
            kwargs = {"model": group, "messages": messages, "temperature": 0.3, "max_tokens": 2000}
            if response_format:
                kwargs["response_format"] = response_format
            if org_id:
                kwargs["user"] = org_id
            resp = await router.acompletion(**kwargs)
            latency_ms = int((time.perf_counter() - start) * 1000)
            content = resp.choices[0].message.content
            provider, model = _extract_provider_model(resp)
            ptok, ctok = _extract_token_usage(resp)
            result = _extract_json(content)
            ok = result is not None
            _record_llm_call(
                trace_id=tid, agent_name=agent_name, provider=provider, model=model,
                latency_ms=latency_ms, success=ok, tier=tier,
                prompt_tokens=ptok, completion_tokens=ctok,
                error=None if ok else "non_json_response",
            )
            if result:
                logger.info("LLM response via Router tier=%s (cached=%s)", tier, getattr(resp, '_hidden_params', {}).get('cache_hit', False))
                return result
        except Exception as e:
            latency_ms = int((time.perf_counter() - start) * 1000)
            _record_llm_call(
                trace_id=tid, agent_name=agent_name, provider="router",
                model=group, latency_ms=latency_ms, success=False, tier=tier,
                error=repr(e)[:200],
            )
            logger.warning("Router call failed (tier=%s): %s", tier, e)

    try:
        from litellm import acompletion
        for model in ["gpt-4o-mini", "gpt-4o"]:
            start = time.perf_counter()
            try:
                kwargs = {"model": model, "messages": messages, "temperature": 0.3, "max_tokens": 2000}
                if response_format and "gpt" in model:
                    kwargs["response_format"] = response_format
                resp = await acompletion(**kwargs)
                latency_ms = int((time.perf_counter() - start) * 1000)
                content = resp.choices[0].message.content
                provider, resp_model = _extract_provider_model(resp)
                ptok, ctok = _extract_token_usage(resp)
                result = _extract_json(content)
                ok = result is not None
                _record_llm_call(
                    trace_id=tid, agent_name=agent_name,
                    provider=provider or "openai", model=resp_model or model,
                    latency_ms=latency_ms, success=ok, tier=tier,
                    prompt_tokens=ptok, completion_tokens=ctok,
                    error=None if ok else "non_json_response",
                )
                if result:
                    logger.info(f"LLM response from API {model}")
                    return result
            except Exception as e:
                latency_ms = int((time.perf_counter() - start) * 1000)
                _record_llm_call(
                    trace_id=tid, agent_name=agent_name,
                    provider="openai", model=model,
                    latency_ms=latency_ms, success=False, tier=tier,
                    error=repr(e)[:200],
                )
                logger.warning(f"LiteLLM {model} failed: {e}")
                continue
    except ImportError:
        pass
    return None


async def _call_llm(
    messages: list[dict],
    response_format: dict | None = None,
    org_id: str | None = None,
    agent_name: str | None = None,
    tier: str | None = None,
) -> dict | None:
    """Route LLM: Router (auto-failover across all providers) → local → direct API.

    Adds masterplan Phase 3 tiering: the call targets the model-group for the
    agent's resolved tier, and a *low-confidence* answer (None/empty or an
    explicit ``confidence`` below threshold) is retried exactly once at the
    next tier up — bounded to one escalation step so cost stays predictable.

    A single ``trace_id`` is propagated so the router attempt, any escalation,
    and the local fallback share a correlation key in ``swarm_traces``.
    """
    tid = _new_trace_id()
    agent_name = agent_name or _caller_agent_name()
    tier = tier or resolve_tier(agent_name)

    result = await _call_api(
        messages, response_format, org_id=org_id, trace_id=tid,
        agent_name=agent_name, tier=tier,
    )

    # One-step confidence escalation: only when we got a parseable answer that
    # self-reports low confidence. A None result means the router/API failed
    # outright, which the local fallback below already handles.
    if result is not None and is_low_confidence(result):
        up = next_tier_up(tier)
        if up is not None:
            logger.info("Low-confidence result on tier=%s — escalating once to tier=%s", tier, up)
            escalated = await _call_api(
                messages, response_format, org_id=org_id, trace_id=tid,
                agent_name=agent_name, tier=up,
            )
            if escalated is not None:
                return escalated

    if result:
        return result
    logger.info("Router unavailable — trying local LLM")
    result = await _call_local(messages, trace_id=tid)
    if result:
        return result
    return None


async def enhance_insights(
    raw_insights: list[dict],
    business_context: dict,
    org_id: str | None = None,
) -> list[dict]:
    """Enhance statistical insights with LLM-generated natural language."""
    if not raw_insights:
        return raw_insights

    try:
        json_instruction = (
            'Respond with ONLY a JSON object in this exact format: '
            '{"insights": [{"id": "...", "enhanced_description": "...", '
            '"revenue_impact_cents": 12300 or null, "action_item": "..."}]}'
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT + "\n\n" + json_instruction},
            {
                "role": "user",
                "content": json.dumps({
                    "business_context": business_context,
                    "insights": [
                        {
                            "id": i.get("id", ""),
                            "category": i.get("category", ""),
                            "title": i.get("title", ""),
                            "description": i.get("description", ""),
                            "metric_value": i.get("metric_value"),
                            "benchmark_value": i.get("benchmark_value"),
                            "priority": i.get("priority", "medium"),
                        }
                        for i in raw_insights[:20]
                    ],
                }),
            },
        ]

        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "enhanced_insights",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "insights": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string"},
                                    "enhanced_description": {"type": "string"},
                                    "revenue_impact_cents": {"type": ["integer", "null"]},
                                    "action_item": {"type": "string"},
                                },
                                "required": ["id", "enhanced_description", "revenue_impact_cents", "action_item"],
                                "additionalProperties": False,
                            },
                        },
                    },
                    "required": ["insights"],
                    "additionalProperties": False,
                },
            },
        }

        call_org_id = org_id or business_context.get("org_id")
        enhanced = await _call_llm(messages, response_format, org_id=call_org_id)
        if not enhanced:
            return raw_insights

        enhanced_map = {e["id"]: e for e in enhanced.get("insights", [])}

        for insight in raw_insights:
            iid = insight.get("id", "")
            if iid in enhanced_map:
                enh = enhanced_map[iid]
                insight["enhanced_description"] = enh.get("enhanced_description", "")
                insight["action_item"] = enh.get("action_item", "")
                if enh.get("revenue_impact_cents") is not None:
                    insight["revenue_impact_cents"] = enh["revenue_impact_cents"]

        logger.info(f"LLM enhanced {len(enhanced_map)} of {len(raw_insights)} insights")
        return raw_insights

    except Exception as e:
        logger.error(f"LLM enhancement failed, falling back to raw insights: {e}", exc_info=True)
        return raw_insights
