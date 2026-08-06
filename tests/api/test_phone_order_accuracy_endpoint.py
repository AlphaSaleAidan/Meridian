"""GET /api/phone/order-accuracy/{merchant_id} — org-scoped, read-only review queue.

Locks in:
  * org-membership is enforced (non-member → 403, before any data is read);
  * a member gets that merchant's mis-captured-order flags, newest first;
  * flagged_only=true (the default) asks the DB only for non-matching orders,
    and flagged_only=false widens it to every checked order;
  * the endpoint is READ-ONLY — the stub DB records zero writes, and nothing
    in this path can modify an order;
  * a malformed merchant_id is rejected (400).

Run: /root/Meridian/.venv/bin/python -m pytest tests/api/test_phone_order_accuracy_endpoint.py -v
"""
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import src.api.routes.phone_dashboard as pd  # noqa: E402

MERCHANT = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"

FLAGS = [
    {
        "call_sid": "CA_wrong_002",
        "merchant_id": MERCHANT,
        "order_matches": False,
        "confidence": 0.9,
        "severity": "medium",
        "discrepancies": [{"type": "wrong_quantity", "item": "Latte",
                           "expected": "2 large", "captured": "1 medium"}],
        "summary": "Captured 1 medium latte instead of 2 large.",
        "checked_at": "2026-08-07T04:20:00Z",
    },
    {
        "call_sid": "CA_wrong_003",
        "merchant_id": MERCHANT,
        "order_matches": False,
        "confidence": 0.95,
        "severity": "high",
        "discrepancies": [{"type": "missing_item", "item": "Garlic naan",
                           "expected": "1 garlic naan", "captured": ""}],
        "summary": "Garlic naan never made it onto the order.",
        "checked_at": "2026-08-07T03:10:00Z",
    },
]


class StubDB:
    def __init__(self, rows):
        self._rows = rows
        self.writes = []
        self.selects = []

    async def select(self, table, columns="*", filters=None, order=None, limit=None, offset=None):
        self.selects.append({"table": table, "filters": dict(filters or {}), "order": order})
        if table != "phone_order_accuracy":
            return []
        mid = (filters or {}).get("merchant_id")
        if mid and mid != f"eq.{MERCHANT}":
            return []
        rows = list(self._rows)
        if (filters or {}).get("order_matches") == "is.false":
            rows = [r for r in rows if r["order_matches"] is False]
        return rows

    async def insert(self, table, row):
        self.writes.append((table, row))
        return [row]

    async def update(self, table, data, filters=None):
        self.writes.append((table, data))
        return []

    async def upsert(self, table, row, on_conflict=None):
        self.writes.append((table, row))
        return [row]


def _make_client(monkeypatch, *, member: bool, rows=None):
    stub = StubDB(rows if rows is not None else FLAGS)
    monkeypatch.setattr(pd, "get_db", lambda: stub)

    async def _member(principal, merchant_id):
        if not member:
            raise HTTPException(403, "Access denied")
    monkeypatch.setattr(pd, "enforce_service_member", _member)

    app = FastAPI()
    app.include_router(pd.router)
    app.dependency_overrides[pd.require_service_auth] = lambda: {"id": "u1", "email": "t@t.co"}
    c = TestClient(app, raise_server_exceptions=False)
    c._stub = stub
    return c


def test_member_sees_flagged_orders(monkeypatch):
    c = _make_client(monkeypatch, member=True)
    r = c.get(f"/api/phone/order-accuracy/{MERCHANT}")

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["merchant_id"] == MERCHANT
    assert body["count"] == 2
    assert body["by_severity"] == {"medium": 1, "high": 1}
    sids = [f["call_sid"] for f in body["flags"]]
    assert sids == ["CA_wrong_002", "CA_wrong_003"]


def test_defaults_to_flagged_only(monkeypatch):
    """The default view is the review queue, not every checked order."""
    c = _make_client(monkeypatch, member=True)
    c.get(f"/api/phone/order-accuracy/{MERCHANT}")

    sel = c._stub.selects[0]
    assert sel["table"] == "phone_order_accuracy"
    assert sel["filters"]["order_matches"] == "is.false"
    assert sel["order"] == "checked_at.desc"


def test_flagged_only_false_widens_to_all_checked_orders(monkeypatch):
    matching = {**FLAGS[0], "call_sid": "CA_ok_001", "order_matches": True,
                "severity": "none", "discrepancies": [], "summary": ""}
    c = _make_client(monkeypatch, member=True, rows=[*FLAGS, matching])

    r = c.get(f"/api/phone/order-accuracy/{MERCHANT}?flagged_only=false")

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["count"] == 3
    assert "order_matches" not in c._stub.selects[0]["filters"]


def test_endpoint_is_read_only(monkeypatch):
    c = _make_client(monkeypatch, member=True)
    c.get(f"/api/phone/order-accuracy/{MERCHANT}")

    assert c._stub.writes == []


def test_non_member_forbidden(monkeypatch):
    c = _make_client(monkeypatch, member=False)
    r = c.get(f"/api/phone/order-accuracy/{MERCHANT}")

    assert r.status_code == 403
    assert c._stub.selects == []  # rejected before any data is read


def test_malformed_merchant_id_rejected(monkeypatch):
    c = _make_client(monkeypatch, member=True)
    r = c.get("/api/phone/order-accuracy/not-a-uuid")

    assert r.status_code == 400


def test_no_findings_returns_empty(monkeypatch):
    c = _make_client(monkeypatch, member=True, rows=[])
    r = c.get(f"/api/phone/order-accuracy/{MERCHANT}")

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["count"] == 0
    assert body["flags"] == []
    assert body["by_severity"] == {}
