"""Deposits — asking for money before the chair is held.

The rule this module exists to enforce: A DEPOSIT IS NEVER TAKEN SILENTLY.
Every path here either sends the customer a link they choose to pay, or acts
on a decision the merchant already made and can see. Nothing charges a card
because a timer expired without a human ever being told what the policy was.

Two properties worth stating because they are easy to get wrong:

  * The amount is COPIED from the service onto the booking when the booking is
    made, and read from the booking thereafter. A merchant who raises their
    deposit on Monday has not changed what Friday's customer agreed to.

  * An unpaid booking still HOLDS the slot, for deposit_hold_minutes and no
    longer. Holding for ever recreates the no-show problem the deposit was
    bought to solve; releasing instantly means a customer who takes two
    minutes to find their card loses the appointment.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from src.services.booking_store import BookingStoreError, get_booking_store

logger = logging.getLogger("meridian.services.booking_deposits")

# Terminal states: money has been decided one way or the other.
RESOLVED = frozenset({"captured", "refunded", "waived", "none"})


def required_cents(service: dict | None, price_cents: int | None = None) -> int:
    """What this service asks for up front.

    A FLAT amount beats a percentage when both are set, because typing an
    amount is the more deliberate act — a percentage is usually left over from
    a template.
    """
    if not service:
        return 0
    flat = service.get("deposit_cents")
    if flat:
        return max(0, int(flat))
    pct = service.get("deposit_percent")
    if not pct:
        return 0
    base = price_cents if price_cents is not None else service.get("price_cents")
    if not base:
        # A percentage of an unpriced service is nothing, and guessing a base
        # would invent a charge the merchant never set.
        return 0
    return max(0, round(int(base) * int(pct) / 100))


def describe(cents: int, policy: str | None = None) -> str:
    """The sentence the agent says out loud. Short, and never a surprise."""
    if cents <= 0:
        return ""
    amount = f"${cents // 100}" if cents % 100 == 0 else f"${cents / 100:.2f}"
    base = f"There's a {amount} deposit to hold the slot"
    if policy:
        return f"{base}. {policy.strip().rstrip('.')}."
    return f"{base}, and it comes off the price on the day."


class DepositService:
    def __init__(self):
        self._store = get_booking_store()

    async def request(
        self,
        booking: dict,
        cents: int,
        *,
        request_base: str = "",
    ) -> dict:
        """Mark a booking as awaiting a deposit and text the customer a link.

        Returns {"sent": bool, "url": str, "reason": str}. Never raises — this
        runs while a caller is on the phone.
        """
        if cents <= 0:
            return {"sent": False, "url": "", "reason": "no_deposit_required"}

        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        try:
            await self._store.update_booking(str(booking["id"]), {
                "deposit_cents": cents,
                "deposit_status": "requested",
                "deposit_requested_at": now,
            })
        except BookingStoreError as e:
            logger.warning("could not mark deposit requested for %s: %s",
                           booking.get("id"), e)
            return {"sent": False, "url": "", "reason": "store_failed"}

        phone = (booking.get("customer_phone") or "").strip()
        if not phone:
            # Nothing to send to. The booking stays 'requested' rather than
            # being quietly treated as paid.
            return {"sent": False, "url": "", "reason": "no_phone"}

        from src.services.booking_links import get_link_service, link_url_for

        pay_url = ""
        try:
            service = get_link_service()
            row = await service.record_send(
                booking.get("merchant_id") or "",
                _pay_target(booking),
                to_phone=phone,
                vapi_call_id=booking.get("vapi_call_id") or "",
            )
            if row:
                pay_url = link_url_for(row["code"], request_base)
        except Exception as e:  # noqa: BLE001
            logger.warning("deposit link not recorded for %s: %s", booking.get("id"), e)

        if not pay_url:
            pay_url = _pay_target(booking)

        from src.sms.client import send_sms

        amount = f"${cents // 100}" if cents % 100 == 0 else f"${cents / 100:.2f}"
        message = (
            f"Your booking is held. To confirm it, pay the {amount} deposit here: {pay_url}"
        )
        try:
            result = await send_sms(phone, message)
        except Exception as e:  # noqa: BLE001
            logger.warning("deposit SMS crashed for %s: %s", booking.get("id"), e)
            result = {"sent": False, "reason": str(e)}

        return {
            "sent": bool(result.get("sent")),
            "url": pay_url,
            "reason": str(result.get("reason") or ""),
        }

    async def mark_paid(self, booking_id: str, payment_intent: str = "") -> dict:
        """The customer paid. The booking is now genuinely confirmed."""
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        fields = {"deposit_status": "held", "deposit_paid_at": now}
        if payment_intent:
            fields["deposit_payment_intent"] = payment_intent
        return await self._store.update_booking(str(booking_id), fields)

    async def capture(self, booking: dict, reason: str = "no_show") -> dict:
        """Keep the deposit, because they did not turn up.

        ONLY ever called from an explicit no-show — never from a timer, never
        from an inference about whether somebody arrived. Taking a customer's
        money because a screen was not tapped is the single fastest way to lose
        a merchant their reputation, and ours.
        """
        if (booking.get("deposit_status") or "none") != "held":
            return {"captured": False, "reason": "nothing_held"}

        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        await self._store.update_booking(str(booking["id"]), {
            "deposit_status": "captured",
            "deposit_resolved_at": now,
            "cancel_reason": reason,
        })
        logger.info("deposit captured for booking %s (%s)", booking.get("id"), reason)
        return {"captured": True, "cents": booking.get("deposit_cents") or 0}

    async def release(self, booking: dict, status: str = "refunded") -> dict:
        """Give it back — they turned up, or the shop cancelled."""
        if (booking.get("deposit_status") or "none") != "held":
            return {"released": False, "reason": "nothing_held"}
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        await self._store.update_booking(str(booking["id"]), {
            "deposit_status": status,
            "deposit_resolved_at": now,
        })
        return {"released": True, "cents": booking.get("deposit_cents") or 0}

    async def expired_requests(self, hold_minutes: int, *, now: datetime | None = None) -> list[dict]:
        """Bookings whose deposit link was never paid inside the window.

        Returned rather than acted on: the caller decides whether to release
        the slot, and that decision is worth keeping visible.
        """
        now = now or datetime.now(timezone.utc)
        cutoff = (now - timedelta(minutes=hold_minutes)).isoformat(timespec="seconds")
        rows = await self._store._req(
            "GET", "bookings",
            params={
                "deposit_status": "eq.requested",
                "deposit_requested_at": f"lt.{cutoff}",
                "status": "in.(confirmed,offered)",
                "limit": "200",
            },
        )
        return rows or []


def _pay_target(booking: dict) -> str:
    """Where the deposit link points.

    Deliberately a function rather than a constant: this is the seam where a
    real Stripe Checkout session URL goes once the payment side is wired, and
    keeping it in one place stops a half-built payment flow leaking into three.
    """
    import os
    base = (os.environ.get("PUBLIC_PAY_BASE") or "https://api.meridian.tips").rstrip("/")
    return f"{base}/pay/deposit/{booking.get('id')}"


_service: DepositService | None = None


def get_deposit_service() -> DepositService:
    global _service
    if _service is None:
        _service = DepositService()
    return _service
