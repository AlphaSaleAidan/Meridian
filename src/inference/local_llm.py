"""Local LLM inference via llama-cpp-python. CPU-optimized for AMD EPYC."""

import logging
import os
from pathlib import Path

logger = logging.getLogger("meridian.inference")

MODEL_DIR = Path(__file__).parent.parent.parent / "data" / "models"
DEFAULT_MODEL = os.environ.get(
    "LOCAL_LLM_MODEL",
    "Qwen2.5-7B-Instruct-Q4_K_M.gguf",
)
FALLBACK_MODEL = "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"

_llm_instance = None


# ── Call budget (cost cap) ────────────────────────────────────────────────
# Batch pipelines (rebuild-all) set a hard cap on LLM calls so a pathological
# repo state / runaway loop can't burn unbounded compute. None = unlimited.

class LLMBudgetExceeded(RuntimeError):
    """Raised by generate() once the configured call budget is exhausted."""


_budget: dict = {"remaining": None, "used": 0, "exceeded": False}


def set_llm_call_budget(max_calls: int) -> None:
    """Arm the call budget. Subsequent generate() calls decrement it."""
    _budget["remaining"] = max(0, int(max_calls))
    _budget["used"] = 0
    _budget["exceeded"] = False


def clear_llm_call_budget() -> int:
    """Disarm the budget; returns how many calls were used."""
    used = _budget["used"]
    _budget["remaining"] = None
    return used


def llm_calls_used() -> int:
    return _budget["used"]


def llm_budget_exceeded() -> bool:
    return _budget["exceeded"]


def _consume_budget() -> None:
    if _budget["remaining"] is None:
        _budget["used"] += 1
        return
    if _budget["remaining"] <= 0:
        _budget["exceeded"] = True
        raise LLMBudgetExceeded(
            f"LLM call budget exhausted after {_budget['used']} calls"
        )
    _budget["remaining"] -= 1
    _budget["used"] += 1


def get_llm(
    model_name: str = DEFAULT_MODEL,
    n_ctx: int = 4096,
    n_threads: int = 8,
):
    global _llm_instance
    if _llm_instance is not None:
        return _llm_instance

    from llama_cpp import Llama

    model_path = MODEL_DIR / model_name
    if not model_path.exists():
        fallback_path = MODEL_DIR / FALLBACK_MODEL
        if fallback_path.exists():
            logger.warning(f"{model_name} not found, using fallback {FALLBACK_MODEL}")
            model_path = fallback_path
        else:
            raise FileNotFoundError(f"No model found in {MODEL_DIR}")

    logger.info(f"Loading local LLM: {model_name} (ctx={n_ctx}, threads={n_threads})")
    _llm_instance = Llama(
        model_path=str(model_path),
        n_ctx=n_ctx,
        n_threads=n_threads,
        n_gpu_layers=0,
        verbose=False,
    )
    logger.info("Local LLM loaded")
    return _llm_instance


def generate(
    prompt: str,
    system: str = "You are a helpful business analytics assistant.",
    max_tokens: int = 1024,
    temperature: float = 0.7,
    model_name: str = DEFAULT_MODEL,
) -> str:
    _consume_budget()
    llm = get_llm(model_name)
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]
    response = llm.create_chat_completion(
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return response["choices"][0]["message"]["content"]


def generate_batch(
    prompts: list[dict],
    system: str = "You are a helpful business analytics assistant.",
    max_tokens: int = 1024,
) -> list[str]:
    """Process multiple prompts sequentially through local LLM."""
    results = []
    for item in prompts:
        text = item if isinstance(item, str) else item.get("prompt", "")
        result = generate(text, system=system, max_tokens=max_tokens)
        results.append(result)
    return results
