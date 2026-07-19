"""
Clover-native pay-by-text (Hosted Checkout) — unified-rail coverage.

Money invariants under test:
  1. TWO independent gates (global CLOVER_NATIVE_PAY_ENABLED env + the
     merchant's payment_link_provider column), both default OFF, tested in
     BOTH directions — one flag alone never routes native.
  2. Native failure falls through to the Stripe rail (no stranded orders).
  3. The lazily-stored Hosted Checkout cart charges items + tax + the
     fee-split surcharge line, and redirects back to /pay/clover/return.
  4. The success REDIRECT alone never marks an order paid — only a payment
     verified against the merchant's Clover does. Fee is booked to the voice
     ledger only on verification, idempotent on the payment id.
"""
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
_PA = str(Path(__file__).resolve().parents[1] / "services" / "phone_agent")
if _PA not in sys.path:
    sys.path.insert(0, _PA)

import payment_links as pl  # noqa: E402
import src.api.routes.pay_redirect as pr  # noqa: E402
import src.services.clover_hco as svc  # noqa: E402

aio = pytest.mark.asyncio

CLOVER_CFG = SimpleNamespace(
    pos_system="clover", pos_access_token="clov_tok", pos_location_id="CLV_MID",
    payment_link_provider="clover", plan_tier="", merchant_id="org-1",
    stripe_account_id="", stripe_charges_enabled=False,
)

ORDER = {
    "merchant_id": "org-1",
    "customer_name": "Priya Sharma",
    "caller_phone": "+16045551234",
    "currency": "cad",
    "items": [
        {"name": "Butter Chicken", "quantity": 2, "unit_price": 15.5},
        {"name": "Garlic Naan", "quantity": 1, "unit_price": 3.0},
    ],
    "total": 34.0,
}


# ── gating: both directions ───────────────────────────────────


def _wire_rails(monkeypatch):
    lazy_calls, stripe_calls = [], []

    async def lazy(order, pos_order_id, mid_hint="", plan_tier="",
                   fee_override_cents=None):
        lazy_calls.append((order, pos_order_id, mid_hint, plan_tier,
                           fee_override_cents))
        return {"method": "clover", "url": "/p/x"}

    async def has_clover(cfg):
        return True

    async def stripe(*a, **k):
        stripe_calls.append(a)
        return {"method": "stripe", "url": "s"}

    monkeypatch.setattr(pl, "_clover_lazy_checkout", lazy)
    monkeypatch.setattr(pl, "_merchant_has_clover", has_clover)
    monkeypatch.setattr(pl, "_stripe_checkout", stripe)
    monkeypatch.setattr(pl, "UNIFIED_PAYMENTS_ENABLED", True)
    monkeypatch.setattr(pl, "STRIPE_SECRET_KEY", "sk_x")
    return lazy_calls, stripe_calls


@aio
async def test_native_rail_needs_both_gates(monkeypatch):
    lazy_calls, _ = _wire_rails(monkeypatch)

    # global OFF + merchant ON → stripe
    monkeypatch.setenv("CLOVER_NATIVE_PAY_ENABLED", "0")
    res = await pl.create_checkout(dict(ORDER), CLOVER_CFG)
    assert res["method"] == "stripe" and lazy_calls == []

    # global ON + merchant OFF (default stripe provider) → stripe
    monkeypatch.setenv("CLOVER_NATIVE_PAY_ENABLED", "1")
    cfg_off = SimpleNamespace(**{**CLOVER_CFG.__dict__,
                                 "payment_link_provider": "stripe"})
    res = await pl.create_checkout(dict(ORDER), cfg_off)
    assert res["method"] == "stripe" and lazy_calls == []

    # both ON → native lazy link, plan tier forwarded for the fee line
    tier_cfg = SimpleNamespace(**{**CLOVER_CFG.__dict__, "plan_tier": "command"})
    res = await pl.create_checkout(dict(ORDER), tier_cfg)
    assert res["method"] == "clover"
    assert lazy_calls[0][3] == "command"


@aio
async def test_no_clover_connection_falls_back_even_when_both_gates_on(monkeypatch):
    lazy_calls, stripe_calls = _wire_rails(monkeypatch)
    monkeypatch.setenv("CLOVER_NATIVE_PAY_ENABLED", "1")

    async def no_clover(cfg):
        return False
    monkeypatch.setattr(pl, "_merchant_has_clover", no_clover)

    res = await pl.create_checkout(dict(ORDER), CLOVER_CFG)
    assert res["method"] == "stripe"
    assert lazy_calls == [] and len(stripe_calls) == 1


@aio
async def test_native_failure_falls_back_to_stripe(monkeypatch):
    _, stripe_calls = _wire_rails(monkeypatch)
    monkeypatch.setenv("CLOVER_NATIVE_PAY_ENABLED", "1")

    async def lazy_boom(*a, **k):
        raise RuntimeError("checkout_sessions_insert_500")
    monkeypatch.setattr(pl, "_clover_lazy_checkout", lazy_boom)

    res = await pl.create_checkout(dict(ORDER), CLOVER_CFG)
    assert res["method"] == "stripe" and len(stripe_calls) == 1


# ── lazily-stored hosted checkout payload ─────────────────────


def test_hco_cart_charges_fee_split_surcharge_line(monkeypatch):
    monkeypatch.setattr(pl, "FEE_SPLIT_ENABLED", True)
    items, total = pl._clover_hco_line_items(dict(ORDER), plan_tier="premium")

    assert items[0] == {"name": "Butter Chicken", "price": 1550, "unitQty": 2}
    # fee-split surcharge rides as its own line so we can reclaim it
    assert items[-1]["name"] == "Service & processing fee"
    assert items[-1]["price"] == pl.customer_surcharge_cents("premium", "cad")
    assert total == sum(i["price"] * i["unitQty"] for i in items)

    # flag OFF → no surcharge line (byte-for-byte existing cart)
    monkeypatch.setattr(pl, "FEE_SPLIT_ENABLED", False)
    items_off, _ = pl._clover_hco_line_items(dict(ORDER), plan_tier="premium")
    assert all(i["name"] != "Service & processing fee" for i in items_off)


class _SupaResp:
    status_code = 201
    text = ""


class _SupaClient:
    """Captures the checkout_sessions insert the lazy path makes."""
    posts: list = []

    def __init__(self, timeout=None):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, json=None, headers=None):
        _SupaClient.posts.append((url, json))
        return _SupaResp()


@aio
async def test_lazy_row_stores_return_redirects_and_plan_tier(monkeypatch):
    monkeypatch.setattr(pl, "SUPABASE_URL", "https://supa.test")
    monkeypatch.setattr(pl, "SUPABASE_KEY", "svc-key")
    monkeypatch.setattr(pl.httpx, "AsyncClient", _SupaClient)
    _SupaClient.posts = []

    res = await pl._clover_lazy_checkout(dict(ORDER), "POS9", "CLV_MID",
                                         plan_tier="premium")
    assert res["method"] == "clover"
    url, row = _SupaClient.posts[0]
    assert "checkout_sessions" in url
    req = row["payload"]["hco_request"]
    assert req["redirectUrls"]["success"].endswith(
        f"/pay/clover/return/{row['short_code']}")
    assert req["redirectUrls"]["cancel"].endswith("/pay/cancel")
    assert row["payload"]["plan_tier"] == "premium"
    assert row["payload"]["clover_merchant_id"] == "CLV_MID"
    # no Clover HTTP at order time, and never the token in the row
    assert all("clover.com" not in u for u, _ in _SupaClient.posts)
    assert "clov_tok" not in str(row)


# ── return route: verification is the gate, not the redirect ──


SESSION_ROW = {
    "id": "row-1", "merchant_id": "org-1", "pos_order_id": "POS9",
    "provider": "clover", "provider_ref": "CHK123", "amount_cents": 3529,
    "currency": "cad", "status": "created", "caller_phone": "+16045551234",
    "created_at": "2026-07-14T20:00:00+00:00", "short_code": "abcd1234",
    "payload": {"plan_tier": ""},
}


class _FakeDB:
    def __init__(self, row):
        self.row = row
        self.updates = []

    async def select(self, table, columns=None, filters=None, limit=None, order=None):
        return [dict(self.row)]

    async def update(self, table, data, filters=None):
        self.updates.append((table, data, filters))
        return [dict(self.row)]


def _wire_route(monkeypatch, db, payment):
    monkeypatch.setattr(pr, "get_db", lambda: db)

    async def verify(sess):
        return payment
    monkeypatch.setattr(pr, "_verify_clover_payment", verify)

    import pay_on_phone
    released = []

    async def fake_mark(**kw):
        released.append(kw)
        return {"released": True}
    monkeypatch.setattr(pay_on_phone, "mark_order_paid", fake_mark)

    import src.services.voice_ledger as vl
    credits = []

    async def fake_credit(merchant_id, cents, source="", ref=None, note=None):
        credits.append((merchant_id, cents, source, ref))
        return True
    monkeypatch.setattr(vl, "credit", fake_credit)

    # The receipt now goes through the SHARED, idempotent helper
    # (order_receipt.send_order_receipt), which resolves send_sms +
    # fetch_optout_status on its own module. Spy the helper's send path and
    # neutralise its opt-out + DB-idempotency lookups so the receipt fires.
    import order_receipt as orc
    texts = []

    async def fake_sms(phone, message):
        texts.append((phone, message))
        return {"sent": True}
    monkeypatch.setattr(orc, "send_sms", fake_sms)

    async def no_optout(merchant_id, phone):
        return {"marketing_optout": False, "transactional_optout": False}
    monkeypatch.setattr(orc, "fetch_optout_status", no_optout)

    async def claim(order_id):
        return True
    monkeypatch.setattr(orc, "_claim_receipt", claim)
    return released, credits, texts


@aio
async def test_spoofed_redirect_never_marks_paid(monkeypatch):
    """Loading the success URL without a real Clover payment must NOT release
    the order or book a fee — just a self-refreshing 'confirming' page."""
    db = _FakeDB(SESSION_ROW)
    released, credits, _ = _wire_route(monkeypatch, db, payment=None)

    resp = await pr.clover_return("abcd1234")
    html = resp.body.decode()
    assert "Confirming your payment" in html
    assert released == [] and credits == []
    assert db.updates == []


@aio
async def test_verified_payment_releases_books_fee_and_texts_receipt(monkeypatch):
    monkeypatch.setenv("MERIDIAN_SERVICE_FEE_CENTS", "149")
    monkeypatch.setattr(pl, "FEE_SPLIT_ENABLED", False)
    db = _FakeDB(SESSION_ROW)
    released, credits, texts = _wire_route(
        monkeypatch, db, payment={"id": "PAY_77", "amount": 3529, "result": "SUCCESS"})

    resp = await pr.clover_return("abcd1234")
    html = resp.body.decode()
    assert "Payment received" in html

    assert released[0]["method"] == "clover"
    assert released[0]["payment_txn_id"] == "PAY_77"
    assert released[0]["pos_order_id"] == "POS9"

    assert credits[0][1] == 149
    assert credits[0][2] == "clover_native_fee"
    assert credits[0][3] == "PAY_77"          # idempotency ref = payment id

    assert db.updates[0][1] == {"status": "paid"}
    assert texts[0][0] == "+16045551234"
    assert "Payment received" in texts[0][1]


@aio
async def test_already_paid_session_short_circuits(monkeypatch):
    db = _FakeDB({**SESSION_ROW, "status": "paid"})
    released, credits, _ = _wire_route(
        monkeypatch, db, payment={"id": "PAY_77", "amount": 3529})

    resp = await pr.clover_return("abcd1234")
    assert "Payment received" in resp.body.decode()
    assert released == [] and credits == []   # no double release/fee


@aio
async def test_native_fee_split_math(monkeypatch):
    monkeypatch.setattr(pl, "FEE_SPLIT_ENABLED", True)
    fee = svc.clover_fee_cents({"amount_cents": 3529, "currency": "cad",
                                "payload": {"plan_tier": "premium"}})
    surcharge = pl.customer_surcharge_cents("premium", "cad")
    assert fee == pl.split_application_fee_cents(3529 - surcharge, surcharge)


def test_rep_fee_override_flows_through_clover_rail(monkeypatch):
    """PR #323's rep-negotiated order_fee_cents must replace the tier fee on
    the Clover rail too — in the charged cart line AND the settled ledger fee
    (read from the payload written at order time, so the booked fee always
    matches the surcharge actually charged)."""
    monkeypatch.setattr(pl, "FEE_SPLIT_ENABLED", True)

    items, _ = pl._clover_hco_line_items(dict(ORDER), plan_tier="premium",
                                         fee_override_cents=45)
    assert items[-1] == {"name": "Service & processing fee",
                         "price": 45 + pl.CUSTOMER_FIXED_FEE_CENTS, "unitQty": 1}

    fee = svc.clover_fee_cents({"amount_cents": 3529, "currency": "cad",
                                "payload": {"plan_tier": "premium",
                                            "fee_override_cents": 45}})
    surcharge = pl.customer_surcharge_cents("premium", "cad", override_cents=45)
    assert surcharge == 45 + pl.CUSTOMER_FIXED_FEE_CENTS
    assert fee == pl.split_application_fee_cents(3529 - surcharge, surcharge)
