"""
Canada Engine Hook — Post-processing hook for the Meridian AI engine.

Detects Canadian merchants and applies the full Canada intelligence
overlay to analysis results. Designed to be called from the engine's
analysis pipeline without modifying engine.py directly.

Usage in engine.py (Phase 2b or similar):
    from .canada.engine_hook import apply_canada_intelligence
    result_dict = await apply_canada_intelligence(result_dict, ctx)

Or as a standalone post-processor:
    from src.ai.canada.engine_hook import apply_canada_intelligence
    enriched = await apply_canada_intelligence(analysis_result, ctx)
"""
import logging

from .intelligence import CanadaIntelligence, is_canadian_merchant

logger = logging.getLogger("meridian.ai.canada.engine_hook")


async def apply_canada_intelligence(result: dict, ctx) -> dict:
    """
    Post-processing hook to apply Canadian intelligence overlay.

    Detects if the merchant is Canadian (by timezone, currency, or
    province), and if so, applies all Canadian-specific adjustments
    to the analysis result.

    Args:
        result: The analysis result dict (or AnalysisResult fields).
                Expected keys: revenue_analysis, product_analysis,
                pattern_analysis, money_left_score, insights, etc.
        ctx:    The AnalysisContext with org_id, timezone, business_vertical.

    Returns:
        The result dict, enriched with `canada_overlay` if Canadian.
        Non-Canadian merchants pass through unchanged.
    """
    # Extract context fields — handle both AnalysisContext objects and dicts
    if hasattr(ctx, "timezone"):
        timezone = ctx.timezone
        vertical = getattr(ctx, "business_vertical", "other")
        org_id = getattr(ctx, "org_id", "unknown")
    elif isinstance(ctx, dict):
        timezone = ctx.get("timezone")
        vertical = ctx.get("business_vertical", "other")
        org_id = ctx.get("org_id", "unknown")
    else:
        logger.warning("Unknown context type, skipping Canada intelligence")
        return result

    # Optional province override from merchant metadata
    province = None
    if isinstance(ctx, dict):
        province = ctx.get("province")
    elif hasattr(ctx, "province"):
        province = getattr(ctx, "province", None)

    # Optional currency from merchant metadata
    currency = None
    if isinstance(ctx, dict):
        currency = ctx.get("currency")
    elif hasattr(ctx, "currency"):
        currency = getattr(ctx, "currency", None)

    # Quick detection — skip overlay for non-Canadian merchants
    if not is_canadian_merchant(
        timezone=timezone, currency=currency, province=province
    ):
        return result

    logger.info(
        f"Canadian merchant detected: org={org_id} tz={timezone} "
        f"province={province} vertical={vertical}"
    )

    try:
        intel = CanadaIntelligence(
            org_id=org_id,
            province=province,
            vertical=vertical,
            timezone=timezone,
            currency=currency,
        )

        # Build a flat dict from result for overlay processing
        if hasattr(result, "__dict__"):
            # AnalysisResult dataclass
            result_dict = _extract_result_dict(result)
            enriched = intel.apply_overlay(result_dict)
            _apply_overlay_to_result(result, enriched)
        elif isinstance(result, dict):
            result = intel.apply_overlay(result)
        else:
            logger.warning(f"Unexpected result type: {type(result)}")
            return result

        # Inject Canada-specific insights into the main insights list
        canada_insights = []
        overlay = (
            result.get("canada_overlay", {})
            if isinstance(result, dict)
            else getattr(result, "canada_overlay", {})
        )

        if overlay:
            # Provincial insights
            for pi in overlay.get("provincial_insights", []):
                canada_insights.append({
                    "id": f"ca-{pi.get('type', 'unknown')}-{org_id[:8]}",
                    "type": pi["type"],
                    "severity": pi.get("severity", "info"),
                    "title": pi.get("title", ""),
                    "body": pi.get("detail", ""),
                    "recommendation": pi.get("recommendation", ""),
                    "source": pi.get("source", "Canada Intelligence"),
                    "source_agent": "canada_intelligence",
                    "tags": ["canada", pi.get("type", "")],
                })

            # Actionable Canada insights
            for ci in overlay.get("canada_insights", []):
                canada_insights.append({
                    "id": f"ca-{ci.get('type', 'unknown')}-{org_id[:8]}",
                    "type": ci["type"],
                    "severity": "info",
                    "title": ci.get("title", ""),
                    "body": ci.get("detail", ""),
                    "actions": ci.get("actions", []),
                    "source_agent": "canada_intelligence",
                    "tags": ["canada", ci.get("type", "")],
                })

        # Merge Canada insights into main insights list
        if canada_insights:
            if isinstance(result, dict):
                existing = result.get("insights", [])
                result["insights"] = existing + canada_insights
            elif hasattr(result, "insights"):
                result.insights.extend(canada_insights)

        logger.info(
            f"Canada overlay applied: {len(canada_insights)} insights added "
            f"for org={org_id}"
        )

    except Exception as e:
        logger.error(
            f"Canada intelligence failed for org={org_id}: {e}",
            exc_info=True,
        )
        # Non-fatal — return original result on failure

    return result


def _extract_result_dict(result) -> dict:
    """Extract a flat dict from an AnalysisResult for overlay processing."""
    d = {}
    if hasattr(result, "revenue_analysis"):
        d["revenue_analysis"] = result.revenue_analysis
    if hasattr(result, "product_analysis"):
        d["product_analysis"] = result.product_analysis
    if hasattr(result, "pattern_analysis"):
        d["pattern_analysis"] = result.pattern_analysis
    if hasattr(result, "money_left_score"):
        d["money_left_score"] = result.money_left_score
    if hasattr(result, "insights"):
        d["insights"] = result.insights
    if hasattr(result, "forecasts"):
        d["forecasts"] = result.forecasts

    # Extract industry benchmarks if present
    money_left = getattr(result, "money_left_score", {})
    if isinstance(money_left, dict) and "industry_benchmarks" in money_left:
        d["industry_benchmarks"] = money_left["industry_benchmarks"]

    return d


def _apply_overlay_to_result(result, enriched: dict):
    """Apply overlay from enriched dict back to AnalysisResult object."""
    if "canada_overlay" in enriched:
        result.canada_overlay = enriched["canada_overlay"]

    # Update money_left_score if adjusted
    overlay = enriched.get("canada_overlay", {})
    if "adjusted_money_left" in overlay and hasattr(result, "money_left_score"):
        result.money_left_score["canada_adjusted"] = overlay["adjusted_money_left"]
