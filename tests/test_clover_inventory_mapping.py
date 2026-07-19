"""
Clover inventory mapping — order line items book against the merchant's real
Clover inventory itemIds (sales-reporting parity), not just freeform name+price.

Mocks httpx so no network. What must be right before this touches a real
Clover register:

  1. when an order item maps to a Clover itemId, the line_item POST carries
     ``{"item": {"id": <cloverItemId>}}`` (plus name+price) so the sale books
     against real inventory and shows in Clover sales reports.
  2. an UNMAPPED item falls back to the current freeform name+price line item
     (no ``item`` key) — a missing mapping never changes existing behavior.
  3. a missing / failed inventory lookup NEVER blocks the order: dispatch still
     fires every line freeform.
  4. the name→id map is built from the merchant's POS-imported menu rows
     (source='pos', source_external_id = Clover catalog id) — the catalog id
     is already captured at menu-sync time, so no schema change is needed.
"""
import pytest

from src.services import menu_store
from src.services.pos_connectors import clover_kitchen as ck
from src.services.pos_connectors import website_order_dispatch as wod

aio = pytest.mark.asyncio

ORDER = {
    "id": "abc12345-0000-0000-0000-000000000000",
    "merchant_id": "org-1",
    "customer_name": "Priya S",
    "order_type": "pickup",
    "items": [
        {"name": "Butter Chicken", "quantity": 2, "price": 15.5},
        {"name": "Garlic Naan", "quantity": 1, "price": 3.0},
    ],
    "total": 34.0,
    "currency": "CAD",
}


class _Resp:
    def __init__(self, status, data=None):
        self.status_code = status
        self._d = data or {}
        self.text = ""

    def json(self):
        return self._d


class _Client:
    def __init__(self, calls, order_status=200, li_status=200, print_status=200):
        self.calls = calls
        self.order_status = order_status
        self.li_status = li_status
        self.print_status = print_status

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, json=None, headers=None):
        self.calls.append((url, json))
        if url.endswith("/print_event"):
            return _Resp(self.print_status, {})
        if url.endswith("/orders"):
            return _Resp(self.order_status, {"id": "CLV_ORD_1"})
        return _Resp(self.li_status, {"id": "LI"})


def _patch_client(monkeypatch, calls, **kw):
    monkeypatch.setattr(
        ck.httpx, "AsyncClient",
        lambda timeout=None: _Client(calls, **kw),
    )


def _line_items(calls):
    """The JSON bodies of the line-item POSTs (calls are (url, json) tuples)."""
    return [body for (url, body) in calls if "/line_items" in url]


# ── connector: mapped line items carry the Clover itemId ─────────────────


@aio
async def test_mapped_item_carries_clover_item_id(monkeypatch):
    calls: list = []
    _patch_client(monkeypatch, calls)
    item_id_map = {"butter chicken": "CLOVER_BC_ID", "garlic naan": "CLOVER_NAAN_ID"}

    out = await ck.submit_clover_kitchen_order(
        access_token="tok", external_merchant_id="MID",
        order=ORDER, item_id_map=item_id_map,
    )

    assert out["success"] is True
    li = _line_items(calls)
    # 2 Butter Chicken units + 1 Naan unit = 3 line-item POSTs
    assert len(li) == 3
    bc = [c for c in li if c.get("name") == "Butter Chicken"]
    naan = [c for c in li if c.get("name") == "Garlic Naan"]
    assert len(bc) == 2 and len(naan) == 1
    # every mapped line carries the Clover itemId AND keeps name+price
    for c in bc:
        assert c["item"] == {"id": "CLOVER_BC_ID"}
        assert c["price"] == 1550
    assert naan[0]["item"] == {"id": "CLOVER_NAAN_ID"}
    # distinct mapped order items reported for support
    assert out["line_items_mapped"] == 2


# ── connector: unmapped item falls back to freeform ──────────────────────


@aio
async def test_unmapped_item_falls_back_to_freeform(monkeypatch):
    calls: list = []
    _patch_client(monkeypatch, calls)
    # only Butter Chicken is mapped; Naan is not
    item_id_map = {"butter chicken": "CLOVER_BC_ID"}

    out = await ck.submit_clover_kitchen_order(
        access_token="tok", external_merchant_id="MID",
        order=ORDER, item_id_map=item_id_map,
    )

    assert out["success"] is True
    li = _line_items(calls)
    bc = [c for c in li if c.get("name") == "Butter Chicken"]
    naan = [c for c in li if c.get("name") == "Garlic Naan"]
    for c in bc:
        assert c["item"] == {"id": "CLOVER_BC_ID"}
    # unmapped item: freeform name+price, NO item id key
    assert "item" not in naan[0]
    assert naan[0]["name"] == "Garlic Naan"
    assert naan[0]["price"] == 300
    assert out["line_items_mapped"] == 1


@aio
async def test_no_map_is_all_freeform(monkeypatch):
    """No map at all (None) → current behavior: every line freeform, none blocked."""
    calls: list = []
    _patch_client(monkeypatch, calls)

    out = await ck.submit_clover_kitchen_order(
        access_token="tok", external_merchant_id="MID",
        order=ORDER, item_id_map=None,
    )

    assert out["success"] is True
    li = _line_items(calls)
    assert len(li) == 3  # order still fully dispatched
    assert all("item" not in c for c in li)
    assert out["line_items_mapped"] == 0


@aio
async def test_explicit_id_on_order_item_wins(monkeypatch):
    """An id threaded onto the order item itself resolves without the map."""
    calls: list = []
    _patch_client(monkeypatch, calls)
    order = {
        **ORDER,
        "items": [{"name": "Butter Chicken", "quantity": 1, "price": 15.5,
                   "clover_item_id": "EXPLICIT_ID"}],
    }

    out = await ck.submit_clover_kitchen_order(
        access_token="tok", external_merchant_id="MID",
        order=order, item_id_map=None,
    )

    li = _line_items(calls)
    assert li[0]["item"] == {"id": "EXPLICIT_ID"}
    assert out["line_items_mapped"] == 1


# ── connector: a failed inventory lookup never blocks the order ──────────


@aio
async def test_dispatch_survives_failed_inventory_lookup(monkeypatch):
    """When the lookup produces nothing (empty map, e.g. it errored and the
    guard returned {}), the order STILL dispatches every line freeform."""
    calls: list = []
    _patch_client(monkeypatch, calls)

    out = await ck.submit_clover_kitchen_order(
        access_token="tok", external_merchant_id="MID",
        order=ORDER, item_id_map={},  # empty map == lookup produced nothing
    )
    assert out["success"] is True
    assert len(_line_items(calls)) == 3
    assert out["line_items_mapped"] == 0


@aio
async def test_clover_inventory_map_guard_returns_empty_on_error(monkeypatch):
    """wod._clover_inventory_map swallows lookup errors and returns {} so the
    caller dispatches every line freeform."""
    async def _raise(*a, **k):
        raise RuntimeError("db down")

    monkeypatch.setattr(menu_store, "get_pos_item_id_map", _raise)
    result = await wod._clover_inventory_map("org-1")
    assert result == {}


# ── mapping source: built from POS-imported menu rows ────────────────────


def test_pos_item_id_map_from_menu_rows():
    """The Clover catalog id is already stored on POS-sourced menu_items
    (source='pos', source_external_id). The map is name→id for those rows."""
    rows = [
        {"name": "Butter Chicken", "source": "pos",
         "source_external_id": "CLOVER_BC_ID", "published": True},
        {"name": "Garlic Naan", "source": "pos",
         "source_external_id": "CLOVER_NAAN_ID", "published": True},
        # manual row — no POS catalog id, excluded from the map
        {"name": "Daily Special", "source": "manual",
         "source_external_id": None, "published": True},
        # POS row with no external id — excluded (nothing to book against)
        {"name": "Mystery Item", "source": "pos",
         "source_external_id": "", "published": True},
    ]
    m = menu_store.pos_item_id_map(rows)
    assert m == {
        "butter chicken": "CLOVER_BC_ID",
        "garlic naan": "CLOVER_NAAN_ID",
    }


@aio
async def test_get_pos_item_id_map_returns_empty_on_db_error(monkeypatch):
    class _DB:
        async def select(self, *a, **k):
            raise RuntimeError("boom")

    m = await menu_store.get_pos_item_id_map(_DB(), "org-1")
    assert m == {}
