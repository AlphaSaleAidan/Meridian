"""
Langfuse observability for Meridian LLM calls.

Provides decorators and context managers for tracing LLM calls,
agent executions, and pipeline runs. Falls back to no-op when
Langfuse is not configured.
"""
import functools
import logging
import os
import time
from contextlib import contextmanager
from typing import Any, Callable

logger = logging.getLogger("meridian.observability")

LANGFUSE_PUBLIC_KEY = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY = os.environ.get("LANGFUSE_SECRET_KEY", "")
LANGFUSE_HOST = os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com")

_langfuse = None
_enabled = False


def _init_langfuse():
    global _langfuse, _enabled
    if _langfuse is not None:
        return
    if not LANGFUSE_PUBLIC_KEY or not LANGFUSE_SECRET_KEY:
        logger.info("Langfuse keys not set — observability disabled")
        return
    try:
        from langfuse import Langfuse
        _langfuse = Langfuse(
            public_key=LANGFUSE_PUBLIC_KEY,
            secret_key=LANGFUSE_SECRET_KEY,
            host=LANGFUSE_HOST,
        )
        _enabled = True
        logger.info("Langfuse observability initialized")
    except ImportError:
        logger.info("langfuse not installed — observability disabled")
    except Exception as e:
        logger.warning(f"Langfuse init failed: {e}")


_init_langfuse()


def trace_llm_call(name: str = "llm_call", metadata: dict | None = None):
    """Decorator for tracing LLM calls (sync or async)."""
    def decorator(fn: Callable) -> Callable:
        if not _enabled:
            return fn

        if _is_async(fn):
            @functools.wraps(fn)
            async def async_wrapper(*args, **kwargs):
                trace = _langfuse.trace(name=name, metadata=metadata or {})
                span = trace.span(name=f"{name}_execution")
                start = time.monotonic()
                try:
                    result = await fn(*args, **kwargs)
                    span.end(output=_safe_serialize(result))
                    trace.update(output={"status": "success", "duration_ms": _elapsed_ms(start)})
                    return result
                except Exception as e:
                    span.end(output={"error": str(e)})
                    trace.update(output={"status": "error", "error": str(e), "duration_ms": _elapsed_ms(start)})
                    raise
            return async_wrapper
        else:
            @functools.wraps(fn)
            def sync_wrapper(*args, **kwargs):
                trace = _langfuse.trace(name=name, metadata=metadata or {})
                span = trace.span(name=f"{name}_execution")
                start = time.monotonic()
                try:
                    result = fn(*args, **kwargs)
                    span.end(output=_safe_serialize(result))
                    trace.update(output={"status": "success", "duration_ms": _elapsed_ms(start)})
                    return result
                except Exception as e:
                    span.end(output={"error": str(e)})
                    trace.update(output={"status": "error", "error": str(e), "duration_ms": _elapsed_ms(start)})
                    raise
            return sync_wrapper
    return decorator


def trace_agent(agent_name: str):
    """Decorator for tracing agent analyze() calls."""
    def decorator(fn: Callable) -> Callable:
        if not _enabled:
            return fn

        @functools.wraps(fn)
        async def wrapper(self, *args, **kwargs):
            trace = _langfuse.trace(
                name=f"agent_{agent_name}",
                metadata={"agent": agent_name, "tier": getattr(self, "tier", 0)},
            )
            generation = trace.generation(
                name=f"{agent_name}_analysis",
                model="meridian-agent",
                metadata={"agent_class": type(self).__name__},
            )
            start = time.monotonic()
            try:
                result = await fn(self, *args, **kwargs)
                generation.end(
                    output=_safe_serialize(result),
                    usage={"total_tokens": _estimate_tokens(result)},
                )
                trace.update(output={
                    "status": result.get("status", "unknown"),
                    "score": result.get("score", 0),
                    "calculation_path": result.get("calculation_path", "unknown"),
                    "duration_ms": _elapsed_ms(start),
                })
                return result
            except Exception as e:
                generation.end(output={"error": str(e)})
                trace.update(output={"status": "error", "error": str(e), "duration_ms": _elapsed_ms(start)})
                raise
        return wrapper
    return decorator


@contextmanager
def trace_pipeline(pipeline_name: str, metadata: dict | None = None):
    """Context manager for tracing full pipeline runs."""
    if not _enabled:
        yield None
        return

    trace = _langfuse.trace(name=pipeline_name, metadata=metadata or {})
    start = time.monotonic()
    try:
        yield trace
        trace.update(output={"status": "success", "duration_ms": _elapsed_ms(start)})
    except Exception as e:
        trace.update(output={"status": "error", "error": str(e), "duration_ms": _elapsed_ms(start)})
        raise


def log_generation(name: str, model: str, input_data: Any, output_data: Any, usage: dict | None = None):
    """Log a standalone LLM generation event."""
    if not _enabled:
        return
    trace = _langfuse.trace(name=name)
    trace.generation(
        name=name,
        model=model,
        input=_safe_serialize(input_data),
        output=_safe_serialize(output_data),
        usage=usage or {},
    )


def flush():
    """Flush pending Langfuse events. No-op when disabled."""
    if _enabled and _langfuse:
        _langfuse.flush()


def _is_async(fn: Callable) -> bool:
    import asyncio
    return asyncio.iscoroutinefunction(fn)


def _elapsed_ms(start: float) -> int:
    return int((time.monotonic() - start) * 1000)


def _estimate_tokens(result: Any) -> int:
    import json
    try:
        return len(json.dumps(result, default=str)) // 4
    except Exception:
        return 0


def _safe_serialize(obj: Any) -> Any:
    import json
    try:
        json.dumps(obj, default=str)
        return obj
    except (TypeError, ValueError):
        return str(obj)[:2000]
