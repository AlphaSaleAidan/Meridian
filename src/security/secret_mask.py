"""Mask secret/key material in error text and logs.

Provider/DB error strings (PostgREST 401 bodies, httpx exceptions, config
dumps) can embed live credentials — the 2026-07-15 hunt found paths in
garry_tools.py and llm_client.py where the Supabase service key could
surface in tool output / raised error text. mask_secrets() scrubs every
known secret env value from a string, leaving at most the last 4 chars
for correlation.
"""
import os

# Env vars whose VALUES must never appear in error text or logs.
SECRET_ENV_VARS = (
    "SUPABASE_SERVICE_ROLE_KEY",
    "SUPABASE_SERVICE_KEY",
    "SUPABASE_ANON_KEY",
    "MERIDIAN_ADMIN_KEY",
    "MERIDIAN_SERVICE_TOKEN",
    "SAMBANOVA_API_KEY",
    "DEEPSEEK_API_KEY",
    "OPENAI_API_KEY",
    "ENCRYPTION_KEY",
    "TWILIO_AUTH_TOKEN",
    "TELNYX_API_KEY",
    "STRIPE_SECRET_KEY",
    "STRIPE_POS_CLIENT_SECRET",
    "SQUARE_ACCESS_TOKEN",
    "RESEND_API_KEY",
    "POSTAL_API_KEY",
)

_MIN_SECRET_LEN = 8  # never treat short/trivial values as maskable secrets


def mask_secrets(text: str) -> str:
    """Replace any known secret env value found in `text` with ``***<last4>``."""
    if not text:
        return text
    out = text
    for var in SECRET_ENV_VARS:
        value = os.environ.get(var, "")
        if len(value) >= _MIN_SECRET_LEN and value in out:
            out = out.replace(value, f"***{value[-4:]}")
    return out
