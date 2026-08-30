"""
Meridian → Foundry lead bridge (server-to-server).

Foundry (foundry.meridian.tips) is the build division's agency platform. Its
inbound endpoint lands a Lead in the Foundry ops pipeline, pings ops, and
emails the prospect a Site Sprint confirmation. We forward ONLY website/CRM-
shaped interest: Foundry's confirmation email pitches website work, so pushing
a POS/analytics prospect through it would read as off-topic noise.

Env (both required to activate; either absent = bridge inert):
  FOUNDRY_INBOUND_URL  e.g. https://foundry.meridian.tips/agency/api/inbound/meridian
  FOUNDRY_INBOUND_KEY  shared secret (Foundry checks x-foundry-inbound-key)

Best-effort by contract: a Foundry outage or slow response must never affect
the prospect's /api/quote-request response — callers wrap us in try/except and
we keep a tight timeout ourselves.
"""
import logging
import os
import re

logger = logging.getLogger("meridian.services.foundry_bridge")

# Website/CRM-shaped interest in the prospect's own words. Deliberately does
# NOT match "online ordering" alone — that's Meridian's POS product, not a
# website build.
_WEBSITE_RE = re.compile(
    r"\b(web\s?site|web\s?page|landing\s+page|web\s+design|online\s+store|"
    r"e-?commerce|storefront|custom\s+crm|crm)\b",
    re.IGNORECASE,
)

_TIMEOUT_SECONDS = 4.0


def is_website_interest(notes: str) -> bool:
    """True when the free-text notes read like website/CRM work."""
    return bool(_WEBSITE_RE.search(notes or ""))


def _config() -> tuple[str, str] | None:
    url = (os.getenv("FOUNDRY_INBOUND_URL") or "").strip()
    key = (os.getenv("FOUNDRY_INBOUND_KEY") or "").strip()
    if not url or not key:
        return None
    return url, key


async def forward_quote_lead(row: dict) -> bool:
    """
    Forward a persisted quote_requests row to Foundry when it is
    website-shaped. Returns True only when Foundry accepted the lead.
    Never raises on transport errors — logs and returns False.
    """
    if not is_website_interest(row.get("notes", "")):
        return False
    config = _config()
    if config is None:
        logger.info("foundry bridge inert: FOUNDRY_INBOUND_URL/KEY not set")
        return False
    url, key = config

    src = (row.get("source") or "").lower()
    market = "canada" if "canada" in src or "ca-" in src else "us"
    window = " ".join(
        part
        for part in (row.get("preferred_date"), row.get("preferred_window"))
        if part
    )
    payload = {
        "company": row.get("business_name", ""),
        "contactName": row.get("full_name", ""),
        "email": row.get("email", ""),
        # Foundry caps phone at 40 chars; quote rows are E.164-normalized.
        "phone": row.get("phone") or None,
        "vertical": "restaurant",
        "notes": (row.get("notes", "") + (f"\nPreferred call window: {window}" if window else "")).strip()[:4000],
        "source": f"meridian-quote-{market}",
    }
    if payload["phone"] is None:
        payload.pop("phone")

    import httpx

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            resp = await client.post(
                url, json=payload, headers={"x-foundry-inbound-key": key}
            )
        if resp.status_code == 200:
            logger.info(
                "foundry bridge: forwarded website lead %s (%s)",
                row.get("business_name"),
                resp.json().get("leadId", "?"),
            )
            return True
        logger.warning(
            "foundry bridge: rejected %s — %s %s",
            row.get("business_name"),
            resp.status_code,
            resp.text[:200],
        )
    except Exception as e:  # transport/timeout — never the prospect's problem
        logger.warning("foundry bridge: forward failed: %s", e)
    return False
