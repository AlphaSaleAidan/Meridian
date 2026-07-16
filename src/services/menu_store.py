"""
Menu Store — the normalized single source of truth for a merchant's menu.

One row per item in the ``menu_items`` table (migration 20260716_menu_store).
Replaces direct writes to the ``phone_agent_config.menu_items`` JSONB blob.

WRITE-THROUGH MIRROR — the backward-compat contract
---------------------------------------------------
Every mutation in this module finishes by rewriting
``phone_agent_config.menu_items`` with the *published, non-sold-out* items in
the agent's legacy dict shape (dollars). That JSONB blob is what every legacy
reader consumes unchanged:

  - services/phone_agent/merchant_config.py (fallback when no store rows)
  - src/api/routes/phone.py TwiML prompt builder
  - the setup wizards' menu-step hydration (GET /api/phone/config)

So merchants whose menus live in the store keep working with zero migration of
any reader, and merchants who never touch the new UI keep their JSONB-only
world (this module is only entered on new-UI / ingestion writes).

UNITS: store rows are integer CENTS (price_cents, topping_price_cents,
size_prices values). The agent/JSONB shape is dollars (floats). Conversions
happen only at the edges (``to_agent_shape`` / ``from_agent_shape``).

Review gates: ingested items (scrape/csv/photo) land ``published=false,
needs_review=true`` — never silently live. POS imports are trusted
(``published=true``) but flag ``needs_review`` when the price is missing/zero.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger("meridian.services.menu_store")

VALID_SOURCES = ("manual", "pos", "scrape", "csv", "photo")
# Ingestion sources that must pass the review screen before going live.
UNTRUSTED_SOURCES = ("scrape", "csv", "photo")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dollars(cents: Optional[int]) -> Optional[float]:
    return round(cents / 100, 2) if isinstance(cents, (int, float)) and cents else None


def _cents(dollars: Any) -> Optional[int]:
    """Best-effort dollars → integer cents; None when absent/unparseable."""
    if dollars is None:
        return None
    try:
        value = float(str(dollars).replace("$", "").replace(",", "").strip())
    except (ValueError, TypeError):
        return None
    return int(round(value * 100)) if value > 0 else None


# ── shape conversion (store row ⇄ legacy agent dict) ─────────────────────

def to_agent_shape(row: dict) -> dict:
    """Store row → the legacy agent dict shape rendered by
    vapi_webhook._system_prompt: {name, price?, category?, sizes?,
    size_prices?, topping_price?, modifications?, description?} in DOLLARS.

    services/phone_agent/merchant_config.py carries a dependency-free twin of
    this converter (_store_row_to_agent_item) — keep them in lockstep
    (tests/test_menu_agent_path.py asserts parity).
    """
    item: dict[str, Any] = {"name": row.get("name") or "item"}
    price = _dollars(row.get("price_cents"))
    if price is not None:
        item["price"] = price
    if row.get("category"):
        item["category"] = row["category"]
    if row.get("description"):
        item["description"] = row["description"]
    sizes = row.get("sizes")
    if isinstance(sizes, list) and sizes:
        item["sizes"] = list(sizes)
    size_prices = row.get("size_prices")
    if isinstance(size_prices, dict) and size_prices:
        converted = {}
        for size, cents in size_prices.items():
            d = _dollars(cents if isinstance(cents, (int, float)) else None)
            if d is not None:
                converted[str(size)] = d
        if converted:
            item["size_prices"] = converted
            item.setdefault("sizes", list(converted.keys()))
    topping = _dollars(row.get("topping_price_cents"))
    if topping is not None:
        item["topping_price"] = topping
    mods = row.get("modifications")
    if isinstance(mods, list) and mods:
        item["modifications"] = list(mods)
    return item


def from_agent_shape(item: dict, *, source: str = "manual") -> dict:
    """Legacy agent dict (dollars) → store row fields (cents). Used by the
    migrate-on-write JSONB import and the wizard write-through."""
    row: dict[str, Any] = {
        "name": str(item.get("name") or "").strip(),
        "source": source if source in VALID_SOURCES else "manual",
    }
    row["price_cents"] = _cents(item.get("price"))
    if item.get("category"):
        row["category"] = str(item["category"]).strip()
    if item.get("description"):
        row["description"] = str(item["description"]).strip()
    sizes = item.get("sizes")
    if isinstance(sizes, list) and sizes:
        row["sizes"] = [str(s) for s in sizes]
    size_prices = item.get("size_prices")
    if isinstance(size_prices, dict) and size_prices:
        converted = {}
        for size, dollars in size_prices.items():
            c = _cents(dollars)
            if c is not None:
                converted[str(size)] = c
        if converted:
            row["size_prices"] = converted
    topping = _cents(item.get("topping_price"))
    if topping is not None:
        row["topping_price_cents"] = topping
    mods = item.get("modifications")
    if isinstance(mods, list) and mods:
        row["modifications"] = [str(m) for m in mods]
    return row


# ── reads ────────────────────────────────────────────────────────────────

def _sorted(rows: list[dict]) -> list[dict]:
    return sorted(rows, key=lambda r: (
        r.get("position") is None,
        r.get("position") or 0,
        (r.get("name") or "").lower(),
    ))


async def list_items(db, merchant_id: str, *, needs_review: bool | None = None) -> list[dict]:
    filters = {"merchant_id": f"eq.{merchant_id}"}
    if needs_review is not None:
        filters["needs_review"] = f"is.{str(needs_review).lower()}"
    rows = await db.select("menu_items", filters=filters, limit=1000)
    return _sorted(rows or [])


def agent_menu(rows: list[dict]) -> list[dict]:
    """Published, non-sold-out items in agent shape, deduped by name (first
    wins in position order). This IS the JSONB mirror payload."""
    out: list[dict] = []
    seen: set[str] = set()
    for row in _sorted(rows):
        if not row.get("published") or row.get("sold_out"):
            continue
        key = (row.get("name") or "").strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(to_agent_shape(row))
    return out


def sold_out_names(rows: list[dict]) -> list[str]:
    """Published-but-sold-out item names, for the prompt's SOLD OUT section."""
    out, seen = [], set()
    for row in _sorted(rows):
        if not row.get("published") or not row.get("sold_out"):
            continue
        name = (row.get("name") or "").strip()
        if name and name.lower() not in seen:
            seen.add(name.lower())
            out.append(name)
    return out


async def get_menu_for_agent(db, merchant_id: str) -> tuple[list[dict], list[str]]:
    """(available items in agent shape, sold-out names) for the live prompt."""
    rows = await list_items(db, merchant_id)
    return agent_menu(rows), sold_out_names(rows)


# ── write-through mirror ─────────────────────────────────────────────────

async def mirror_to_config(db, merchant_id: str, rows: list[dict] | None = None) -> list[dict]:
    """Rewrite phone_agent_config.menu_items from the store.

    THE COMPAT CONTRACT: after any store mutation the JSONB blob equals the
    published/non-sold-out agent-shape projection, so every legacy reader
    (TwiML prompt, wizard hydration, merchant_config fallback) stays correct
    without knowing the store exists.
    """
    if rows is None:
        rows = await list_items(db, merchant_id)
    menu = agent_menu(rows)
    payload = {"menu_items": menu, "updated_at": _now()}
    existing = await db.select(
        "phone_agent_config", filters={"merchant_id": f"eq.{merchant_id}"}, limit=1)
    if existing:
        await db.update("phone_agent_config", payload,
                        filters={"merchant_id": f"eq.{merchant_id}"})
    else:
        await db.insert("phone_agent_config", {"merchant_id": merchant_id, **payload})
    return menu


# ── migrate-on-write ─────────────────────────────────────────────────────

async def import_jsonb_menu(db, merchant_id: str) -> int:
    """When a merchant still lives in JSONB-only world and touches the new
    menu UI, import their phone_agent_config.menu_items into the store as
    published manual rows. No-op when store rows already exist. Returns the
    number of rows imported."""
    existing = await db.select(
        "menu_items", filters={"merchant_id": f"eq.{merchant_id}"}, limit=1)
    if existing:
        return 0
    config = await db.select(
        "phone_agent_config", filters={"merchant_id": f"eq.{merchant_id}"}, limit=1)
    legacy = (config[0].get("menu_items") if config else None) or []
    rows = []
    seen: set[str] = set()
    for pos, item in enumerate(legacy):
        if not isinstance(item, dict):
            continue
        row = from_agent_shape(item, source="manual")
        key = row["name"].lower()
        if not row["name"] or key in seen:
            continue
        seen.add(key)
        row.update({
            "merchant_id": merchant_id, "published": True,
            "needs_review": False, "sold_out": False, "position": pos,
        })
        rows.append(row)
    if rows:
        await db.insert("menu_items", rows)
        logger.info("menu_store: imported %d JSONB items for %s", len(rows), merchant_id)
    return len(rows)


# ── ingestion (all four paths land here) ─────────────────────────────────

async def ingest_items(db, merchant_id: str, items: list[dict], *, source: str) -> dict:
    """Land ingested items in the store behind the review gate.

    ``items`` are agent-shape-ish dicts (dollars) optionally carrying
    ``source_external_id`` (POS) and ``confidence`` (LLM/OCR, 0..1).

    Rules ("a menu that quotes wrong prices is worse than no menu"):
      - scrape/csv/photo → published=false, needs_review=true (never live)
      - pos (trusted)    → published=true, needs_review only when price missing
      - an incoming item matching an already-published row is skipped for
        untrusted sources (never clobber a live price with a guess); POS
        updates its own rows (fresh catalog wins).
    """
    if source not in VALID_SOURCES:
        raise ValueError(f"invalid source: {source}")
    trusted = source == "pos"
    await import_jsonb_menu(db, merchant_id)  # migrate-on-write
    existing = await list_items(db, merchant_id)
    by_key = {((r.get("name") or "").strip().lower(),
               (r.get("source_external_id") or "")): r for r in existing}
    by_name: dict[str, dict] = {}
    for r in existing:
        by_name.setdefault((r.get("name") or "").strip().lower(), r)

    inserted = updated = skipped = review_count = 0
    seen: set[tuple[str, str]] = set()
    for item in items:
        row = from_agent_shape(item, source=source)
        if not row["name"]:
            continue
        ext_id = str(item.get("source_external_id") or "").strip()
        key = (row["name"].lower(), ext_id)
        if key in seen:
            continue
        seen.add(key)
        if ext_id:
            row["source_external_id"] = ext_id
        confidence = item.get("confidence")
        if isinstance(confidence, (int, float)):
            row["confidence"] = max(0.0, min(1.0, float(confidence)))

        match = by_key.get(key) or by_name.get(row["name"].lower())
        if trusted:
            row["published"] = True
            row["needs_review"] = not row.get("price_cents") and not row.get("size_prices")
        else:
            row["published"] = False
            row["needs_review"] = True

        if match:
            if not trusted and match.get("published"):
                skipped += 1  # never shadow a live item with an unreviewed guess
                continue
            patch = {k: v for k, v in row.items() if k != "source"}
            patch["updated_at"] = _now()
            await db.update("menu_items", patch, filters={
                "id": f"eq.{match['id']}", "merchant_id": f"eq.{merchant_id}"})
            updated += 1
        else:
            row["merchant_id"] = merchant_id
            await db.insert("menu_items", row)
            inserted += 1
        if row["needs_review"]:
            review_count += 1

    if trusted and (inserted or updated):
        await mirror_to_config(db, merchant_id)
    logger.info("menu_store ingest[%s] %s: +%d ~%d skip=%d review=%d",
                source, merchant_id, inserted, updated, skipped, review_count)
    return {"inserted": inserted, "updated": updated,
            "skipped_existing": skipped, "needs_review": review_count}


# ── review / manage ──────────────────────────────────────────────────────

_EDITABLE = ("name", "description", "category", "sizes", "modifications", "position")


def _edit_patch(edits: dict) -> dict:
    """UI edit dict (dollars) → store column patch (cents)."""
    patch: dict[str, Any] = {}
    for field in _EDITABLE:
        if field in edits and edits[field] is not None:
            patch[field] = edits[field]
    if "price" in edits:
        patch["price_cents"] = _cents(edits.get("price"))
    if "price_cents" in edits:
        patch["price_cents"] = edits.get("price_cents")
    if "size_prices" in edits and isinstance(edits["size_prices"], dict):
        patch["size_prices"] = {
            str(k): c for k, v in edits["size_prices"].items()
            if (c := _cents(v)) is not None
        }
    if "topping_price" in edits:
        patch["topping_price_cents"] = _cents(edits.get("topping_price"))
    if "sold_out" in edits:
        patch["sold_out"] = bool(edits["sold_out"])
    return patch


async def confirm_items(db, merchant_id: str, confirmations: list[dict]) -> int:
    """Review screen accept: apply per-item edits and publish. Each entry is
    {id, name?, price?, category?, ...}. Returns the number published."""
    published = 0
    for entry in confirmations:
        item_id = str(entry.get("id") or "").strip()
        if not item_id:
            continue
        patch = _edit_patch(entry)
        patch.update({"published": True, "needs_review": False, "updated_at": _now()})
        await db.update("menu_items", patch, filters={
            "id": f"eq.{item_id}", "merchant_id": f"eq.{merchant_id}"})
        published += 1
    await mirror_to_config(db, merchant_id)
    return published


async def update_item(db, merchant_id: str, item_id: str, edits: dict) -> dict:
    """Inline edit / sold-out toggle. Mirrors after every change so sold-out
    propagates instantly to the agent prompt and the public page."""
    patch = _edit_patch(edits)
    if not patch:
        return {"updated": False}
    patch["updated_at"] = _now()
    await db.update("menu_items", patch, filters={
        "id": f"eq.{item_id}", "merchant_id": f"eq.{merchant_id}"})
    await mirror_to_config(db, merchant_id)
    return {"updated": True}


async def delete_item(db, merchant_id: str, item_id: str) -> None:
    await db.delete("menu_items", filters={
        "id": f"eq.{item_id}", "merchant_id": f"eq.{merchant_id}"})
    await mirror_to_config(db, merchant_id)


async def replace_menu_from_agent_items(db, merchant_id: str, items: list[dict]) -> bool:
    """Write-through for the legacy save path (POST /api/phone/config with
    menu_items): once a merchant has store rows, the wizard's full-menu save
    must update the store too or the next mirror would clobber their edits.

    Matches by name: existing rows get price/category updates (fields the
    wizard doesn't carry — sizes, description — are preserved), new names are
    inserted as manual, and published rows missing from a NON-EMPTY payload
    are deleted (the wizard list is authoritative). No store rows → returns
    False and the caller keeps legacy JSONB-only behavior.
    """
    existing = await list_items(db, merchant_id)
    if not existing:
        return False
    incoming: dict[str, dict] = {}
    for pos, item in enumerate(items or []):
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if name and name.lower() not in incoming:
            incoming[name.lower()] = {**item, "position": pos}
    by_name: dict[str, dict] = {}
    for r in existing:
        by_name.setdefault((r.get("name") or "").strip().lower(), r)

    for key, item in incoming.items():
        match = by_name.get(key)
        if match:
            patch: dict[str, Any] = {"position": item["position"], "updated_at": _now()}
            price_cents = _cents(item.get("price"))
            if price_cents is not None:
                patch["price_cents"] = price_cents
            if item.get("category"):
                patch["category"] = str(item["category"]).strip()
            await db.update("menu_items", patch, filters={
                "id": f"eq.{match['id']}", "merchant_id": f"eq.{merchant_id}"})
        else:
            row = from_agent_shape(item, source="manual")
            row.update({"merchant_id": merchant_id, "published": True,
                        "needs_review": False, "position": item["position"]})
            await db.insert("menu_items", row)
    if incoming:  # never nuke the store on an empty payload
        for key, row in by_name.items():
            if key not in incoming and row.get("published"):
                await db.delete("menu_items", filters={
                    "id": f"eq.{row['id']}", "merchant_id": f"eq.{merchant_id}"})
    await mirror_to_config(db, merchant_id)
    return True


# ── public hosted menu (/m/{slug}) ───────────────────────────────────────

async def ensure_public_menu(db, merchant_id: str, display_name: str = "") -> dict:
    """Create/publish the merchant's public menu page metadata; auto-generates
    a unique slug on first publish (website_scraper.generate_slug pattern)."""
    from .website_scraper import generate_slug

    rows = await db.select(
        "merchant_menus", filters={"merchant_id": f"eq.{merchant_id}"}, limit=1)
    if rows and rows[0].get("public_slug"):
        row = rows[0]
        if not row.get("published") or (display_name and display_name != row.get("display_name")):
            patch = {"published": True, "updated_at": _now()}
            if display_name:
                patch["display_name"] = display_name
            await db.update("merchant_menus", patch,
                            filters={"merchant_id": f"eq.{merchant_id}"})
            row = {**row, **patch}
        return row

    base = generate_slug(display_name or merchant_id)
    slug = base
    for attempt in range(2, 30):
        taken = await db.select(
            "merchant_menus", filters={"public_slug": f"eq.{slug}"}, limit=1)
        if not taken:
            break
        slug = f"{base}-{attempt}"
    row = {"merchant_id": merchant_id, "public_slug": slug,
           "display_name": display_name or "", "published": True, "updated_at": _now()}
    if rows:
        await db.update("merchant_menus", row,
                        filters={"merchant_id": f"eq.{merchant_id}"})
    else:
        await db.insert("merchant_menus", row)
    return row


async def get_public_menu(db, slug: str) -> Optional[dict]:
    """Published menu payload for GET /api/menu/public/{slug}; None → 404."""
    menus = await db.select(
        "merchant_menus",
        filters={"public_slug": f"eq.{slug}", "published": "is.true"}, limit=1)
    if not menus:
        return None
    menu = menus[0]
    rows = await list_items(db, menu["merchant_id"])
    items, seen = [], set()
    for row in _sorted(rows):
        if not row.get("published"):
            continue
        key = (row.get("name") or "").strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        items.append({**to_agent_shape(row), "sold_out": bool(row.get("sold_out"))})
    return {
        "slug": slug,
        "business_name": menu.get("display_name") or "",
        "items": items,
        "updated_at": menu.get("updated_at"),
    }
