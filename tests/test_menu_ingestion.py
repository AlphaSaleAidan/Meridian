"""
MENU INGESTION — CSV validation, scrape extraction parsing, API review gates.

Covers:
  1. CSV template parsing — good rows, per-row errors (bad price, malformed
     size_prices, missing name, duplicates), missing-header rejection.
  2. Scraper pure pieces — HTML → text/links, menu-link discovery (same-origin
     + hint words), LLM output normalization (confidence clamped, junk
     dropped), PDF text extraction unavailable in this env → None (the
     pdf_unsupported flag path).
  3. Ingestion routes land everything behind the review gate (never live),
     scrape failure surfaces a clean 422 (never partial-silent).
  4. Public endpoint: published → payload, unpublished/unknown → 404.

Run:  python -m pytest tests/test_menu_ingestion.py -v
"""
from __future__ import annotations

import io
import os
import sys

import pytest
from fastapi import HTTPException, UploadFile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("ENCRYPTION_KEY", "0" * 64)

from src.services import menu_scraper, menu_store  # noqa: E402
from src.services.menu_ingestion import CSV_TEMPLATE, MenuIngestError, parse_menu_csv  # noqa: E402

from tests.test_menu_store import MID, FakeDB, _run  # noqa: E402

SERVICE = {"kind": "service"}


# ── 1. CSV ───────────────────────────────────────────────────────────────

def test_csv_template_parses_cleanly():
    items, errors = parse_menu_csv(CSV_TEMPLATE)
    assert errors == []
    assert [i["name"] for i in items] == ["Margherita Pizza", "Caesar Salad", "Iced Latte"]
    pizza = items[0]
    assert pizza["sizes"] == ["medium", "large"]
    assert pizza["size_prices"] == {"medium": 14.0, "large": 18.0}
    assert items[1]["price"] == 9.5


def test_csv_per_row_errors_keep_good_rows():
    text = (
        "name,price,category,description,sizes,size_prices\n"
        "Good Item,9.50,Mains,,,\n"
        ",4.00,Mains,,,\n"                       # row 2: no name
        "Bad Price,abc,Mains,,,\n"               # row 3: unparseable price
        "Bad Sizes,,Pizzas,,m|l,m-14\n"          # row 4: malformed size_prices
        "Good Item,8.00,Mains,,,\n"              # row 5: duplicate name
        "Another Good,$12.00,Mains,,,\n"
    )
    items, errors = parse_menu_csv(text)
    assert [i["name"] for i in items] == ["Good Item", "Another Good"]
    assert items[1]["price"] == 12.0  # "$12.00" tolerated
    assert [e["row"] for e in errors] == [2, 3, 4, 5]
    assert "name is required" in errors[0]["error"]
    assert "not a number" in errors[1]["error"]
    assert "must look like" in errors[2]["error"]
    assert "duplicate" in errors[3]["error"]


def test_csv_missing_header_rejected():
    with pytest.raises(MenuIngestError):
        parse_menu_csv("Wings,12.00\nCoke,3.00\n")


# ── 2. scraper pieces ────────────────────────────────────────────────────

FIXTURE_HTML = """
<html><head><title>Tony's</title><style>.x{color:red}</style>
<script>var nope = 'not text';</script></head>
<body>
  <nav><a href="/about">About</a><a href="/menu">Our Menu</a>
       <a href="/order-online">Order Online</a>
       <a href="https://other-site.com/menu">Partner menu</a>
       <a href="/menu.pdf">Menu PDF</a></nav>
  <h1>Tony's Pizza</h1>
  <p>Cheese Pizza — medium $14 / large $18</p>
  <img src="/img/menu-board.jpg">
</body></html>
"""


def test_parse_page_text_links_images():
    text, links, images = menu_scraper.parse_page(FIXTURE_HTML)
    assert "Cheese Pizza" in text and "$14" in text
    assert "not text" not in text and "color:red" not in text
    assert "/menu" in links and "/img/menu-board.jpg" in images


def test_candidate_menu_links_same_origin_and_hints():
    _, links, _ = menu_scraper.parse_page(FIXTURE_HTML)
    out = menu_scraper.candidate_menu_links("https://tonys.example.com", links)
    assert out == [
        "https://tonys.example.com/menu",
        "https://tonys.example.com/order-online",
        "https://tonys.example.com/menu.pdf",
    ]  # /about skipped, cross-origin skipped


def test_parse_llm_items_normalizes():
    content = (
        '{"items": ['
        '{"name": "Pad Thai", "price": 15.5, "category": "Mains",'
        ' "description": "Rice noodles", "confidence": 0.95},'
        '{"name": "Spring Rolls", "price": null, "confidence": 1.7},'
        '{"name": "", "price": 4},'
        '{"name": "Hours: 9-5", "confidence": "high"}'
        ']}'
    )
    items = menu_scraper.parse_llm_items(content)
    assert [i["name"] for i in items] == ["Pad Thai", "Spring Rolls", "Hours: 9-5"]
    assert items[0]["price"] == 15.5 and items[0]["confidence"] == 0.95
    assert items[1]["confidence"] == 1.0          # clamped
    assert "price" not in items[1]                # null price dropped
    assert items[2]["confidence"] == 0.5          # non-numeric → default


def test_parse_llm_items_garbage_raises():
    with pytest.raises(menu_scraper.MenuScrapeError):
        menu_scraper.parse_llm_items("sorry, here is the menu: ...")


def test_pdf_text_handles_a_corrupt_pdf_either_way():
    """Never crash on a corrupt PDF — and say which kind of nothing it is.

    This asserted `is None` unconditionally, which only holds when no PDF
    library is installed. pypdf IS present in some environments (it arrives as
    a transitive dependency), and there a corrupt file takes the parse-failed
    branch and returns "". So the test passed or failed on what happened to be
    installed rather than on behaviour.

    The distinction is real and worth keeping: None means "we cannot read PDFs
    at all" and the caller flags pdf_unsupported; "" means "we read it and it
    was junk". Both are valid; crashing is not.
    """
    out = menu_scraper._pdf_to_text(b"%PDF-1.4 fake")
    assert out is None or out == "", f"expected None or empty, got {out!r}"


# ── 3. ingestion routes → review gate ────────────────────────────────────

def _patch_db(monkeypatch, db):
    import src.db as db_mod
    monkeypatch.setattr(db_mod, "_db_instance", db)


def test_scrape_route_lands_in_review(monkeypatch):
    from src.api.routes import menu_ingest
    from src.services import menu_scraper as scraper_mod

    db = FakeDB({"merchant_id": MID, "menu_items": []})
    _patch_db(monkeypatch, db)

    async def _fake_scrape(url):
        assert url == "https://tonys.example.com"
        return {"items": [{"name": "Pad Thai", "price": 15.5, "confidence": 0.9},
                          {"name": "Mystery", "confidence": 0.4}],
                "pages": [url], "flags": ["low_confidence_items"]}
    monkeypatch.setattr(scraper_mod, "scrape_menu", _fake_scrape)

    out = _run(menu_ingest.scrape_menu_from_website(
        MID, menu_ingest.ScrapeRequest(url="tonys.example.com"), principal=SERVICE))
    assert out["found"] == 2 and out["pending_review"] == 2
    assert "low_confidence_items" in out["flags"]
    assert all(not r["published"] for r in db.tables["menu_items"])  # never live


def test_scrape_route_failure_is_clean_422(monkeypatch):
    from src.api.routes import menu_ingest
    from src.services import menu_scraper as scraper_mod

    db = FakeDB()
    _patch_db(monkeypatch, db)

    async def _boom(url):
        raise scraper_mod.MenuScrapeError("Couldn't load that website: timeout")
    monkeypatch.setattr(scraper_mod, "scrape_menu", _boom)

    with pytest.raises(HTTPException) as exc:
        _run(menu_ingest.scrape_menu_from_website(
            MID, menu_ingest.ScrapeRequest(url="https://x.example.com"), principal=SERVICE))
    assert exc.value.status_code == 422
    assert "Couldn't load" in exc.value.detail
    assert db.tables["menu_items"] == []  # no partial writes


def test_csv_route_reports_row_errors(monkeypatch):
    from src.api.routes import menu_ingest

    db = FakeDB({"merchant_id": MID, "menu_items": []})
    _patch_db(monkeypatch, db)
    csv_bytes = (
        b"name,price,category,description,sizes,size_prices\n"
        b"Wings,12.00,Apps,,,\n"
        b"Bad,abc,Apps,,,\n"
    )
    upload = UploadFile(filename="menu.csv", file=io.BytesIO(csv_bytes))
    out = _run(menu_ingest.import_menu_csv(MID, file=upload, principal=SERVICE))
    assert out["found"] == 1 and out["pending_review"] == 1
    assert out["row_errors"] == [{"row": 2, "error": "price 'abc' is not a number"}]
    rows = db.tables["menu_items"]
    assert len(rows) == 1 and not rows[0]["published"] and rows[0]["source"] == "csv"


def test_photo_route_lands_in_review(monkeypatch):
    from src.api.routes import menu_ingest

    db = FakeDB({"merchant_id": MID, "menu_items": []})
    _patch_db(monkeypatch, db)

    async def _fake_photo(image_bytes, content_type):
        return [{"name": "Daily Special", "price": 11.0, "confidence": 0.6}], "vision"
    monkeypatch.setattr(menu_ingest, "extract_menu_from_photo", _fake_photo)

    upload = UploadFile(filename="menu.jpg", file=io.BytesIO(b"\xff\xd8fake"))
    out = _run(menu_ingest.import_menu_photo(MID, photo=upload, principal=SERVICE))
    assert out["found"] == 1 and out["pending_review"] == 1 and out["engine"] == "vision"
    assert not db.tables["menu_items"][0]["published"]


# ── 4. public endpoint ───────────────────────────────────────────────────

def test_public_endpoint_published_unpublished_404(monkeypatch):
    from src.api.routes import menu as menu_routes

    db = FakeDB({"merchant_id": MID, "menu_items": [{"name": "Wings", "price": 12.0}]})
    _patch_db(monkeypatch, db)
    _run(menu_store.import_jsonb_menu(db, MID))
    _run(menu_store.ensure_public_menu(db, MID, "Tony's Pizza"))

    out = _run(menu_routes.get_public_menu("tonys-pizza"))
    assert out["business_name"] == "Tony's Pizza"
    assert out["items"][0]["name"] == "Wings" and out["items"][0]["sold_out"] is False

    # Unpublish → 404 (page disappears immediately).
    _run(db.update("merchant_menus", {"published": False},
                   filters={"merchant_id": f"eq.{MID}"}))
    with pytest.raises(HTTPException) as exc:
        _run(menu_routes.get_public_menu("tonys-pizza"))
    assert exc.value.status_code == 404

    with pytest.raises(HTTPException) as exc404:
        _run(menu_routes.get_public_menu("never-existed"))
    assert exc404.value.status_code == 404
