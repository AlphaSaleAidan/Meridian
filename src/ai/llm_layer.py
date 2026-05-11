"""
LLM Enhancement Layer — Transforms statistical analysis into actionable business intelligence.

Uses LiteLLM for multi-model routing (GPT-4o, Claude, Gemini) with automatic
fallback. Rewrites raw statistical insights with:
  - Natural language explanations
  - Specific dollar-amount recommendations
  - Industry-contextualized advice
  - Priority-ranked action items

Gracefully falls back to raw statistical output if LLM is unavailable.
"""
import json
import logging
import os

logger = logging.getLogger("meridian.ai.llm_layer")

try:
    from litellm import acompletion
    HAS_LITELLM = True
except ImportError:
    HAS_LITELLM = False

_DEFAULT_MODEL = os.environ.get("MERIDIAN_LLM_MODEL", "gpt-4o")
_FALLBACK_MODEL = os.environ.get("MERIDIAN_LLM_FALLBACK", "claude-3-5-haiku-20241022")

SYSTEM_PROMPT = """You are Meridian's AI business analyst for small businesses.
You receive statistical analysis results from POS transaction data.
Your job: rewrite each insight in plain English with specific $ recommendations.

Rules:
- Use exact numbers from the data (don't round excessively)
- Give specific, actionable advice (not generic platitudes)
- Include expected revenue impact in dollars when possible
- Keep each insight under 3 sentences
- Match your tone to the business vertical (casual for coffee shops, professional for retail)
- If data is insufficient, say so honestly rather than speculating"""


async def _call_llm(messages: list[dict], response_format: dict | None = None) -> dict | None:
    """Route LLM call through LiteLLM with fallback, or raw httpx as last resort."""
    if HAS_LITELLM:
        for model in [_DEFAULT_MODEL, _FALLBACK_MODEL]:
            try:
                kwargs = {
                    "model": model,
                    "messages": messages,
                    "temperature": 0.3,
                    "max_tokens": 2000,
                }
                if response_format and "gpt" in model:
                    kwargs["response_format"] = response_format
                resp = await acompletion(**kwargs)
                content = resp.choices[0].message.content
                logger.info(f"LLM response from {model}")
                return json.loads(content)
            except Exception as e:
                logger.warning(f"LiteLLM {model} failed: {e}")
                continue
        return None

    # Fallback: raw httpx to OpenAI (original behavior)
    openai_key = os.environ.get("OPENAI_API_KEY", "")
    if not openai_key:
        return None

    try:
        import httpx
        payload = {
            "model": "gpt-4o",
            "temperature": 0.3,
            "max_tokens": 2000,
            "messages": messages,
        }
        if response_format:
            payload["response_format"] = response_format

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                json=payload,
                headers={
                    "Authorization": f"Bearer {openai_key}",
                    "Content-Type": "application/json",
                },
            )
        if resp.status_code != 200:
            logger.warning(f"OpenAI API returned {resp.status_code}: {resp.text[:200]}")
            return None

        content = resp.json()["choices"][0]["message"]["content"]
        return json.loads(content)
    except Exception as e:
        logger.warning(f"Raw OpenAI call failed: {e}")
        return None


async def enhance_insights(
    raw_insights: list[dict],
    business_context: dict,
) -> list[dict]:
    """
    Enhance statistical insights with LLM-generated natural language.

    Args:
        raw_insights: List of insight dicts from the statistical analyzers
        business_context: Dict with org_id, business_vertical, org_name, etc.

    Returns:
        Enhanced insights with 'enhanced_description' field added.
        Falls back to original insights if LLM is unavailable.
    """
    if not HAS_LITELLM and not os.environ.get("OPENAI_API_KEY"):
        logger.info("No LLM provider configured — skipping enhancement")
        return raw_insights

    if not raw_insights:
        return raw_insights

    try:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
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

        enhanced = await _call_llm(messages, response_format)
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
