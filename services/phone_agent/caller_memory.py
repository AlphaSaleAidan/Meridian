"""
Per-caller memory for the phone agent.

Looks up a caller's past orders by their phone number, summarises favourites
and the most recent order, and produces a short text block the LLM can read
to greet returning customers personally ("welcome back, your usual?").

Data source: phone_orders table (caller_phone, items, total, created_at).
Read path runs once per call at handshake time, so latency budget is ~50ms.
"""
import logging
import os
from collections import Counter
from datetime import datetime, timezone
from typing import Any

import httpx

logger = logging.getLogger("meridian.phone_agent.memory")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY", "")

# Pull the last N orders for the caller; small N keeps the prompt tight.
_HISTORY_LIMIT = 5
_FREQUENT_TOP_N = 3
# Don't burn LLM tokens on history older than this — preferences drift.
_MAX_AGE_DAYS = 180


def _normalize_phone(phone: str) -> str:
    return "".join(c for c in (phone or "") if c.isdigit() or c == "+").strip()


def _days_ago(iso_ts: str) -> int | None:
    try:
        dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
        return max(0, (datetime.now(timezone.utc) - dt).days)
    except (ValueError, AttributeError):
        return None


def _format_relative(days: int | None) -> str:
    if days is None:
        return "previously"
    if days == 0:
        return "earlier today"
    if days == 1:
        return "yesterday"
    if days < 7:
        return f"{days} days ago"
    if days < 30:
        return f"{days // 7} week{'s' if days // 7 > 1 else ''} ago"
    return f"{days // 30} month{'s' if days // 30 > 1 else ''} ago"


def _summarize_items(items: list[dict[str, Any]]) -> str:
    parts = []
    for it in items[:6]:
        qty = it.get("quantity", 1)
        name = it.get("name", "item")
        size = it.get("size")
        parts.append(f"{qty}x {size + ' ' if size else ''}{name}")
    return ", ".join(parts)


async def fetch_caller_history(
    merchant_id: str,
    phone_number: str,
    limit: int = _HISTORY_LIMIT,
) -> list[dict[str, Any]]:
    """Return up to `limit` recent phone_orders for this caller, newest first."""
    phone = _normalize_phone(phone_number)
    if not phone or not SUPABASE_URL or not SUPABASE_KEY:
        return []

    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    select = "items,total,order_type,created_at,status"
    query = (
        f"{SUPABASE_URL}/rest/v1/phone_orders"
        f"?caller_phone=eq.{phone}"
        f"&merchant_id=eq.{merchant_id}"
        f"&status=eq.placed"
        f"&select={select}"
        f"&order=created_at.desc&limit={limit}"
    )
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            res = await client.get(query, headers=headers)
            if res.status_code != 200:
                logger.warning("caller history %d: %s", res.status_code, res.text[:120])
                return []
            return res.json() or []
    except Exception as e:
        logger.warning("caller history lookup failed for %s: %s", phone, e)
        return []


def build_memory_block(orders: list[dict[str, Any]]) -> str:
    """Render the caller history into a short prompt-ready block.

    Returns either a REGULAR CALLER summary or a FIRST-TIME CALLER stub.
    The LLM uses this to greet personally and offer "the usual" without
    needing tool calls during the time-critical greeting turn.
    """
    if not orders:
        return "CALLER: First-time caller. Use the standard greeting."

    recent = [o for o in orders if (_days_ago(o.get("created_at", "")) or 9999) <= _MAX_AGE_DAYS]
    if not recent:
        return "CALLER: First-time caller (no recent orders). Use the standard greeting."

    last = recent[0]
    last_items = last.get("items", []) or []
    last_summary = _summarize_items(last_items) or "their usual order"
    last_when = _format_relative(_days_ago(last.get("created_at", "")))

    name_counter: Counter[str] = Counter()
    for order in recent:
        for it in order.get("items", []) or []:
            name = it.get("name")
            if name:
                name_counter[name] += int(it.get("quantity", 1))
    frequent = [name for name, _ in name_counter.most_common(_FREQUENT_TOP_N)]

    lines = [
        f"CALLER: Returning customer — {len(recent)} previous order{'s' if len(recent) != 1 else ''} on file.",
        f"Last order ({last_when}): {last_summary}.",
    ]
    if frequent:
        lines.append(f"Most-ordered items: {', '.join(frequent)}.")
    lines.append(
        'If they say "the usual", "same as last time", or similar, offer to repeat the last order above and confirm before submitting.'
    )
    return "\n".join(lines)


async def build_memory_block_for(merchant_id: str, phone_number: str) -> str:
    """One-shot helper: fetch + render. Safe to call in the call handshake path."""
    orders = await fetch_caller_history(merchant_id, phone_number)
    return build_memory_block(orders)
