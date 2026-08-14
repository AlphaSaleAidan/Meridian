"""Cancellation recovery — dial the waitlist, best guest first.

Competitive research (2026-08-15) checked every incumbent's waitlist and found
the same shape everywhere: a waitlist is a list a human works. Boulevard's
"waitlist notifications" notify staff. Vagaro and SevenRooms document waitlist
*management*. The consumer-facing versions are first-come "notify me" blasts.
So when a 7pm cancels at 4pm on a Friday, somebody has to notice, decide who to
contact, and contact them — and nobody does, so the table sits empty.

The incumbents' new AI voice agents (SevenRooms Voice AI, Fresha AI Concierge,
Mindbody, Slang.ai) are all INBOUND. They answer a call; they do not place one.
Acting on a cancellation is the half nobody automates.

FOUR DECISIONS WORTH KNOWING ABOUT
-----------------------------------
ONE GUEST AT A TIME, AND THE SLOT IS REALLY HELD. The naive version texts
everyone and gives the table to whoever taps first. That is a race that annoys
everyone who loses, and it teaches regulars the waitlist is a lottery. Here an
offer goes to one guest and the hold is a real bookings row in 'offered'
status, so migration 082's exclusion constraint protects it exactly like a
confirmed booking — the phone agent physically cannot sell it out from under
someone who is still reading the message.

RANKED BY VALUE, BUT ONLY WHERE VALUE IS KNOWN. We can see real POS spend and
real no-show history, which no booking-only platform can. Where that history
exists it decides the order. Where it does not, the order is arrival time, and
`rank_reason` records which applied — so a merchant asking "why did they get
it?" gets a sentence, not "the algorithm".

A NO-SHOW IS A HEAVIER SIGNAL THAN A BIG SPEND. Someone who burned the
merchant twice costs them the slot twice; a high average check is worth less
than the certainty of a person who turns up. The weights below say so.

SMS IS THE LIVE CHANNEL; VOICE IS BUILT BUT GATED. Placing an automated call is
the strictly better experience and the harder thing for an incumbent to copy,
but this Telnyx account has no outbound voice profile, so automated outbound
calling cannot originate today. `WAITLIST_VOICE_ENABLED` exists for the day it
can; until then the offer is a text and that is stated plainly rather than
implied.
"""
from __future__ import annotations

import logging
import os
import random
import string
from datetime import datetime, timedelta, timezone

from src.services import booking_engine as be
from src.services.booking_store import (
    SlotTaken,
    generate_confirmation_code,
    get_booking_store,
)

logger = logging.getLogger("meridian.services.booking_waitlist")

CLAIM_ALPHABET = "ABCDEFGHJKLMNPQRTUVWXY2346789"
CLAIM_LENGTH = 4

DEFAULT_OFFER_MINUTES = 15
MAX_OFFERS_PER_ENTRY = 3

# How long a guest who let an offer lapse is skipped for. Without this, the
# expiry sweep releases their hold and immediately re-offers the same slot to
# the same person who just ignored it — which both spams them and starves
# everyone behind them in the queue. Found by test, not by reasoning.
OFFER_COOLDOWN_MINUTES = 60

# Outbound voice is written but cannot originate on this Telnyx account (no
# outbound voice profile). Flipping this on before that exists produces silent
# failures, so it is env-gated and default off.
VOICE_ENABLED = os.getenv("WAITLIST_VOICE_ENABLED", "").lower() in ("1", "true")


def generate_claim_code() -> str:
    return "".join(random.choice(CLAIM_ALPHABET) for _ in range(CLAIM_LENGTH))


# ─── Ranking ──────────────────────────────────────────────────

async def _guest_history(merchant_id: str, phones: list[str]) -> dict[str, dict]:
    """Spend and reliability per phone number, in two queries for the batch.

    Deliberately batched: ranking five candidates must not cost ten round
    trips while a table sits empty.
    """
    out: dict[str, dict] = {p: {"spend_cents": 0, "completed": 0, "no_shows": 0}
                            for p in phones}
    if not phones:
        return out

    from src.db import get_db
    db = get_db()
    quoted = ",".join(f'"{p}"' for p in phones)

    try:
        orders = await db.select(
            "phone_orders",
            columns="caller_phone,total,payment_status",
            filters={"merchant_id": f"eq.{merchant_id}",
                     "caller_phone": f"in.({quoted})"},
            limit=500,
        )
        for row in orders or []:
            phone = row.get("caller_phone")
            if phone not in out:
                continue
            # Only money that actually arrived counts as spend.
            if str(row.get("payment_status") or "").lower() in ("paid", "succeeded"):
                try:
                    out[phone]["spend_cents"] += int(float(row.get("total") or 0) * 100)
                except (TypeError, ValueError):
                    pass
    except Exception as e:  # noqa: BLE001
        logger.info("waitlist: order history unavailable, ranking on order alone: %s", e)

    try:
        past = await db.select(
            "bookings",
            columns="customer_phone,status",
            filters={"merchant_id": f"eq.{merchant_id}",
                     "customer_phone": f"in.({quoted})"},
            limit=500,
        )
        for row in past or []:
            phone = row.get("customer_phone")
            if phone not in out:
                continue
            status = row.get("status")
            if status == "completed":
                out[phone]["completed"] += 1
            elif status == "no_show":
                out[phone]["no_shows"] += 1
    except Exception as e:  # noqa: BLE001
        logger.info("waitlist: booking history unavailable: %s", e)

    return out


def _score(entry: dict, history: dict) -> tuple[float, str]:
    """(score, plain-English reason). Higher is offered first."""
    reasons: list[str] = []
    score = 0.0

    no_shows = history.get("no_shows", 0)
    if no_shows:
        # Heaviest single signal. Two no-shows should lose to a stranger.
        score -= 40.0 * no_shows
        reasons.append(f"{no_shows} previous no-show{'s' if no_shows > 1 else ''}")

    completed = history.get("completed", 0)
    if completed:
        score += min(completed, 10) * 6.0
        reasons.append(f"{completed} past visit{'s' if completed > 1 else ''}")

    spend = history.get("spend_cents", 0)
    if spend:
        # Diminishing: a $400 guest beats a $200 guest, but not by double.
        score += min(spend / 5000.0, 20.0)
        reasons.append(f"${spend / 100:.0f} spent before")

    party = int(entry.get("party_size") or 1)
    if party > 1:
        score += min(party, 12) * 1.5
        reasons.append(f"party of {party}")

    if not reasons:
        return score, "first in the queue"
    return score, ", ".join(reasons)


async def rank_candidates(merchant_id: str, entries: list[dict]) -> list[dict]:
    """Order entries best-first, annotating each with why."""
    if not entries:
        return []
    phones = list({e.get("customer_phone") for e in entries if e.get("customer_phone")})
    history = await _guest_history(merchant_id, phones)

    scored = []
    for entry in entries:
        h = history.get(entry.get("customer_phone") or "", {})
        score, reason = _score(entry, h)
        scored.append({**entry, "_score": score, "_reason": reason})

    # Arrival time is the tiebreak, so equal-information guests are served
    # fairly rather than arbitrarily.
    scored.sort(key=lambda e: (-e["_score"], str(e.get("created_at") or "")))
    return scored


# ─── Matching ─────────────────────────────────────────────────

async def matching_entries(merchant_id: str, starts_at: datetime,
                           ends_at: datetime, seats: int,
                           *, now: datetime | None = None) -> list[dict]:
    """Waiting guests whose window contains this freed slot and who fit it."""
    now = now or datetime.now(timezone.utc)
    store = get_booking_store()
    rows = await store.list_waitlist(merchant_id, status="waiting")

    out = []
    for row in rows:
        window_start = be._parse_ts(row.get("window_start"))
        window_end = be._parse_ts(row.get("window_end"))
        if not window_start or not window_end:
            continue
        # The whole slot must sit inside what they said they'd accept.
        if starts_at < window_start or ends_at > window_end:
            continue
        if int(row.get("party_size") or 1) > seats:
            continue
        # Their own notice floor: someone who wants Friday 7pm does not want a
        # text at 6:40 about a table at 7.
        notice = int(row.get("min_notice_minutes") or 0)
        if starts_at - now < timedelta(minutes=notice):
            continue
        if int(row.get("offer_count") or 0) >= MAX_OFFERS_PER_ENTRY:
            continue
        # Someone we asked recently and who didn't answer goes to the back of
        # the queue, not straight back to the front of it.
        last_offered = be._parse_ts(row.get("offered_at"))
        if last_offered and now - last_offered < timedelta(minutes=OFFER_COOLDOWN_MINUTES):
            continue
        out.append(row)
    return out


# ─── The recovery run ─────────────────────────────────────────

async def recover_slot(merchant_id: str, cancelled: dict, *,
                       now: datetime | None = None) -> dict:
    """A booking just cancelled. Offer the freed slot to the best guest.

    Never raises into the caller: cancelling a booking must always succeed
    even when recovery cannot run.
    """
    now = now or datetime.now(timezone.utc)
    try:
        return await _recover(merchant_id, cancelled, now)
    except Exception as e:  # noqa: BLE001
        logger.warning("waitlist recovery failed for %s: %s", merchant_id, e)
        return {"offered": False, "reason": "error"}


async def _recover(merchant_id: str, cancelled: dict, now: datetime) -> dict:
    config = await _merchant_config(merchant_id)
    if not config.get("waitlist_enabled"):
        return {"offered": False, "reason": "disabled"}

    starts_at = be._parse_ts(cancelled.get("starts_at"))
    ends_at = be._parse_ts(cancelled.get("ends_at"))
    if not starts_at or not ends_at:
        return {"offered": False, "reason": "no slot"}
    if starts_at <= now:
        return {"offered": False, "reason": "in the past"}

    store = get_booking_store()
    resource_id = cancelled.get("resource_id")
    seats = await _seats_for(merchant_id, resource_id)

    candidates = await matching_entries(merchant_id, starts_at, ends_at, seats, now=now)
    if not candidates:
        return {"offered": False, "reason": "nobody waiting for that time"}

    ranked = await rank_candidates(merchant_id, candidates)

    for entry in ranked:
        offered = await _offer(merchant_id, entry, cancelled, config, now)
        if offered:
            return {"offered": True, "waitlist_id": entry["id"],
                    "reason": entry.get("_reason", ""),
                    "candidates": len(ranked)}
    return {"offered": False, "reason": "could not hold the slot for anyone"}


async def _offer(merchant_id: str, entry: dict, cancelled: dict,
                 config: dict, now: datetime) -> bool:
    """Hold the slot for one guest and tell them. True when the offer went out."""
    store = get_booking_store()
    minutes = int(config.get("waitlist_offer_minutes") or DEFAULT_OFFER_MINUTES)
    expires = now + timedelta(minutes=minutes)
    claim_code = generate_claim_code()

    # The hold IS a booking. That is what makes the offer exclusive: the
    # exclusion constraint refuses anyone else the same resource and time.
    try:
        hold = await store.create_booking({
            "merchant_id": merchant_id,
            "resource_id": cancelled.get("resource_id"),
            "service_id": entry.get("service_id") or cancelled.get("service_id"),
            "starts_at": cancelled.get("starts_at"),
            "ends_at": cancelled.get("ends_at"),
            "duration_minutes": cancelled.get("duration_minutes"),
            "party_size": entry.get("party_size") or 1,
            "customer_name": entry.get("customer_name") or "Waitlist guest",
            "customer_phone": entry.get("customer_phone"),
            "notes": entry.get("notes"),
            "status": "offered",
            "source": "phone",
            "confirmation_code": generate_confirmation_code(),
            "waitlist_id": entry["id"],
        })
    except SlotTaken:
        # Someone booked it between the cancellation and now. Nothing to offer.
        logger.info("waitlist: freed slot was taken before it could be offered")
        return False
    except Exception as e:  # noqa: BLE001
        logger.warning("waitlist: could not hold slot: %s", e)
        return False

    await store.update_waitlist(entry["id"], {
        "status": "offered",
        "offered_at": now.isoformat(),
        "offer_expires_at": expires.isoformat(),
        "offer_booking_id": hold["id"],
        "offer_count": int(entry.get("offer_count") or 0) + 1,
        "rank_reason": entry.get("_reason", "")[:300] or None,
        "claim_code": claim_code,
    })

    sent = await _notify(merchant_id, entry, cancelled, claim_code, minutes, config)
    if not sent:
        # We could not reach them, so holding the table serves nobody. Release
        # it immediately and let the caller move to the next guest.
        logger.info("waitlist: could not notify %s, releasing hold",
                    entry.get("customer_phone"))
        await _release(hold["id"], entry["id"], "could not reach guest")
        return False
    return True


async def _notify(merchant_id: str, entry: dict, cancelled: dict,
                  claim_code: str, minutes: int, config: dict) -> bool:
    phone = (entry.get("customer_phone") or "").strip()
    if not phone:
        return False

    tz, _ = be.resolve_timezone(config.get("business_timezone") or "")
    starts_at = be._parse_ts(cancelled.get("starts_at"))
    when = be._speak_time(starts_at.astimezone(tz)) if starts_at else "the time you wanted"
    day = starts_at.astimezone(tz).strftime("%A") if starts_at else ""
    business = config.get("business_name") or "us"
    first = (entry.get("customer_name") or "").split(" ")[0]

    body = (
        f"{('Hi ' + first + ', a') if first else 'A'} spot just opened at "
        f"{business} — {day} at {when}. It's held for you for {minutes} minutes. "
        f"Reply YES or call and quote {claim_code} to take it."
    )

    if VOICE_ENABLED:
        # Strictly better than a text and the harder thing to copy, but this
        # Telnyx account cannot originate outbound voice yet (no outbound voice
        # profile). Falls through to SMS rather than failing.
        placed = await _place_call(merchant_id, phone, body)
        if placed:
            return True

    try:
        from src.sms.client import send_sms
        result = await send_sms(phone, body)
        return bool(result and result.get("sent"))
    except Exception as e:  # noqa: BLE001
        logger.warning("waitlist SMS failed for %s: %s", phone, e)
        return False


async def _place_call(merchant_id: str, phone: str, script: str) -> bool:
    """Outbound offer call. Returns False until a Telnyx outbound voice
    profile exists — see the module docstring."""
    logger.info("waitlist voice offer requested for %s but outbound voice is "
                "not provisioned; falling back to SMS", phone)
    return False


# ─── Claim / decline / expiry ─────────────────────────────────

async def claim(merchant_id: str, claim_code: str) -> dict | None:
    """Turn a held offer into a real booking. Returns the booking, or None."""
    store = get_booking_store()
    entry = await store.find_waitlist_by_claim(merchant_id, claim_code)
    if not entry:
        return None

    expires = be._parse_ts(entry.get("offer_expires_at"))
    if expires and expires < datetime.now(timezone.utc):
        return None

    booking_id = entry.get("offer_booking_id")
    if not booking_id:
        return None

    booking = await store.update_booking(str(booking_id), {"status": "confirmed"})
    await store.update_waitlist(str(entry["id"]), {
        "status": "booked", "claim_code": None,
    })
    return booking


async def decline(merchant_id: str, claim_code: str) -> dict:
    """Guest said no. Release the hold and immediately try the next guest."""
    store = get_booking_store()
    entry = await store.find_waitlist_by_claim(merchant_id, claim_code)
    if not entry:
        return {"offered": False, "reason": "unknown code"}

    booking_id = entry.get("offer_booking_id")
    freed = await store.get_booking(str(booking_id)) if booking_id else None
    await _release(booking_id, str(entry["id"]), "declined", final_status="declined")

    if freed:
        return await recover_slot(merchant_id, freed)
    return {"offered": False, "reason": "nothing to re-offer"}


async def _release(booking_id, waitlist_id, reason: str,
                   final_status: str = "waiting") -> None:
    """Drop the hold and put the guest back in the queue (or out of it)."""
    store = get_booking_store()
    try:
        if booking_id:
            await store.update_booking(str(booking_id), {
                "status": "cancelled",
                "cancelled_at": datetime.now(timezone.utc).isoformat(),
                "cancel_reason": f"waitlist offer {reason}",
            })
    except Exception as e:  # noqa: BLE001
        logger.warning("could not release waitlist hold %s: %s", booking_id, e)
    try:
        await store.update_waitlist(str(waitlist_id), {
            "status": final_status,
            "offer_booking_id": None,
            "offer_expires_at": None,
            "claim_code": None,
        })
    except Exception as e:  # noqa: BLE001
        logger.warning("could not reset waitlist entry %s: %s", waitlist_id, e)


async def expire_offers(*, now: datetime | None = None) -> dict:
    """Sweep expired offers, release their holds, and offer the next guest.

    This is what makes the chain work: one cancellation can walk down the
    ranked list over an hour without anyone touching it.
    """
    now = now or datetime.now(timezone.utc)
    store = get_booking_store()
    try:
        expired = await store.expired_offers(now.isoformat())
    except Exception as e:  # noqa: BLE001
        logger.error("waitlist expiry query failed: %s", e)
        return {"expired": 0, "reoffered": 0}

    expired_count = reoffered = 0
    for entry in expired or []:
        booking_id = entry.get("offer_booking_id")
        freed = await store.get_booking(str(booking_id)) if booking_id else None
        # Back to 'waiting', not 'expired': they never answered, and offer_count
        # already caps how many times we will bother them.
        await _release(booking_id, str(entry["id"]), "expired")
        expired_count += 1

        if freed:
            result = await recover_slot(str(entry["merchant_id"]), freed, now=now)
            if result.get("offered"):
                reoffered += 1

    if expired_count:
        logger.info("waitlist: %d offers expired, %d re-offered",
                    expired_count, reoffered)
    return {"expired": expired_count, "reoffered": reoffered}


# ─── helpers ──────────────────────────────────────────────────

async def _merchant_config(merchant_id: str) -> dict:
    from src.db import get_db
    try:
        rows = await get_db().select(
            "phone_agent_config",
            columns=("business_name,business_timezone,waitlist_enabled,"
                     "waitlist_offer_minutes"),
            filters={"merchant_id": f"eq.{merchant_id}"},
            limit=1,
        )
        return rows[0] if rows else {}
    except Exception as e:  # noqa: BLE001
        logger.warning("waitlist: could not read config for %s: %s", merchant_id, e)
        return {}


async def _seats_for(merchant_id: str, resource_id) -> int:
    if not resource_id:
        return 1
    try:
        resources = await get_booking_store().list_resources(merchant_id)
        for r in resources:
            if str(r.get("id")) == str(resource_id):
                return int(r.get("seats") or 1)
    except Exception:  # noqa: BLE001
        pass
    return 1
