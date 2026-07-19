"""Shared dedup guard for unauthenticated public submission endpoints.

Careers applications and quote requests have no auth, so a bot (or a
double-click) can insert unlimited duplicate rows and fire unlimited
notification emails. Per-IP rate limiting lives in
src/api/middleware/rate_limiter.py (RATE_LIMITS); this module adds the
second, IP-independent layer: "same email within a window → treat as
already received".

Contract: callers respond 200 to duplicates (never tip off a bot, never
punish a nervous double-submitter) but skip the insert and the email.
Best-effort by design — if the dedup lookup itself fails, the submission
goes through (an outage must never drop a real lead).
"""
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("meridian.services.submission_guard")

DEFAULT_WINDOW_HOURS = 24


async def is_recent_duplicate(
    db,
    table: str,
    email: str,
    *,
    extra_filters: dict[str, str] | None = None,
    window_hours: int = DEFAULT_WINDOW_HOURS,
) -> bool:
    """True if `table` already holds a row for `email` (+extra_filters)
    created within the last `window_hours`. Fails open on lookup errors."""
    if not email:
        return False
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=window_hours)).isoformat()
    filters = {
        "email": f"eq.{email}",
        "created_at": f"gte.{cutoff}",
        **(extra_filters or {}),
    }
    try:
        rows = await db.select(table, "id", filters=filters, limit=1)
        return bool(rows)
    except Exception as e:
        logger.warning("dedup lookup failed for %s (%s): %s — allowing through", table, email, e)
        return False
