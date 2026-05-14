"""
Prompt injection defense for Meridian's AI agents and Garry chat.

Strips known injection patterns from merchant-supplied data before
it enters any LLM prompt. Apply sanitize_for_llm() to every string
from Supabase or user input before including it in a prompt.
"""
import re
import logging
from typing import Any

_log = logging.getLogger("meridian.security.sanitizer")

INJECTION_PATTERNS: list[tuple[str, str]] = [
    # Instruction override
    (r"ignore\s+(all\s+)?(previous|prior|above|preceding)\s+instructions?", "high"),
    (r"disregard\s+(all\s+)?(previous|prior|above)\s+instructions?", "high"),
    (r"forget\s+(everything|all previous|your instructions)", "high"),
    (r"you\s+are\s+now\s+(an?\s+)?[a-z]", "high"),
    (r"act\s+as\s+(an?\s+)?[a-z]", "high"),
    (r"pretend\s+(you\s+are|to\s+be)", "high"),
    (r"new\s+system\s+prompt", "high"),
    (r"override\s+(the\s+)?(system|previous|original)", "high"),
    (r"jailbreak", "high"),
    (r"DAN\s+mode", "high"),
    # Delimiter injection
    (r"</?system>", "high"),
    (r"</?user>", "high"),
    (r"</?assistant>", "high"),
    (r"\[INST\]", "high"),
    (r"\[/INST\]", "high"),
    (r"<\|im_start\|>", "high"),
    (r"<\|im_end\|>", "high"),
    (r"###\s+System", "medium"),
    (r"###\s+Human", "medium"),
    (r"###\s+Assistant", "medium"),
    # Data exfiltration
    (r"(email|send|transmit|reveal|show|display)\s+(the\s+)?(database|schema|api.?key|password|secret|token)", "high"),
    (r"what\s+(are\s+)?your\s+(system\s+)?(instructions|prompt|rules)", "medium"),
    (r"reveal\s+your\s+(system\s+)?prompt", "high"),
    # SQL injection via LLM
    (r"(DROP|DELETE|TRUNCATE|ALTER)\s+TABLE", "high"),
    (r"UNION\s+SELECT", "high"),
]

MAX_INPUT_LENGTH = 2000
REDACTION = "[REMOVED]"


def sanitize_for_llm(
    text: str,
    field_name: str = "unknown",
    wrap_as_data: bool = True,
) -> str:
    if not text or not isinstance(text, str):
        return str(text) if text is not None else ""

    try:
        cleaned = text.strip()
        detected = []

        for pattern, severity in INJECTION_PATTERNS:
            if re.search(pattern, cleaned, flags=re.IGNORECASE):
                detected.append((pattern, severity))
                cleaned = re.sub(pattern, REDACTION, cleaned, flags=re.IGNORECASE)

        if detected:
            high = any(s == "high" for _, s in detected)
            _log.warning(
                "Injection detected in '%s': %d patterns (%s)",
                field_name,
                len(detected),
                "HIGH" if high else "medium",
            )
            if high:
                try:
                    from src.api.security.audit_log import (
                        log_security_event,
                        SecurityEvent,
                    )
                    log_security_event(
                        event_type=SecurityEvent.PROMPT_INJECTION,
                        severity="critical",
                        details={
                            "field": field_name,
                            "patterns": len(detected),
                        },
                    )
                except Exception:
                    pass

        if len(cleaned) > MAX_INPUT_LENGTH:
            cleaned = cleaned[:MAX_INPUT_LENGTH] + "...[truncated]"

        if wrap_as_data and cleaned:
            cleaned = f"<data>{cleaned}</data>"

        return cleaned

    except Exception as e:
        _log.error("Sanitizer error on %s: %s", field_name, e)
        return text[:MAX_INPUT_LENGTH] if text else ""


def sanitize_merchant_context(data: dict) -> dict:
    if not isinstance(data, dict):
        return data

    result = {}
    for key, value in data.items():
        if isinstance(value, str):
            result[key] = sanitize_for_llm(value, field_name=key)
        elif isinstance(value, dict):
            result[key] = sanitize_merchant_context(value)
        elif isinstance(value, list):
            result[key] = [
                sanitize_for_llm(v, field_name=f"{key}[{i}]")
                if isinstance(v, str)
                else sanitize_merchant_context(v)
                if isinstance(v, dict)
                else v
                for i, v in enumerate(value)
            ]
        else:
            result[key] = value

    return result
