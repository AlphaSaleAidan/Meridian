"""
Highlight.io Monitoring Service — Errors, traces, logs, session replays.

Backend integration: auto-captures FastAPI errors and adds custom spans
for agent execution timing.

Initialize BEFORE FastAPI app creation.
"""
import logging
import os
from contextlib import contextmanager
from typing import Any, Optional

logger = logging.getLogger("meridian.monitoring")

_initialized = False
HIGHLIGHT_PROJECT_ID = os.environ.get("HIGHLIGHT_PROJECT_ID", "")


def init_highlight(app=None):
    """Initialize Highlight.io backend SDK. Call before FastAPI mounts routes."""
    global _initialized
    if _initialized or not HIGHLIGHT_PROJECT_ID:
        if not HIGHLIGHT_PROJECT_ID:
            logger.info("HIGHLIGHT_PROJECT_ID not set — monitoring disabled")
        return

    try:
        import highlight_io
        from highlight_io.integrations.fastapi import FastAPIMiddleware

        highlight_io.H(
            HIGHLIGHT_PROJECT_ID,
            instrument_logging=True,
            service_name="meridian-api",
            service_version="0.2.0",
            environment=os.environ.get("ENVIRONMENT", "development"),
        )

        if app is not None:
            app.add_middleware(FastAPIMiddleware)

        _initialized = True
        logger.info("Highlight.io monitoring initialized")
    except ImportError:
        logger.debug("highlight-io not installed — monitoring disabled")
    except Exception as e:
        logger.warning(f"Highlight.io init failed: {e}")


@contextmanager
def trace_agent(agent_name: str, org_id: str):
    """Custom span for agent execution timing.

    Usage:
        with trace_agent("revenue_trend", org_id):
            result = await agent.analyze()
    """
    if not _initialized:
        yield
        return

    try:
        import highlight_io
        with highlight_io.H.trace(
            span_name=f"agent.{agent_name}",
            attributes={
                "agent.name": agent_name,
                "org.id": org_id,
                "service.component": "ai_engine",
            },
        ):
            yield
    except Exception:
        yield


def capture_error(error: Exception, context: Optional[dict[str, Any]] = None):
    """Manually capture an error with optional context."""
    if not _initialized:
        return

    try:
        import highlight_io
        highlight_io.H.record_exception(error)
        if context:
            for key, value in context.items():
                highlight_io.H.set_attribute(key, str(value))
    except Exception:
        pass


def record_metric(name: str, value: float, attributes: Optional[dict[str, str]] = None):
    """Record a custom metric."""
    if not _initialized:
        return

    try:
        import highlight_io
        highlight_io.H.record_metric(name, value, attributes or {})
    except Exception:
        pass
