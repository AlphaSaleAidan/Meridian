"""
SUPPLEMENTARY MENU BUILDER (photo) — vision-extraction coverage.

The vision HTTP call is isolated in ``extract_menu_from_image`` so the parts
that carry the real logic — normalizing model output into the agent's
``{name, price?, category?}`` shape and *merging* a scanned menu onto an
existing one — are tested here with no network:

  1. normalize_items coerces messy model output (string prices, $/comma,
     ranges, missing names, over-long junk) into the canonical shape.
  2. merge_menu_items is supplementary: it appends new items, dedupes by
     case-insensitive name, and back-fills a missing price/category on an
     existing item (re-scanning a now-priced board enriches it).
  3. extract_menu_from_image fails closed with a clean MenuVisionError on a
     missing key or an unsupported image type — no network call attempted.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.services.menu_vision import (  # noqa: E402
    MenuVisionError,
    _coerce_price,
    extract_menu_from_image,
    merge_menu_items,
    normalize_items,
)


def test_coerce_price_variants():
    assert _coerce_price(12) == 12.0
    assert _coerce_price(12.509) == 12.51
    assert _coerce_price("$12.50") == 12.50
    assert _coerce_price("12,50") == 12.50
    assert _coerce_price("market") is None
    assert _coerce_price("") is None
    assert _coerce_price(None) is None
    assert _coerce_price(-5) is None


def test_normalize_drops_nameless_and_keeps_shape():
    raw = [
        {"name": "  Margherita Pizza ", "price": "$14.00", "category": "Mains"},
        {"name": "", "price": 9},                       # dropped: no name
        {"price": 5},                                    # dropped: no name
        {"name": "Water", "price": None, "category": ""},  # price/category omitted
        "not a dict",                                    # dropped
    ]
    items = normalize_items(raw)
    assert items == [
        {"name": "Margherita Pizza", "price": 14.0, "category": "Mains"},
        {"name": "Water"},
    ]


def test_normalize_non_list():
    assert normalize_items(None) == []
    assert normalize_items({"items": []}) == []


def test_merge_appends_and_dedupes_case_insensitive():
    existing = [{"name": "Fries", "price": 4.0, "category": "Sides"}]
    scanned = [
        {"name": "fries", "price": 4.0},        # dup (case-insensitive) -> not added
        {"name": "Onion Rings", "price": 5.5},  # new
    ]
    merged = merge_menu_items(existing, scanned)
    names = [m["name"] for m in merged]
    assert names == ["Fries", "Onion Rings"]
    # existing identity preserved (original casing + category kept)
    assert merged[0] == {"name": "Fries", "price": 4.0, "category": "Sides"}


def test_merge_backfills_missing_price_and_category():
    existing = [{"name": "Daily Soup"}]                       # no price yet
    scanned = [{"name": "daily soup", "price": 6.0, "category": "Starters"}]
    merged = merge_menu_items(existing, scanned)
    assert merged == [{"name": "Daily Soup", "price": 6.0, "category": "Starters"}]


def test_merge_does_not_mutate_inputs():
    existing = [{"name": "Cola"}]
    scanned = [{"name": "cola", "price": 2.5}]
    merge_menu_items(existing, scanned)
    assert existing == [{"name": "Cola"}]  # untouched


def test_merge_handles_empty_existing():
    assert merge_menu_items(None, [{"name": "Taco", "price": 3.0}]) == [
        {"name": "Taco", "price": 3.0}
    ]


@pytest.mark.asyncio
async def test_extract_requires_api_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    with pytest.raises(MenuVisionError, match="not configured"):
        await extract_menu_from_image(b"\xff\xd8\xff", "image/jpeg")


@pytest.mark.asyncio
async def test_extract_rejects_unsupported_type(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    with pytest.raises(MenuVisionError, match="unsupported image type"):
        await extract_menu_from_image(b"%PDF-1.4", "application/pdf")


@pytest.mark.asyncio
async def test_extract_rejects_empty_image(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    with pytest.raises(MenuVisionError, match="empty image"):
        await extract_menu_from_image(b"", "image/png")
