"""
PostHog Analytics Service — Product analytics + feature flags.

Tracks merchant usage patterns and gates features via flags.
Uses org_id as distinct_id — never PII.
"""
import logging
import os
from typing import Any, Optional

logger = logging.getLogger("meridian.analytics")

_posthog = None


def _get_client():
    """Lazy-init PostHog client."""
    global _posthog
    if _posthog is not None:
        return _posthog

    api_key = os.environ.get("POSTHOG_API_KEY", "")
    if not api_key:
        logger.warning("POSTHOG_API_KEY not set — analytics disabled")
        return None

    import posthog
    posthog.project_api_key = api_key
    posthog.host = os.environ.get("POSTHOG_HOST", "https://us.i.posthog.com")

    personal_key = os.environ.get("POSTHOG_PERSONAL_API_KEY", "")
    if personal_key:
        posthog.personal_api_key = personal_key

    _posthog = posthog
    return _posthog


def track(org_id: str, event: str, properties: Optional[dict[str, Any]] = None):
    """Track an analytics event. org_id as distinct_id, never PII."""
    client = _get_client()
    if not client:
        return

    client.capture(
        distinct_id=org_id,
        event=event,
        properties=properties or {},
    )


def track_page_view(org_id: str, page: str, referrer: Optional[str] = None):
    track(org_id, "page_view", {"page": page, "referrer": referrer})


def track_agent_run(org_id: str, agent_name: str, duration_ms: int, status: str):
    track(org_id, "agent_run", {
        "agent_name": agent_name,
        "duration_ms": duration_ms,
        "status": status,
    })


def track_insight_generated(org_id: str, category: str, severity: str):
    track(org_id, "insight_generated", {"category": category, "severity": severity})


def track_action_taken(org_id: str, action_type: str, source_insight: Optional[str] = None):
    track(org_id, "action_taken", {"action_type": action_type, "source_insight": source_insight})


def track_feature_used(org_id: str, feature: str, metadata: Optional[dict] = None):
    track(org_id, "feature_used", {"feature": feature, **(metadata or {})})


def is_feature_enabled(org_id: str, flag: str) -> bool:
    """Check a PostHog feature flag for an org."""
    client = _get_client()
    if not client:
        return False
    return client.feature_enabled(flag, org_id) or False


# Feature flag constants
FLAG_VISION_BETA = "vision_beta"
FLAG_VOICE_AI = "voice_ai"
FLAG_ADVANCED_FORECAST = "advanced_forecast"


def shutdown():
    """Flush pending events. Call on app shutdown."""
    client = _get_client()
    if client:
        client.shutdown()
