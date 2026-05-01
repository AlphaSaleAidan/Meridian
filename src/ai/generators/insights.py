"""
Insight Generator v2 — Doctorate-Level Financial Intelligence.

Thin facade over per-category insight modules. All public API preserved.
"""
import logging
from ._insight_helpers import score_priority, MODEL_VERSION
from . import revenue_insights
from . import product_insights
from . import pattern_insights
from . import money_left_insights
from . import anomaly_insights
from . import economic_insights

logger = logging.getLogger("meridian.ai.generators.insights")

try:
    from ..economics import IndustryBenchmarks, EconomicModels
    _HAS_ECONOMICS = True
except ImportError:
    _HAS_ECONOMICS = False
    logger.warning("Economics module not available — falling back to basic insights")


class InsightGenerator:
    """Generates prioritized, PhD-grade financial insights with citations."""

    MODEL_VERSION = MODEL_VERSION

    def __init__(self, vertical: str = "coffee_shop"):
        self.vertical = vertical
        if _HAS_ECONOMICS:
            self.bench = IndustryBenchmarks(vertical)
            self.models = EconomicModels()
        else:
            self.bench = None
            self.models = None

    def generate(
        self,
        ctx,
        revenue: dict,
        products: dict,
        patterns: dict,
        money_left: dict,
    ) -> list[dict]:
        insights = []

        insights.extend(revenue_insights.generate(ctx, revenue, self.bench, self.models))
        insights.extend(product_insights.generate(ctx, products, self.bench, self.models))
        insights.extend(pattern_insights.generate(ctx, patterns, self.bench, self.models))
        insights.extend(money_left_insights.generate(ctx, money_left, self.bench, self.models))
        insights.extend(anomaly_insights.generate(ctx, revenue, self.bench, self.models))

        if self.models:
            insights.extend(economic_insights.generate(
                ctx, revenue, products, patterns, self.bench, self.models
            ))

        for insight in insights:
            insight["priority_score"] = score_priority(insight)

        insights.sort(key=lambda x: x.get("priority_score", 0), reverse=True)

        seen_types: dict[str, int] = {}
        deduped = []
        for insight in insights:
            itype = insight.get("type", "general")
            seen_types[itype] = seen_types.get(itype, 0) + 1
            if seen_types[itype] <= 5:
                deduped.append(insight)
        insights = deduped

        insights = insights[:25]

        logger.info(f"Generated {len(insights)} insights for {ctx.org_id}")
        return insights
