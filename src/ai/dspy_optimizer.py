"""
DSPy automatic prompt optimization for Meridian insight agents.

Wraps the LLM enhancement step so DSPy can automatically tune prompts
for better insight quality based on merchant feedback signals.
"""
import logging
import os

logger = logging.getLogger("meridian.ai.dspy_optimizer")

_DSPY_AVAILABLE = False
try:
    import dspy
    _DSPY_AVAILABLE = True
except ImportError:
    logger.info("dspy not installed — prompt optimization disabled")


class InsightSignature(dspy.Signature if _DSPY_AVAILABLE else object):
    """Optimize a raw statistical insight into an actionable business recommendation."""
    if _DSPY_AVAILABLE:
        raw_insight = dspy.InputField(desc="Raw statistical insight from POS data analysis")
        business_context = dspy.InputField(desc="Business vertical, size, and location context")
        enhanced_insight = dspy.OutputField(desc="Clear, actionable business recommendation with dollar amounts")
        action_item = dspy.OutputField(desc="Single specific action the merchant should take")


class MeridianOptimizer:
    """DSPy-powered prompt optimizer for insight generation.

    Falls back to direct LLM calls when DSPy is not installed or
    no optimized prompts are available.
    """

    def __init__(self):
        self._module = None
        self._compiled = False
        if _DSPY_AVAILABLE:
            self._configure_dspy()
            self._module = dspy.ChainOfThought(InsightSignature)

    def _configure_dspy(self):
        model = os.environ.get("DSPY_MODEL", "openai/gpt-4o")
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            logger.warning("OPENAI_API_KEY not set — DSPy optimizer will not function")
            return
        lm = dspy.LM(model, api_key=api_key, temperature=0.3, max_tokens=500)
        dspy.configure(lm=lm)

    async def optimize_insight(self, raw_insight: dict, business_context: dict) -> dict:
        if not _DSPY_AVAILABLE or not self._module:
            return raw_insight

        try:
            result = self._module(
                raw_insight=str(raw_insight),
                business_context=str(business_context),
            )
            raw_insight["enhanced_description"] = result.enhanced_insight
            raw_insight["action_item"] = result.action_item
            raw_insight["_dspy_optimized"] = True
            return raw_insight
        except Exception as e:
            logger.warning(f"DSPy optimization failed: {e}")
            return raw_insight

    async def optimize_batch(self, insights: list[dict], business_context: dict) -> list[dict]:
        if not _DSPY_AVAILABLE or not self._module:
            return insights
        optimized = []
        for insight in insights:
            optimized.append(await self.optimize_insight(insight, business_context))
        return optimized

    def compile_with_examples(self, examples: list[dict]):
        """Compile the optimizer with labeled examples for better quality.

        Each example: {raw_insight, business_context, enhanced_insight, action_item}
        """
        if not _DSPY_AVAILABLE or not self._module:
            logger.info("DSPy not available — skipping compilation")
            return

        try:
            trainset = [
                dspy.Example(
                    raw_insight=str(ex["raw_insight"]),
                    business_context=str(ex["business_context"]),
                    enhanced_insight=ex["enhanced_insight"],
                    action_item=ex["action_item"],
                ).with_inputs("raw_insight", "business_context")
                for ex in examples
            ]

            def metric(example, pred, trace=None):
                return (
                    len(pred.enhanced_insight) > 20
                    and len(pred.action_item) > 10
                    and "$" in pred.enhanced_insight
                )

            optimizer = dspy.MIPROv2(metric=metric, auto="light", num_threads=4)
            self._module = optimizer.compile(self._module, trainset=trainset)
            self._compiled = True
            logger.info(f"DSPy optimizer compiled with {len(trainset)} examples")
        except Exception as e:
            logger.error(f"DSPy compilation failed: {e}")

    @property
    def is_compiled(self) -> bool:
        return self._compiled

    @property
    def is_available(self) -> bool:
        return _DSPY_AVAILABLE and self._module is not None
