"""
Vapi voice-agent webhook (POC).

Vapi (https://vapi.ai) is being trialed as an alternative to the Telnyx/Pipecat
voice agent. The trial assistant's `submit_order` tool POSTs here; we log the
captured order and return a spoken confirmation so the call completes cleanly.

Handles both Vapi tool-call shapes:
  - message.type == "tool-calls"  → respond {"results":[{"toolCallId","result"}]}
  - message.type == "function-call" (legacy) → respond {"result": "..."}
Other message types (status-update, end-of-call-report) are acknowledged 200.

POC scope: capture + confirm only. Wiring the order into the real POS pipeline
(create_pos_order/route_order) is a follow-up once we decide Vapi is the path.
"""
import logging

from fastapi import APIRouter, Request

logger = logging.getLogger("meridian.api.vapi")

router = APIRouter(prefix="/api/vapi", tags=["vapi"])


def _confirm(args: dict) -> str:
    items = args.get("items") or []
    n = sum(int(i.get("quantity", 1) or 1) for i in items)
    who = args.get("customer_name") or "there"
    otype = (args.get("order_type") or "pickup").replace("_", " ")
    return (f"Thanks {who}! Got your {otype} order — {n} item"
            f"{'s' if n != 1 else ''} in. It'll be ready in about 20 minutes.")


@router.post("/webhook")
async def vapi_webhook(request: Request):
    try:
        payload = await request.json()
    except Exception:
        return {"received": True}
    msg = (payload or {}).get("message", {}) or {}
    mtype = msg.get("type", "")

    # New tool-calls shape (one response per toolCall).
    if mtype == "tool-calls":
        results = []
        for tc in msg.get("toolCallList", []) or msg.get("toolCalls", []) or []:
            fn = tc.get("function", {}) or {}
            args = fn.get("arguments", {}) or {}
            if isinstance(args, str):
                import json
                try:
                    args = json.loads(args)
                except Exception:
                    args = {}
            if fn.get("name") == "submit_order":
                logger.info("VAPI submit_order captured: %s", args)
                results.append({"toolCallId": tc.get("id"), "result": _confirm(args)})
            else:
                results.append({"toolCallId": tc.get("id"), "result": "ok"})
        return {"results": results}

    # Legacy function-call shape.
    if mtype == "function-call":
        fc = msg.get("functionCall", {}) or {}
        args = fc.get("parameters", {}) or {}
        if fc.get("name") == "submit_order":
            logger.info("VAPI submit_order captured (legacy): %s", args)
            return {"result": _confirm(args)}
        return {"result": "ok"}

    if mtype == "end-of-call-report":
        logger.info("VAPI end-of-call: ended=%s", msg.get("endedReason"))

    return {"received": True}
