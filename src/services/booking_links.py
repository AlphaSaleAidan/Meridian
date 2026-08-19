"""Texting the booking link, and finding out whether anyone opened it.

For merchants who keep their own booking system (booking_mode='external_link')
the phone agent used to READ A URL ALOUD. This replaces that: the link goes out
as a text message on every call that asks about booking, and the agent says it
has sent it rather than spelling it.

Three things follow from that choice and are all handled here:

  * The destination is snapshotted onto the send row. A merchant editing their
    booking URL must not silently repoint links already sitting in someone's
    message history.
  * Every send gets its OWN short code, so "opened" attributes to one caller
    rather than to the day.
  * A send can fail — a landline has no inbox. The failure is returned rather
    than swallowed, because the agent's fallback (read it out after all) is
    only correct if it knows the text did not land.

The link service never raises at the caller. A phone call in progress must not
end because a database write or an SMS provider had a bad minute; the tool
returns sent=False and the agent adapts.
"""
from __future__ import annotations

import logging
import os
import random
from datetime import datetime, timezone

from src.services.booking_store import BookingStoreError, get_booking_store

logger = logging.getLogger("meridian.services.booking_links")

# No O/0, I/1, S/5 — the code is spoken aloud as the fallback when a text
# cannot be delivered, and those are the pairs people mishear.
_CODE_ALPHABET = "abcdefghjkmnpqrtuvwxy2346789"
_CODE_LENGTH = 7

# A code is generated optimistically and inserted; a collision is a unique-index
# violation, not something we pre-check with a SELECT. At 28^7 the retry
# effectively never runs, and a check-then-insert would be a race anyway.
_MAX_CODE_ATTEMPTS = 5


def generate_code() -> str:
    return "".join(random.choice(_CODE_ALPHABET) for _ in range(_CODE_LENGTH))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def public_base(request_base: str = "") -> str:
    """Where /b/{code} lives. API_PUBLIC_URL in production; the request's own
    origin in development, so a preview box links to itself."""
    return (os.environ.get("API_PUBLIC_URL") or request_base or "").rstrip("/")


def link_url_for(code: str, request_base: str = "") -> str:
    return f"{public_base(request_base)}/b/{code}"


def configured_url(config) -> str:
    """The merchant's own booking page.

    booking_link_url is the field a merchant edits in the Bookings screen.
    reservation_config.website_url is the older onboarding-questionnaire
    answer and is honoured as a fallback so merchants who already told us
    where they book do not have to say it twice.
    """
    direct = (getattr(config, "booking_link_url", "") or "").strip()
    if direct:
        return direct
    resv = getattr(config, "reservation_config", None) or {}
    if resv.get("on_website"):
        return (resv.get("website_url") or "").strip()
    return ""


def _normalize_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    return url


def compose_message(business_name: str, short_url: str) -> str:
    """Deliberately short and unbranded-by-us.

    The caller asked THIS restaurant for a table; a text that leads with our
    product name reads like spam and gets reported as such. One line, the
    shop's own name, the link.
    """
    name = (business_name or "").strip() or "your booking"
    return f"{name} — book your table here: {short_url}"


class BookingLinkService:
    def __init__(self):
        self._store = get_booking_store()

    async def record_send(
        self,
        merchant_id: str,
        target_url: str,
        *,
        to_phone: str = "",
        vapi_call_id: str = "",
        delivery: str = "sent",
        error: str = "",
    ) -> dict | None:
        payload = {
            "merchant_id": merchant_id,
            "target_url": target_url,
            "to_phone": to_phone or None,
            "vapi_call_id": vapi_call_id or None,
            "delivery": delivery,
            "error": error or None,
        }
        for _ in range(_MAX_CODE_ATTEMPTS):
            payload["code"] = generate_code()
            try:
                rows = await self._store._req(
                    "POST", "booking_link_sends", json=payload,
                )
                return rows[0] if rows else None
            except BookingStoreError as e:
                # Only a code collision is worth retrying; anything else will
                # fail identically next time.
                if "duplicate key" in str(e).lower() or "23505" in str(e):
                    continue
                raise
        return None

    async def resolve(self, code: str) -> dict | None:
        rows = await self._store._req(
            "GET", "booking_link_sends",
            params={"code": f"ilike.{code}", "limit": "1"},
        )
        return rows[0] if rows else None

    async def record_click(self, row: dict) -> None:
        """Best-effort. A failed counter update must never turn into a failed
        redirect — the caller is standing there waiting for a booking page."""
        now = _now_iso()
        patch = {
            "click_count": int(row.get("click_count") or 0) + 1,
            "last_clicked_at": now,
        }
        if not row.get("clicked_at"):
            patch["clicked_at"] = now
        try:
            await self._store._req(
                "PATCH", "booking_link_sends",
                params={"id": f"eq.{row['id']}"},
                json=patch,
                prefer="return=minimal",
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("booking link click not recorded for %s: %s",
                           row.get("code"), e)

    async def stats(self, merchant_id: str, limit: int = 20) -> dict:
        rows = await self._store._req(
            "GET", "booking_link_sends",
            params={
                "merchant_id": f"eq.{merchant_id}",
                "order": "created_at.desc",
                "limit": str(limit),
            },
        )
        sent = [r for r in rows if r.get("delivery") == "sent"]
        opened = [r for r in sent if r.get("clicked_at")]
        return {
            "recent": rows,
            "sent": len(sent),
            "opened": len(opened),
            "failed": len([r for r in rows if r.get("delivery") == "failed"]),
        }


_service: BookingLinkService | None = None


def get_link_service() -> BookingLinkService:
    global _service
    if _service is None:
        _service = BookingLinkService()
    return _service


async def text_booking_link(
    config,
    to_phone: str,
    *,
    vapi_call_id: str = "",
    request_base: str = "",
) -> dict:
    """Text the merchant's booking link to the caller.

    Returns {"sent": bool, "url": str, "reason": str}. Never raises: the agent
    is mid-sentence on a live call.
    """
    merchant_id = getattr(config, "merchant_id", "") or ""
    target = _normalize_url(configured_url(config))
    if not target:
        return {"sent": False, "url": "", "reason": "no_booking_url"}
    if not (to_phone or "").strip():
        return {"sent": False, "url": target, "reason": "no_phone"}

    service = get_link_service()

    # The row is written FIRST so the short code exists to put in the message.
    try:
        row = await service.record_send(
            merchant_id, target, to_phone=to_phone, vapi_call_id=vapi_call_id,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("booking link send not recorded for %s: %s", merchant_id, e)
        row = None

    # No row means no short code, so no click evidence — but the caller still
    # needs the link. Fall back to the merchant's own URL rather than failing.
    short_url = link_url_for(row["code"], request_base) if row else target

    from src.sms.client import send_sms

    business = getattr(config, "business_name", "") or ""
    try:
        result = await send_sms(to_phone, compose_message(business, short_url))
    except Exception as e:  # noqa: BLE001
        logger.warning("booking link SMS crashed for %s: %s", merchant_id, e)
        result = {"sent": False, "reason": str(e)}

    if not result.get("sent") and row:
        try:
            await service._store._req(
                "PATCH", "booking_link_sends",
                params={"id": f"eq.{row['id']}"},
                json={"delivery": "failed",
                      "error": str(result.get("reason") or "")[:300]},
                prefer="return=minimal",
            )
        except Exception:  # noqa: BLE001
            pass

    return {
        "sent": bool(result.get("sent")),
        "url": short_url,
        "target": target,
        "reason": str(result.get("reason") or ""),
    }


def compose_running_late(business_name: str, minutes: int, booking_label: str = "") -> str:
    """The text a customer gets when the van is behind.

    Written as the shop would say it out loud, and it says the ONE thing the
    customer needs: the new time. "We are running late" without a number is
    the message that makes someone ring you, which is the call this exists to
    prevent.
    """
    who = (business_name or "").strip()
    lead = f"{who}: " if who else ""
    when = f" for your {booking_label}" if booking_label else ""
    return (
        f"{lead}we are running about {minutes} minutes behind{when}. "
        "Sorry for the wait — no need to do anything, we will be there."
    )


def compose_payment_link(business_name: str, label: str,
                         amount_cents: int, url: str) -> str:
    """The text a customer gets when the shop sends them the bill.

    Says the three things that make someone tap a link from an unknown
    number: who it is, what it is for, and how much. A bare URL is spam;
    "$220 for your Full detail" is a receipt.
    """
    who = (business_name or "").strip()
    lead = f"{who}: " if who else ""
    what = f" for your {label}" if label else ""
    amount = (f"${amount_cents // 100}" if amount_cents % 100 == 0
              else f"${amount_cents / 100:.2f}")
    return f"{lead}here is your payment link{what} — {amount}. Pay here: {url}"


async def text_payment_link(
    config,
    booking: dict,
    amount_cents: int,
    *,
    request_base: str = "",
) -> dict:
    """Create a checkout for a booking and text the customer the link.

    RIDES THE PHONE-ORDER PAYMENT RAIL (services/phone_agent/payment_links),
    not the deposit seam — that rail is the one live in production: Square
    merchants get a native Square pay link, everyone else gets the
    Meridian-hosted checkout page. A second checkout implementation for
    bookings would be a second place for money bugs to live.

    Returns {"sent": bool, "url": str, "reason": str} and NEVER raises. The
    url is returned even when the SMS fails or there is no number on file —
    the operator can copy it into any channel they like, which also keeps the
    button useful while US 10DLC approval is pending.
    """
    merchant_id = getattr(config, "merchant_id", "") or ""
    if amount_cents <= 0:
        return {"sent": False, "url": "", "reason": "no_price"}

    # Fee helpers live in services/phone_agent — same sys.path arrangement
    # website.py and the phone routes use.
    import sys
    from pathlib import Path as _Path
    _phone_agent_dir = str(
        _Path(__file__).resolve().parents[2] / "services" / "phone_agent")
    if _phone_agent_dir not in sys.path:
        sys.path.insert(0, _phone_agent_dir)
    from payment_links import create_payment_link  # type: ignore[import]

    label = (booking.get("service_name") or "").strip()
    phone = (booking.get("customer_phone") or "").strip()
    order = {
        "merchant_id": merchant_id,
        "customer_name": (booking.get("customer_name") or "").strip(),
        "caller_phone": phone,
        "order_type": "booking",
        "items": [{
            "name": label or "Booking",
            "quantity": 1,
            "unit_price": amount_cents / 100,
        }],
        "subtotal": amount_cents / 100,
        "tax": 0,
        "total": amount_cents / 100,
    }

    try:
        link = await create_payment_link(
            order=order,
            pos_system=getattr(config, "pos_system", "") or "",
            pos_order_id="",
            access_token=getattr(config, "pos_access_token", "") or "",
            location_id=getattr(config, "pos_location_id", "") or "",
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("booking payment link failed for %s: %s", merchant_id, e)
        return {"sent": False, "url": "", "reason": "link_failed"}

    url = (link or {}).get("url") or ""
    if not url:
        return {"sent": False, "url": "", "reason": "link_failed"}

    if not phone:
        return {"sent": False, "url": url, "reason": "no_phone"}

    from src.sms.client import send_sms

    business = getattr(config, "business_name", "") or ""
    try:
        result = await send_sms(
            phone, compose_payment_link(business, label, amount_cents, url))
    except Exception as e:  # noqa: BLE001
        logger.warning("booking payment link SMS crashed for %s: %s", merchant_id, e)
        result = {"sent": False, "reason": str(e)}

    return {
        "sent": bool(result.get("sent")),
        "url": url,
        "reason": str(result.get("reason") or ""),
    }


async def text_running_late(
    config,
    to_phone: str,
    minutes: int,
    *,
    booking_label: str = "",
) -> dict:
    """Tell a customer the arrival has slipped.

    Returns {"sent": bool, "reason": str}. Never raises — this is fired from a
    van, one-handed, and an exception surfacing as a red screen helps nobody.

    NOT RECORDED IN booking_link_sends: that table is click attribution for
    booking links, and a late notice has no link and nothing to attribute. The
    SMS provider's own log is the record.
    """
    if not (to_phone or "").strip():
        return {"sent": False, "reason": "no_phone"}
    minutes = max(5, min(240, int(minutes or 0)))

    from src.sms.client import send_sms

    business = getattr(config, "business_name", "") or ""
    try:
        result = await send_sms(
            to_phone, compose_running_late(business, minutes, booking_label))
    except Exception as e:  # noqa: BLE001
        logger.warning("running-late SMS crashed: %s", e)
        return {"sent": False, "reason": str(e)}

    return {"sent": bool(result.get("sent")),
            "reason": str(result.get("reason") or ""),
            "minutes": minutes}
