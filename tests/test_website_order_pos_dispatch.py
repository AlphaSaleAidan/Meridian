"""
Website order → POS kitchen dispatch — coverage for the new write path.

Mocks httpx so no network. What must be right before this touches a real
Clover register:

  1. the Clover order carries the "Meridian Mobile Order" tag (title) and a
     kitchen note with customer / type / per-item instructions.
  2. one line-item POST PER UNIT (quantity expansion), item notes attached.
  3. a print_event fires the ticket to the kitchen printer; its failure is
     non-fatal (order already on the register).
  4. the dispatcher honors the POS_ORDERS_DISABLED killswitch, skips cleanly
     when no POS is connected, and records the outcome on the order row.
"""
import pytest

from src.services.pos_connectors import clover_kitchen as ck
from src.services.pos_connectors import website_order_dispatch as wod

aio = pytest.mark.asyncio

ORDER = {
    "id": "abc12345-0000-0000-0000-000000000000",
    "merchant_id": "org-1",
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


# ── clover_kitchen ────────────────────────────────────────────


def test_kitchen_note_contains_tag_customer_and_items():
    note = ck.build_kitchen_note(ORDER, "Meridian Mobile Order")
    assert "Meridian Mobile Order #ABC12345" in note
    assert "Priya S (+16045551234)" in note
    assert "Type: PICKUP" in note
    assert "2x Butter Chicken — no cilantro" in note
    assert "1x Garlic Naan" in note
    assert "34.00 CAD" in note
    assert "UNPAID" in note


@aio
async def test_clover_happy_path_tags_expands_qty_and_fires_kitchen(monkeypatch):
    calls = []
    _patch_client(monkeypatch, calls)

    res = await ck.submit_clover_kitchen_order(
        access_token="tok", external_merchant_id="MID",
        order={**ORDER, "order_ref": ORDER["id"]},
    )

    assert res == {
        "success": True, "pos_order_id": "CLV_ORD_1", "kitchen_print_fired": True,
        # no item_id_map passed → every line freeform, nothing booked to inventory
        "line_items_mapped": 0,
    }
    order_calls = [c for c in calls if c[0].endswith("/orders")]
    li_calls = [c for c in calls if "/line_items" in c[0]]
    print_calls = [c for c in calls if c[0].endswith("/print_event")]

    assert order_calls[0][1]["title"] == "Meridian Mobile Order — Priya S"
    assert "Meridian Mobile Order" in order_calls[0][1]["note"]
    assert order_calls[0][1]["state"] == "open"
    # ties the Clover order back to the Meridian order id (Square parity).
    # Clover's Invoice ID must be <=12 chars AND alphanumeric-only — a
    # hyphen (present in every UUID) 400s the ENTIRE order create with a
    # misleading length error (probed live 2026-07-21). Pin strip + cut.
    ref = order_calls[0][1]["externalReferenceId"]
    import re as _re
    assert ref == _re.sub(r"[^A-Za-z0-9]", "", ORDER["id"])[:12]
    assert len(ref) <= 12 and ref.isalnum()

    # 2x Butter Chicken + 1x Naan → 3 line-item POSTs, per unit
    assert len(li_calls) == 3
    butter = [c[1] for c in li_calls if c[1]["name"] == "Butter Chicken"]
    assert len(butter) == 2
    assert all(b["price"] == 1550 and b["note"] == "no cilantro" for b in butter)

    assert print_calls[0][1] == {"orderRef": {"id": "CLV_ORD_1"}}


@aio
async def test_print_event_failure_is_nonfatal(monkeypatch):
    calls = []
    _patch_client(monkeypatch, calls, print_status=500)

    res = await ck.submit_clover_kitchen_order(
        access_token="tok", external_merchant_id="MID", order=ORDER,
    )
    assert res["success"] is True
    assert res["kitchen_print_fired"] is False


@aio
async def test_order_create_failure_stops_before_line_items(monkeypatch):
    calls = []
    _patch_client(monkeypatch, calls, order_status=401)

    res = await ck.submit_clover_kitchen_order(
        access_token="tok", external_merchant_id="MID", order=ORDER,
    )
    assert res == {"success": False, "reason": "clover_order_http_401"}
    assert not [c for c in calls if "/line_items" in c[0]]
    assert not [c for c in calls if c[0].endswith("/print_event")]


@aio
async def test_missing_credentials_never_calls_http(monkeypatch):
    calls = []
    _patch_client(monkeypatch, calls)

    res = await ck.submit_clover_kitchen_order(
        access_token="  ", external_merchant_id="MID", order=ORDER,
    )
    assert res == {"success": False, "reason": "missing_clover_credentials"}
    assert calls == []


def test_sandbox_env_switches_base(monkeypatch):
    monkeypatch.setenv("CLOVER_ENVIRONMENT", "sandbox")
    assert ck.clover_api_base() == "https://apisandbox.dev.clover.com"
    monkeypatch.delenv("CLOVER_ENVIRONMENT")
    assert ck.clover_api_base() == "https://api.clover.com"


# ── website_order_dispatch ────────────────────────────────────


def _silence_recording(monkeypatch, sink):
    async def fake_record(order_id, result):
        sink.append((order_id, result))
    monkeypatch.setattr(wod, "_record_outcome", fake_record)


@aio
async def test_killswitch_blocks_before_connection_lookup(monkeypatch):
    monkeypatch.setenv("POS_ORDERS_DISABLED", "1")
    recorded = []
    _silence_recording(monkeypatch, recorded)

    async def boom(_):
        raise AssertionError("connection lookup must not run under killswitch")
    monkeypatch.setattr(wod, "_resolve_connection", boom)

    res = await wod.dispatch_website_order_to_pos(dict(ORDER))
    assert res == {"dispatched": False, "reason": "pos_orders_disabled"}
    assert recorded[0][1]["reason"] == "pos_orders_disabled"


@aio
async def test_no_connection_falls_back_to_merchant_notify(monkeypatch):
    """No POS connected is no longer a silent skip: the ticket goes to the
    merchant by SMS/email. With no contact either, it's a recorded failure."""
    monkeypatch.delenv("POS_ORDERS_DISABLED", raising=False)
    recorded = []
    _silence_recording(monkeypatch, recorded)

    async def none_conn(_):
        return None
    monkeypatch.setattr(wod, "_resolve_connection", none_conn)

    notified = []

    async def fake_notify(order_row, api_reason):
        notified.append(api_reason)
        return {"delivered": True, "method": "sms"}
    monkeypatch.setattr(wod, "_notify_merchant", fake_notify)

    res = await wod.dispatch_website_order_to_pos(dict(ORDER))
    assert res["dispatched"] is True and res["method"] == "sms"
    assert notified == ["no_pos_connection"]

    # and when the merchant has no contact info at all → failed, with reason
    async def no_contact(order_row, api_reason):
        return {"delivered": False, "reason": "no_merchant_contact"}
    monkeypatch.setattr(wod, "_notify_merchant", no_contact)
    res2 = await wod.dispatch_website_order_to_pos(dict(ORDER))
    assert res2["dispatched"] is False
    assert "no_pos_connection" in res2["reason"]


@aio
async def test_clover_connection_routes_to_kitchen_submitter(monkeypatch):
    monkeypatch.delenv("POS_ORDERS_DISABLED", raising=False)
    recorded = []
    _silence_recording(monkeypatch, recorded)

    async def conn(_):
        return {"system": "clover", "token": "tok",
                "external_merchant_id": "MID", "location_id": ""}
    monkeypatch.setattr(wod, "_resolve_connection", conn)

    seen = {}

    async def fake_submit(**kw):
        seen.update(kw)
        return {"success": True, "pos_order_id": "CLV_ORD_9",
                "kitchen_print_fired": True}
    monkeypatch.setattr(wod, "submit_clover_kitchen_order", fake_submit)

    res = await wod.dispatch_website_order_to_pos(dict(ORDER))

    assert res["dispatched"] is True
    assert res["pos_system"] == "clover"
    assert res["pos_order_id"] == "CLV_ORD_9"
    assert seen["source_tag"] == "Meridian Mobile Order"
    assert seen["access_token"] == "tok"
    assert seen["external_merchant_id"] == "MID"
    # outcome recorded against the website order row
    assert recorded[0][0] == ORDER["id"]
    assert recorded[0][1]["dispatched"] is True


@aio
async def test_clover_bank_rebrand_alias_still_routes_to_clover(monkeypatch):
    """fiserv-pos / pnc-pos etc. are Clover under the hood — the alias map
    must land them on the kitchen submitter, not the generic connector."""
    monkeypatch.delenv("POS_ORDERS_DISABLED", raising=False)
    _silence_recording(monkeypatch, [])

    async def conn(_):
        return {"system": "fiserv-pos", "token": "tok",
                "external_merchant_id": "MID", "location_id": ""}
    monkeypatch.setattr(wod, "_resolve_connection", conn)

    called = []

    async def fake_submit(**kw):
        called.append(kw)
        return {"success": True, "pos_order_id": "X", "kitchen_print_fired": True}
    monkeypatch.setattr(wod, "submit_clover_kitchen_order", fake_submit)

    res = await wod.dispatch_website_order_to_pos(dict(ORDER))
    assert res["dispatched"] is True and res["pos_system"] == "clover"
    assert called


@aio
async def test_clover_failure_falls_back_to_notify_then_reports(monkeypatch):
    monkeypatch.delenv("POS_ORDERS_DISABLED", raising=False)
    recorded = []
    _silence_recording(monkeypatch, recorded)

    async def conn(_):
        return {"system": "clover", "token": "tok",
                "external_merchant_id": "MID", "location_id": ""}
    monkeypatch.setattr(wod, "_resolve_connection", conn)

    async def fake_submit(**kw):
        return {"success": False, "reason": "clover_order_http_500"}
    monkeypatch.setattr(wod, "submit_clover_kitchen_order", fake_submit)

    # API failed but the merchant is reachable by SMS → still delivered
    async def fake_notify(order_row, api_reason):
        assert api_reason == "clover_order_http_500"
        return {"delivered": True, "method": "sms"}
    monkeypatch.setattr(wod, "_notify_merchant", fake_notify)

    res = await wod.dispatch_website_order_to_pos(dict(ORDER))
    assert res["dispatched"] is True and res["method"] == "sms"
    assert "clover_order_http_500" in res["delivery_note"]

    # API failed AND notify failed → recorded failure carrying both reasons
    async def notify_fail(order_row, api_reason):
        return {"delivered": False, "reason": "sms_and_email_failed"}
    monkeypatch.setattr(wod, "_notify_merchant", notify_fail)
    res2 = await wod.dispatch_website_order_to_pos(dict(ORDER))
    assert res2["dispatched"] is False
    assert "clover_order_http_500" in res2["reason"]


@aio
async def test_dispatch_never_raises(monkeypatch):
    """A bug anywhere in dispatch must not propagate into the ordering
    endpoint's task — the order row is already saved."""
    monkeypatch.delenv("POS_ORDERS_DISABLED", raising=False)
    recorded = []
    _silence_recording(monkeypatch, recorded)

    async def explode(_):
        raise RuntimeError("db is down")
    monkeypatch.setattr(wod, "_resolve_connection", explode)

    res = await wod.dispatch_website_order_to_pos(dict(ORDER))
    assert res["dispatched"] is False
    assert "db is down" in res["reason"]


# ── order-time token resolution: expiring Clover v2 (1-click OAuth) tokens ──
#
# The 1-click connect path stores a ~30-minute access token + refresh token.
# _connection_token must refresh Clover rows inline (via ensure_fresh_clover_token)
# or a merchant who OAuth-connected would receive orders for half an hour and
# then silently fall to the SMS path forever. Non-Clover rows and legacy
# (non-expiring) Clover rows must NOT touch the refresh machinery.

def _patch_token_helpers(monkeypatch, refresh_calls, refresh_result="fresh-tok"):
    import src.clover.oauth as clover_oauth
    import src.api.routes.phone_dashboard as pd

    async def fake_refresh(conn):
        refresh_calls.append(conn)
        if isinstance(refresh_result, Exception):
            raise refresh_result
        return refresh_result
    monkeypatch.setattr(clover_oauth, "ensure_fresh_clover_token", fake_refresh)
    monkeypatch.setattr(pd, "_decrypt_connection_token", lambda conn: "stored-tok")


@aio
async def test_clover_v2_connection_refreshes_inline(monkeypatch):
    refresh_calls = []
    _patch_token_helpers(monkeypatch, refresh_calls)
    conn = {"id": "c1", "provider": "clover", "refresh_token_enc": "enc-rt",
            "access_token_enc": "enc-at"}
    assert await wod._connection_token(conn) == "fresh-tok"
    assert refresh_calls == [conn]


@aio
async def test_legacy_clover_connection_skips_refresh(monkeypatch):
    refresh_calls = []
    _patch_token_helpers(monkeypatch, refresh_calls)
    conn = {"id": "c2", "provider": "clover", "access_token_enc": "enc-at"}
    assert await wod._connection_token(conn) == "stored-tok"
    assert refresh_calls == []


@aio
async def test_non_clover_connection_never_touches_clover_refresh(monkeypatch):
    refresh_calls = []
    _patch_token_helpers(monkeypatch, refresh_calls)
    conn = {"id": "c3", "provider": "square", "refresh_token_enc": "enc-rt",
            "access_token_enc": "enc-at"}
    assert await wod._connection_token(conn) == "stored-tok"
    assert refresh_calls == []


@aio
async def test_refresh_failure_falls_back_to_stored_token(monkeypatch):
    refresh_calls = []
    _patch_token_helpers(monkeypatch, refresh_calls,
                         refresh_result=RuntimeError("clover 503"))
    conn = {"id": "c4", "provider": "clover", "refresh_token_enc": "enc-rt",
            "access_token_enc": "enc-at"}
    assert await wod._connection_token(conn) == "stored-tok"
    assert len(refresh_calls) == 1
