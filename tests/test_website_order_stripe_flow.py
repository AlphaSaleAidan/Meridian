"""
Website order pay-first flow — Stripe before the kitchen.

What must be right before this touches real money and real kitchens:

  1. POST /api/website/order stores the row as awaiting_payment, creates a
     Stripe Checkout session carrying website_order_id metadata, and does NOT
     dispatch to the POS.
  2. If checkout creation fails, the endpoint fails CLOSED (503) — an unpaid
     order can never reach the kitchen.
  3. mark_paid_and_dispatch (webhook path) flips status→paid exactly once
     (idempotent under Stripe retries + the payment_intent.succeeded twin)
     and only then releases the kitchen dispatch.
  4. The kitchen ticket says PAID when the order is paid.
"""
import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
_PA = str(Path(__file__).resolve().parents[1] / "services" / "phone_agent")
if _PA not in sys.path:
    sys.path.insert(0, _PA)

import payment_links as pl  # noqa: E402
from src.services.pos_connectors import clover_kitchen as ck  # noqa: E402
from src.services.pos_connectors import website_order_dispatch as wod  # noqa: E402

aio = pytest.mark.asyncio

PAID_ORDER = {
    "id": "abc12345-0000-0000-0000-000000000000",
    "customer_name": "Priya S",
    "customer_phone": "+16045551234",
    "order_type": "pickup",
    "items": [{"name": "Butter Chicken", "quantity": 1, "price": 15.5}],
    "total": 16.0,
    "currency": "CAD",
    "status": "paid",
}


# ── kitchen ticket payment state ──────────────────────────────


def test_kitchen_note_paid_order_says_paid_not_collect():
    note = ck.build_kitchen_note(PAID_ORDER, "Meridian Mobile Order")
    assert "PAID ONLINE (Stripe) — do not collect" in note
    assert "UNPAID" not in note


def test_kitchen_note_unpaid_order_still_says_collect():
    note = ck.build_kitchen_note({**PAID_ORDER, "status": "awaiting_payment"},
                                 "Meridian Mobile Order")
    assert "UNPAID, collect in store" in note
    assert "PAID ONLINE" not in note


# ── create_website_checkout (strict, no POS-link fallback) ────


@aio
async def test_create_website_checkout_fails_closed_when_unconfigured(monkeypatch):
    monkeypatch.setattr(pl, "UNIFIED_PAYMENTS_ENABLED", False)
    with pytest.raises(RuntimeError):
        await pl.create_website_checkout({}, SimpleNamespace(), "oid-1")


@aio
async def test_create_website_checkout_threads_metadata_and_urls(monkeypatch):
    monkeypatch.setattr(pl, "UNIFIED_PAYMENTS_ENABLED", True)
    monkeypatch.setattr(pl, "STRIPE_SECRET_KEY", "sk_test_x")
    captured = {}

    class FakeSession:
        @staticmethod
        def create(**kw):
            captured.update(kw)
            return {"id": "cs_test_1", "url": "https://checkout.stripe.com/pay/cs_test_1"}

    monkeypatch.setattr(
        pl, "_stripe",
        lambda: SimpleNamespace(checkout=SimpleNamespace(Session=FakeSession)),
    )

    async def no_record(*a, **k):
        return False
    monkeypatch.setattr(pl, "_record_checkout_session", no_record)

    cfg = SimpleNamespace(stripe_account_id="acct_9", stripe_charges_enabled=True,
                          plan_tier="")
    res = await pl.create_website_checkout(
        {
            "merchant_id": "m1",
            "caller_phone": "+16045551234",
            "currency": "cad",
            "items": [{"name": "Naan", "price": 3.0, "quantity": 2}],
            "total": 6.0,
        },
        cfg, "web-order-77",
        success_url="https://meridian.tips/sites/x?order=success",
        cancel_url="https://meridian.tips/sites/x?order=cancelled",
    )

    assert res["session_id"] == "cs_test_1"
    assert res["checkout_url"].startswith("https://checkout.stripe.com/")
    assert captured["metadata"]["website_order_id"] == "web-order-77"
    assert captured["metadata"]["caller_phone"] == "+16045551234"
    assert captured["success_url"] == "https://meridian.tips/sites/x?order=success"
    assert captured["cancel_url"] == "https://meridian.tips/sites/x?order=cancelled"
    # destination charge to the merchant's connected account
    assert captured["payment_intent_data"]["transfer_data"]["destination"] == "acct_9"
    # itemized: 2x Naan at 300¢
    li = captured["line_items"][0]
    assert li["quantity"] == 2 and li["price_data"]["unit_amount"] == 300


@aio
async def test_create_website_checkout_platform_direct_when_not_onboarded(monkeypatch):
    monkeypatch.setattr(pl, "UNIFIED_PAYMENTS_ENABLED", True)
    monkeypatch.setattr(pl, "STRIPE_SECRET_KEY", "sk_test_x")
    captured = {}

    class FakeSession:
        @staticmethod
        def create(**kw):
            captured.update(kw)
            return {"id": "cs_test_2", "url": "https://checkout.stripe.com/pay/cs_test_2"}

    monkeypatch.setattr(
        pl, "_stripe",
        lambda: SimpleNamespace(checkout=SimpleNamespace(Session=FakeSession)),
    )

    async def no_record(*a, **k):
        return False
    monkeypatch.setattr(pl, "_record_checkout_session", no_record)

    cfg = SimpleNamespace(stripe_account_id="", stripe_charges_enabled=False, plan_tier="")
    await pl.create_website_checkout(
        {"merchant_id": "m1", "currency": "cad",
         "items": [{"name": "Naan", "price": 3.0, "quantity": 1}], "total": 3.0},
        cfg, "web-order-78",
    )
    assert "payment_intent_data" not in captured  # platform-direct charge


# ── mark_paid_and_dispatch (webhook release path) ─────────────


class _FakeDB:
    def __init__(self, rows):
        self.rows = rows
        self.update_calls = []

    async def update(self, table, data, filters):
        self.update_calls.append((table, data, filters))
        # emulate `status=neq.paid`: only unpaid rows match
        out = []
        for r in self.rows:
            if str(r.get("id")) == filters["id"].split("eq.", 1)[1] and r.get("status") != "paid":
                r.update(data)
                out.append(dict(r))
        return out


def _patch_db(monkeypatch, fake):
    import src.db as dbmod
    monkeypatch.setattr(dbmod, "get_db", lambda: fake)


@aio
async def test_mark_paid_flips_once_and_releases_dispatch(monkeypatch):
    fake = _FakeDB([{"id": "w1", "status": "awaiting_payment", "merchant_id": "m1"}])
    _patch_db(monkeypatch, fake)
    dispatched = []

    async def fake_dispatch(row):
        dispatched.append(row)
        return {"dispatched": True}
    monkeypatch.setattr(wod, "dispatch_website_order_to_pos", fake_dispatch)

    res1 = await wod.mark_paid_and_dispatch("w1", payment_txn_id="pi_123")
    await asyncio.sleep(0.05)  # let the background task run
    res2 = await wod.mark_paid_and_dispatch("w1", payment_txn_id="pi_123")  # Stripe retry
    await asyncio.sleep(0.05)

    assert res1["released"] is True
    assert res2 == {"released": False, "reason": "already_paid_or_missing"}
    assert len(dispatched) == 1                       # exactly one kitchen ticket
    assert dispatched[0]["status"] == "paid"          # dispatched as a PAID order
    assert dispatched[0]["stripe_session_id"] == "pi_123"


@aio
async def test_mark_paid_retries_status_only_on_pre_migration_schema(monkeypatch):
    """Before migration 040 the paid_at/stripe_session_id columns don't exist;
    the critical status flip must still happen."""
    calls = {"n": 0}
    row = {"id": "w2", "status": "awaiting_payment"}

    class SchemaPickyDB(_FakeDB):
        async def update(self, table, data, filters):
            calls["n"] += 1
            if "paid_at" in data:
                raise RuntimeError("42703 column does not exist")
            return await super().update(table, data, filters)

    fake = SchemaPickyDB([row])
    _patch_db(monkeypatch, fake)

    async def fake_dispatch(r):
        return {"dispatched": True}
    monkeypatch.setattr(wod, "dispatch_website_order_to_pos", fake_dispatch)

    res = await wod.mark_paid_and_dispatch("w2", payment_txn_id="pi_9")
    assert res["released"] is True
    assert row["status"] == "paid"
    assert calls["n"] == 2  # full patch failed, status-only retry succeeded


# ── paid tag on the generic (non-Clover) dispatch path ────────


@aio
async def test_generic_path_note_carries_paid_tag(monkeypatch):
    monkeypatch.delenv("POS_ORDERS_DISABLED", raising=False)

    async def silent(_oid, _res):
        pass
    monkeypatch.setattr(wod, "_record_outcome", silent)

    async def conn(_):
        return {"system": "square", "token": "tok",
                "external_merchant_id": "SQ_M", "location_id": "L1"}
    monkeypatch.setattr(wod, "_resolve_connection", conn)

    seen = {}

    async def fake_create(system_key, order_data, config=None):
        seen.update(order_data)
        return SimpleNamespace(success=True, fallback_used=False, order_id="sq1",
                               fallback_reason="")
    monkeypatch.setattr(wod, "create_pos_order", fake_create)

    await wod.dispatch_website_order_to_pos(dict(PAID_ORDER))
    assert "PAID ONLINE, do not collect" in seen["special_instructions"]
    assert "Meridian Mobile Order" in seen["special_instructions"]
