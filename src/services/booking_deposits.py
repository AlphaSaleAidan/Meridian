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

        phone = (booking.get("customer_phone") or "").strip()
        if not phone:
            # Nothing to send the link to, so nothing is requested — asking
            # for money with no way to pay it would only feed the sweep a
            # booking it will cancel through no fault of the customer's.
            return {"sent": False, "url": "", "reason": "no_phone"}

        # A REAL payable link or no request at all. The checkout session is
        # what /pay/deposit was always meant to become: if Stripe cannot mint
        # one, the deposit is quietly waived rather than texting a dead page
        # or holding the customer's slot hostage to our outage. The customer
        # gets the Stripe URL directly (the same direct-link doctrine as
        # phone-order pay links).
        pay_url = ""
        try:
            from merchant_config import get_merchant_config
            from payment_links import create_deposit_checkout

            cfg = await get_merchant_config(str(booking.get("merchant_id") or ""))
            if cfg:
                checkout = await create_deposit_checkout(booking, cfg, cents)
                pay_url = str(checkout.get("url") or "")
        except Exception as e:  # noqa: BLE001 — a booking is never lost to a payment hiccup
            logger.warning("deposit checkout not created for %s: %s",
                           booking.get("id"), e)
        if not pay_url:
            return {"sent": False, "url": "", "reason": "checkout_unavailable"}

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

        if not result.get("sent"):
            # The link never reached them, so the sweep must not cancel the
            # booking over an unpaid deposit they were never asked for. Waive
            # it: the booking stands, the merchant collects in person.
            try:
                await self._store.update_booking(str(booking["id"]), {
                    "deposit_status": "waived",
                    "deposit_resolved_at":
                        datetime.now(timezone.utc).isoformat(timespec="seconds"),
                })
            except BookingStoreError:
                logger.warning("could not waive unsendable deposit for %s",
                               booking.get("id"))

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


async def run_deposit_sweep(*, now: datetime | None = None) -> dict:
    """Release bookings whose deposit link was never paid inside the merchant's
    hold window — the module's second property, enforced: an unpaid booking
    holds the slot for deposit_hold_minutes and no longer.

    Releasing is NOT taking money (capture stays no-show-only); it returns the
    slot to inventory, takes the ghost off the merchant's calendar, offers the
    slot to the waitlist, and tells the customer — who was told at request time
    the booking was held pending payment.
    """
    now = now or datetime.now(timezone.utc)
    svc = get_deposit_service()

    # Widest net first (the schema's 5-minute floor); each row is then judged
    # against its own merchant's window.
    rows = await svc.expired_requests(5, now=now)
    if not rows:
        return {"released": 0, "kept": 0}

    merchant_ids = sorted({str(r.get("merchant_id")) for r in rows if r.get("merchant_id")})
    holds: dict[str, int] = {}
    try:
        cfg_rows = await svc._store._req(
            "GET", "phone_agent_config",
            params={
                "merchant_id": f"in.({','.join(merchant_ids)})",
                "select": "merchant_id,deposit_hold_minutes",
            },
        ) or []
        holds = {str(c["merchant_id"]): int(c.get("deposit_hold_minutes") or 60)
                 for c in cfg_rows}
    except Exception as e:  # noqa: BLE001 — fall back to the 60-minute default
        logger.warning("deposit sweep could not read hold windows: %s", e)

    from src.services.booking_engine import _parse_ts

    released = 0
    kept = 0
    for row in rows:
        merchant_id = str(row.get("merchant_id") or "")
        hold = holds.get(merchant_id, 60)
        requested_at = _parse_ts(row.get("deposit_requested_at"))
        if not requested_at or now - requested_at < timedelta(minutes=hold):
            kept += 1
            continue

        try:
            await svc._store.cancel_booking(
                str(row["id"]), reason="deposit not paid in time")
            await svc._store.update_booking(str(row["id"]), {
                "deposit_status": "failed",
                "deposit_resolved_at": now.isoformat(timespec="seconds"),
            })
        except Exception as e:  # noqa: BLE001 — skip, retry next sweep
            logger.warning("deposit sweep could not release %s: %s", row.get("id"), e)
            continue

        # Same aftermath as any other cancellation: off their calendar, slot to
        # the waitlist. Each best-effort — the release itself already stands.
        try:
            from src.services.booking_sync import withdraw_booking
            await withdraw_booking(merchant_id, row)
        except Exception as e:  # noqa: BLE001
            logger.warning("deposit sweep withdraw failed for %s: %s", row.get("id"), e)
        try:
            from src.services.booking_waitlist import recover_slot
            await recover_slot(merchant_id, row)
        except Exception as e:  # noqa: BLE001
            logger.warning("deposit sweep recovery failed for %s: %s", row.get("id"), e)

        phone = (row.get("customer_phone") or "").strip()
        if phone:
            try:
                from src.sms.client import send_sms
                await send_sms(phone, (
                    "We didn't receive your deposit in time, so your booking "
                    "was released. Call us back any time to rebook."))
            except Exception as e:  # noqa: BLE001
                logger.warning("deposit release SMS failed for %s: %s", row.get("id"), e)

        released += 1

    logger.info("deposit sweep: released=%d kept=%d", released, kept)
    return {"released": released, "kept": kept}


_service: DepositService | None = None


def get_deposit_service() -> DepositService:
    global _service
    if _service is None:
        _service = DepositService()
    return _service
