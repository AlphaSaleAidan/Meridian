"""
Meridian AI Phone Agent — FastAPI server.
Receives WebSocket connections from Fonoster (FreeSWITCH) and runs
a fully isolated Pipecat pipeline per call.

100% open source stack:
  STT: WhisperLiveKit + faster-whisper
  LLM: Ollama + Llama 3.3
  TTS: Kokoro
  SIP: Fonoster + FreeSWITCH
"""
import logging
import os

from fastapi import FastAPI, WebSocket
from fastapi.responses import JSONResponse

import aiohttp

from bot import run_call_bot
from merchant_config import get_merchant_config, get_merchant_by_phone

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(name)s] %(levelname)s — %(message)s",
)
logger = logging.getLogger("meridian.phone_agent")

app = FastAPI(title="Meridian Phone Agent", version="1.0.0")

OLLAMA_URL = os.getenv("OLLAMA_HOST", "http://localhost:11434")


@app.get("/health")
async def health():
    ollama_ok = False
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{OLLAMA_URL}/api/tags", timeout=aiohttp.ClientTimeout(total=5)) as r:
                ollama_ok = r.status == 200
    except Exception:
        pass

    return JSONResponse({
        "status": "ok",
        "ollama": "ok" if ollama_ok else "unreachable",
        "stt": "whisperlivekit",
        "tts": "kokoro",
        "llm": os.getenv("OLLAMA_MODEL", "llama3.3:70b"),
    })


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
    """
    Generic inbound handler — Fonoster sends the called number
    in the initial WebSocket message. We look up the merchant
    from the phone number.
    """
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


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PHONE_AGENT_PORT", "8090"))
    uvicorn.run(app, host="0.0.0.0", port=port)
