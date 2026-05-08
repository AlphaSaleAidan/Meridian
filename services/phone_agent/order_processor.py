"""
Order processor — intercepts LLM function calls and executes the order pipeline.
Receives submit_order(), transfer_to_human(), end_call_no_order() from the LLM
and routes them to POS creation, SMS/email notification, and call logging.
"""
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

from pipecat.processors.frame_processor import FrameProcessor
from pipecat.frames.frames import FunctionCallFrame, TextFrame

from merchant_config import MerchantPhoneConfig
from order_normalizer import normalize_order
from pos_connector import create_pos_order
from order_router import route_order

logger = logging.getLogger("meridian.phone_agent.order")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", "")


class OrderProcessor(FrameProcessor):

    def __init__(
        self,
        merchant_id: str,
        call_sid: str,
        merchant_config: MerchantPhoneConfig,
        caller_info: dict,
    ):
        super().__init__()
        self._merchant_id = merchant_id
        self._call_sid = call_sid
        self._config = merchant_config
        self._caller_info = caller_info
        self._order_submitted = False
        self._transcript: list[dict] = []

    async def process_frame(self, frame, direction):
        if isinstance(frame, FunctionCallFrame):
            await self._handle_function_call(frame)
        else:
            await self.push_frame(frame, direction)

    async def _handle_function_call(self, frame: FunctionCallFrame):
        name = frame.function_name
        args = frame.arguments if isinstance(frame.arguments, dict) else {}

        logger.info("Function call received: %s", name)

        if name == "submit_order":
            await self._handle_submit_order(args)
        elif name == "transfer_to_human":
            await self._handle_transfer(args)
        elif name == "end_call_no_order":
            await self._handle_end_call(args)
        else:
            logger.warning("Unknown function call: %s", name)

    async def _handle_submit_order(self, args: dict[str, Any]):
        if self._order_submitted:
            logger.warning("Duplicate submit_order call — ignoring")
            return

        self._order_submitted = True

        normalized = normalize_order(args, self._config)

        pos_result = await create_pos_order(
            normalized,
            self._config.pos_system,
            self._config.pos_access_token,
            self._config.pos_location_id,
        )

        await route_order(
            normalized,
            self._config,
            self._caller_info,
            pos_result,
        )

        await self._log_call(
            status="order_placed",
            order_data=normalized,
            pos_result=pos_result,
        )

        confirmation = self._build_confirmation(normalized, pos_result)
        await self.push_frame(TextFrame(text=confirmation))

    async def _handle_transfer(self, args: dict[str, Any]):
        reason = args.get("reason", "Customer requested")
        logger.info("Transfer requested: %s", reason)

        await self._log_call(status="transferred", notes=reason)

        await self.push_frame(
            TextFrame(
                text="Let me transfer you to a team member. Please hold for just a moment."
            )
        )

    async def _handle_end_call(self, args: dict[str, Any]):
        reason = args.get("reason", "unknown")
        logger.info("Call ended without order: %s", reason)

        await self._log_call(status=f"no_order_{reason}")

        if reason == "order_completed":
            await self.push_frame(
                TextFrame(text="Thank you for your order! Have a great day. Goodbye!")
            )
        elif reason == "customer_declined":
            await self.push_frame(
                TextFrame(text="No problem at all. Thank you for calling! Goodbye.")
            )
        else:
            await self.push_frame(
                TextFrame(text="Thank you for calling. Have a great day!")
            )

    def _build_confirmation(self, order: dict, pos_result: dict) -> str:
        items = order.get("items", [])
        item_summary = ", ".join(
            f"{item['quantity']} {item.get('size', '')} {item['name']}".strip()
            for item in items
        )
        order_type = order.get("order_type", "pickup")
        name = order.get("customer_name", "")

        msg = f"Great, {name}! I've placed your order for {item_summary} for {order_type}."

        if pos_result.get("success"):
            eta = pos_result.get("estimated_ready_minutes")
            if eta:
                msg += f" It should be ready in about {eta} minutes."
        else:
            msg += " The kitchen has been notified and will prepare your order."

        msg += " Is there anything else I can help with?"
        return msg

    async def _log_call(
        self,
        status: str,
        order_data: Optional[dict] = None,
        pos_result: Optional[dict] = None,
        notes: str = "",
    ):
        log_entry = {
            "merchant_id": self._merchant_id,
            "call_sid": self._call_sid,
            "caller_phone": self._caller_info.get("phone", ""),
            "status": status,
            "order_data": order_data,
            "pos_result": pos_result,
            "notes": notes,
            "transcript": self._transcript,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        if SUPABASE_URL and SUPABASE_KEY:
            try:
                import httpx

                async with httpx.AsyncClient() as client:
                    await client.post(
                        f"{SUPABASE_URL}/rest/v1/phone_call_logs",
                        json=log_entry,
                        headers={
                            "apikey": SUPABASE_KEY,
                            "Authorization": f"Bearer {SUPABASE_KEY}",
                            "Content-Type": "application/json",
                            "Prefer": "return=minimal",
                        },
                    )
            except Exception as e:
                logger.error("Failed to log call to Supabase: %s", e)
        else:
            logger.info("Call log (no Supabase): %s", json.dumps(log_entry, default=str))
