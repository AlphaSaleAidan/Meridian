"""
Clover-native pay-by-text (Hosted Checkout) — experimental rail coverage.

Money invariants under test:
  1. TWO independent gates (global env + per-merchant column), both default
     OFF, tested in BOTH directions — one flag alone never routes native.
  2. Native failure falls through to the Stripe rail (no stranded orders).
  3. The Hosted Checkout cart charges items + the fee-split surcharge line.
  4. The success REDIRECT alone never marks an order paid — only a payment
     verified against the merchant's Clover does. Fee is booked to the voice
     ledger only on verification.
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

aio = pytest.mark.asyncio

CLOVER_CFG = SimpleNamespace(
    pos_system="clover", pos_access_token="clov_tok", pos_location_id="CLV_MID",
    native_pos_pay=True, plan_tier="", stripe_account_id="", stripe_charges_enabled=False,
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


class _Resp:
    def __init__(self, status, data=None):
        self.status_code = status
        self._d = data or {}
        self.text = ""

    def json(self):
        return self._d


class _Client:
    def __init__(self, calls, status=200, data=None):
        self.calls = calls
        self.status = status
        self.data = data if data is not None else {
            "href": "https://www.clover.com/checkout/CHK123",
            "checkoutSessionId": "CHK123",
        }

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, json=None, headers=None):
        self.calls.append((url, json, headers))
        return _Resp(self.status, self.data)


# ── gating: both directions ───────────────────────────────────


@aio
async def test_native_rail_needs_both_gates(monkeypatch):
    async def native(*a, **k):
        return {"method": "clover_native", "url": "x"}

    async def stripe(*a, **k):
        return {"method": "stripe", "url": "s"}
    monkeypatch.setattr(pl, "_clover_hosted_checkout", native)
    monkeypatch.setattr(pl, "_stripe_checkout", stripe)
    monkeypatch.setattr(pl, "UNIFIED_PAYMENTS_ENABLED", True)
    monkeypatch.setattr(pl, "STRIPE_SECRET_KEY", "sk_x")

    # global OFF + merchant ON → stripe
    monkeypatch.setattr(pl, "CLOVER_NATIVE_PAY_ENABLED", False)
    res = await pl.create_checkout(dict(ORDER), CLOVER_CFG)
    assert res["method"] == "stripe"

    # global ON + merchant OFF → stripe
    monkeypatch.setattr(pl, "CLOVER_NATIVE_PAY_ENABLED", True)
    cfg_off = SimpleNamespace(**{**CLOVER_CFG.__dict__, "native_pos_pay": False})
    res = await pl.create_checkout(dict(ORDER), cfg_off)
    assert res["method"] == "stripe"

    # both ON + clover → native
    res = await pl.create_checkout(dict(ORDER), CLOVER_CFG)
    assert res["method"] == "clover_native"

    # both ON but NOT a clover merchant → stripe
    cfg_sq = SimpleNamespace(**{**CLOVER_CFG.__dict__, "pos_system": "square"})
    res = await pl.create_checkout(dict(ORDER), cfg_sq)
    assert res["method"] == "stripe"


@aio
async def test_native_failure_falls_back_to_stripe(monkeypatch):
    async def native_boom(*a, **k):
        raise RuntimeError("clover_hco_http_500")

    async def stripe(*a, **k):
        return {"method": "stripe", "url": "s"}
    monkeypatch.setattr(pl, "_clover_hosted_checkout", native_boom)
    monkeypatch.setattr(pl, "_stripe_checkout", stripe)
    monkeypatch.setattr(pl, "CLOVER_NATIVE_PAY_ENABLED", True)
    monkeypatch.setattr(pl, "UNIFIED_PAYMENTS_ENABLED", True)
    monkeypatch.setattr(pl, "STRIPE_SECRET_KEY", "sk_x")

    res = await pl.create_checkout(dict(ORDER), CLOVER_CFG)
    assert res["method"] == "stripe"


# ── hosted checkout payload ───────────────────────────────────


@aio
async def test_hco_payload_cart_fee_line_and_redirects(monkeypatch):
    calls = []
    monkeypatch.setattr(pl.httpx, "AsyncClient", lambda timeout=None: _Client(calls))
    monkeypatch.setattr(pl, "FEE_SPLIT_ENABLED", True)

    async def recorded(*a, **k):
        assert k.get("provider") == "clover_hco"
        return True
    monkeypatch.setattr(pl, "_record_checkout_session", recorded)

    res = await pl._clover_hosted_checkout(dict(ORDER), CLOVER_CFG, "")

    url, payload, headers = calls[0]
    assert url.endswith("/invoicingcheckoutservice/v1/checkouts")
    assert headers["X-Clover-Merchant-Id"] == "CLV_MID"

    items = payload["shoppingCart"]["lineItems"]
    assert items[0] == {"name": "Butter Chicken", "unitQty": 2, "price": 1550}
    # fee-split surcharge rides as its own line so we can reclaim it
    assert items[-1]["name"] == "Service & processing fee"
    assert items[-1]["price"] == pl.customer_surcharge_cents("", "cad")

    assert payload["customer"]["firstName"] == "Priya"
    assert payload["customer"]["phoneNumber"] == "+16045551234"
    assert "/pay/clover/return/" in payload["redirectUrls"]["success"]
    assert payload["redirectUrls"]["cancel"].endswith("/pay/cancel")

    assert res["method"] == "clover_native"
    assert res["session_id"] == "CHK123"
    assert "/p/" in res["url"]  # branded short link when recorded


@aio
async def test_hco_missing_credentials_raises(monkeypatch):
    cfg = SimpleNamespace(pos_access_token="", pos_location_id="", plan_tier="")
    with pytest.raises(RuntimeError):
        await pl._clover_hosted_checkout(dict(ORDER), cfg, "")


# ── return route: verification is the gate, not the redirect ──


SESSION_ROW = {
    "merchant_id": "org-1", "pos_order_id": "POS9", "provider": "clover_hco",
    "provider_ref": "CHK123", "amount_cents": 3529, "currency": "cad",
    "status": "created", "caller_phone": "+16045551234",
    "created_at": "2026-07-14T20:00:00+00:00",
}


class _FakeDB:
    def __init__(self, row):
        self.row = row
        self.updates = []

    async def select(self, table, columns=None, filters=None, limit=None):
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

    import src.sms.client as sms
    texts = []

    async def fake_sms(phone, message):
        texts.append((phone, message))
        return {"sent": True}
    monkeypatch.setattr(sms, "send_sms", fake_sms)
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

    class _NoCfgDB:
        async def select(self, *a, **k):
            return []
    monkeypatch.setattr(pr, "get_db", lambda: _NoCfgDB())
    fee = await pr._clover_native_fee_cents({"amount_cents": 3529, "currency": "cad"})
    surcharge = pl.customer_surcharge_cents("", "cad")
    assert fee == pl.split_application_fee_cents(3529 - surcharge, surcharge)
