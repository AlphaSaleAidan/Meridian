"""
Phone-number pool — pre-bought, Vapi-bound Telnyx DIDs ready for instant
assignment at onboarding.

Buying ahead removes the live-purchase latency and failure surface from the
signup path: `buy_into_pool` purchases N Telnyx numbers and imports each into
Vapi (bound to our webhook) up front; `claim_from_pool` hands a merchant a
ready-to-ring number with no external call. All Telnyx — no Twilio.

Every pool number is fully wired before it lands in the table (Telnyx order +
Vapi import), so an assigned number answers as the agent immediately. A partial
failure never leaves a half-provisioned row: the Telnyx number is released and
the row is skipped.
"""
import logging
from datetime import datetime, timezone

logger = logging.getLogger("meridian.phone.number_pool")


async def buy_into_pool(count: int, *, country: str = "CA",
                        area_code: str | None = None) -> dict:
    """Buy `count` Telnyx numbers, bind each to Vapi, and add them to the pool.

    Returns {requested, added, failed, numbers:[...], errors:[...]}. Each number
    is search → purchase → Vapi-import; a failure at any step releases the
    Telnyx number (if bought) and moves on, so the pool only ever holds fully
    wired numbers. Stops early on repeated provider failures (no funds / no
    inventory) rather than hammering Telnyx."""
    from ..db import get_db
    from ..api.routes.phone_dashboard import (
        _telnyx_search, _telnyx_purchase, _telnyx_release,
    )
    from .vapi_provisioning import import_telnyx_number, vapi_telnyx_enabled

    if not vapi_telnyx_enabled():
        return {"requested": count, "added": 0, "failed": count,
                "numbers": [], "errors": ["vapi_telnyx_not_configured"]}

    db = get_db()
    added, failed, numbers, errors = 0, 0, [], []
    consecutive_provider_fail = 0

    for _ in range(max(0, count)):
        if consecutive_provider_fail >= 3:
            errors.append("aborted: 3 consecutive Telnyx failures (funds/inventory?)")
            break
        # 1) find + buy at Telnyx
        try:
            candidate = await _telnyx_search(country, area_code)
            if not candidate:
                consecutive_provider_fail += 1
                errors.append("no_available_number")
                continue
            purchased = await _telnyx_purchase(candidate)
        except Exception as e:  # noqa: BLE001 — HTTPException(502) etc.
            consecutive_provider_fail += 1
            failed += 1
            errors.append(f"purchase_failed: {str(e)[:120]}")
            continue
        consecutive_provider_fail = 0
        number = purchased.get("phone_number") or candidate
        sid = purchased.get("sid")

        # 2) bind into Vapi — on failure, release the Telnyx number (no orphans)
        vapi_id = await import_telnyx_number(number, name="Meridian (pool)")
        if not vapi_id:
            await _telnyx_release(number, sid)
            failed += 1
            errors.append(f"vapi_import_failed: {number} (released)")
            continue

        # 3) record the ready number
        try:
            await db.insert("phone_number_pool", {
                "provider": "telnyx",
                "phone_number": number,
                "provider_sid": sid,
                "vapi_phone_number_id": vapi_id,
                "country": country,
                "status": "available",
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
        except Exception as e:  # noqa: BLE001
            # Row write failed after buying+binding — release both so we don't
            # pay for a number that isn't tracked.
            from .vapi_provisioning import delete_vapi_number
            await delete_vapi_number(vapi_id)
            await _telnyx_release(number, sid)
            failed += 1
            errors.append(f"pool_insert_failed: {number} (released): {str(e)[:80]}")
            continue

        added += 1
        numbers.append(number)
        logger.info("pool: added %s (vapi %s)", number, vapi_id)

    return {"requested": count, "added": added, "failed": failed,
            "numbers": numbers, "errors": errors}


async def claim_from_pool(db, merchant_id: str) -> dict | None:
    """Claim one available pool number for a merchant. Returns the claimed row
    ({phone_number, provider_sid, vapi_phone_number_id}) or None if the pool is
    empty. The claim is a conditional update (status available→assigned filtered
    on the row id) so two concurrent claimers can't take the same number — the
    loser's update matches zero rows and it retries the next candidate."""
    for _ in range(5):  # bounded retry on contention
        rows = await db.select(
            "phone_number_pool",
            filters={"status": "eq.available"},
            order="created_at.asc",
            limit=1,
        )
        if not rows:
            return None
        row = rows[0]
        claimed = await db.update(
            "phone_number_pool",
            {
                "status": "assigned",
                "assigned_merchant_id": merchant_id,
                "assigned_at": datetime.now(timezone.utc).isoformat(),
            },
            filters={"id": f"eq.{row['id']}", "status": "eq.available"},
        )
        if claimed:
            logger.info("pool: claimed %s for merchant %s",
                        row.get("phone_number"), merchant_id)
            return {
                "phone_number": row.get("phone_number"),
                "provider_sid": row.get("provider_sid"),
                "vapi_phone_number_id": row.get("vapi_phone_number_id"),
            }
        # lost the race — try the next available number
    logger.warning("pool: claim contention exhausted for merchant %s", merchant_id)
    return None


async def pool_status(db) -> dict:
    """Counts by status for the admin view."""
    out = {"available": 0, "assigned": 0, "released": 0}
    for st in list(out):
        try:
            rows = await db.select("phone_number_pool", "id",
                                   filters={"status": f"eq.{st}"})
            out[st] = len(rows or [])
        except Exception:  # noqa: BLE001
            pass
    return out
