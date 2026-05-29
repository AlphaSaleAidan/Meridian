"""Credit balance service: thin wrapper around the Supabase RPC functions.

All mutations go through the Postgres functions `credits_deduct` and
`credits_grant`, which are transactional and won't let balance go negative.
This file just speaks HTTP to the PostgREST endpoint that exposes them.
"""
import logging
import os
from typing import Any, Optional

import httpx

from .costs import STARTER_GRANT

logger = logging.getLogger("meridian.credits")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = (
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    or os.getenv("SUPABASE_SERVICE_KEY")
    or os.getenv("SUPABASE_ANON_KEY", "")
)


class InsufficientCredits(Exception):
    """Raised when an action would push balance below zero."""

    def __init__(self, merchant_id: str, requested: int, available: int):
        self.merchant_id = merchant_id
        self.requested = requested
        self.available = available
        super().__init__(
            f"merchant {merchant_id} needs {requested} credits but only has {available}"
        )


def _headers() -> dict[str, str]:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def _configured() -> bool:
    return bool(SUPABASE_URL and SUPABASE_KEY)


async def get_balance(merchant_id: str) -> int:
    """Current balance (0 if no row exists yet)."""
    if not _configured():
        return 0
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            res = await client.get(
                f"{SUPABASE_URL}/rest/v1/merchant_credits"
                f"?merchant_id=eq.{merchant_id}&select=balance",
                headers=_headers(),
            )
            if res.status_code != 200:
                logger.warning("get_balance %d: %s", res.status_code, res.text[:120])
                return 0
            rows = res.json()
            return int(rows[0]["balance"]) if rows else 0
    except Exception as e:
        logger.warning("get_balance failed for %s: %s", merchant_id, e)
        return 0


async def has_balance(merchant_id: str, required: int) -> bool:
    """Cheap pre-check; doesn't lock the row. Use deduct() for the source of truth."""
    return await get_balance(merchant_id) >= required


async def deduct(
    merchant_id: str,
    amount: int,
    action_type: str,
    action_id: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> int:
    """Atomically deduct credits. Raises InsufficientCredits if balance < amount.

    Returns the new balance. The Postgres function inserts a ledger row in
    the same transaction so the balance and ledger never disagree.
    """
    if amount <= 0:
        return await get_balance(merchant_id)
    if not _configured():
        logger.warning("credits not configured — skipping deduct of %d for %s", amount, merchant_id)
        return 0

    payload = {
        "p_merchant_id": merchant_id,
        "p_amount": amount,
        "p_action_type": action_type,
        "p_action_id": action_id,
        "p_metadata": metadata or {},
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.post(
                f"{SUPABASE_URL}/rest/v1/rpc/credits_deduct",
                headers=_headers(),
                json=payload,
            )
            if res.status_code != 200:
                logger.error("credits_deduct %d: %s", res.status_code, res.text[:200])
                # Failing open here would let the operation through for free.
                # Failing closed would block real users on a transient outage.
                # Mid-ground: treat as insufficient so the caller decides.
                raise InsufficientCredits(merchant_id, amount, await get_balance(merchant_id))
            new_balance = res.json()
            if new_balance is None:
                available = await get_balance(merchant_id)
                raise InsufficientCredits(merchant_id, amount, available)
            return int(new_balance)
    except InsufficientCredits:
        raise
    except Exception as e:
        logger.error("credits_deduct error for %s amount=%d: %s", merchant_id, amount, e)
        raise InsufficientCredits(merchant_id, amount, 0) from e


async def grant(
    merchant_id: str,
    amount: int,
    action_type: str,
    action_id: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
    is_free: bool = False,
) -> int:
    """Add credits. Creates the balance row on first grant. Returns new balance."""
    if amount <= 0:
        return await get_balance(merchant_id)
    if not _configured():
        logger.warning("credits not configured — skipping grant of %d for %s", amount, merchant_id)
        return 0

    payload = {
        "p_merchant_id": merchant_id,
        "p_amount": amount,
        "p_action_type": action_type,
        "p_action_id": action_id,
        "p_metadata": metadata or {},
        "p_is_free": is_free,
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.post(
                f"{SUPABASE_URL}/rest/v1/rpc/credits_grant",
                headers=_headers(),
                json=payload,
            )
            if res.status_code != 200:
                logger.error("credits_grant %d: %s", res.status_code, res.text[:200])
                return await get_balance(merchant_id)
            return int(res.json())
    except Exception as e:
        logger.error("credits_grant error for %s amount=%d: %s", merchant_id, amount, e)
        return await get_balance(merchant_id)


async def ensure_starter_grant(merchant_id: str) -> int:
    """Grant the free starter pool if this merchant has never been credited.

    Idempotent — uses the ledger to detect whether a starter grant has
    already happened, so calling this on every signup is safe.
    """
    if not _configured() or not merchant_id:
        return 0

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            res = await client.get(
                f"{SUPABASE_URL}/rest/v1/credit_ledger"
                f"?merchant_id=eq.{merchant_id}&action_type=eq.starter_grant&select=id&limit=1",
                headers=_headers(),
            )
            if res.status_code == 200 and res.json():
                return await get_balance(merchant_id)
    except Exception as e:
        logger.warning("ensure_starter_grant check failed for %s: %s", merchant_id, e)

    return await grant(
        merchant_id=merchant_id,
        amount=STARTER_GRANT,
        action_type="starter_grant",
        metadata={"reason": "first-time signup bonus"},
        is_free=True,
    )
