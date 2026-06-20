"""
Meridian AI Phone Agent — FastAPI server.

Two modes:
  1. Twilio Voice webhooks (production-ready, no GPU needed)
     - Twilio handles STT + TTS, Claude API handles the brain
     - Works immediately with a Twilio phone number

  2. Open-source Pipecat pipeline (requires GPU + Docker)
     - Fonoster/FreeSWITCH SIP, Ollama LLM, WhisperLiveKit STT, Kokoro TTS
"""
import logging
import os
import time

from fastapi import FastAPI, WebSocket
from fastapi.responses import JSONResponse

import aiohttp

from merchant_config import get_merchant_config, get_merchant_by_phone

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(name)s] %(levelname)s — %(message)s",
)
logger = logging.getLogger("meridian.phone_agent")

app = FastAPI(title="Meridian Phone Agent", version="1.1.0")

# --- Twilio Voice mode (always available) ---
from twilio_voice import router as twilio_router
app.include_router(twilio_router)

# --- SMS Text-to-Order mode (always available) ---
from sms_order import router as sms_router
app.include_router(sms_router)

# --- Open-source Pipecat mode (requires Ollama + GPU) ---
try:
    from bot import run_call_bot
    HAS_PIPECAT = True
except ImportError:
    HAS_PIPECAT = False
    logger.info("Pipecat not available — Twilio-only mode")

OLLAMA_URL = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# Which media-stream envelope the inbound provider speaks. The backend's /voice
# TwiML hands the call to wss://{MEDIA_STREAM_HOST}/twilio/media-stream/{merchant_id};
# this sidecar is that host, so it must drain the same start event the backend would.
PHONE_PROVIDER = os.getenv("PHONE_PROVIDER", "twilio").lower()


@app.get("/health")
async def health():
    result: dict = {
        "status": "ok",
        "twilio_mode": "active",
        "anthropic_key_set": bool(os.getenv("ANTHROPIC_API_KEY")),
    }

    if HAS_PIPECAT:
        ollama_ok = False
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{OLLAMA_URL}/api/tags", timeout=aiohttp.ClientTimeout(total=5)) as r:
                    ollama_ok = r.status == 200
        except Exception:
            pass
        result["pipecat_mode"] = "available"
        result["ollama"] = "ok" if ollama_ok else "unreachable"
    else:
        result["pipecat_mode"] = "not_installed"

    return JSONResponse(result)


if HAS_PIPECAT:
    @app.websocket("/ws/{merchant_id}/{session_ref}")
    async def websocket_handler(
        websocket: WebSocket,
        merchant_id: str,
        session_ref: str,
    ):
        await websocket.accept()
        logger.info("Call connected: merchant=%s session=%s", merchant_id, session_ref)

        config = await get_merchant_config(merchant_id)
        if not config:
            logger.warning("No config for merchant %s — rejecting call", merchant_id)
            await websocket.close(code=1008, reason="Merchant not configured")
            return

        if not config.active:
            logger.info("Phone agent disabled for merchant %s", merchant_id)
            await websocket.close(code=1008, reason="Phone agent disabled")
            return

        caller_info = {"phone": "", "session_ref": session_ref}

        try:
            await run_call_bot(
                websocket=websocket,
                merchant_id=merchant_id,
                session_ref=session_ref,
                merchant_config=config,
                caller_info=caller_info,
            )
        except Exception as e:
            logger.error("Call pipeline error: %s", e, exc_info=True)
        finally:
            logger.info("Call ended: merchant=%s session=%s", merchant_id, session_ref)

    @app.websocket("/ws/inbound")
    async def inbound_handler(websocket: WebSocket):
        await websocket.accept()

        try:
            init_msg = await websocket.receive_json()
            called_number = init_msg.get("to", "")
            caller_number = init_msg.get("from", "")
            session_ref = init_msg.get("session_ref", "unknown")

            merchant_id = await get_merchant_by_phone(called_number)
            if not merchant_id:
                logger.warning("No merchant for number %s", called_number)
                await websocket.close(code=1008)
                return

            config = await get_merchant_config(merchant_id)
            if not config or not config.active:
                await websocket.close(code=1008)
                return

            caller_info = {
                "phone": caller_number,
                "session_ref": session_ref,
            }

            await run_call_bot(
                websocket=websocket,
                merchant_id=merchant_id,
                session_ref=session_ref,
                merchant_config=config,
                caller_info=caller_info,
            )
        except Exception as e:
            logger.error("Inbound call error: %s", e, exc_info=True)

    @app.websocket("/twilio/media-stream/{merchant_id}")
    async def media_stream(websocket: WebSocket, merchant_id: str):
        """Provider Media Streams WebSocket → Pipecat pipeline.

        This is the endpoint the backend's /voice TwiML points Twilio/Telnyx at
        (wss://MEDIA_STREAM_HOST/twilio/media-stream/{merchant_id}). It drains the
        provider's connected→start prelude to capture the stream id (and, for
        Telnyx, the call_control_id + encoding), then hands the socket to the
        pipeline. The TwilioFrameSerializer/TelnyxFrameSerializer in run_call_bot
        decode the mu-law media frames from here on.
        """
        await websocket.accept()
        logger.info("Media stream connected: merchant=%s provider=%s", merchant_id, PHONE_PROVIDER)

        config = await get_merchant_config(merchant_id)
        if not config:
            logger.warning("No config for merchant %s — rejecting", merchant_id)
            await websocket.close(code=1008, reason="Merchant not configured")
            return
        if not getattr(config, "active", True):
            logger.info("Phone agent disabled for merchant %s", merchant_id)
            await websocket.close(code=1008, reason="Phone agent disabled")
            return

        stream_sid: str | None = None
        call_sid = ""
        caller_phone = ""
        call_control_id = ""
        outbound_encoding = "PCMU"
        try:
            for _ in range(5):
                msg = await websocket.receive_json()
                if msg.get("event") != "start":
                    continue
                start = msg.get("start", {})
                if PHONE_PROVIDER == "telnyx":
                    stream_sid = start.get("stream_id") or msg.get("stream_id")
                    call_control_id = start.get("call_control_id", "")
                    call_sid = call_control_id
                    fmt = start.get("media_format", {}) or {}
                    outbound_encoding = (fmt.get("encoding") or "PCMU").upper()
                    params = start.get("custom_parameters", {}) or start.get("customParameters", {}) or {}
                    caller_phone = params.get("caller_phone", "") or start.get("from", "")
                else:
                    stream_sid = start.get("streamSid")
                    call_sid = start.get("callSid", "")
                    params = start.get("customParameters", {}) or {}
                    caller_phone = params.get("caller_phone", "")
                break
        except Exception as e:
            logger.error("Failed to read %s start event: %s", PHONE_PROVIDER, e)
            await websocket.close(code=1011, reason="Bad media handshake")
            return

        if not stream_sid:
            logger.error("No stream id in %s handshake — aborting", PHONE_PROVIDER)
            await websocket.close(code=1011, reason="Missing stream id")
            return

        session_ref = call_sid or f"mstream-{int(time.time() * 1000)}"
        caller_info = {"phone": caller_phone, "session_ref": session_ref}
        try:
            await run_call_bot(
                websocket=websocket,
                merchant_id=merchant_id,
                session_ref=session_ref,
                merchant_config=config,
                caller_info=caller_info,
                stream_sid=stream_sid,
                call_sid=call_sid,
                provider=PHONE_PROVIDER,
                call_control_id=call_control_id,
                outbound_encoding=outbound_encoding,
            )
        except Exception as e:
            logger.error("Media stream pipeline error: %s", e, exc_info=True)
        finally:
            logger.info("Media stream ended: merchant=%s session=%s", merchant_id, session_ref)


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PHONE_AGENT_PORT", "8090"))
    uvicorn.run(app, host="0.0.0.0", port=port)
