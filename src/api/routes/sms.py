"""SMS routes — thin re-export of the sidecar SMS handler.

The sidecar (services/phone_agent/sms_order.py) holds the actual handler
because it shares helpers (menu rendering, order normalization, payment
links) with the phone-call code. This file just exposes its router for
mounting under the main API app, alongside the credit metering that was
wired into sms_order.py itself.

This mirrors the sys.path-insert pattern used by routes/phone.py for the
Media Streams WebSocket — sidecar code, main-app mount.
"""
import sys
from pathlib import Path

from fastapi import APIRouter

_PHONE_AGENT_DIR = str(Path(__file__).resolve().parents[3] / "services" / "phone_agent")
if _PHONE_AGENT_DIR not in sys.path:
    sys.path.insert(0, _PHONE_AGENT_DIR)

try:
    from sms_order import router as router  # type: ignore
except ImportError:
    # Sidecar not available — surface an empty router so the app still
    # boots. Twilio webhooks pointed at /sms/inbound will 404, which is
    # the correct signal that SMS isn't wired up in this deploy.
    router = APIRouter(prefix="/sms", tags=["sms-order-stub"])

    @router.post("/inbound")
    async def _sms_stub():
        return {"error": "sms_handler_not_available"}
