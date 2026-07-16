"""
MENU STORE → LIVE AGENT PATH coverage.

Proves the hot call path picks the store up correctly:
  1. merchant_config._store_row_to_agent_item is byte-for-byte parity with
     menu_store.to_agent_shape (the two are intentional twins — merchant_config
     is standalone and can't import src.*).
  2. _store_rows_to_menu: sold-out items leave the orderable menu and land in
     the sold-out list; unpublished rows never surface; names dedupe.
  3. vapi_webhook._system_prompt renders a SOLD OUT section / hosted-menu line
     only when the config carries them — otherwise byte-for-byte unchanged.
  4. save_phone_config write-through: a config save carrying menu_items updates
     the store when store rows exist, and no-ops (JSONB-only) when they don't.

Run:  python -m pytest tests/test_menu_agent_path.py -v
"""
from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("ENCRYPTION_KEY", "0" * 64)

_PHONE_AGENT_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "services", "phone_agent"))
if _PHONE_AGENT_DIR not in sys.path:
    sys.path.insert(0, _PHONE_AGENT_DIR)

import merchant_config as mc  # noqa: E402
from src.api.routes.vapi_webhook import _system_prompt  # noqa: E402
from src.services import menu_store  # noqa: E402

from tests.test_menu_store import MID, FakeDB, _run  # noqa: E402

SERVICE = {"kind": "service"}


# ── 1. converter parity (the twins must not drift) ───────────────────────

PARITY_ROWS = [
    {"name": "Coke", "price_cents": 300},
    {"name": "Cheese Pizza", "sizes": ["medium", "large"],
     "size_prices": {"medium": 1400, "large": 1800},
     "topping_price_cents": 200, "modifications": ["pepperoni", "mushroom"],
     "category": "Pizzas", "description": "Classic."},
    {"name": "Market Fish", "price_cents": None, "category": "Mains"},
    {"name": "Combo", "size_prices": {"solo": 999}},
]


def test_store_row_converter_parity():
    for row in PARITY_ROWS:
        assert mc._store_row_to_agent_item(row) == menu_store.to_agent_shape(row), row


# ── 2. store rows → (menu, sold_out) ─────────────────────────────────────

def test_store_rows_to_menu_sold_out_and_published():
    rows = [
        {"name": "Wings", "price_cents": 1200, "published": True, "sold_out": True},
        {"name": "Coke", "price_cents": 300, "published": True, "sold_out": False},
        {"name": "Secret Item", "price_cents": 500, "published": False},
        {"name": "coke", "price_cents": 350, "published": True},  # dupe name
    ]
    items, sold_out = mc._store_rows_to_menu(rows)
    assert [i["name"] for i in items] == ["Coke"]
    assert sold_out == ["Wings"]


# ── 3. prompt rendering ──────────────────────────────────────────────────

def test_prompt_sold_out_section_and_menu_link():
    config = mc._demo_config("demo")
    baseline = _system_prompt(config)
    assert "SOLD OUT" not in baseline and "/m/" not in baseline

    config.sold_out_items = ["Wings", "Garlic Bread"]
    config.menu_public_url = "https://meridian.tips/m/tonys-pizza"
    prompt = _system_prompt(config)
    assert "SOLD OUT TODAY" in prompt
    assert "- Wings" in prompt and "- Garlic Bread" in prompt
    assert "https://meridian.tips/m/tonys-pizza" in prompt

    # Fields cleared → byte-for-byte back to baseline (no-regression contract).
    config.sold_out_items = None
    config.menu_public_url = ""
    assert _system_prompt(config) == baseline


# ── 4. config-save write-through ─────────────────────────────────────────

def _patch_membership(monkeypatch):
    from src.api import auth

    async def _ok(user, org_id):
        return True
    monkeypatch.setattr(auth, "_check_org_membership", _ok)


def test_config_save_writes_through_to_store(monkeypatch):
    import src.db as db_mod
    from src.api.routes.phone_dashboard import PhoneConfigRequest, save_phone_config

    db = FakeDB({"merchant_id": MID, "menu_items": []})
    _run(menu_store.ingest_items(
        db, MID, [{"name": "Latte", "price": 4.5, "source_external_id": "sq-1"}],
        source="pos"))
    monkeypatch.setattr(db_mod, "_db_instance", db)

    req = PhoneConfigRequest(merchant_id=MID, menu_items=[
        {"name": "Latte", "price": 5.0}, {"name": "Muffin", "price": 3.5}])
    _run(save_phone_config(req, principal=SERVICE))

    rows = {r["name"]: r for r in db.tables["menu_items"]}
    assert rows["Latte"]["price_cents"] == 500
    assert rows["Muffin"]["source"] == "manual" and rows["Muffin"]["price_cents"] == 350
    # Mirror equals the store projection after the save.
    config_row = db.tables["phone_agent_config"][0]
    assert config_row["menu_items"] == menu_store.agent_menu(db.tables["menu_items"])


def test_config_save_without_store_rows_stays_jsonb_only(monkeypatch):
    import src.db as db_mod
    from src.api.routes.phone_dashboard import PhoneConfigRequest, save_phone_config

    db = FakeDB()
    monkeypatch.setattr(db_mod, "_db_instance", db)
    req = PhoneConfigRequest(merchant_id=MID, menu_items=[{"name": "Coke", "price": 3.0}])
    _run(save_phone_config(req, principal=SERVICE))

    assert db.tables["menu_items"] == []  # store untouched
    assert db.tables["phone_agent_config"][0]["menu_items"] == [
        {"name": "Coke", "price": 3.0}]
