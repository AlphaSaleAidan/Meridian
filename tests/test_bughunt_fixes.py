"""
Fixes from the 2026-07-15 full-system bug hunt — each test pins one
user-facing bug closed:

  1. Off-menu items are DROPPED (never billed $0.00) and the caller is told.
  2. Clover-native settlement honors the rep fee override in the FLAT model.
  3. CAD orders show CA$ in SMS regardless of currency casing.
  5. End-of-call reports with no call id get a synthesized idempotency ref.
  6. Unmapped-DID calls are flagged (note carries the dialed number).
  7. Overage is clamped to the disclosed per-call maximum under the cap.
"""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
_PA = str(Path(__file__).resolve().parents[1] / "services" / "phone_agent")
if _PA not in sys.path:
    sys.path.insert(0, _PA)

import sms_checkout  # noqa: E402
import src.api.routes.vapi_webhook as vw  # noqa: E402
from order_normalizer import normalize_order  # noqa: E402
from src.services.clover_hco import clover_fee_cents  # noqa: E402

aio = pytest.mark.asyncio

MENU_CFG = SimpleNamespace(
    merchant_id="m1", business_name="Maple Tandoor", tax_rate=0.13,
    currency="cad", pos_system="", country="CA", language="en",
    menu_items=[{"name": "Butter Chicken", "price": 15.5},
                {"name": "Garlic Naan", "price": 3.0}],
)


# ── 1. off-menu items ─────────────────────────────────────────


def test_off_menu_item_dropped_not_zero_priced():
    order = normalize_order({"items": [
        {"name": "Butter Chicken", "quantity": 1},
        {"name": "Pizza Supreme", "quantity": 2},   # not on this menu
    ]}, MENU_CFG)
    assert [i["name"] for i in order["items"]] == ["Butter Chicken"]
    assert order["unavailable_items"] == ["Pizza Supreme"]
    assert order["subtotal"] == 15.5                # no $0 lines in the total
    assert all(i["unit_price"] > 0 for i in order["items"])


def test_no_menu_merchant_keeps_passthrough():
    cfg = SimpleNamespace(merchant_id="m2", business_name="No Menu Diner",
                          tax_rate=0.13, currency="usd", pos_system="",
                          country="US", language="en", menu_items=[])
    order = normalize_order({"items": [{"name": "Daily Special", "quantity": 1}]}, cfg)
    # legacy behavior preserved: merchants without menus still take orders
    assert len(order["items"]) == 1
    assert order["unavailable_items"] == []


@aio
async def test_all_items_off_menu_never_dispatches(monkeypatch):
    import pay_on_phone as pop
    called = []

    async def boom(*a, **k):
        called.append(1)
        return {}
    monkeypatch.setattr(pop, "dispatch_order", boom)
    reply = await vw._place_order(
        {"customer_name": "Priya", "order_type": "pickup",
         "items": [{"name": "Pizza Supreme", "quantity": 1}]},
        MENU_CFG, "16045551234")
    assert "couldn't find Pizza Supreme" in reply
    assert called == []                              # nothing reached the POS


@aio
async def test_partial_off_menu_mentions_dropped_item(monkeypatch):
    import src.api.routes.vapi_webhook as _vw

    async def fake_dispatch(normalized, config, caller, pay_choice=""):
        assert [i["name"] for i in normalized["items"]] == ["Butter Chicken"]
        return {"sms_sent": True, "pos_result": {"success": True}}
    monkeypatch.setattr(_vw, "_place_order", _vw._place_order)  # sanity
    import pay_on_phone as pop
    monkeypatch.setattr(pop, "dispatch_order", fake_dispatch)
    reply = await vw._place_order(
        {"customer_name": "Priya", "order_type": "pickup",
         "items": [{"name": "Butter Chicken", "quantity": 1},
                   {"name": "Pizza Supreme", "quantity": 1}]},
        MENU_CFG, "16045551234")
    assert "1 item" in reply                         # count reflects what was placed
    assert "couldn't find Pizza Supreme" in reply


# ── 2. Clover flat-model fee override ─────────────────────────


def test_clover_flat_model_honors_override(monkeypatch):
    import payment_links as pl
    monkeypatch.setattr(pl, "FEE_SPLIT_ENABLED", False)
    monkeypatch.setenv("MERIDIAN_SERVICE_FEE_CENTS", "50")
    sess = {"amount_cents": 3400, "currency": "cad",
            "payload": {"plan_tier": "premium", "fee_override_cents": 85}}
    assert clover_fee_cents(sess) == 85              # NOT the env 50¢
    # no override → env default (unchanged behavior)
    assert clover_fee_cents({"amount_cents": 3400, "payload": {}}) == 50
    # garbage override → env default, never a crash
    assert clover_fee_cents({"amount_cents": 3400,
                             "payload": {"fee_override_cents": "x"}}) == 50


# ── 3. CAD SMS symbol ─────────────────────────────────────────


def test_cad_sms_symbol_case_insensitive():
    order = {"currency": "cad", "total": 45.99, "items": [], "order_type": "pickup"}
    body = sms_checkout._format_checkout_sms(order, "https://x/p/1", "Maple Tandoor")
    assert "CA$45.99" in body
    body_usd = sms_checkout._format_checkout_sms(
        {**order, "currency": "usd"}, "https://x/p/1", "Maple Tandoor")
    assert "CA$" not in body_usd and "$45.99" in body_usd


# ── 5/6/7. end-of-call billing integrity ──────────────────────


def _eoc_msg(**over):
    msg = {"type": "end-of-call-report", "endedReason": "customer-ended-call",
           "cost": 0.30, "durationSeconds": 300,
           "call": {"id": "call_1", "phoneNumber": {"number": "+17805550100"}}}
    msg.update(over)
    return msg


class _Ledger:
    def __init__(self):
        self.debits, self.credits = [], []

    async def debit(self, mid, cents, source="", ref=None, note=None):
        self.debits.append({"mid": mid, "cents": cents, "ref": ref, "note": note})
        return True

    async def credit(self, mid, cents, source="", ref=None, note=None):
        self.credits.append({"mid": mid, "cents": cents, "ref": ref, "note": note})
        return True


async def _run_eoc(monkeypatch, msg, merchant_id="m1"):
    from fastapi import FastAPI
    import httpx
    ledger = _Ledger()
    import src.services.voice_ledger as vl
    monkeypatch.setattr(vl, "debit", ledger.debit)
    monkeypatch.setattr(vl, "credit", ledger.credit)

    async def resolve(_did):
        return SimpleNamespace(merchant_id=merchant_id)
    monkeypatch.setattr(vw, "_resolve_config", resolve)
    monkeypatch.setattr(vw, "VAPI_SERVER_SECRET", "s3")

    app = FastAPI()
    app.include_router(vw.router)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        r = await c.post("/api/vapi/webhook", json={"message": msg},
                         headers={"x-vapi-secret": "s3"})
        assert r.status_code == 200
    return ledger


@aio
async def test_missing_call_id_gets_stable_synthesized_ref(monkeypatch):
    msg = _eoc_msg(call={"phoneNumber": {"number": "+17805550100"}})
    led1 = await _run_eoc(monkeypatch, msg)
    led2 = await _run_eoc(monkeypatch, json.loads(json.dumps(msg)))  # exact retry
    ref1, ref2 = led1.debits[0]["ref"], led2.debits[0]["ref"]
    assert ref1 and ref1.startswith("noid-")
    assert ref1 == ref2          # identical retry → same ref → ledger dedupes


@aio
async def test_overage_clamped_to_disclosed_max(monkeypatch):
    monkeypatch.setattr(vw, "VOICE_MAX_CALL_MIN", 5)
    # grace/rounding lands the call at 5:20 → ceil 6 min; unclamped would be
    # 3 min over = 135¢, above the disclosed 90¢ maximum
    led = await _run_eoc(monkeypatch, _eoc_msg(durationSeconds=320))
    assert led.credits[0]["cents"] == 2 * vw.VOICE_OVERAGE_CENTS_PER_MIN


@aio
async def test_unmapped_did_billed_to_demo_with_dialed_note(monkeypatch):
    led = await _run_eoc(monkeypatch, _eoc_msg(), merchant_id="demo")
    assert led.debits[0]["mid"] == "demo"
    assert "unmapped:+17805550100" in (led.debits[0]["note"] or "")


# ── accent validation (papercut) ──────────────────────────────


def test_phone_config_accent_validation():
    from src.api.routes.phone_dashboard import PhoneConfigRequest
    ok = PhoneConfigRequest(merchant_id="m1", accent="Indian ")
    assert ok.accent == "indian"                     # normalized
    assert PhoneConfigRequest(merchant_id="m1").accent is None
    with pytest.raises(Exception):
        PhoneConfigRequest(merchant_id="m1", accent="klingon")
