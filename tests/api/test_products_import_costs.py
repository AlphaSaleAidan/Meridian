"""
Regression tests for POST /api/dashboard/products/import-costs/{org_id}
(src/api/routes/dashboard.py::import_product_costs).

Covers: header-flexible CSV parsing (name/item/product × cost/unit_cost/
price_paid/unit price), stock-up rows (total + quantity → unit cost),
exact/prefix/substring name matching, unmatched reporting, per-product
dedupe, and the 1 MB / 2000-row caps.

Convention (see test_notifications_exception_handling.py): endpoints are
called directly with a fake db (AsyncMock) and a stub Request — no
pytest-asyncio, no HTTP server.

Run:
    cd <repo> && python -m pytest tests/api/test_products_import_costs.py -v
"""
from __future__ import annotations

import asyncio
import os
import sys
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

# Ensure the src package is importable when running from the repo root.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.api.routes.dashboard import (  # noqa: E402
    _MAX_COST_CSV_ROWS,
    _match_product,
    _money_to_cents,
    _parse_cost_csv,
    import_product_costs,
)

VALID_ORG = "biz_9f349894e8aa498081fa7e2af8e42f80"

CATALOG = [
    {"id": "p-latte", "name": "Latte", "cost_cents": None},
    {"id": "p-croissant", "name": "Butter Croissant", "cost_cents": None},
    {"id": "p-espresso", "name": "Espresso", "cost_cents": 40},
    {"id": "p-espresso-double", "name": "Espresso Doppio", "cost_cents": None},
]


def _run(coro):
    """Fresh event loop per call — keeps the suite pytest-asyncio-free."""
    return asyncio.run(coro)


class FakeRequest:
    """Just enough of starlette.Request for the endpoint: headers + body/form."""

    def __init__(self, body: bytes, content_type: str = "text/csv", form: dict | None = None):
        self.headers = {"content-type": content_type}
        self._body = body
        self._form = form or {}

    async def body(self) -> bytes:
        return self._body

    async def form(self) -> dict:
        return self._form


class FakeUpload:
    def __init__(self, data: bytes):
        self._data = data

    async def read(self) -> bytes:
        return self._data


def _fake_db(products: list[dict] | None = None):
    db = AsyncMock()
    db.get_products = AsyncMock(return_value=products if products is not None else list(CATALOG))
    db.update = AsyncMock(return_value=None)
    return db


def _import(csv_text: str, db=None, **req_kwargs):
    db = db or _fake_db()
    req = FakeRequest(csv_text.encode(), **req_kwargs)
    return _run(import_product_costs(org_id=VALID_ORG, request=req, db=db)), db


def _updated_costs(db) -> dict[str, int]:
    """{product_id: cost_cents} from every db.update("products", ...) call."""
    out = {}
    for call in db.update.await_args_list:
        table, fields = call.args[0], call.args[1]
        if table != "products":
            continue
        pid = call.kwargs["filters"]["id"].removeprefix("eq.")
        out[pid] = fields["cost_cents"]
    return out


# ─── Money parsing ───────────────────────────────────────────────────────

@pytest.mark.parametrize("raw,expected", [
    ("1.50", 150),
    ("$1,234.50", 123450),
    (" 2 ", 200),
    ("", None),
    (None, None),
    ("n/a", None),
    ("-3.00", None),  # negative costs rejected
])
def test_money_to_cents(raw, expected):
    assert _money_to_cents(raw) == expected


# ─── Header-flexible parsing ─────────────────────────────────────────────

@pytest.mark.parametrize("header", [
    "name,cost",
    "Item,Unit_Cost",
    "Product,Price Paid",
    "product name,unit price",
    "ITEM NAME,Cost Per Unit",
])
def test_header_variants_parse(header):
    rows = _parse_cost_csv(f"{header}\nLatte,1.25\n")
    assert rows == [{"name": "Latte", "cost_cents": 125, "line": 2}]


def test_stockup_rows_total_over_quantity():
    """Stock-up shape: no unit-cost column; cost = total / quantity."""
    rows = _parse_cost_csv(
        "item,quantity,total\n"
        "Latte,10,$15.00\n"          # → 150
        "Butter Croissant,24,30.00\n"  # → 125
    )
    assert rows[0]["cost_cents"] == 150
    assert rows[1]["cost_cents"] == 125


def test_unit_cost_preferred_over_total_quantity():
    """When both a unit-cost and total+quantity are present, the explicit
    unit cost wins; total/qty only backfills rows missing a unit cost."""
    rows = _parse_cost_csv(
        "item,unit cost,quantity,total\n"
        "Latte,1.10,10,99.00\n"   # explicit unit cost → 110, not 990
        "Espresso,,4,2.00\n"       # blank unit cost → 200/4 = 50
    )
    assert rows[0]["cost_cents"] == 110
    assert rows[1]["cost_cents"] == 50


def test_rows_without_name_or_cost_are_skipped():
    rows = _parse_cost_csv(
        "name,cost\n"
        ",1.00\n"        # no name
        "Latte,\n"       # no cost
        "Latte,zero\n"   # unparseable
        "Latte,0\n"      # zero cost → skipped
        "\n"              # blank line
        "Espresso,0.40\n"
    )
    assert rows == [{"name": "Espresso", "cost_cents": 40, "line": 7}]


def test_missing_name_column_422():
    with pytest.raises(HTTPException) as exc:
        _parse_cost_csv("sku,cost\nX1,1.00\n")
    assert exc.value.status_code == 422


def test_missing_cost_column_422():
    with pytest.raises(HTTPException) as exc:
        _parse_cost_csv("name,category\nLatte,drinks\n")
    assert exc.value.status_code == 422


def test_row_cap_413():
    body = "name,cost\n" + "".join(
        f"Item {i},1.00\n" for i in range(_MAX_COST_CSV_ROWS + 1)
    )
    with pytest.raises(HTTPException) as exc:
        _parse_cost_csv(body)
    assert exc.value.status_code == 413


# ─── Name matching ───────────────────────────────────────────────────────

def test_match_exact_case_insensitive():
    by_name = {(p["name"]).lower(): p for p in CATALOG}
    assert _match_product("lAtTe", CATALOG, by_name)["id"] == "p-latte"


def test_match_prefix_fallback():
    by_name = {(p["name"]).lower(): p for p in CATALOG}
    # "Butter Croissant (dozen)" starts with the catalog name.
    assert _match_product("Butter Croissant (dozen)", CATALOG, by_name)["id"] == "p-croissant"


def test_match_substring_fallback_prefers_most_specific():
    by_name = {(p["name"]).lower(): p for p in CATALOG}
    # Substring tier: "Doppio" appears inside "Espresso Doppio" only.
    assert _match_product("doppio", CATALOG, by_name)["id"] == "p-espresso-double"


def test_exact_match_beats_prefix():
    by_name = {(p["name"]).lower(): p for p in CATALOG}
    # "Espresso" is an exact name AND a prefix of "Espresso Doppio" —
    # exact must win.
    assert _match_product("Espresso", CATALOG, by_name)["id"] == "p-espresso"


def test_no_match_returns_none():
    by_name = {(p["name"]).lower(): p for p in CATALOG}
    assert _match_product("Kombucha", CATALOG, by_name) is None


# ─── Endpoint: end-to-end over the db seam ──────────────────────────────

def test_import_updates_matched_and_reports_unmatched():
    result, db = _import(
        "name,cost\n"
        "latte,$1.25\n"
        "Butter Croissant,0.90\n"
        "Kombucha,2.00\n"   # not in catalog
    )
    assert result["matched"] == 2
    assert result["updated"] == 2
    assert result["unmatched"] == ["Kombucha"]
    assert result["total_rows"] == 3
    assert _updated_costs(db) == {"p-latte": 125, "p-croissant": 90}


def test_import_dedupes_repeat_rows_last_wins():
    """A stock-up sheet may list the same product twice — one UPDATE per
    product, last row wins."""
    result, db = _import(
        "item,quantity,total\n"
        "Latte,10,10.00\n"   # 100
        "Latte,10,20.00\n"   # 200 ← wins
    )
    assert result["matched"] == 2
    assert result["updated"] == 1
    assert _updated_costs(db) == {"p-latte": 200}


def test_import_update_is_org_scoped():
    _, db = _import("name,cost\nLatte,1.00\n")
    call = db.update.await_args_list[0]
    assert call.kwargs["filters"]["org_id"] == f"eq.{VALID_ORG}"
    assert "updated_at" in call.args[1]


def test_import_multipart_field():
    db = _fake_db()
    req = FakeRequest(
        b"", content_type="multipart/form-data; boundary=x",
        form={"file": FakeUpload(b"name,cost\nLatte,1.00\n")},
    )
    result = _run(import_product_costs(org_id=VALID_ORG, request=req, db=db))
    assert result["updated"] == 1
    assert _updated_costs(db) == {"p-latte": 100}


def test_import_empty_body_400():
    with pytest.raises(HTTPException) as exc:
        _import("")
    assert exc.value.status_code == 400


def test_import_size_cap_413():
    with pytest.raises(HTTPException) as exc:
        _import("name,cost\n" + "x" * (1024 * 1024))
    assert exc.value.status_code == 413


def test_import_invalid_org_id_422():
    db = _fake_db()
    req = FakeRequest(b"name,cost\nLatte,1.00\n")
    with pytest.raises(HTTPException) as exc:
        _run(import_product_costs(org_id="not-an-org", request=req, db=db))
    assert exc.value.status_code == 422


def test_import_no_usable_rows_soft_returns():
    result, db = _import("name,cost\nLatte,\n")
    assert result["matched"] == 0
    assert result["updated"] == 0
    db.update.assert_not_awaited()
