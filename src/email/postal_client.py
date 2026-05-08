"""
Postal REST API client for Meridian.

Postal is a self-hosted, MIT-licensed mail delivery platform.
Docs: https://docs.postalserver.io/developer/api
"""
import os
import logging
from typing import Optional
from dataclasses import dataclass

import httpx

logger = logging.getLogger("meridian.email.postal")


@dataclass(frozen=True)
class PostalConfig:
    host: str = os.getenv("POSTAL_HOST", "https://postal.meridian.tips")
    api_key: str = os.getenv("POSTAL_API_KEY", "")
    default_from: str = os.getenv("POSTAL_FROM", "Meridian <hello@meridian.tips>")
    webhook_secret: str = os.getenv("POSTAL_WEBHOOK_SECRET", "")
    server_hostname: str = os.getenv("POSTAL_SERVER_HOSTNAME", "postal.meridian.tips")


_config = PostalConfig()


class PostalClient:
    """Async HTTP client for the Postal send API."""

    def __init__(self, config: Optional[PostalConfig] = None):
        self._cfg = config or _config
        self._base = self._cfg.host.rstrip("/") + "/api/v1"

    async def send(
        self,
        to: str,
        subject: str,
        html: str,
        *,
        from_addr: Optional[str] = None,
        tag: Optional[str] = None,
        reply_to: Optional[str] = None,
        cc: Optional[str] = None,
    ) -> dict:
        """Send a single email via Postal."""
        if not self._cfg.api_key:
            logger.warning("[Postal] No API key — email not sent: %s → %s", subject, to)
            return {"status": "skipped", "reason": "no_api_key"}

        payload: dict = {
            "to": [to],
            "from": from_addr or self._cfg.default_from,
            "subject": subject,
            "html_body": html,
        }
        if tag:
            payload["tag"] = tag
        if reply_to:
            payload["reply_to"] = reply_to
        if cc:
            payload["cc"] = [cc]

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"{self._base}/send/message",
                    json=payload,
                    headers={
                        "X-Server-API-Key": self._cfg.api_key,
                        "Content-Type": "application/json",
                        "Host": self._cfg.server_hostname,
                    },
                )
                data = resp.json()

            if resp.status_code == 200 and data.get("status") == "success":
                msg_id = data.get("data", {}).get("message_id", "")
                logger.info("[Postal] Sent '%s' to %s (id=%s)", subject, to, msg_id)
                return {"status": "sent", "message_id": msg_id}

            logger.error("[Postal] API error %d: %s", resp.status_code, data)
            return {"status": "error", "code": resp.status_code, "detail": data}

        except httpx.TimeoutException:
            logger.error("[Postal] Timeout sending '%s' to %s", subject, to)
            return {"status": "error", "reason": "timeout"}
        except Exception as exc:
            logger.error("[Postal] Exception: %s", exc)
            return {"status": "error", "reason": str(exc)}

    async def send_raw(
        self,
        to: str,
        mail_from: str,
        raw_message: str,
        *,
        tag: Optional[str] = None,
    ) -> dict:
        """Send a raw RFC 2822 message (for MIME attachments, etc)."""
        if not self._cfg.api_key:
            return {"status": "skipped", "reason": "no_api_key"}

        payload: dict = {
            "mail_from": mail_from,
            "rcpt_to": [to],
            "data": raw_message,
        }
        if tag:
            payload["tag"] = tag

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"{self._base}/send/raw",
                    json=payload,
                    headers={
                        "X-Server-API-Key": self._cfg.api_key,
                        "Content-Type": "application/json",
                        "Host": self._cfg.server_hostname,
                    },
                )
                return resp.json()
        except Exception as exc:
            logger.error("[Postal] Raw send error: %s", exc)
            return {"status": "error", "reason": str(exc)}
