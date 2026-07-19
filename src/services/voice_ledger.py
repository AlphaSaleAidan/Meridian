"""
Per-merchant voice ledger.

The AI phone agent costs money per call (Vapi) and earns money per paid order
(the Stripe service fee we auto-take). This module records both as ledger
postings keyed by merchant, so each account has a running net balance:

    balance = SUM(credit) - SUM(debit)

  credit  → `credit(merchant_id, cents, source='stripe_fee', ref=<cs_...>)`
            called from the Stripe Connect webhook on each paid order.
  debit   → `debit(merchant_id, cents, source='vapi_call', ref=<call id>)`
            called from the Vapi end-of-call-report with the call's cost.

Both are idempotent on (source, ref): a webhook retry never double-posts.

This is the per-merchant P&L behind the auto-reload idea (revenue funds usage).
Vapi's native auto-top-up (card on file) covers the *global* float; the optional
`balance_cents()` gate lets us fall calls back to Telnyx for an account that's
deep underwater. Everything degrades quietly — a ledger failure must never break
a payment webhook or strand a phone call.
"""
import logging

from ..db import get_db

logger = logging.getLogger("meridian.voice_ledger")


async def _post(merchant_id: str, kind: str, amount_cents: int, source: str,
                ref: str | None = None, note: str | None = None) -> bool:
    """Insert one posting; idempotent on (source, ref). Returns True if a new row
    was written (or already existed), False on error/no-op."""
    if not merchant_id or not amount_cents or amount_cents <= 0:
        return False
    db = get_db()
    try:
        if ref:
            existing = await db.select(
                "voice_ledger",
                filters={"source": f"eq.{source}", "ref": f"eq.{ref}"},
                limit=1,
            )
            if existing:
                return True  # already posted — idempotent no-op
        await db.insert("voice_ledger", {
            "merchant_id": merchant_id,
            "kind": kind,
            "amount_cents": int(round(amount_cents)),
            "source": source,
            "ref": ref,
            "note": note,
        })
        logger.info("voice_ledger %s %s %d¢ merchant=%s ref=%s",
                    kind, source, amount_cents, merchant_id, ref or "-")
        return True
    except Exception as e:  # noqa: BLE001 — ledger must never break the caller
        logger.error("voice_ledger %s failed for %s: %s", kind, merchant_id, e)
        return False


async def credit(merchant_id: str, amount_cents: int, source: str = "stripe_fee",
                 ref: str | None = None, note: str | None = None) -> bool:
    return await _post(merchant_id, "credit", amount_cents, source, ref, note)


async def debit(merchant_id: str, amount_cents: int, source: str = "vapi_call",
                ref: str | None = None, note: str | None = None) -> bool:
    return await _post(merchant_id, "debit", amount_cents, source, ref, note)


async def balance_cents(merchant_id: str) -> int | None:
    """Net balance for a merchant: SUM(credit) - SUM(debit). None if unknown
    (no DB / error) so callers can fail open rather than block calls."""
    if not merchant_id:
        return None
    db = get_db()
    try:
        rows = await db.select(
            "voice_ledger",
            columns="kind,amount_cents",
            filters={"merchant_id": f"eq.{merchant_id}"},
            limit=10000,
        )
    except Exception as e:  # noqa: BLE001
        logger.error("voice_ledger balance failed for %s: %s", merchant_id, e)
        return None
    bal = 0
    for r in rows or []:
        amt = int(r.get("amount_cents") or 0)
        bal += amt if r.get("kind") == "credit" else -amt
    return bal


def summarize_ledger(rows: list[dict], window_days: int, cutoff_iso: str | None) -> dict:
    """Pure P&L rollup (no I/O) — unit-testable core of the voice wallet.

    - balance_cents: all-time SUM(credit) - SUM(debit)  (the self-funding line)
    - window_*: credit/debit for rows with created_at >= cutoff_iso (run-rate)
    - avg_daily_debit_cents: window debit / window_days (burn rate)
    - runway_days: balance / avg_daily_debit when burning AND funded, else None
      (underwater or zero-burn ⇒ no finite runway).
    """
    balance = 0
    win_credit = 0
    win_debit = 0
    for r in rows or []:
        amt = int(r.get("amount_cents") or 0)
        is_credit = r.get("kind") == "credit"
        balance += amt if is_credit else -amt
        if cutoff_iso is not None and (r.get("created_at") or "") >= cutoff_iso:
            if is_credit:
                win_credit += amt
            else:
                win_debit += amt
    avg_daily_debit = (win_debit / window_days) if (window_days and win_debit) else 0.0
    runway_days = round(balance / avg_daily_debit, 1) if (avg_daily_debit > 0 and balance > 0) else None
    return {
        "balance_cents": balance,
        "self_funded": balance >= 0,
        "window_days": window_days,
        "window_credit_cents": win_credit,
        "window_debit_cents": win_debit,
        "window_net_cents": win_credit - win_debit,
        "avg_daily_debit_cents": round(avg_daily_debit, 2),
        "runway_days": runway_days,
    }


async def wallet_summary(merchant_id: str, window_days: int = 30) -> dict | None:
    """Per-location voice wallet: all-time balance + windowed credit/debit +
    burn rate + runway. None if the ledger is unreadable (caller fails open).
    The read behind the operator 'Voice Wallet' card — it never mutates."""
    if not merchant_id:
        return None
    db = get_db()
    try:
        rows = await db.select(
            "voice_ledger",
            columns="kind,amount_cents,created_at,source",
            filters={"merchant_id": f"eq.{merchant_id}"},
            limit=100000,
        )
    except Exception as e:  # noqa: BLE001
        logger.error("voice_ledger wallet_summary failed for %s: %s", merchant_id, e)
        return None
    cutoff_iso = None
    if window_days and window_days > 0:
        from datetime import datetime, timedelta, timezone
        cutoff_iso = (datetime.now(timezone.utc) - timedelta(days=window_days)).isoformat()
    return {"merchant_id": merchant_id, **summarize_ledger(rows or [], window_days, cutoff_iso)}
