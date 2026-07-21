"""
Vapi phone-number binding — the missing link that makes a self-serve merchant's
provisioned DID actually ring the AI agent.

Provisioning buys a Twilio number and (until now) pointed its VoiceUrl at the
legacy /twilio/voice pipeline — but the live agent runs on Vapi, so a
wizard-provisioned number never reached the assistant and forwarding
verification (which waits for a Vapi `assistant-request`) could never pass.

This module imports a purchased Twilio number INTO Vapi with our webhook as the
server URL and no static assistant, so every inbound call fires
`assistant-request` → src/api/routes/vapi_webhook.py resolves the merchant by
the dialed number and returns a transient assistant.

Gating: binding is active only when VAPI_PRIVATE_KEY is set. Without it every
function no-ops (returns None / False) and provisioning falls back to its prior
behavior unchanged — so the key can be added to prod to switch this on with no
code change.
"""
import logging
import os

import httpx

logger = logging.getLogger("meridian.vapi.provisioning")

_VAPI_API = "https://api.vapi.ai"
_TIMEOUT = 20.0


def _api_key() -> str:
    return os.getenv("VAPI_PRIVATE_KEY", "").strip()


def vapi_binding_enabled() -> bool:
    """True when we can bind numbers into Vapi (private API key present).

    Kept as a call-time read (not a module constant) so ops can add the key on
    the running service and tests can monkeypatch the env."""
    return bool(_api_key())


def _server_config() -> dict:
    """The server block Vapi calls on every inbound event. `secret` is echoed
    back as the x-vapi-secret header our webhook checks (fail-closed), so the
    two MUST match. No assistantId/squadId/workflowId → Vapi sends
    `assistant-request` to this URL, which is exactly the dynamic path
    vapi_webhook.py implements."""
    host = os.getenv("MEDIA_STREAM_HOST", "api.meridian.tips")
    cfg: dict = {
        "url": f"https://{host}/api/vapi/webhook",
        "timeoutSeconds": 20,
    }
    secret = os.getenv("VAPI_SERVER_SECRET", "").strip()
    if secret:
        cfg["secret"] = secret
    return cfg


async def import_twilio_number(
    number: str,
    *,
    twilio_account_sid: str,
    twilio_auth_token: str,
    name: str = "",
) -> str | None:
    """Register an existing Twilio number with Vapi for dynamic assistant
    routing. Returns the Vapi phone-number id, or None when binding is disabled
    or the import fails (logged — the caller decides whether to roll back)."""
    if not vapi_binding_enabled():
        return None
    if not (number and twilio_account_sid and twilio_auth_token):
        logger.error("vapi import: missing number/twilio credentials")
        return None

    body = {
        "provider": "twilio",
        "number": number,
        "twilioAccountSid": twilio_account_sid,
        "twilioAuthToken": twilio_auth_token,
        "server": _server_config(),
    }
    if name:
        body["name"] = name[:40]

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            res = await client.post(
                f"{_VAPI_API}/phone-number",
                json=body,
                headers={"Authorization": f"Bearer {_api_key()}"},
            )
    except httpx.HTTPError as e:
        logger.error("vapi import: network error for %s: %s", number, e)
        return None

    if res.status_code not in (200, 201):
        logger.error("vapi import %s failed HTTP %s: %s",
                     number, res.status_code, res.text[:300])
        return None
    vapi_id = (res.json() or {}).get("id", "")
    if not vapi_id:
        logger.error("vapi import %s: 2xx but no id in response", number)
        return None
    logger.info("vapi import: bound %s → phone-number %s", number, vapi_id)
    return vapi_id


async def delete_vapi_number(vapi_id: str) -> bool:
    """Release a Vapi phone-number binding (best-effort). Returns True on a
    2xx or 404 (already gone). Never raises — callers use it during swap /
    disconnect where a failure must not block the primary operation."""
    if not (vapi_binding_enabled() and vapi_id):
        return False
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            res = await client.delete(
                f"{_VAPI_API}/phone-number/{vapi_id}",
                headers={"Authorization": f"Bearer {_api_key()}"},
            )
    except httpx.HTTPError as e:
        logger.warning("vapi delete %s: network error: %s", vapi_id, e)
        return False
    if res.status_code in (200, 201, 202, 204, 404):
        return True
    logger.warning("vapi delete %s failed HTTP %s: %s",
                   vapi_id, res.status_code, res.text[:200])
    return False


async def list_vapi_numbers() -> list[dict]:
    """All phone numbers registered in the Vapi workspace (diagnostics /
    reconciliation). Empty list when disabled or on error."""
    if not vapi_binding_enabled():
        return []
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            res = await client.get(
                f"{_VAPI_API}/phone-number",
                headers={"Authorization": f"Bearer {_api_key()}"},
            )
    except httpx.HTTPError as e:
        logger.warning("vapi list: network error: %s", e)
        return []
    if res.status_code != 200:
        logger.warning("vapi list failed HTTP %s: %s", res.status_code, res.text[:200])
        return []
    body = res.json()
    return body if isinstance(body, list) else body.get("results", []) or []
