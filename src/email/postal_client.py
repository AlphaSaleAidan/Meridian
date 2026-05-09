"""
Email delivery client for Meridian.

Supports two backends:
  1. Postal (self-hosted) — set POSTAL_API_KEY
  2. Resend (cloud fallback) — set RESEND_API_KEY

If both are set, Postal is preferred. If Postal fails, Resend is tried.
If neither is set, emails are logged and skipped.
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
    resend_api_key: str = os.getenv("RESEND_API_KEY", "")
    resend_from: str = os.getenv("RESEND_FROM", "Meridian <hello@meridian.tips>")


_config = PostalConfig()


class PostalClient:
    """Async email client — Postal primary, Resend fallback."""

    def __init__(self, config: Optional[PostalConfig] = None):
        self._cfg = config or _config
        self._base = self._cfg.host.rstrip("/") + "/api/v1"

    async def _send_resend(
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
        """Send via Resend REST API (https://resend.com/docs/api-reference)."""
        payload: dict = {
            "from": from_addr or self._cfg.resend_from,
            "to": [to],
            "subject": subject,
            "html": html,
        }
        if reply_to:
            payload["reply_to"] = [reply_to]
        if cc:
            payload["cc"] = [cc]
        if tag:
            payload["tags"] = [{"name": "category", "value": tag}]

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    "https://api.resend.com/emails",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {self._cfg.resend_api_key}",
                        "Content-Type": "application/json",
                    },
                )
                data = resp.json()

            if resp.status_code in (200, 201):
                msg_id = data.get("id", "")
                logger.info("[Resend] Sent '%s' to %s (id=%s)", subject, to, msg_id)
                return {"status": "sent", "message_id": msg_id, "provider": "resend"}

            logger.error("[Resend] API error %d: %s", resp.status_code, data)
            return {"status": "error", "code": resp.status_code, "detail": data, "provider": "resend"}

        except httpx.TimeoutException:
            logger.error("[Resend] Timeout sending '%s' to %s", subject, to)
            return {"status": "error", "reason": "timeout", "provider": "resend"}
        except Exception as exc:
            logger.error("[Resend] Exception: %s", exc)
            return {"status": "error", "reason": str(exc), "provider": "resend"}

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
        """Send email via Postal, falling back to Resend if unavailable."""
        kwargs = dict(from_addr=from_addr, tag=tag, reply_to=reply_to, cc=cc)

        # Try Postal first
        if self._cfg.api_key:
            result = await self._send_postal(to, subject, html, **kwargs)
            if result.get("status") == "sent":
                return result
            # Postal failed — try Resend fallback
            if self._cfg.resend_api_key:
                logger.info("[Email] Postal failed, falling back to Resend for '%s' → %s", subject, to)
                return await self._send_resend(to, subject, html, **kwargs)
            return result

        # No Postal key — try Resend directly
        if self._cfg.resend_api_key:
            return await self._send_resend(to, subject, html, **kwargs)

        logger.warning("[Email] No API key (Postal or Resend) — email not sent: %s → %s", subject, to)
        return {"status": "skipped", "reason": "no_api_key"}

    async def _send_postal(
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
        """Send via self-hosted Postal."""
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
                return {"status": "sent", "message_id": msg_id, "provider": "postal"}

            logger.error("[Postal] API error %d: %s", resp.status_code, data)
            return {"status": "error", "code": resp.status_code, "detail": data, "provider": "postal"}

        except httpx.TimeoutException:
            logger.error("[Postal] Timeout sending '%s' to %s", subject, to)
            return {"status": "error", "reason": "timeout", "provider": "postal"}
        except Exception as exc:
            logger.error("[Postal] Exception: %s", exc)
            return {"status": "error", "reason": str(exc), "provider": "postal"}

    async def send_raw(
        self,
        to: str,
        mail_from: str,
        raw_message: str,
        *,
        tag: Optional[str] = None,
    ) -> dict:
        """Send a raw RFC 2822 message (Postal only, no Resend equivalent)."""
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
