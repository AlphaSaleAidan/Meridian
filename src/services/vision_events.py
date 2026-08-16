"""The camera event recorder.

Counts tell a merchant how busy Tuesday was. Events tell them a bottle went
over by the coffee machine eleven minutes ago and nobody has mopped it. Only
one of those is worth interrupting somebody for, and until now the vision
pipeline could only produce the other.

ANONYMOUS BY CONSTRUCTION. An event says a person at the counter was on a
handset for four minutes. It does not say who, there is no column that could
hold who, and there is no lookup that could recover who. That is a deliberate
ceiling on the feature, not an unfinished part of it: "someone at the till" is
enough to walk over and look, and it is the version a merchant can run without
first taking legal advice about monitoring staff.

The vocabulary is closed. A detector cannot invent a category — the database
CHECK constraint and EVENT_KINDS below have to agree, or the write fails, which
is the correct outcome: an event the portal cannot render or explain is worse
than a dropped one.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("meridian.services.vision_events")

# ── The vocabulary ──────────────────────────────────────────────────────
#
# `title` is what the merchant reads in the feed. `why` is the sentence that
# justifies the interruption, because an alert that does not say why it
# matters trains people to close alerts.
EVENT_KINDS: dict[str, dict] = {
    "spill": {
        "title": "Spill on the floor",
        "why": "A wet floor is a slip claim until somebody mops it.",
        "default_severity": "critical",
    },
    "product_loss": {
        "title": "Product left without a sale",
        "why": "Stock moved off the shelf with no matching transaction.",
        "default_severity": "warning",
    },
    "phone_use": {
        "title": "Prolonged phone use in a work zone",
        "why": "Time on a handset in a work zone is time a customer is waiting.",
        "default_severity": "info",
    },
    "unattended": {
        "title": "Counter unattended",
        "why": "Customers were waiting with nobody serving.",
        "default_severity": "warning",
    },
    "blocked_exit": {
        "title": "Exit or aisle blocked",
        "why": "A blocked fire exit is the one that fails an inspection.",
        "default_severity": "critical",
    },
    "after_hours": {
        "title": "Movement after hours",
        "why": "Something moved while the shop should have been empty.",
        "default_severity": "critical",
    },
}

SEVERITIES = ("critical", "warning", "info")
STATUSES = ("new", "acknowledged", "resolved", "dismissed")

# Below this the detector is guessing, and a feed of guesses is a feed nobody
# opens twice. Tuned deliberately high: a missed spill costs a mop, a feed full
# of phantom spills costs the whole feature.
MIN_CONFIDENCE = 0.55


def describe(kind: str) -> dict:
    """Merchant-facing copy for a kind, or a safe fallback."""
    return EVENT_KINDS.get(kind) or {
        "title": "Something worth a look",
        "why": "The camera flagged this and could not categorise it.",
        "default_severity": "info",
    }


def normalise(payload: dict) -> dict | None:
    """Turn one detector payload into a row, or None to drop it.

    Returns None rather than raising: this runs on a device-authenticated hot
    path where one malformed event must never cost the whole batch.
    """
    kind = str(payload.get("kind") or "").strip()
    if kind not in EVENT_KINDS:
        logger.info("dropping vision event with unknown kind %r", kind)
        return None

    confidence = payload.get("confidence")
    try:
        confidence = float(confidence) if confidence is not None else None
    except (TypeError, ValueError):
        confidence = None
    if confidence is not None and confidence < MIN_CONFIDENCE:
        return None

    severity = str(payload.get("severity") or "").strip()
    if severity not in SEVERITIES:
        severity = describe(kind)["default_severity"]

    detected_at = str(payload.get("detected_at") or "").strip()
    if not detected_at:
        detected_at = datetime.now(timezone.utc).isoformat()

    duration = payload.get("duration_sec")
    try:
        duration = int(duration) if duration is not None else None
    except (TypeError, ValueError):
        duration = None

    row = {
        "kind": kind,
        "severity": severity,
        "detected_at": detected_at,
        "zone": (payload.get("zone") or None),
        "duration_sec": duration,
        "confidence": confidence,
        "snapshot_url": (payload.get("snapshot_url") or None),
        "detail": (str(payload.get("detail") or "")[:500] or None),
        # Falls back to a key the detector cannot forget to send. Coarse on
        # purpose — kind + zone + minute — so a detector re-firing across
        # frames within the same minute collapses to one row instead of forty.
        "dedupe_key": (payload.get("dedupe_key")
                       or f"{kind}:{payload.get('zone') or '-'}:{detected_at[:16]}"),
    }
    return row


def summarise(rows: list[dict]) -> dict:
    """Counts the feed header needs, computed once rather than in the client."""
    open_rows = [r for r in rows if r.get("status") == "new"]
    by_kind: dict[str, int] = {}
    for r in rows:
        by_kind[r.get("kind", "?")] = by_kind.get(r.get("kind", "?"), 0) + 1
    return {
        "total": len(rows),
        "open": len(open_rows),
        "critical_open": len([r for r in open_rows if r.get("severity") == "critical"]),
        "by_kind": by_kind,
    }


def window_start(hours: int) -> str:
    """ISO timestamp `hours` ago, clamped to something a query can serve."""
    hours = max(1, min(24 * 30, int(hours or 24)))
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
