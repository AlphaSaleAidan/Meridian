"""Paid-without-kitchen-push monitor — the standing watch over "the customer
paid, so food is being made".

This closes the #1 entry in the DEFCON detection-gap backlog
(docs/runbooks/incidents/DEFCON.md, "POS & Fulfillment"): a customer is charged,
the order row flips to paid, and then the kitchen ticket never lands — the POS
push 400s, the connector times out, the merchant SMS fallback also fails, or the
post-claim PATCH that records the push outcome never runs. Nothing today notices:
`mark_order_paid` deliberately swallows a POS failure so a connector hiccup can
never un-commit the money truth (services/phone_agent/pay_on_phone.py), the
merchant sees no ticket, and the first person to learn is a customer standing at
the counter for food nobody started.

Every sweep reads PAID phone_orders from the last WINDOW hours and asks one
question per row: did a kitchen ticket reach the merchant by ANY channel?

  delivered  = POS push succeeded (pos_success / pos_delivery_status sent |
               demo_safe, or a pos_order_id with no failure recorded, or the
               fulfillment prove-out confirmed the ticket make-able in the POS)
               OR the merchant notification SMS was sent (the no-POS fallback —
               the merchant still got the order, so no food is missing).
  finding    = paid, past the grace period, and NEITHER channel delivered.

Grace exists because the push is asynchronous: an order that paid seconds ago is
mid-push, not broken. Age is measured from the LATEST timestamp the row knows
about (created_at and every delivery_detail leg's "at"), so a payment-link order
paid hours after it was created isn't flagged the moment its push starts.

Detection + alerting ONLY. This monitor never re-pushes a ticket: a blind re-push
races the original and risks a double kitchen ticket (the exact failure the CAS
claim in mark_order_paid was built to prevent). Humans re-push through the
existing tooling — see docs/runbooks/incidents/payments-unconfirmed.md.

ON BY DEFAULT — needs no configuration beyond the Supabase credentials the app
already requires. Env:
  MERIDIAN_KITCHEN_MONITOR           "0" disables (default enabled)
  MERIDIAN_KITCHEN_MONITOR_INTERVAL  seconds between sweeps (default 600 = 10m)
  MERIDIAN_KITCHEN_MONITOR_WINDOW_H  lookback hours per sweep (default 24)
  MERIDIAN_KITCHEN_GRACE_MIN         minutes to let an async push land (default 5)
  MERIDIAN_OPS_ALERT_EMAIL           digest recipient (default aidanpierce72@gmail.com)

Started by the FastAPI lifespan handler in app.py. Fail-quiet throughout: an
unreachable DB, a renamed column, or a failed email logs and moves on — the
watch never dies and never blocks startup.
"""
import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone

import httpx

logger = logging.getLogger("meridian.services.kitchen_monitor")

DEFAULT_INTERVAL = 600
DEFAULT_WINDOW_H = 24
DEFAULT_GRACE_MIN = 5
DEFAULT_EMAIL = "aidanpierce72@gmail.com"
DB_TIMEOUT = 20
ROW_LIMIT = 200

# Demo/test merchants bill a flat test charge and run the POS connector in
# logs-only mode by design — never a missing ticket. (Same list the billing
# monitor skips.)
_DEMO_MERCHANT_IDS = {"demo", "demo-merchant", "demo-tryout"}

# pos_delivery_status values that mean the ticket reached the POS (or was
# intentionally not sent to a real one). See
# supabase/migrations/20260716_order_fanout_delivery_status.sql.
_POS_OK = {"sent", "demo_safe"}
_POS_BAD = {"failed", "deferred_pending_payment"}
# Kitchen prove-out states proving the POS holds a make-able ticket.
_FULFILLED_STATES = {"kitchen_fired", "OPEN", "COMPLETED"}

_task: asyncio.Task | None = None
_running = False
_alerted_orders: set[str] = set()
_status: dict = {"sweeps": 0, "last_sweep": None, "orders_checked": 0,
                 "missing_tickets": 0, "last_error": ""}


def is_enabled() -> bool:
    return os.environ.get("MERIDIAN_KITCHEN_MONITOR", "1") != "0"


def _interval() -> int:
    try:
        return max(60, int(os.environ.get(
            "MERIDIAN_KITCHEN_MONITOR_INTERVAL", str(DEFAULT_INTERVAL))))
    except ValueError:
        return DEFAULT_INTERVAL


def _window_hours() -> int:
    try:
        return max(1, int(os.environ.get(
            "MERIDIAN_KITCHEN_MONITOR_WINDOW_H", str(DEFAULT_WINDOW_H))))
    except ValueError:
        return DEFAULT_WINDOW_H


def _grace_minutes() -> int:
    try:
        return max(0, int(os.environ.get(
            "MERIDIAN_KITCHEN_GRACE_MIN", str(DEFAULT_GRACE_MIN))))
    except ValueError:
        return DEFAULT_GRACE_MIN


def _db_creds() -> tuple[str, str]:
    url = os.environ.get("SUPABASE_URL", "")
    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
           or os.environ.get("SUPABASE_SERVICE_KEY")
           or os.environ.get("SUPABASE_KEY", ""))
    return url, key


# The exact phone_orders columns this monitor keys on. Every one is a real
# column (migrations/025_phone_orders_pay_status.sql,
# supabase/migrations/20260704_phone_orders_payment_columns.sql,
# supabase/migrations/20260716_order_fanout_delivery_status.sql,
# supabase/migrations/20260507_phone_agent.sql).
_SELECT = ",".join((
    "id", "merchant_id", "caller_phone", "customer_name", "total", "created_at",
    "status", "payment_status", "kitchen_released", "payment_method",
    "pos_order_id", "pos_success", "pos_system", "pos_delivery_status",
    "merchant_notify_status", "fulfillment_state", "fulfillment_confirmed_at",
    "delivery_detail", "source",
))


async def _fetch_paid_orders(since: datetime) -> list[dict]:
    """PAID phone_orders created within the window. Raises on transport/HTTP
    errors so the sweep can record them and move on."""
    url, key = _db_creds()
    if not (url and key):
        return []
    async with httpx.AsyncClient(timeout=DB_TIMEOUT) as client:
        r = await client.get(
            f"{url}/rest/v1/phone_orders",
            params={
                # Either flag alone is enough: mark_order_paid's CAS claim sets
                # both, but a partial write must never hide a charged order.
                "or": "(payment_status.eq.paid,status.eq.paid)",
                "created_at": f"gte.{since.isoformat()}",
                "select": _SELECT,
                "order": "created_at.desc",
                "limit": ROW_LIMIT,
            },
            headers={"apikey": key, "Authorization": f"Bearer {key}"})
        r.raise_for_status()
        return r.json() or []


def _parse_ts(value) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _latest_activity(row: dict) -> datetime | None:
    """The most recent moment this row is known to have been touched:
    created_at plus every delivery leg's recorded timestamp. Using the LATEST
    (not created_at alone) keeps a link-paid order that was created hours ago
    from being flagged the instant its deferred push starts."""
    stamps = [_parse_ts(row.get("created_at")),
              _parse_ts(row.get("fulfillment_confirmed_at"))]
    detail = row.get("delivery_detail")
    if isinstance(detail, dict):
        for leg in detail.values():
            if isinstance(leg, dict):
                stamps.append(_parse_ts(leg.get("at")))
    known = [s for s in stamps if s is not None]
    return max(known) if known else None


def _pos_delivered(row: dict) -> bool:
    """Did the kitchen ticket reach the POS?"""
    if row.get("pos_success") is True:
        return True
    status = (row.get("pos_delivery_status") or "").strip()
    if status in _POS_OK:
        return True
    if row.get("fulfillment_confirmed_at"):
        return True
    if (row.get("fulfillment_state") or "").strip() in _FULFILLED_STATES:
        return True
    # A pos_order_id with no failure recorded means the POS accepted a ticket
    # (the id only exists because the connector returned one).
    if (row.get("pos_order_id") or "").strip() and status not in _POS_BAD:
        return True
    return False


def _merchant_notified(row: dict) -> bool:
    """Did the merchant-notification SMS fallback deliver the order? A merchant
    without a connected POS legitimately works off this text, so a sent
    notification means the food is being made."""
    return (row.get("merchant_notify_status") or "").strip() == "sent"


def _is_paid(row: dict) -> bool:
    return (row.get("payment_status") or "").strip() == "paid" or \
           (row.get("status") or "").strip() == "paid"


def _why(row: dict) -> str:
    """Human-readable reason the ticket is considered missing."""
    pos = (row.get("pos_delivery_status") or "").strip() or "not recorded"
    notify = (row.get("merchant_notify_status") or "").strip() or "not recorded"
    return f"pos_delivery_status={pos}, merchant_notify_status={notify}"


def _finding(row: dict, age_min: float) -> dict:
    return {
        "order_id": str(row.get("id") or ""),
        "pos_order_id": (row.get("pos_order_id") or "").strip(),
        "merchant_id": row.get("merchant_id") or "",
        "caller_phone": row.get("caller_phone") or "",
        "customer_name": row.get("customer_name") or "",
        "total": row.get("total"),
        "pos_system": row.get("pos_system") or "",
        "kitchen_released": bool(row.get("kitchen_released")),
        "payment_method": row.get("payment_method") or "",
        "age_minutes": round(age_min, 1),
        "reason": _why(row),
    }


async def _sweep_once(now: datetime | None = None) -> list[dict]:
    """One pass. Returns the NEW paid-without-kitchen-ticket findings."""
    now = now or datetime.now(timezone.utc)
    since = now - timedelta(hours=_window_hours())
    grace = timedelta(minutes=_grace_minutes())
    try:
        rows = await _fetch_paid_orders(since)
    except Exception as e:  # noqa: BLE001 — a DB blip never kills the watch
        _status["last_error"] = str(e)
        logger.warning("kitchen monitor: paid-order fetch failed: %s", e)
        return []

    findings: list[dict] = []
    for row in rows:
        order_id = str(row.get("id") or "")
        if not order_id or order_id in _alerted_orders:
            continue
        if not _is_paid(row):  # defensive: the filter already selects paid rows
            continue
        if (row.get("merchant_id") or "") in _DEMO_MERCHANT_IDS:
            continue
        _status["orders_checked"] += 1
        if _pos_delivered(row) or _merchant_notified(row):
            continue
        last = _latest_activity(row)
        if last is None or (now - last) < grace:
            continue  # mid-push (or no usable timestamp) — give it time

        _alerted_orders.add(order_id)
        age_min = (now - last).total_seconds() / 60
        finding = _finding(row, age_min)
        findings.append(finding)
        logger.critical(
            "KITCHEN MONITOR: order %s (merchant %s, %s) has been PAID for "
            "%.0f min with NO kitchen ticket on any channel (%s) — customer "
            "charged, no food being made. "
            "RUN: docs/runbooks/incidents/payments-unconfirmed.md (DEFCON 1).",
            finding["pos_order_id"] or order_id, finding["merchant_id"],
            finding["caller_phone"] or "no phone", age_min, finding["reason"])
        await _page(finding)
    return findings


async def _page(finding: dict) -> None:
    """DEFCON 1 for a single finding. Deduped by order id inside notify_defcon's
    cooldown as well as by _alerted_orders here."""
    try:
        from .defcon_alert import notify_defcon
        ident = finding["pos_order_id"] or finding["order_id"]
        await notify_defcon(
            1,
            f"Paid order with no kitchen ticket: {ident}",
            f"Merchant {finding['merchant_id']} — order {ident} "
            f"({finding['customer_name'] or 'customer'}, "
            f"{finding['caller_phone'] or 'no phone'}, total {finding['total']}) "
            f"has been paid for {finding['age_minutes']:.0f} minutes with no POS "
            f"ticket and no merchant notification ({finding['reason']}). "
            f"The customer has been CHARGED and no food is being made. "
            f"Re-push manually (never automatically — a blind re-push can double "
            f"the ticket) and refund if the order can't be made.",
            protocol="payments-unconfirmed.md",
            event_key=f"kitchen-push:{finding['order_id']}")
    except Exception as e:  # noqa: BLE001 — paging never breaks the sweep
        logger.error("kitchen monitor DEFCON page failed: %s", e)


async def _send_digest(findings: list[dict]) -> None:
    try:
        from ..email.send import send_anomaly_alert
        lines = [
            f"• merchant {f['merchant_id']}: order "
            f"{f['pos_order_id'] or f['order_id']} paid {f['age_minutes']:.0f} min "
            f"ago, total {f['total']}, caller {f['caller_phone'] or 'unknown'} "
            f"({f['reason']})"
            for f in findings]
        await send_anomaly_alert(
            os.environ.get("MERIDIAN_OPS_ALERT_EMAIL", DEFAULT_EMAIL),
            "Meridian Kitchen Monitor",
            f"{len(findings)} paid order(s) with NO kitchen ticket",
            "Customers were charged and no kitchen ticket reached the merchant "
            "on any channel (POS push and merchant SMS both missing/failed). "
            "RUN: docs/runbooks/incidents/payments-unconfirmed.md (DEFCON 1). "
            "Re-push by hand — an automatic re-push risks a double ticket. "
            "Findings:\n" + "\n".join(lines),
            severity="high")
    except Exception as e:  # noqa: BLE001 — alerting never breaks the monitor
        logger.error("kitchen monitor digest email failed: %s", e)


async def _loop() -> None:
    global _running
    _running = True
    logger.info("kitchen monitor started (interval %ss, window %sh, grace %smin)",
                _interval(), _window_hours(), _grace_minutes())
    while _running:
        try:
            found = await _sweep_once()
            _status["sweeps"] += 1
            _status["last_sweep"] = datetime.now(timezone.utc).isoformat()
            if found:
                _status["missing_tickets"] += len(found)
                await _send_digest(found)
        except Exception as e:  # noqa: BLE001 — the watch never dies
            _status["last_error"] = str(e)
            logger.error("kitchen monitor sweep failed: %s", e)
        try:
            await asyncio.sleep(_interval())
        except asyncio.CancelledError:
            break


def start_kitchen_monitor() -> bool:
    """Idempotent start; False when disabled or no Supabase credentials."""
    global _task
    if not is_enabled():
        logger.info("kitchen monitor disabled (MERIDIAN_KITCHEN_MONITOR=0)")
        return False
    url, key = _db_creds()
    if not (url and key):
        logger.info("kitchen monitor: no Supabase credentials — not starting")
        return False
    if _task and not _task.done():
        return True
    _task = asyncio.ensure_future(_loop())
    return True


def stop_kitchen_monitor() -> None:
    global _running, _task
    _running = False
    if _task and not _task.done():
        _task.cancel()
    _task = None


def get_kitchen_monitor_status() -> dict:
    return dict(_status, running=_running,
                alerted_orders=len(_alerted_orders),
                interval_s=_interval(), window_h=_window_hours(),
                grace_min=_grace_minutes())
