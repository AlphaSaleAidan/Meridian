"""
LLM Enhancement Layer — Transforms statistical analysis into actionable business intelligence.

Uses GPT-4o to rewrite raw statistical insights with:
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

_OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")

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
    if not _OPENAI_KEY:
        logger.info("OPENAI_API_KEY not set — skipping LLM enhancement")
        return raw_insights

    if not raw_insights:
        return raw_insights

    try:
        import httpx

        payload = {
            "model": "gpt-4o",
            "temperature": 0.3,
            "max_tokens": 2000,
            "messages": [
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
            ],
            "response_format": {
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
            },
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                json=payload,
                headers={
                    "Authorization": f"Bearer {_OPENAI_KEY}",
                    "Content-Type": "application/json",
                },
            )

        if resp.status_code != 200:
            logger.warning(f"LLM API returned {resp.status_code}: {resp.text[:200]}")
            return raw_insights

        content = resp.json()["choices"][0]["message"]["content"]
        enhanced = json.loads(content)

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
