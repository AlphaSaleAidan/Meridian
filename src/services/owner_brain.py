"""Owner Brain — the knowledge an owner carries in their head, mined from POS.

Extends the smart upsell brief (upsell_brief.py) with the two signals that make
suggestions feel like the OWNER is on the phone rather than a script:

  pairings  — what actually gets ordered together HERE ("42% of burger orders
              add a shake"), mined from transaction_items co-occurrence, so the
              agent's suggestion is anchored to this restaurant's real habits.
  dayparts  — what sells at this hour (morning/lunch/afternoon/dinner/late),
              so the 8am caller hears pastries and the 8pm caller hears mains.

Pure mining functions are dependency-free and unit-tested; the async fetch is
tolerant and fail-open like everything else on the call path. All output is
filtered to the phone menu upstream (upsell_brief) — nothing off-menu is ever
suggested.
"""
import logging
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger("meridian.owner_brain")

WINDOW_DAYS = 30
FETCH_LIMIT = 20000
# an item needs this many appearances before its pairing stats are trusted
MIN_SUPPORT = 5
MIN_ATTACH_PCT = 15.0
TOP_PARTNERS = 2
TOP_DAYPART_ITEMS = 4

DAYPARTS = (
    ("morning", 6, 11),
    ("lunch", 11, 15),
    ("afternoon", 15, 17),
    ("dinner", 17, 22),
    ("late-night", 22, 24),   # 22:00–06:00 wraps; 0–6 handled below
)


def _parse_ts(value: Any) -> Optional[datetime]:
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def _local_hour(ts: Any, tz_name: str) -> Optional[int]:
    dt = _parse_ts(ts)
    if dt is None:
        return None
    if tz_name:
        try:
            from zoneinfo import ZoneInfo
            dt = dt.astimezone(ZoneInfo(tz_name))
        except Exception:  # noqa: BLE001 — bad tz falls back to UTC
            pass
    return dt.hour


def daypart_for_hour(hour: int) -> str:
    if hour < 6:
        return "late-night"
    for name, lo, hi in DAYPARTS:
        if lo <= hour < hi:
            return name
    return "late-night"


def current_daypart(tz_name: str, now: Optional[datetime] = None) -> str:
    dt = now or datetime.now(timezone.utc)
    if tz_name:
        try:
            from zoneinfo import ZoneInfo
            dt = dt.astimezone(ZoneInfo(tz_name))
        except Exception:  # noqa: BLE001
            pass
    return daypart_for_hour(dt.hour)


def mine_pairings(item_rows: list[dict],
                  min_support: int = MIN_SUPPORT,
                  min_attach_pct: float = MIN_ATTACH_PCT,
                  top_partners: int = TOP_PARTNERS) -> dict[str, list[dict]]:
    """Co-occurrence mining over transaction_items rows.

    Returns {item_name: [{"partner": name, "attach_pct": float}, ...]} where
    attach_pct = share of the item's orders that also contained the partner.
    Pure function — rows only need transaction_id + product_name."""
    baskets: dict[str, set[str]] = defaultdict(set)
    for r in item_rows or []:
        tid = r.get("transaction_id")
        name = str(r.get("product_name") or "").strip()
        if tid and name:
            baskets[str(tid)].add(name)

    item_count: Counter[str] = Counter()
    pair_count: Counter[tuple[str, str]] = Counter()
    for names in baskets.values():
        for n in names:
            item_count[n] += 1
        ordered = sorted(names)
        for i, a in enumerate(ordered):
            for b in ordered[i + 1:]:
                pair_count[(a, b)] += 1

    out: dict[str, list[dict]] = {}
    for item, count in item_count.items():
        if count < min_support:
            continue
        partners = []
        for (a, b), c in pair_count.items():
            if item == a:
                partner = b
            elif item == b:
                partner = a
            else:
                continue
            pct = c / count * 100.0
            if pct >= min_attach_pct:
                partners.append({"partner": partner, "attach_pct": round(pct, 1)})
        partners.sort(key=lambda p: p["attach_pct"], reverse=True)
        if partners:
            out[item] = partners[:top_partners]
    return out


def mine_dayparts(item_rows: list[dict], tz_name: str = "",
                  top_n: int = TOP_DAYPART_ITEMS) -> dict[str, list[str]]:
    """Top items per daypart (merchant-local hours). Pure given rows + tz."""
    counters: dict[str, Counter[str]] = defaultdict(Counter)
    for r in item_rows or []:
        name = str(r.get("product_name") or "").strip()
        if not name:
            continue
        hour = _local_hour(r.get("transaction_at"), tz_name)
        if hour is None:
            continue
        try:
            qty = float(r.get("quantity") or 1)
        except (TypeError, ValueError):
            qty = 1.0
        counters[daypart_for_hour(hour)][name] += qty
    return {dp: [n for n, _ in c.most_common(top_n)] for dp, c in counters.items()}


async def fetch_transaction_items(merchant_id: str,
                                  days: int = WINDOW_DAYS) -> list[dict]:
    """Recent transaction_items rows for the merchant's org. Fail-open []."""
    try:
        from ..db import get_db
        from ..db.org_ids import connection_org_id
        from ..db.supabase_rest import _days_ago
        db = get_db()
        org_id = connection_org_id(merchant_id) or merchant_id
        return await db.select(
            "transaction_items",
            columns="transaction_id,product_name,quantity,transaction_at",
            filters={"org_id": f"eq.{org_id}",
                     "transaction_at": f"gte.{_days_ago(days)}"},
            order="transaction_at.desc",
            limit=FETCH_LIMIT,
        ) or []
    except Exception as e:  # noqa: BLE001 — mining is best-effort
        logger.warning("transaction_items fetch failed for %s: %s", merchant_id, e)
        return []
