"""
MENU STORE — normalized single-source-of-truth coverage.

Proves the core contract of src/services/menu_store.py:
  1. Shape conversion round-trips (dollars agent shape ⇄ cents store rows).
  2. Migrate-on-write imports the legacy JSONB blob exactly once.
  3. Ingestion gates: scrape/csv/photo land unpublished+needs_review (never
     silently live); POS is trusted but flags missing prices; an unreviewed
     guess never shadows a published item.
  4. MIRROR INTEGRITY: after any mutation, phone_agent_config.menu_items ==
     agent_menu(published rows) — the backward-compat contract.
  5. Sold-out propagation: excluded from the mirror + agent menu, listed in
     sold_out_names for the prompt's SOLD OUT section.
  6. Public menu payload (published/unpublished/404 handled in route tests).

Pattern mirrors tests/test_menu_builder.py: direct calls + FakeDB, asyncio.run.

Run:  python -m pytest tests/test_menu_store.py -v
"""
from __future__ import annotations

import asyncio
import os
import sys
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.services import menu_store  # noqa: E402

MID = "biz_0123456789abcdef"


def _run(coro):
    return asyncio.run(coro)


def _match(row: dict, filters: dict | None) -> bool:
    for col, expr in (filters or {}).items():
        if expr.startswith("eq."):
            if str(row.get(col)) != expr[3:]:
                return False
        elif expr in ("is.true", "is.false"):
            if bool(row.get(col)) is not (expr == "is.true"):
                return False
    return True


class FakeDB:
    """In-memory PostgREST-ish store for menu_items / merchant_menus /
    phone_agent_config supporting the eq./is. filters menu_store uses."""

    def __init__(self, config_row: dict | None = None):
        self.tables: dict[str, list[dict]] = {
            "menu_items": [],
            "merchant_menus": [],
            "phone_agent_config": [dict(config_row)] if config_row else [],
        }

    async def select(self, table, columns="*", filters=None, order=None,
                     limit=None, offset=None):
        rows = [dict(r) for r in self.tables.get(table, []) if _match(r, filters)]
        return rows[:limit] if limit else rows

    async def insert(self, table, data, return_data=True):
        rows = data if isinstance(data, list) else [data]
        stored = []
        for row in rows:
            row = dict(row)
            row.setdefault("id", str(uuid.uuid4()))
            self.tables.setdefault(table, []).append(row)
            stored.append(row)
        return stored

    async def update(self, table, data, filters=None):
        hit = []
        for row in self.tables.get(table, []):
            if _match(row, filters):
                row.update(data)
                hit.append(dict(row))
        return hit

    async def delete(self, table, filters=None):
        before = len(self.tables.get(table, []))
        self.tables[table] = [r for r in self.tables.get(table, []) if not _match(r, filters)]
        return len(self.tables[table]) < before


def _mirror(db: FakeDB) -> list[dict]:
    rows = [r for r in db.tables["phone_agent_config"] if r["merchant_id"] == MID]
    return rows[0].get("menu_items", []) if rows else []


def _assert_mirror_integrity(db: FakeDB):
    """The compat contract: JSONB blob == published/non-sold-out projection."""
    projection = menu_store.agent_menu(
        [r for r in db.tables["menu_items"] if r["merchant_id"] == MID])
    assert _mirror(db) == projection


# ── 1. shape conversion ──────────────────────────────────────────────────

def test_agent_shape_roundtrip_cents():
    legacy = {"name": "Cheese Pizza", "sizes": ["medium", "large"],
              "size_prices": {"medium": 14, "large": 18}, "topping_price": 2.0,
              "modifications": ["pepperoni"], "category": "Pizzas"}
    row = menu_store.from_agent_shape(legacy)
    assert row["size_prices"] == {"medium": 1400, "large": 1800}
    assert row["topping_price_cents"] == 200
    back = menu_store.to_agent_shape(row)
    assert back["size_prices"] == {"medium": 14.0, "large": 18.0}
    assert back["topping_price"] == 2.0
    assert back["sizes"] == ["medium", "large"]
    assert back["modifications"] == ["pepperoni"]


def test_simple_price_roundtrip():
    row = menu_store.from_agent_shape({"name": "Coke", "price": 3.0})
    assert row["price_cents"] == 300
    assert menu_store.to_agent_shape(row) == {"name": "Coke", "price": 3.0}


# ── 2. migrate-on-write ──────────────────────────────────────────────────

def test_import_jsonb_menu_once():
    db = FakeDB({"merchant_id": MID, "menu_items": [
        {"name": "Wings", "price": 12.0}, {"name": "Coke", "price": 3.0}]})
    assert _run(menu_store.import_jsonb_menu(db, MID)) == 2
    assert all(r["source"] == "manual" and r["published"]
               for r in db.tables["menu_items"])
    # Second call is a no-op (store rows exist).
    assert _run(menu_store.import_jsonb_menu(db, MID)) == 0
    assert len(db.tables["menu_items"]) == 2


# ── 3. ingestion gates ───────────────────────────────────────────────────

def test_untrusted_ingest_never_silently_live():
    db = FakeDB({"merchant_id": MID, "menu_items": []})
    summary = _run(menu_store.ingest_items(
        db, MID, [{"name": "Pad Thai", "price": 15.5, "confidence": 0.9},
                  {"name": "Spring Rolls", "confidence": 0.4}], source="scrape"))
    assert summary == {"inserted": 2, "updated": 0,
                       "skipped_existing": 0, "needs_review": 2}
    assert all(not r["published"] and r["needs_review"]
               for r in db.tables["menu_items"])
    assert _mirror(db) == []  # nothing went live
    _assert_mirror_integrity(db)


def test_pos_ingest_trusted_but_flags_missing_price():
    db = FakeDB({"merchant_id": MID, "menu_items": []})
    summary = _run(menu_store.ingest_items(
        db, MID,
        [{"name": "Latte", "price": 4.5, "source_external_id": "sq-1"},
         {"name": "Mystery Special", "source_external_id": "sq-2"}],
        source="pos"))
    rows = {r["name"]: r for r in db.tables["menu_items"]}
    assert rows["Latte"]["published"] and not rows["Latte"]["needs_review"]
    assert rows["Mystery Special"]["published"] and rows["Mystery Special"]["needs_review"]
    assert summary["needs_review"] == 1
    assert [i["name"] for i in _mirror(db)] == ["Latte", "Mystery Special"]
    _assert_mirror_integrity(db)


def test_untrusted_never_shadows_published_item():
    db = FakeDB({"merchant_id": MID, "menu_items": [{"name": "Wings", "price": 12.0}]})
    summary = _run(menu_store.ingest_items(
        db, MID, [{"name": "Wings", "price": 1.0, "confidence": 0.3}], source="photo"))
    assert summary["skipped_existing"] == 1 and summary["inserted"] == 0
    wings = next(r for r in db.tables["menu_items"] if r["name"] == "Wings")
    assert wings["price_cents"] == 1200 and wings["published"]  # live price untouched


def test_pos_resync_updates_own_rows():
    db = FakeDB({"merchant_id": MID, "menu_items": []})
    _run(menu_store.ingest_items(
        db, MID, [{"name": "Latte", "price": 4.5, "source_external_id": "sq-1"}],
        source="pos"))
    _run(menu_store.ingest_items(
        db, MID, [{"name": "Latte", "price": 5.0, "source_external_id": "sq-1"}],
        source="pos"))
    rows = [r for r in db.tables["menu_items"] if r["name"] == "Latte"]
    assert len(rows) == 1 and rows[0]["price_cents"] == 500
    assert _mirror(db)[0]["price"] == 5.0
    _assert_mirror_integrity(db)


# ── 4. review confirm + mirror integrity ─────────────────────────────────

def test_confirm_publishes_with_edits_and_mirrors():
    db = FakeDB({"merchant_id": MID, "menu_items": []})
    _run(menu_store.ingest_items(
        db, MID, [{"name": "Pad Tai", "price": 15.5, "confidence": 0.6}], source="scrape"))
    pending = _run(menu_store.list_items(db, MID, needs_review=True))
    assert len(pending) == 1
    n = _run(menu_store.confirm_items(db, MID, [
        {"id": pending[0]["id"], "name": "Pad Thai", "price": 16.0}]))
    assert n == 1
    assert _mirror(db) == [{"name": "Pad Thai", "price": 16.0}]
    _assert_mirror_integrity(db)


def test_delete_item_mirrors():
    db = FakeDB({"merchant_id": MID, "menu_items": [{"name": "Coke", "price": 3.0}]})
    _run(menu_store.import_jsonb_menu(db, MID))
    item_id = db.tables["menu_items"][0]["id"]
    _run(menu_store.delete_item(db, MID, item_id))
    assert db.tables["menu_items"] == [] and _mirror(db) == []


# ── 5. sold-out propagation ──────────────────────────────────────────────

def test_sold_out_toggle_propagates_to_agent_shape():
    db = FakeDB({"merchant_id": MID, "menu_items": [
        {"name": "Wings", "price": 12.0}, {"name": "Coke", "price": 3.0}]})
    _run(menu_store.import_jsonb_menu(db, MID))
    wings_id = next(r["id"] for r in db.tables["menu_items"] if r["name"] == "Wings")
    _run(menu_store.update_item(db, MID, wings_id, {"sold_out": True}))

    menu, sold_out = _run(menu_store.get_menu_for_agent(db, MID))
    assert [i["name"] for i in menu] == ["Coke"]
    assert sold_out == ["Wings"]
    assert [i["name"] for i in _mirror(db)] == ["Coke"]  # legacy readers never offer it
    _assert_mirror_integrity(db)

    # Back in stock → instantly restored everywhere.
    _run(menu_store.update_item(db, MID, wings_id, {"sold_out": False}))
    menu, sold_out = _run(menu_store.get_menu_for_agent(db, MID))
    assert {i["name"] for i in menu} == {"Coke", "Wings"} and sold_out == []
    _assert_mirror_integrity(db)


# ── 6. legacy save write-through ─────────────────────────────────────────

def test_replace_menu_from_agent_items_is_authoritative():
    db = FakeDB({"merchant_id": MID, "menu_items": [
        {"name": "Cheese Pizza", "size_prices": {"medium": 14, "large": 18}},
        {"name": "Coke", "price": 3.0}]})
    _run(menu_store.import_jsonb_menu(db, MID))
    # Wizard save: price edit + new item + Coke removed. The wizard payload
    # strips sizes — the store row must PRESERVE them.
    adopted = _run(menu_store.replace_menu_from_agent_items(db, MID, [
        {"name": "Cheese Pizza", "price": 0, "category": "Pizzas"},
        {"name": "Garlic Bread", "price": 6.0}]))
    assert adopted
    rows = {r["name"]: r for r in db.tables["menu_items"]}
    assert "Coke" not in rows
    assert rows["Cheese Pizza"]["size_prices"] == {"medium": 1400, "large": 1800}
    assert rows["Garlic Bread"]["price_cents"] == 600 and rows["Garlic Bread"]["source"] == "manual"
    _assert_mirror_integrity(db)


def test_replace_menu_noop_without_store_rows():
    db = FakeDB({"merchant_id": MID, "menu_items": [{"name": "Coke", "price": 3.0}]})
    assert not _run(menu_store.replace_menu_from_agent_items(
        db, MID, [{"name": "Sprite", "price": 3.0}]))
    assert db.tables["menu_items"] == []  # store untouched, legacy world intact


# ── 7. public menu ───────────────────────────────────────────────────────

def test_public_menu_payload_and_slug():
    db = FakeDB({"merchant_id": MID, "menu_items": [
        {"name": "Wings", "price": 12.0}]})
    _run(menu_store.import_jsonb_menu(db, MID))
    wings_id = db.tables["menu_items"][0]["id"]
    _run(menu_store.update_item(db, MID, wings_id, {"sold_out": True}))

    meta = _run(menu_store.ensure_public_menu(db, MID, "Tony's Pizza"))
    assert meta["public_slug"] == "tonys-pizza" and meta["published"]
    # Idempotent: second publish keeps the slug.
    again = _run(menu_store.ensure_public_menu(db, MID, "Tony's Pizza"))
    assert again["public_slug"] == "tonys-pizza"

    payload = _run(menu_store.get_public_menu(db, "tonys-pizza"))
    assert payload["business_name"] == "Tony's Pizza"
    # Sold-out items stay VISIBLE on the public page, flagged.
    assert payload["items"] == [{"name": "Wings", "price": 12.0, "sold_out": True}]
    assert _run(menu_store.get_public_menu(db, "nope")) is None


def test_slug_collision_appends_suffix():
    db = FakeDB()
    db.tables["merchant_menus"] = [
        {"merchant_id": "other", "public_slug": "tonys-pizza", "published": True}]
    meta = _run(menu_store.ensure_public_menu(db, MID, "Tony's Pizza"))
    assert meta["public_slug"] == "tonys-pizza-2"
