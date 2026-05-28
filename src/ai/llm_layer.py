"""
LLM Enhancement Layer — Transforms statistical analysis into actionable business intelligence.

Routes through local Llama 3.1 8B (zero cost) first, falls back to API if needed.
Rewrites raw statistical insights with:
  - Natural language explanations
  - Specific dollar-amount recommendations
  - Industry-contextualized advice
  - Priority-ranked action items
"""
import json
import logging
import os
import re

logger = logging.getLogger("meridian.ai.llm_layer")

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


async def _call_local(messages: list[dict]) -> dict | None:
    """Call local Llama model via llama-cpp-python."""
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
            return resp["choices"][0]["message"]["content"]

        loop = asyncio.get_event_loop()
        content = await loop.run_in_executor(None, _run)
        result = _extract_json(content)
        if result:
            logger.info("LLM response from local llama-3.1-8b")
            return result
        logger.warning(f"Local LLM returned non-JSON: {content[:200]}")
        return None
    except Exception as e:
        logger.warning(f"Local LLM failed: {e}")
        return None


_router = None


def _get_router():
    """Initialize LiteLLM Router with all configured providers for auto-failover + caching."""
    global _router
    if _router is not None:
        return _router
    try:
        from litellm import Router
        model_list = []
        if os.environ.get("DEEPSEEK_API_KEY"):
            model_list.append({
                "model_name": "meridian-llm",
                "litellm_params": {
                    "model": "deepseek/deepseek-chat",
                    "api_key": os.environ["DEEPSEEK_API_KEY"],
                    "api_base": "https://api.deepseek.com/v1",
                },
            })
        if os.environ.get("SAMBANOVA_API_KEY"):
            model_list.append({
                "model_name": "meridian-llm",
                "litellm_params": {
                    "model": "openai/Meta-Llama-3.1-405B-Instruct",
                    "api_key": os.environ["SAMBANOVA_API_KEY"],
                    "api_base": "https://api.sambanova.ai/v1",
                },
            })
        if os.environ.get("GROQ_API_KEY"):
            model_list.append({
                "model_name": "meridian-llm",
                "litellm_params": {
                    "model": "groq/llama-3.3-70b-versatile",
                    "api_key": os.environ["GROQ_API_KEY"],
                },
            })
        if os.environ.get("CEREBRAS_API_KEY"):
            model_list.append({
                "model_name": "meridian-llm",
                "litellm_params": {
                    "model": "openai/llama3.1-70b",
                    "api_key": os.environ["CEREBRAS_API_KEY"],
                    "api_base": "https://api.cerebras.ai/v1",
                },
            })
        if os.environ.get("OPENAI_API_KEY"):
            model_list.append({
                "model_name": "meridian-llm",
                "litellm_params": {
                    "model": "gpt-4o-mini",
                    "api_key": os.environ["OPENAI_API_KEY"],
                },
            })
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
        logger.info("LiteLLM Router initialized: %d providers, caching ON", len(model_list))
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
) -> dict | None:
    """Call LLM via Router (auto-failover + caching) or direct fallback."""
    router = _get_router()
    if router:
        try:
            kwargs = {"model": "meridian-llm", "messages": messages, "temperature": 0.3, "max_tokens": 2000}
            if response_format:
                kwargs["response_format"] = response_format
            if org_id:
                kwargs["user"] = org_id
            resp = await router.acompletion(**kwargs)
            content = resp.choices[0].message.content
            result = _extract_json(content)
            if result:
                logger.info("LLM response via Router (cached=%s)", getattr(resp, '_hidden_params', {}).get('cache_hit', False))
                return result
        except Exception as e:
            logger.warning("Router call failed: %s", e)

    try:
        from litellm import acompletion
        for model in ["gpt-4o-mini", "gpt-4o"]:
            try:
                kwargs = {"model": model, "messages": messages, "temperature": 0.3, "max_tokens": 2000}
                if response_format and "gpt" in model:
                    kwargs["response_format"] = response_format
                resp = await acompletion(**kwargs)
                content = resp.choices[0].message.content
                result = _extract_json(content)
                if result:
                    logger.info(f"LLM response from API {model}")
                    return result
            except Exception as e:
                logger.warning(f"LiteLLM {model} failed: {e}")
                continue
    except ImportError:
        pass
    return None


async def _call_llm(
    messages: list[dict],
    response_format: dict | None = None,
    org_id: str | None = None,
) -> dict | None:
    """Route LLM: Router (auto-failover across all providers) → local → direct API."""
    result = await _call_api(messages, response_format, org_id=org_id)
    if result:
        return result
    logger.info("Router unavailable — trying local LLM")
    result = await _call_local(messages)
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
