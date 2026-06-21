"""
CPA Handoff ("Taxes & Expenses") backend tests — no live DB.

Strategy (mirrors the repo's "call with fakes" style, but here via FastAPI
TestClient so the full router + Pydantic validation + responses are exercised):

  * A FakeDB implements the subset of SupabaseREST used by cpa.py
    (select/insert/delete) over in-memory lists, seeded with phone_orders,
    cpa_expenses, and (after a bank connect) cpa_transactions.
  * `src.api.routes.cpa._get_db` is monkeypatched to return the FakeDB, and the
    router-level `require_org_access` dependency is overridden to a no-op so we
    don't need a live Supabase session.
  * Demo mode for the bank feed is forced by clearing PLAID_* env, so
    bank_provider returns synthetic transactions.

Run:  .venv-test/bin/python -m pytest tests/test_cpa.py -v
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Force demo mode for the bank provider (no Plaid keys) BEFORE importing the app.
os.environ.pop("PLAID_CLIENT_ID", None)
os.environ.pop("PLAID_SECRET", None)

import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import src.api.routes.cpa as cpa  # noqa: E402
from src.api.routes.cpa import router, _get_db  # noqa: E402
from src.api.auth import require_org_access  # noqa: E402

ORG = "168b6df2-e9af-4b00-8fec-51e51149ff19"
OTHER_ORG = "00000000-0000-4000-8000-000000000abc"
YEAR = 2026


# ─── In-memory fake DB ───────────────────────────────────────────────────────

def _match(row: dict, filters: dict) -> bool:
    for col, expr in filters.items():
        op, _, val = expr.partition(".")
        cur = row.get(col)
        s = "" if cur is None else str(cur)
        if op == "eq":
            if s != val:
                return False
        elif op == "gte":
            if s < val:
                return False
        elif op == "lte":
            if s > val:
                return False
        elif op == "lt":
            if not (s < val):
                return False
        else:
            raise AssertionError(f"unsupported op {op!r}")
    return True


class FakeDB:
    def __init__(self):
        self.tables: dict[str, list[dict]] = {
            "phone_orders": [],
            "cpa_expenses": [],
            "cpa_bank_connections": [],
            "cpa_transactions": [],
        }
        self._auto = 0

    def _next_id(self) -> str:
        self._auto += 1
        # Valid-shaped UUID so _UUID_RE accepts it on delete.
        return f"00000000-0000-4000-8000-{self._auto:012d}"

    async def select(self, table, columns="*", filters=None, order=None,
                     limit=None, offset=None):
        rows = [r for r in self.tables.get(table, []) if _match(r, filters or {})]
        if order:
            col, _, direction = order.partition(".")
            rows.sort(key=lambda r: (r.get(col) is None, r.get(col)),
                      reverse=(direction == "desc"))
        if offset:
            rows = rows[offset:]
        if limit:
            rows = rows[:limit]
        return [dict(r) for r in rows]

    async def insert(self, table, data, return_data=True):
        rows = data if isinstance(data, list) else [data]
        out = []
        for r in rows:
            row = dict(r)
            row.setdefault("id", self._next_id())
            row.setdefault("created_at", "2026-06-21T00:00:00Z")
            self.tables.setdefault(table, []).append(row)
            out.append(dict(row))
        return out

    async def delete(self, table, filters):
        before = len(self.tables.get(table, []))
        self.tables[table] = [
            r for r in self.tables.get(table, []) if not _match(r, filters)
        ]
        return before != len(self.tables[table])


@pytest.fixture()
def db():
    fake = FakeDB()
    # Seed two 2026 phone orders ($120.00 rev + $15.60 tax; $80.00 rev + $10.40 tax)
    # and one 2025 order that must be excluded by the year filter.
    fake.tables["phone_orders"] = [
        {"id": "o1", "merchant_id": ORG, "total": "120.00", "tax": "15.60",
         "created_at": "2026-03-04T12:00:00Z"},
        {"id": "o2", "merchant_id": ORG, "total": "80.00", "tax": "10.40",
         "created_at": "2026-07-15T18:30:00Z"},
        {"id": "o3", "merchant_id": ORG, "total": "999.00", "tax": "99.00",
         "created_at": "2025-12-31T23:59:00Z"},
    ]
    # Seed one manual expense ($482.30) in 2026.
    fake.tables["cpa_expenses"] = [
        {"id": "e1", "org_id": ORG, "expense_date": "2026-03-10",
         "category": "supplies", "vendor": "Costco Business",
         "amount_cents": 48230, "note": "paper goods"},
    ]
    return fake


@pytest.fixture()
def client(db):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[require_org_access] = lambda: None
    app.dependency_overrides[_get_db] = lambda: db
    cpa._get_db_orig = cpa._get_db
    # _load_year_data / endpoints import _db_instance lazily via _get_db Depends,
    # which is overridden above; nothing else reaches the real singleton.
    with TestClient(app) as c:
        yield c


# ─── Summary math ────────────────────────────────────────────────────────────

def test_summary_revenue_tax_expenses_net(client):
    r = client.get("/api/cpa/summary", params={"org_id": ORG, "year": YEAR})
    assert r.status_code == 200, r.text
    d = r.json()
    # 120.00 + 80.00 = 200.00 (2025 order excluded)
    assert d["revenue_cents"] == 20000
    assert d["sales_tax_collected_cents"] == 2600  # 15.60 + 10.40
    assert d["order_count"] == 2
    # Only the manual expense so far (no bank txns yet).
    assert d["expenses_total_cents"] == 48230
    assert d["net_cents"] == 20000 - 48230
    assert d["currency"] == "CAD"
    assert d["disclaimer"] == cpa.CPA_DISCLAIMER
    assert len(d["monthly"]) == 12
    # March bucket carries the $120 order + $482.30 expense.
    march = next(m for m in d["monthly"] if m["month"] == "2026-03")
    assert march["revenue_cents"] == 12000
    assert march["expenses_total_cents"] == 48230


def test_disclaimer_byte_identical_to_design_doc():
    expected = (
        "We prepare, your CPA files. Meridian organizes your sales and expense records into\n"
        "a CPA-ready summary. These figures are a starting point for your accountant — Meridian\n"
        "does not calculate income tax, file returns, or provide tax advice. Confirm all numbers\n"
        "with your CPA before filing."
    )
    assert cpa.CPA_DISCLAIMER == expected


# ─── Expenses CRUD ───────────────────────────────────────────────────────────

def test_expenses_list_and_create_and_delete(client, db):
    # list (seeded one)
    r = client.get("/api/cpa/expenses", params={"org_id": ORG, "year": YEAR})
    assert r.status_code == 200
    assert r.json()["total"] == 1

    # create
    body = {"org_id": ORG, "expense_date": "2026-05-01", "category": "rent",
            "vendor": "City Property", "amount_cents": 250000, "note": "May rent"}
    r = client.post("/api/cpa/expenses", params={"org_id": ORG}, json=body)
    assert r.status_code == 200, r.text
    new_id = r.json()["expense"]["id"]
    assert r.json()["expense"]["amount_cents"] == 250000

    # list now two
    r = client.get("/api/cpa/expenses", params={"org_id": ORG, "year": YEAR})
    assert r.json()["total"] == 2

    # summary expense total reflects both
    r = client.get("/api/cpa/summary", params={"org_id": ORG, "year": YEAR})
    assert r.json()["expenses_total_cents"] == 48230 + 250000

    # delete
    r = client.delete(f"/api/cpa/expenses/{new_id}", params={"org_id": ORG})
    assert r.status_code == 200 and r.json()["ok"] is True
    r = client.get("/api/cpa/expenses", params={"org_id": ORG, "year": YEAR})
    assert r.json()["total"] == 1


def test_create_expense_rejects_bad_category(client):
    body = {"org_id": ORG, "expense_date": "2026-05-01", "category": "yacht",
            "vendor": "X", "amount_cents": 100}
    r = client.post("/api/cpa/expenses", params={"org_id": ORG}, json=body)
    assert r.status_code == 422


def test_create_expense_rejects_nonpositive_amount(client):
    body = {"org_id": ORG, "expense_date": "2026-05-01", "category": "rent",
            "vendor": "X", "amount_cents": 0}
    r = client.post("/api/cpa/expenses", params={"org_id": ORG}, json=body)
    assert r.status_code == 422


def test_delete_rejects_bad_uuid(client):
    r = client.delete("/api/cpa/expenses/not-a-uuid", params={"org_id": ORG})
    assert r.status_code == 400


def test_create_expense_uses_query_org_not_body(client, db):
    # Body claims OTHER_ORG, query says ORG. Row must be written to ORG.
    body = {"org_id": OTHER_ORG, "expense_date": "2026-06-01", "category": "fees",
            "vendor": "Spoof", "amount_cents": 999}
    r = client.post("/api/cpa/expenses", params={"org_id": ORG}, json=body)
    assert r.status_code == 200
    written = [e for e in db.tables["cpa_expenses"] if e["vendor"] == "Spoof"]
    assert written and written[0]["org_id"] == ORG


# ─── CSV export ──────────────────────────────────────────────────────────────

def test_export_csv_contains_rows(client):
    r = client.get("/api/cpa/export.csv", params={"org_id": ORG, "year": YEAR})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"]
    body = r.text
    assert "Meridian CPA Handoff" in body
    assert "Revenue,200.00" in body
    assert "Sales tax collected,26.00" in body
    assert "Costco Business" in body            # expense detail row
    assert "Per-card spend" in body
    assert "Bank/card transactions detail" in body


# ─── HTML export ─────────────────────────────────────────────────────────────

def test_export_html_is_valid_with_disclaimer(client):
    r = client.get("/api/cpa/export.html", params={"org_id": ORG, "year": YEAR})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    html = r.text
    assert html.startswith("<!DOCTYPE html>")
    assert html.rstrip().endswith("</html>")
    assert "<title>Meridian CPA Handoff" in html
    assert "CPA Handoff" in html
    # Disclaimer present (first sentence; newlines become <br>).
    assert "We prepare, your CPA files." in html
    # Five section tables: summary + monthly + per-card + expenses + transactions.
    assert html.count("<table") == 5


def test_export_html_has_all_sections(client):
    r = client.get("/api/cpa/export.html", params={"org_id": ORG, "year": YEAR})
    html = r.text
    for heading in ("Summary", "Monthly breakdown", "Per-card spend",
                    "Expenses detail", "Bank/card transactions detail"):
        assert f">{heading}</h2>" in html, heading


# ─── Bank connect (demo) + per-card breakdown ────────────────────────────────

def test_bank_link_token_demo(client):
    r = client.post("/api/cpa/bank/link-token", params={"org_id": ORG})
    assert r.status_code == 200
    d = r.json()
    assert d["demo"] is True
    assert d["link_token"]


def test_bank_connect_seeds_transactions_and_summary_updates(client, db):
    # before: no transactions, expenses_total is just the manual expense
    r = client.get("/api/cpa/summary", params={"org_id": ORG, "year": YEAR})
    base_expense = r.json()["expenses_total_cents"]
    assert base_expense == 48230
    assert r.json()["cards"] == []

    # connect (demo) → synthetic transactions seeded
    r = client.post("/api/cpa/bank/connect", params={"org_id": ORG},
                    json={"org_id": ORG, "public_token": "public-demo",
                          "institution_name": "RBC"})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["demo"] is True
    assert d["synced_transactions"] > 0
    assert d["connection"]["status"] == "connected"
    # access_ref/item_id are secret refs — must NOT be in the response
    assert "access_ref" not in d["connection"]
    assert "item_id" not in d["connection"]

    # transactions exist in the fake DB across the two synthetic cards
    txns = db.tables["cpa_transactions"]
    assert txns
    cards = {t["card_last4"] for t in txns}
    assert cards == {"4821", "9032"}

    # summary now includes debit transactions (non-transfer) in the expense total
    r = client.get("/api/cpa/summary", params={"org_id": ORG, "year": YEAR})
    d = r.json()
    assert d["expenses_total_cents"] > base_expense
    # per-card breakdown present, one entry per card, totals positive
    assert {c["card_last4"] for c in d["cards"]} == {"4821", "9032"}
    for c in d["cards"]:
        assert c["total_cents"] > 0
        assert c["txn_count"] >= 1
    # expenses_total == manual + sum of non-transfer debit txns
    debit_non_transfer = sum(
        t["amount_cents"] for t in txns
        if t["direction"] == "debit" and t["category"] != "transfer"
    )
    assert d["expenses_total_cents"] == 48230 + debit_non_transfer


def test_bank_connect_is_idempotent_on_resync(client, db):
    r1 = client.post("/api/cpa/bank/connect", params={"org_id": ORG},
                     json={"org_id": ORG, "public_token": "public-demo"})
    n_first = r1.json()["synced_transactions"]
    count_after_connect = len(db.tables["cpa_transactions"])
    assert n_first == count_after_connect

    # re-sync should add ZERO new rows (dedup on natural key)
    r2 = client.post("/api/cpa/bank/sync", params={"org_id": ORG, "year": YEAR})
    assert r2.status_code == 200
    assert r2.json()["new_transactions"] == 0
    assert len(db.tables["cpa_transactions"]) == count_after_connect


def test_bank_transactions_filter_by_card(client, db):
    client.post("/api/cpa/bank/connect", params={"org_id": ORG},
                json={"org_id": ORG, "public_token": "public-demo"})

    r_all = client.get("/api/cpa/bank/transactions", params={"org_id": ORG, "year": YEAR})
    assert r_all.status_code == 200
    total_all = r_all.json()["total"]
    assert total_all > 0

    r_one = client.get("/api/cpa/bank/transactions",
                       params={"org_id": ORG, "year": YEAR, "card_last4": "4821"})
    assert r_one.status_code == 200
    one = r_one.json()["transactions"]
    assert one and all(t["card_last4"] == "4821" for t in one)
    assert len(one) < total_all  # filtered subset


def test_bank_connections_list(client):
    client.post("/api/cpa/bank/connect", params={"org_id": ORG},
                json={"org_id": ORG, "public_token": "public-demo",
                      "institution_name": "Scotiabank"})
    r = client.get("/api/cpa/bank/connections", params={"org_id": ORG})
    assert r.status_code == 200
    d = r.json()
    assert d["total"] == 1
    assert d["connections"][0]["institution_name"] == "Scotiabank"
    assert "access_ref" not in d["connections"][0]
