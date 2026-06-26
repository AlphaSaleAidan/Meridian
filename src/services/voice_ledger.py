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
