"""
Menu ingestion helpers — CSV template/parser and photo extraction.

Both produce agent-shape-ish item dicts (dollars, optional confidence) that
``menu_store.ingest_items`` lands behind the review gate. Used by the
/api/menu ingestion routes and the legacy /api/phone/menu/* endpoints.
"""
from __future__ import annotations

import csv
import io
import logging

logger = logging.getLogger("meridian.services.menu_ingestion")


class MenuIngestError(RuntimeError):
    """Raised when an upload cannot be processed; message is UI-safe."""


# ── CSV ──────────────────────────────────────────────────────────────────
# Published template (GET /api/menu/csv-template). sizes are pipe-separated,
# size_prices are "size:dollars" pairs separated by semicolons.

CSV_COLUMNS = ("name", "price", "category", "description", "sizes", "size_prices")

CSV_TEMPLATE = (
    "name,price,category,description,sizes,size_prices\n"
    "Margherita Pizza,,Pizzas,San Marzano tomato and fresh basil,medium|large,medium:14;large:18\n"
    "Caesar Salad,9.50,Salads,Romaine with house dressing,,\n"
    "Iced Latte,4.75,Drinks,,small|large,small:4.75;large:5.75\n"
)

_MAX_NAME_LEN = 120
_MAX_ROWS = 1000


def _parse_price(raw: str, field: str):
    cleaned = raw.replace("$", "").replace(",", "").strip()
    try:
        value = float(cleaned)
    except ValueError:
        raise ValueError(f"{field} '{raw}' is not a number")
    if value < 0:
        raise ValueError(f"{field} cannot be negative")
    return round(value, 2)


def _parse_size_prices(raw: str) -> dict:
    """'medium:14;large:18' → {'medium': 14.0, 'large': 18.0} (dollars)."""
    out: dict[str, float] = {}
    for pair in raw.split(";"):
        pair = pair.strip()
        if not pair:
            continue
        if ":" not in pair:
            raise ValueError(f"size_prices entry '{pair}' must look like 'medium:14'")
        size, _, price = pair.partition(":")
        size = size.strip()
        if not size:
            raise ValueError(f"size_prices entry '{pair}' is missing the size name")
        out[size] = _parse_price(price, f"size_prices[{size}]")
    return out


def parse_menu_csv(text: str) -> tuple[list[dict], list[dict]]:
    """Validate a template-format CSV row by row.

    Returns (items, errors) where errors is [{row, error}] with 1-based data
    row numbers (header excluded). Bad rows are skipped, good rows kept, so
    the UI can show exactly which lines to fix.
    """
    reader = csv.DictReader(io.StringIO(text))
    header = [h.strip().lower() for h in (reader.fieldnames or [])]
    if "name" not in header:
        raise MenuIngestError(
            "first row must be a header row including a 'name' column — "
            "download the template from the CSV option")

    items: list[dict] = []
    errors: list[dict] = []
    seen: set[str] = set()
    for n, row in enumerate(reader, start=1):
        if n > _MAX_ROWS:
            errors.append({"row": n, "error": f"too many rows (max {_MAX_ROWS}); rest ignored"})
            break
        cells = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
        if not any(cells.values()):
            continue  # blank line
        try:
            name = cells.get("name", "")
            if not name:
                raise ValueError("name is required")
            if len(name) > _MAX_NAME_LEN:
                raise ValueError(f"name is too long (max {_MAX_NAME_LEN} chars)")
            if name.lower() in seen:
                raise ValueError(f"duplicate item name '{name}'")
            item: dict = {"name": name}
            if cells.get("price"):
                item["price"] = _parse_price(cells["price"], "price")
            if cells.get("category"):
                item["category"] = cells["category"][:60]
            if cells.get("description"):
                item["description"] = cells["description"][:300]
            if cells.get("sizes"):
                item["sizes"] = [s.strip() for s in cells["sizes"].split("|") if s.strip()]
            if cells.get("size_prices"):
                size_prices = _parse_size_prices(cells["size_prices"])
                if size_prices:
                    item["size_prices"] = size_prices
                    item.setdefault("sizes", list(size_prices.keys()))
            seen.add(name.lower())
            items.append(item)
        except ValueError as exc:
            errors.append({"row": n, "error": str(exc)})
    return items, errors


# ── Photo ────────────────────────────────────────────────────────────────

async def extract_menu_from_photo(image_bytes: bytes, content_type: str) -> tuple[list[dict], str]:
    """Photo of a printed menu → items. Prefers the wired vision model
    (menu_vision, gpt-4o) and falls back to the local PaddleOCR parser
    (documents/ocr_service, doc_type='menu') when vision isn't configured.

    Returns (items, engine). Items carry ``confidence`` so the review screen
    can amber-flag them — 0.6 for vision (no per-item score), 0.5 for OCR.
    Raises MenuIngestError when neither engine can run.
    """
    from .menu_vision import MenuVisionError, extract_menu_from_image

    try:
        items = await extract_menu_from_image(image_bytes, content_type)
        return [{**it, "confidence": 0.6} for it in items], "vision"
    except MenuVisionError as vision_exc:
        logger.info("menu photo: vision unavailable (%s) — trying OCR", vision_exc)
        items = _ocr_menu_photo(image_bytes)
        if items is None:
            raise MenuIngestError(str(vision_exc)) from vision_exc
        return items, "ocr"


def _ocr_menu_photo(image_bytes: bytes) -> list[dict] | None:
    """PaddleOCR fallback via ocr_service.parse_menu. None → OCR unavailable."""
    import tempfile

    from ..documents import ocr_service

    with tempfile.NamedTemporaryFile(suffix=".png") as tmp:
        tmp.write(image_bytes)
        tmp.flush()
        lines = ocr_service.extract_text(tmp.name)
    if not lines:
        return None
    parsed = ocr_service.parse_menu(lines)
    items = []
    for it in parsed.get("items", []):
        item: dict = {"name": it.get("name", ""), "confidence": 0.5}
        if it.get("price_cents"):
            item["price"] = round(it["price_cents"] / 100, 2)
        if it.get("category"):
            item["category"] = it["category"]
        if item["name"]:
            items.append(item)
    return items
