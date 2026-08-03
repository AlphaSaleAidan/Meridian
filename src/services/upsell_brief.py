"""Smart Upsell Brief — data-driven upsell priorities for the phone agent.

The generic upsell step ("can I throw in a drink or a side?") ignores
everything Meridian actually knows about the restaurant. This module turns the
POS data we already sync into a per-merchant priority list the voice agent can
sell from:

  • margin      — items whose cost data shows the fattest margin (best add-on)
  • overstock   — on-hand quantity vs. 30-day sales velocity says we're deep
                  on stock; the agent nudges those items before they die
  • crowd pick  — the restaurant's most-ordered item (social-proof pitch)

The brief is computed from `daily_product_performance` + `inventory_snapshots`
(+ the `products` catalog for cost), matched against the PHONE MENU by
normalized name — the agent only ever offers what's orderable on the menu and
never anything sold out. It is cached (dashboard_cache, 6h) and read
synchronously on the assistant-request hot path: cache miss returns None and
schedules a background refresh, so call setup latency is never touched and the
prompt degrades to the proven generic upsell step.

An empty/missing brief renders to "" — the system prompt stays byte-for-byte
unchanged (same no-regression contract as restaurant_brief / personality).
"""
import asyncio
import logging
import re
import unicodedata
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any, Optional

logger = logging.getLogger("meridian.upsell_brief")

CACHE_TTL_SECONDS = 6 * 3600
CACHE_PREFIX = "upsell_brief"
WINDOW_DAYS = 30
MAX_CANDIDATES = 5
# days-of-stock beyond which an item counts as overstocked (needs real stock)
OVERSTOCK_DAYS = 10.0
MIN_STOCK_UNITS = 5
HIGH_MARGIN_PCT = 55.0
NAME_MATCH_RATIO = 0.78

# in-flight refresh dedup so a burst of calls schedules one recompute
_inflight: set[str] = set()


# ── name matching ───────────────────────────────────────────────────────────

_SIZE_WORDS = re.compile(
    r"\b(small|medium|large|regular|double|xl|x-large|kids?|side|full|"
    r"\d+\s*(?:pc|piece|oz|ml|l|inch|\"))\b"
)
_NON_ALNUM = re.compile(r"[^a-z0-9 ]+")


def _norm(name: str) -> str:
    """Normalize a product/menu name for cross-system matching: casefold,
    strip accents/punctuation/size words, collapse whitespace."""
    s = unicodedata.normalize("NFKD", str(name or "")).encode("ascii", "ignore").decode()
    s = _NON_ALNUM.sub(" ", s.lower())
    s = _SIZE_WORDS.sub(" ", s)
    return " ".join(s.split())


def match_menu_item(pos_name: str, menu_norms: dict[str, str]) -> Optional[str]:
    """Best menu item (original name) for a POS product name, or None.
    menu_norms maps normalized menu name → original menu name."""
    n = _norm(pos_name)
    if not n:
        return None
    if n in menu_norms:
        return menu_norms[n]
    for mn, orig in menu_norms.items():
        if not mn:
            continue
        # containment either way ("coke" ↔ "coca cola classic" won't hit, but
        # "caesar salad" ↔ "chicken caesar salad" will) …
        if mn in n or n in mn:
            return orig
        # … then fuzzy for spelling drift between POS catalog and menu store
        if SequenceMatcher(None, n, mn).ratio() >= NAME_MATCH_RATIO:
            return orig
    return None


# ── tolerant row readers (schemas differ slightly per POS sync) ─────────────

def _num(row: dict, *keys: str) -> float:
    for k in keys:
        v = row.get(k)
        if v is None:
            continue
        try:
            return float(v)
        except (TypeError, ValueError):
            continue
    return 0.0


def aggregate_performance(perf_rows: list[dict]) -> dict[str, dict[str, Any]]:
    """Collapse daily_product_performance rows → per-product totals keyed by
    normalized product name: {revenue_cents, qty, cost_cents, name}."""
    agg: dict[str, dict[str, Any]] = {}
    for r in perf_rows or []:
        name = str(r.get("product_name") or r.get("name") or "").strip()
        if not name:
            continue
        key = _norm(name)
        if not key:
            continue
        a = agg.setdefault(key, {"name": name, "revenue_cents": 0.0, "qty": 0.0,
                                 "cost_cents": 0.0})
        a["revenue_cents"] += _num(r, "total_revenue_cents", "revenue_cents", "revenue")
        a["qty"] += _num(r, "total_quantity", "quantity_sold", "quantity", "times_sold")
        a["cost_cents"] += _num(r, "total_cost_cents", "cost_cents", "cost")
    return agg


# ── scoring ─────────────────────────────────────────────────────────────────

def score_candidates(
    menu_items: list[dict],
    sold_out: list[str],
    perf_by_name: dict[str, dict[str, Any]],
    inventory_rows: list[dict],
    window_days: int = WINDOW_DAYS,
) -> list[dict[str, Any]]:
    """Rank menu items as upsell candidates. Pure function — unit-testable.

    Returns [{name, price, score, reasons, pitch, margin_pct, days_of_stock}]
    sorted best-first; only items with at least one real reason survive."""
    sold_out_norms = {_norm(s) for s in sold_out or []}
    menu_norms = {_norm(m.get("name", "")): m.get("name", "")
                  for m in menu_items or [] if m.get("name")}

    # on-hand stock per matched menu item
    stock: dict[str, float] = {}
    for inv in inventory_rows or []:
        m = match_menu_item(str(inv.get("product_name") or ""), menu_norms)
        if m:
            stock[m] = stock.get(m, 0.0) + _num(inv, "current_stock", "quantity_on_hand")

    # performance per matched menu item
    perf: dict[str, dict[str, Any]] = {}
    for p in perf_by_name.values():
        m = match_menu_item(p["name"], menu_norms)
        if m:
            t = perf.setdefault(m, {"revenue_cents": 0.0, "qty": 0.0, "cost_cents": 0.0})
            for k in t:
                t[k] += p[k]

    revenues = sorted((v["revenue_cents"] for v in perf.values()), reverse=True)
    top_quartile_rev = revenues[max(0, len(revenues) // 4 - 1)] if revenues else 0.0
    prices = sorted(float(m.get("price") or 0) for m in menu_items or [] if m.get("price"))
    median_price = prices[len(prices) // 2] if prices else 0.0

    out: list[dict[str, Any]] = []
    for m in menu_items or []:
        name = m.get("name")
        if not name or _norm(name) in sold_out_norms:
            continue
        price = float(m.get("price") or 0)
        p = perf.get(name, {})
        qty = p.get("qty", 0.0)
        revenue = p.get("revenue_cents", 0.0)
        cost = p.get("cost_cents", 0.0)
        velocity = qty / window_days if qty else 0.0

        margin_pct = None
        if revenue > 0 and cost > 0:
            margin_pct = max(0.0, min(100.0, (revenue - cost) / revenue * 100.0))

        on_hand = stock.get(name, 0.0)
        days_of_stock = (on_hand / velocity) if (on_hand and velocity > 0) else None

        reasons: list[str] = []
        if margin_pct is not None and margin_pct >= HIGH_MARGIN_PCT:
            reasons.append("high-margin")
        if (days_of_stock is not None and days_of_stock >= OVERSTOCK_DAYS
                and on_hand >= MIN_STOCK_UNITS):
            reasons.append("overstocked")
        # needs a real field to beat — with <3 performing items everything
        # would trivially be "top quartile" of itself
        if (len(revenues) >= 3 and revenue and top_quartile_rev
                and revenue >= top_quartile_rev and qty >= 3):
            reasons.append("crowd-favorite")
        if not reasons:
            continue

        margin_norm = (margin_pct or 0.0) / 100.0
        overstock_norm = min((days_of_stock or 0.0) / (OVERSTOCK_DAYS * 3), 1.0) \
            if "overstocked" in reasons else 0.0
        popularity_norm = (revenue / revenues[0]) if revenues and revenues[0] else 0.0
        score = 0.45 * margin_norm + 0.35 * overstock_norm + 0.20 * popularity_norm
        # attachability: cheap add-ons are far easier to say yes to mid-order
        if median_price and price:
            score *= 1.25 if price <= median_price * 0.7 else \
                (1.0 if price <= median_price * 1.3 else 0.6)

        out.append({
            "name": name,
            "price": round(price, 2) if price else None,
            "score": round(score, 4),
            "reasons": reasons,
            "pitch": _pitch(name, reasons),
            "margin_pct": round(margin_pct, 1) if margin_pct is not None else None,
            "days_of_stock": round(days_of_stock, 1) if days_of_stock is not None else None,
        })

    out.sort(key=lambda c: c["score"], reverse=True)
    return out[:MAX_CANDIDATES]


def _pitch(name: str, reasons: list[str]) -> str:
    if "overstocked" in reasons and "high-margin" in reasons:
        return f"top priority — deep stock AND one of the best margins; work {name} into any fitting order"
    if "overstocked" in reasons:
        return f"we're deep on stock — steer callers toward {name} while it's fresh"
    if "high-margin" in reasons and "crowd-favorite" in reasons:
        return "best of both — a favorite that's also a top margin item"
    if "high-margin" in reasons:
        return "one of the kitchen's best margins — the ideal add-on suggestion"
    return "the most-ordered item here — 'want to try our most popular?' lands well"


# ── prompt rendering ────────────────────────────────────────────────────────

def render_upsell_block(brief: Optional[dict], upsell_mode: str,
                        tz_name: str = "") -> str:
    """The prompt block. Empty string when there's nothing actionable or the
    merchant disabled upselling — prompt stays byte-for-byte unchanged.

    Beyond the priority list, renders the owner-brain signals when present:
    real pairing stats and what sells at this hour (merchant-local)."""
    mode = (upsell_mode or "").strip().lower()
    if mode == "none" or not brief:
        return ""
    cands = brief.get("candidates") or []
    pairings = brief.get("pairings") or {}
    dayparts = brief.get("dayparts") or {}
    if not cands and not pairings and not dayparts:
        return ""
    limit = "TWO suggestions max" if mode == "active" else "ONE suggestion max"
    parts: list[str] = []

    if cands:
        lines = []
        for c in cands:
            tag = ", ".join(c.get("reasons") or [])
            price = f" (${c['price']:.2f})" if c.get("price") else ""
            lines.append(f"- {c['name']}{price} — {c['pitch']} [{tag}]")
        parts.append(
            "\n\nTODAY'S UPSELL PRIORITIES (computed from THIS restaurant's live "
            "sales, margins and inventory — refreshed automatically):\n"
            + "\n".join(lines)
        )

    if pairings:
        pair_lines = []
        for item, partners in list(pairings.items())[:4]:
            for p in partners[:1]:
                pair_lines.append(
                    f"- Order has {item} → suggest {p['partner']} "
                    f"({p['attach_pct']:.0f}% of {item} orders here add it)")
        if pair_lines:
            parts.append(
                "\nPAIRINGS (mined from this restaurant's actual order history — "
                "use these over generic suggestions):\n" + "\n".join(pair_lines))

    if dayparts:
        try:
            from .owner_brain import current_daypart
            dp = current_daypart(tz_name)
            now_items = dayparts.get(dp) or []
            if now_items:
                parts.append(
                    f"\nRIGHT NOW ({dp}): customers here most often order "
                    f"{', '.join(now_items)} — when several suggestions fit, "
                    "lead with one of these.")
        except Exception:  # noqa: BLE001 — daypart line is optional garnish
            pass

    if not parts:
        return ""
    parts.append(
        "\nWhen the call flow reaches the upsell step, pick the FIRST priority "
        "that naturally fits what the caller ordered — phrase it as a friendly "
        f"suggestion, never a pitch. {limit} per call; drop it instantly if the "
        "caller declines. Never suggest something already in the order or "
        "anything sold out."
    )
    return "".join(parts)


# ── compute + cache ─────────────────────────────────────────────────────────

def _cache_key(merchant_id: str) -> str:
    return f"{CACHE_PREFIX}:{merchant_id}"


async def compute_upsell_brief(merchant_id: str, menu_items: list[dict],
                               sold_out: list[str] | None = None,
                               tz_name: str = "") -> dict:
    """Compute (and cache) the brief from live POS data. Never raises —
    an empty brief is the failure mode."""
    from ..db import get_db
    from ..db.cache import dashboard_cache

    brief: dict[str, Any] = {
        "merchant_id": merchant_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window_days": WINDOW_DAYS,
        "candidates": [],
        "has_cost_data": False,
    }
    try:
        db = get_db()
        perf_rows = await db.get_product_performance(merchant_id, days=WINDOW_DAYS)
        inventory = await db.get_inventory_current(merchant_id)
        perf = aggregate_performance(perf_rows)
        brief["has_cost_data"] = any(p["cost_cents"] > 0 for p in perf.values())
        brief["candidates"] = score_candidates(
            menu_items, sold_out or [], perf, inventory)
        logger.info("upsell brief for %s: %d candidates (cost_data=%s)",
                    merchant_id, len(brief["candidates"]), brief["has_cost_data"])
    except Exception as e:  # noqa: BLE001 — a brief failure must never matter
        logger.warning("upsell brief compute failed for %s: %s", merchant_id, e)

    # Owner-brain signals: pairings + dayparts from transaction_items, mapped
    # onto the phone menu (only orderable items ever reach the prompt).
    try:
        from .owner_brain import fetch_transaction_items, mine_dayparts, mine_pairings
        item_rows = await fetch_transaction_items(merchant_id)
        if item_rows:
            menu_norms = {_norm(m.get("name", "")): m.get("name", "")
                          for m in menu_items or [] if m.get("name")}

            def _on_menu(name: str) -> Optional[str]:
                return match_menu_item(name, menu_norms)

            pairings: dict[str, list[dict]] = {}
            for item, partners in mine_pairings(item_rows).items():
                mi = _on_menu(item)
                if not mi:
                    continue
                mapped = []
                for p in partners:
                    mp = _on_menu(p["partner"])
                    if mp and mp != mi:
                        mapped.append({"partner": mp, "attach_pct": p["attach_pct"]})
                if mapped:
                    pairings[mi] = mapped
            brief["pairings"] = pairings

            dayparts: dict[str, list[str]] = {}
            for dp, names in mine_dayparts(item_rows, tz_name=tz_name).items():
                on_menu = []
                for n in names:
                    mn = _on_menu(n)
                    if mn and mn not in on_menu:
                        on_menu.append(mn)
                if on_menu:
                    dayparts[dp] = on_menu
            brief["dayparts"] = dayparts
            logger.info("owner brain for %s: %d pairings, %d dayparts",
                        merchant_id, len(pairings), len(dayparts))
    except Exception as e:  # noqa: BLE001 — owner brain is additive only
        logger.warning("owner brain compute failed for %s: %s", merchant_id, e)
    try:
        dashboard_cache.set(_cache_key(merchant_id), brief, CACHE_TTL_SECONDS)
    except Exception:  # noqa: BLE001
        pass
    return brief


def get_cached_brief(merchant_id: str) -> Optional[dict]:
    try:
        from ..db.cache import dashboard_cache
        return dashboard_cache.get(_cache_key(merchant_id))
    except Exception:  # noqa: BLE001
        return None


def cached_or_schedule(merchant_id: str, menu_items: list[dict],
                       sold_out: list[str] | None = None,
                       tz_name: str = "") -> Optional[dict]:
    """Hot-path read: cached brief, or None + a background refresh. Never
    blocks — assistant-request latency is sacred."""
    brief = get_cached_brief(merchant_id)
    if brief is not None:
        return brief
    if merchant_id in _inflight:
        return None
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return None
    _inflight.add(merchant_id)

    async def _run():
        try:
            await compute_upsell_brief(merchant_id, menu_items, sold_out, tz_name)
        finally:
            _inflight.discard(merchant_id)

    loop.create_task(_run())
    return None
