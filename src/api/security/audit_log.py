"""
Structured security event logging for Meridian.

Logs go to:
1. Python logging (always — visible in pm2/Railway logs)
2. Supabase security_events table (for critical/warning — Garry monitors)
"""
import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import Request

security_logger = logging.getLogger("meridian.security")
security_logger.setLevel(logging.INFO)


class SecurityEvent:
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    RATE_LIMIT_HIT = "rate_limit_hit"
    INVALID_TOKEN = "invalid_token"
    TOKEN_EXPIRED = "token_expired"
    RLS_VIOLATION = "rls_violation_attempt"
    POS_CONNECT = "pos_connect"
    POS_CREDENTIAL_ACCESS = "pos_credential_access"
    ADMIN_ACTION = "admin_action"
    PAYOUT_RATE_CHANGE = "payout_rate_change"
    DATA_EXPORT = "data_export"
    PROMPT_INJECTION = "prompt_injection_detected"
    AGENT_ERROR = "agent_error"
    UNUSUAL_ACCESS = "unusual_access_pattern"
    BRUTE_FORCE = "brute_force_detected"


def log_security_event(
    event_type: str,
    request: Optional[Request] = None,
    severity: str = "info",
    user_id: Optional[str] = None,
    merchant_id: Optional[str] = None,
    portal_context: Optional[str] = None,
    details: Optional[dict] = None,
) -> None:
    try:
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "severity": severity,
            "ip_address": (
                request.client.host
                if request and request.client
                else "internal"
            ),
            "user_agent": (
                request.headers.get("user-agent", "")[:200]
                if request
                else "internal"
            ),
            "path": str(request.url.path) if request else "internal",
            "method": request.method if request else "internal",
            "user_id": str(user_id) if user_id else None,
            "merchant_id": str(merchant_id) if merchant_id else None,
            "portal_context": portal_context,
            "details": details or {},
            "environment": os.environ.get("RAILWAY_ENVIRONMENT", "development"),
        }

        security_logger.info(json.dumps(event))

        if severity in ("critical", "warning"):
            try:
                from ...db import get_db
                import asyncio

                db = get_db()
                if db:
                    asyncio.ensure_future(
                        db.insert("security_events", event)
                    )
            except Exception as db_err:
                security_logger.error(
                    f"Failed to write security event to DB: {db_err}"
                )

    except Exception as log_err:
        import sys
        print(
            f"SECURITY LOG FAILURE: {event_type} — {log_err}",
            file=sys.stderr,
        )


def log_brute_force(
    request: Request,
    target: str,
    attempt_count: int,
    window_seconds: int,
) -> None:
    log_security_event(
        event_type=SecurityEvent.BRUTE_FORCE,
        request=request,
        severity="critical",
        details={
            "target": target,
            "attempts": attempt_count,
            "window_seconds": window_seconds,
        },
    )
