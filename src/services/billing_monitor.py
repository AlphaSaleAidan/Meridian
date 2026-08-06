"""Billing reconciliation monitor — the standing watch over "the customer paid
exactly what the order was confirmed at".

Born from the 2026-08-06 tax/modifier-drop incident: itemized payment links
billed the raw menu sum while phone_orders recorded the taxed total, and
nothing in the system could notice. Three defenses now exist at charge time
and settlement time (payment_links invariant, rail delta lines, mark_order_paid
reconciliation); this monitor is the independent fourth layer — it re-derives
the truth from Stripe itself, on a schedule, across EVERY account key, so a
drift on any rail or any future code path surfaces within hours, not lawsuits.

Every sweep:
  1. Lists completed Checkout Sessions from the last WINDOW hours on each
     configured Stripe key (platform + phone-order account).
  2. Matches phone-order sessions (metadata.pos_order_id) to their
     phone_orders row.
  3. Flags any session that settled BELOW the order's confirmed total —
     CRITICAL log per finding + one digest email per sweep (deduped per
     session id for the process lifetime). Demo merchants are skipped (the
     demo test-charge override intentionally bills a flat 75¢).

ON BY DEFAULT — requires no configuration beyond the Stripe keys the payment
rails already need. Env:
  MERIDIAN_BILLING_MONITOR           "0" disables (default enabled)
  MERIDIAN_BILLING_MONITOR_INTERVAL  seconds between sweeps (default 21600 = 6h)
  MERIDIAN_BILLING_MONITOR_WINDOW_H  lookback hours per sweep (default 72)
  MERIDIAN_OPS_ALERT_EMAIL           digest recipient (default aidanpierce72@gmail.com)

Started by the FastAPI lifespan handler in app.py. Fail-quiet throughout:
a dead Stripe key, an unreachable DB, or a failed email logs and moves on.
"""
import asyncio
import logging
import os
import time
from datetime import datetime, timezone

import httpx

logger = logging.getLogger("meridian.services.billing_monitor")

DEFAULT_INTERVAL = 21600
DEFAULT_WINDOW_H = 72
DEFAULT_EMAIL = "aidanpierce72@gmail.com"
STRIPE_TIMEOUT = 30

# The demo override bills a flat test charge by design — never a mismatch.
_DEMO_MERCHANT_IDS = {"demo", "demo-merchant", "demo-tryout"}

_task: asyncio.Task | None = None
_running = False
_alerted_sessions: set[str] = set()
_status: dict = {"sweeps": 0, "last_sweep": None, "sessions_checked": 0,
                 "mismatches_found": 0, "last_error": ""}


def is_enabled() -> bool:
    return os.environ.get("MERIDIAN_BILLING_MONITOR", "1") != "0"


def _interval() -> int:
    try:
        return max(300, int(os.environ.get(
            "MERIDIAN_BILLING_MONITOR_INTERVAL", str(DEFAULT_INTERVAL))))
    except ValueError:
        return DEFAULT_INTERVAL


def _window_hours() -> int:
    try:
        return max(1, int(os.environ.get(
            "MERIDIAN_BILLING_MONITOR_WINDOW_H", str(DEFAULT_WINDOW_H))))
    except ValueError:
        return DEFAULT_WINDOW_H


def _stripe_keys() -> list[tuple[str, str]]:
    """(label, key) for every distinct configured account."""
    keys = []
    platform = os.environ.get("STRIPE_SECRET_KEY", "")
    phone = os.environ.get("STRIPE_PHONE_SECRET_KEY", "")
    if platform:
        keys.append(("platform", platform))
    if phone and phone != platform:
        keys.append(("phone", phone))
    return keys


async def _list_completed_sessions(key: str, since_epoch: int) -> list[dict]:
    """Completed Checkout Sessions since `since_epoch`, one page of 100 per
    sweep (phone volume is far below that; the window overlaps sweeps so
    nothing is missed across pages over time)."""
    async with httpx.AsyncClient(timeout=STRIPE_TIMEOUT) as client:
        r = await client.get(
            "https://api.stripe.com/v1/checkout/sessions",
            params={"limit": 100, "status": "complete",
                    "created[gte]": since_epoch},
            auth=(key, ""))
        r.raise_for_status()
        return r.json().get("data", [])


async def _fetch_order_row(pos_order_id: str) -> dict | None:
    url = os.environ.get("SUPABASE_URL", "")
    db_key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
              or os.environ.get("SUPABASE_SERVICE_KEY")
              or os.environ.get("SUPABASE_KEY", ""))
    if not (url and db_key):
        return None
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(
            f"{url}/rest/v1/phone_orders",
            params={"pos_order_id": f"eq.{pos_order_id}",
                    "select": "pos_order_id,merchant_id,business_name,total",
                    "limit": 1},
            headers={"apikey": db_key, "Authorization": f"Bearer {db_key}"})
        r.raise_for_status()
        rows = r.json()
        return rows[0] if rows else None


def _order_cents(row: dict) -> int:
    try:
        return int(round(float(row.get("total") or 0) * 100))
    except (TypeError, ValueError):
        return 0


async def _sweep_once() -> list[dict]:
    """One reconciliation pass. Returns the NEW mismatches found."""
    since = int(time.time()) - _window_hours() * 3600
    new_mismatches: list[dict] = []
    for label, key in _stripe_keys():
        try:
            sessions = await _list_completed_sessions(key, since)
        except Exception as e:  # noqa: BLE001 — one bad account never kills the sweep
            _status["last_error"] = f"{label}: {e}"
            logger.warning("billing monitor: session list failed (%s): %s", label, e)
            continue
        for s in sessions:
            md = s.get("metadata") or {}
            pos_order_id = md.get("pos_order_id") or ""
            merchant_id = md.get("merchant_id") or ""
            if not pos_order_id or merchant_id in _DEMO_MERCHANT_IDS:
                continue
            if s.get("id") in _alerted_sessions:
                continue
            _status["sessions_checked"] += 1
            try:
                row = await _fetch_order_row(pos_order_id)
            except Exception as e:  # noqa: BLE001
                logger.warning("billing monitor: order fetch failed (%s): %s",
                               pos_order_id, e)
                continue
            if not row:
                continue
            expected = _order_cents(row)
            paid = int(s.get("amount_total") or 0)
            if expected and paid and paid < expected:
                _alerted_sessions.add(s["id"])
                finding = {
                    "session": s["id"], "account": label,
                    "pos_order_id": pos_order_id,
                    "merchant_id": row.get("merchant_id") or merchant_id,
                    "business_name": row.get("business_name") or "",
                    "paid_cents": paid, "expected_cents": expected,
                    "currency": s.get("currency") or "",
                }
                new_mismatches.append(finding)
                logger.critical(
                    "BILLING MONITOR: session %s (%s) settled at %d¢ but order "
                    "%s was confirmed at %d¢ — merchant %s shorted %d¢",
                    s["id"], label, paid, pos_order_id, expected,
                    finding["merchant_id"], expected - paid)
    return new_mismatches


async def _send_digest(mismatches: list[dict]) -> None:
    try:
        from ..email.send import send_anomaly_alert
        lines = [
            f"• {m['business_name'] or m['merchant_id']}: order {m['pos_order_id']} "
            f"settled {m['paid_cents']}¢ vs confirmed {m['expected_cents']}¢ "
            f"({m['currency']}, {m['account']} account, session {m['session']})"
            for m in mismatches]
        total_short = sum(m["expected_cents"] - m["paid_cents"] for m in mismatches)
        await send_anomaly_alert(
            os.environ.get("MERIDIAN_OPS_ALERT_EMAIL", DEFAULT_EMAIL),
            "Meridian Billing Monitor",
            f"{len(mismatches)} underpaid phone order(s) — {total_short}¢ total shortfall",
            "A payment-link builder is billing below confirmed order totals "
            "(tax/modifier drift). Findings:\n" + "\n".join(lines),
            severity="high")
    except Exception as e:  # noqa: BLE001 — alerting never breaks the monitor
        logger.error("billing monitor digest email failed: %s", e)


async def _loop() -> None:
    global _running
    _running = True
    logger.info("billing monitor started (interval %ss, window %sh, %d account key(s))",
                _interval(), _window_hours(), len(_stripe_keys()))
    while _running:
        try:
            found = await _sweep_once()
            _status["sweeps"] += 1
            _status["last_sweep"] = datetime.now(timezone.utc).isoformat()
            if found:
                _status["mismatches_found"] += len(found)
                await _send_digest(found)
        except Exception as e:  # noqa: BLE001 — the watch never dies
            _status["last_error"] = str(e)
            logger.error("billing monitor sweep failed: %s", e)
        try:
            await asyncio.sleep(_interval())
        except asyncio.CancelledError:
            break


def start_billing_monitor() -> bool:
    """Idempotent start; False when disabled or no Stripe key configured."""
    global _task
    if not is_enabled():
        logger.info("billing monitor disabled (MERIDIAN_BILLING_MONITOR=0)")
        return False
    if not _stripe_keys():
        logger.info("billing monitor: no Stripe keys configured — not starting")
        return False
    if _task and not _task.done():
        return True
    _task = asyncio.ensure_future(_loop())
    return True


def stop_billing_monitor() -> None:
    global _running, _task
    _running = False
    if _task and not _task.done():
        _task.cancel()
    _task = None


def get_billing_monitor_status() -> dict:
    return dict(_status, running=_running,
                alerted_sessions=len(_alerted_sessions))
