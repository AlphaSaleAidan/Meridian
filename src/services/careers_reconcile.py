"""Careers pipeline reconciliation — the invariant guard behind the daily
careers-reconcile worker (celery beat).

Invariants checked (the exact ways the flow broke silently 07-16 → 07-29):
  1. Every pending career application has a sales_reps row, so the applicant
     is visible in their portal's Team > Applications tab.
  2. Every application from the last 25h produced at least one
     career_application alert email (email_send_log), so the hiring team saw it.

Healthy → returns counts, sends nothing. Broken → one alert email to the
hiring team listing exactly who is affected. Pure logic lives in
find_careers_gaps() so tests can drive it with fake rows.
"""
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("meridian.services.careers_reconcile")

_TEST_EMAIL_MARKER = "e2e-careers-test-"


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def find_careers_gaps(
    applications: list[dict],
    rep_emails: set[str],
    email_log: list[dict],
    now: datetime | None = None,
) -> tuple[list[dict], list[dict]]:
    """Return (visibility_gaps, email_gaps) among pending applications."""
    now = now or datetime.now(timezone.utc)
    email_window_start = now - timedelta(hours=25)

    visibility_gaps: list[dict] = []
    email_gaps: list[dict] = []

    log_times = [t for t in (_parse_ts(r.get("created_at")) for r in email_log) if t]

    for app in applications:
        email = (app.get("email") or "").strip().lower()
        if not email or _TEST_EMAIL_MARKER in email:
            continue

        if email not in rep_emails:
            visibility_gaps.append(app)

        applied_at = _parse_ts(app.get("created_at"))
        if applied_at and applied_at >= email_window_start:
            if not any(applied_at <= t <= applied_at + timedelta(hours=1) for t in log_times):
                email_gaps.append(app)

    return visibility_gaps, email_gaps


async def run_reconciliation(db) -> dict:
    """Fetch live rows, evaluate invariants, alert the hiring team on breakage."""
    applications = await db.select(
        "career_applications", filters={"status": "eq.pending"},
    )
    reps = await db.select("sales_reps", columns="email")
    rep_emails = {(r.get("email") or "").strip().lower() for r in reps}

    cutoff = (datetime.now(timezone.utc) - timedelta(hours=26)).isoformat()
    try:
        email_log = await db.select(
            "email_send_log",
            columns="created_at",
            filters={"template": "eq.career_application", "created_at": f"gte.{cutoff}"},
        )
    except Exception as exc:  # table may not exist in some environments
        logger.warning("careers-reconcile: email_send_log unavailable (%s) — skipping email check", exc)
        email_log = None

    visibility_gaps, email_gaps = find_careers_gaps(
        applications, rep_emails, email_log or [],
    )
    if email_log is None:
        email_gaps = []

    result = {
        "pending_applications": len(applications),
        "visibility_gaps": len(visibility_gaps),
        "email_gaps": len(email_gaps),
    }

    if not visibility_gaps and not email_gaps:
        logger.info("careers-reconcile: healthy (%s)", result)
        return result

    from ..api.routes.careers import _ADMIN_NOTIFY_EMAILS
    from ..email.send import send_careers_reconcile_alert

    for to in _ADMIN_NOTIFY_EMAILS:
        try:
            await send_careers_reconcile_alert(
                to, visibility_gaps=visibility_gaps, email_gaps=email_gaps,
            )
        except Exception as exc:
            logger.error("careers-reconcile: alert to %s failed: %s", to, exc)

    logger.warning("careers-reconcile: BROKEN — %s", result)
    return result
