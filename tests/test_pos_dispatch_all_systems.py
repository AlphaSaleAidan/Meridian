"""
Every POS connection type gets the paid mobile order — coverage for the
all-systems dispatch matrix.

  square  → first-class Square Order (fulfillment drives KDS/kitchen print),
            Meridian source name, PAID note, stable idempotency key.
  routing → square connections hit the Square submitter, not the generic
            connector (whose payload Square rejects).
  fallback → CSV-only systems and API failures deliver the full kitchen
            ticket by SMS, then email; killswitch stops even the fallback.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.services.pos_connectors import square_kitchen as sk  # noqa: E402
from src.services.pos_connectors import website_order_dispatch as wod  # noqa: E402

aio = pytest.mark.asyncio

PAID_ORDER = {
    "id": "abc12345-0000-0000-0000-000000000000",
    "merchant_id": "org-1",
    "website_id": "web-1",
    "customer_name": "Priya S",
    "customer_phone": "+16045551234",
    "order_type": "pickup",
    "items": [
        {"name": "Butter Chicken", "quantity": 2, "price": 15.5,
         "special_instructions": "no cilantro"},
        {"name": "Garlic Naan", "quantity": 1, "price": 3.0},
    ],
    "total": 34.0,
    "currency": "CAD",
    "status": "paid",
}


class _Resp:
    def __init__(self, status, data=None, text=""):
        self.status_code = status
        self._d = data or {}
        self.text = text

    def json(self):
        return self._d


class _Client:
    def __init__(self, calls, status=200):
        self.calls = calls
        self.status = status

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, json=None, headers=None):
        self.calls.append((url, json, headers))
        return _Resp(self.status, {"order": {"id": "SQ_ORD_9"}})


# ── square_kitchen ────────────────────────────────────────────


@aio
async def test_square_order_payload_is_valid_and_tagged(monkeypatch):
    calls = []
    monkeypatch.setattr(sk.httpx, "AsyncClient", lambda timeout=None: _Client(calls))

    res = await sk.submit_square_kitchen_order(
        access_token="tok", location_id="LOC1",
        order={**PAID_ORDER, "order_ref": PAID_ORDER["id"]},
    )

    assert res == {"success": True, "pos_order_id": "SQ_ORD_9"}
    url, payload, headers = calls[0]
    assert url.endswith("/v2/orders")
    assert headers["Square-Version"]

    o = payload["order"]
    assert o["location_id"] == "LOC1"
    assert o["source"]["name"] == "Meridian Mobile Order"
    assert o["reference_id"].startswith("abc12345")
    # webhook retries can't create a second Square order
    assert payload["idempotency_key"] == f"mmo-{PAID_ORDER['id']}"[:45]

    li = o["line_items"]
    assert li[0]["quantity"] == "2"                       # string, per Square
    assert li[0]["base_price_money"] == {"amount": 1550, "currency": "CAD"}
    assert li[0]["note"] == "no cilantro"
    assert "note" not in li[1]

    f = o["fulfillments"][0]
    assert f["type"] == "PICKUP" and f["state"] == "PROPOSED"
    assert f["pickup_details"]["recipient"]["display_name"] == "Priya S"
    assert f["pickup_details"]["recipient"]["phone_number"] == "+16045551234"
    assert "PAID ONLINE (Stripe) — do not collect" in f["pickup_details"]["note"]
    assert f["pickup_details"]["pickup_at"]


@aio
async def test_square_delivery_order_uses_delivery_fulfillment(monkeypatch):
    calls = []
    monkeypatch.setattr(sk.httpx, "AsyncClient", lambda timeout=None: _Client(calls))
    await sk.submit_square_kitchen_order(
        access_token="tok", location_id="LOC1",
        order={**PAID_ORDER, "order_type": "delivery"},
    )
    f = calls[0][1]["order"]["fulfillments"][0]
    assert f["type"] == "DELIVERY" and f["delivery_details"]["deliver_at"]


@aio
async def test_square_missing_location_refused_before_http(monkeypatch):
    calls = []
    monkeypatch.setattr(sk.httpx, "AsyncClient", lambda timeout=None: _Client(calls))
    res = await sk.submit_square_kitchen_order(
        access_token="tok", location_id="", order=PAID_ORDER)
    assert res == {"success": False, "reason": "square_missing_location_id"}
    assert calls == []


def test_square_sandbox_env_switches_base(monkeypatch):
    monkeypatch.setenv("SQUARE_ENVIRONMENT", "sandbox")
    assert sk.square_api_base() == "https://connect.squareupsandbox.com"
    monkeypatch.delenv("SQUARE_ENVIRONMENT")
    assert sk.square_api_base() == "https://connect.squareup.com"


# ── dispatch routing ──────────────────────────────────────────


def _silence(monkeypatch):
    async def silent(_oid, _res):
        pass
    monkeypatch.setattr(wod, "_record_outcome", silent)


@aio
async def test_square_connection_routes_to_square_submitter(monkeypatch):
    monkeypatch.delenv("POS_ORDERS_DISABLED", raising=False)
    _silence(monkeypatch)

    async def conn(_):
        return {"system": "square-for-restaurants", "token": "tok",
                "external_merchant_id": "SQ_M", "location_id": "LOC1"}
    monkeypatch.setattr(wod, "_resolve_connection", conn)

    seen = {}

    async def fake_square(**kw):
        seen.update(kw)
        return {"success": True, "pos_order_id": "SQ_ORD_1"}
    monkeypatch.setattr(wod, "submit_square_kitchen_order", fake_square)

    res = await wod.dispatch_website_order_to_pos(dict(PAID_ORDER))
    assert res["dispatched"] is True and res["method"] == "api"
    assert res["pos_system"] == "square"          # alias resolved
    assert res["pos_order_id"] == "SQ_ORD_1"
    assert seen["location_id"] == "LOC1"
    assert seen["source_tag"] == "Meridian Mobile Order"


@aio
async def test_csv_only_system_goes_straight_to_notify(monkeypatch):
    """'cake' has no order API — the ticket must reach the merchant by
    SMS/email instead of being dropped."""
    monkeypatch.delenv("POS_ORDERS_DISABLED", raising=False)
    _silence(monkeypatch)

    async def conn(_):
        return {"system": "cake", "token": "tok",
                "external_merchant_id": "C_M", "location_id": ""}
    monkeypatch.setattr(wod, "_resolve_connection", conn)

    async def fake_notify(order_row, api_reason):
        assert api_reason == "no_order_api:cake"
        return {"delivered": True, "method": "sms"}
    monkeypatch.setattr(wod, "_notify_merchant", fake_notify)

    res = await wod.dispatch_website_order_to_pos(dict(PAID_ORDER))
    assert res["dispatched"] is True and res["method"] == "sms"


# ── notify fallback delivery chain ────────────────────────────


@aio
async def test_notify_sends_full_ticket_by_sms(monkeypatch):
    async def contact(_):
        return {"phone": "+16045550000", "email": "owner@resto.ca", "name": "Maple Tandoor"}
    monkeypatch.setattr(wod, "_merchant_contact", contact)

    sent = {}

    async def fake_sms(phone, message):
        sent["phone"], sent["message"] = phone, message
        return {"sent": True, "method": "telnyx"}
    import src.sms.client as sms_client
    monkeypatch.setattr(sms_client, "send_sms", fake_sms)

    res = await wod._notify_merchant(dict(PAID_ORDER), "clover_order_http_500")
    assert res == {"delivered": True, "method": "sms"}
    assert sent["phone"] == "+16045550000"
    assert "NEW PAID MOBILE ORDER — Maple Tandoor" in sent["message"]
    assert "2x Butter Chicken — no cilantro" in sent["message"]
    assert "PAID ONLINE (Stripe) — do not collect" in sent["message"]


@aio
async def test_notify_falls_back_to_email_when_sms_fails(monkeypatch):
    async def contact(_):
        return {"phone": "+16045550000", "email": "owner@resto.ca", "name": "Maple Tandoor"}
    monkeypatch.setattr(wod, "_merchant_contact", contact)

    async def sms_down(phone, message):
        return {"sent": False, "method": "none", "reason": "not_configured"}
    import src.sms.client as sms_client
    monkeypatch.setattr(sms_client, "send_sms", sms_down)

    emails = []

    class FakePostal:
        async def send(self, to, subject, html, **kw):
            emails.append((to, subject, html))
            return {"status": "sent", "id": "em1"}
    import src.email.postal_client as pc
    monkeypatch.setattr(pc, "PostalClient", FakePostal)

    res = await wod._notify_merchant(dict(PAID_ORDER), "no_pos_connection")
    assert res == {"delivered": True, "method": "email"}
    to, subject, html = emails[0]
    assert to == "owner@resto.ca"
    assert "PAID mobile order" in subject
    assert "Butter Chicken" in html


@aio
async def test_notify_without_contact_reports_undeliverable(monkeypatch):
    async def contact(_):
        return {"phone": "", "email": "", "name": ""}
    monkeypatch.setattr(wod, "_merchant_contact", contact)
    res = await wod._notify_merchant(dict(PAID_ORDER), "no_pos_connection")
    assert res == {"delivered": False, "reason": "no_merchant_contact"}


@aio
async def test_killswitch_blocks_api_and_notify(monkeypatch):
    monkeypatch.setenv("POS_ORDERS_DISABLED", "1")
    _silence(monkeypatch)

    async def boom(*a, **k):
        raise AssertionError("nothing may run under the killswitch")
    monkeypatch.setattr(wod, "_resolve_connection", boom)
    monkeypatch.setattr(wod, "_notify_merchant", boom)

    res = await wod.dispatch_website_order_to_pos(dict(PAID_ORDER))
    assert res == {"dispatched": False, "reason": "pos_orders_disabled"}
