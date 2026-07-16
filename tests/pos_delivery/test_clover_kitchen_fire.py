"""
CLOVER KITCHEN FIRE — verifier + phone_orders threading (no live calls).

Pins the two halves of the direct-injection prove-out that live OUTSIDE the
connector (connector-level print_event coverage: tests/test_clover_orders.py):

  1. pos_fulfillment._verify_clover: GET /v3/merchants/{mId}/orders/{id}
     ?expand=lineItems — open + line items ⇒ confirmed; 404 ⇒ unconfirmed;
     shape identical to the Square verifier so the "send test order" button
     proves the Clover leg end-to-end.
  2. Row threading: kitchen_fired flows into delivery_detail.pos.pos_result
     (support visibility) and sets fulfillment_state='kitchen_fired'.
"""
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PHONE_AGENT_DIR = str(_ROOT / "services" / "phone_agent")
if _PHONE_AGENT_DIR not in sys.path:
    sys.path.insert(0, _PHONE_AGENT_DIR)

import delivery_channels as dc  # noqa: E402
import pay_on_phone as pop  # noqa: E402

from src.services import pos_fulfillment as pf  # noqa: E402


# ─── Clover verifier ─────────────────────────────────────────────────────────


class _Resp:
    def __init__(self, status, data=None):
        self.status_code = status
        self._d = data or {}
        self.text = ""

    def json(self):
        return self._d


class _FakeCloverHTTP:
    """Stands in for httpx.AsyncClient — class-level script of GET responses."""
    responses: list[_Resp] = []
    calls: list[tuple] = []

    def __init__(self, *a, **kw):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, url, params=None, headers=None):
        cls = type(self)
        idx = min(len(cls.calls), len(cls.responses) - 1)
        cls.calls.append((url, params))
        return cls.responses[idx]


@pytest.fixture
def fake_clover(monkeypatch):
    _FakeCloverHTTP.responses = []
    _FakeCloverHTTP.calls = []
    monkeypatch.setattr(pf.httpx, "AsyncClient", _FakeCloverHTTP)
    monkeypatch.setenv("CLOVER_ENVIRONMENT", "production")
    monkeypatch.setenv("CLOVER_REGION", "na")
    monkeypatch.delenv("CLOVER_API_BASE", raising=False)
    return _FakeCloverHTTP


async def test_clover_verifier_confirms_open_order_with_items(fake_clover):
    fake_clover.responses = [
        _Resp(200, {"state": "open", "lineItems": {"elements": []}}),  # not ready
        _Resp(200, {"state": "open",
                    "lineItems": {"elements": [{"name": "Coke"}, {"name": "Pizza"}]}}),
    ]
    result = await pf.verify_fulfillment(
        "clover", "CLV1", "tok", "MID", attempts=3, delay_seconds=0,
    )
    assert result == {
        "supported": True, "confirmed": True, "state": "open",
        "detail": "2 line item(s)",
    }
    assert len(fake_clover.calls) == 2
    url, params = fake_clover.calls[0]
    assert url == "https://api.clover.com/v3/merchants/MID/orders/CLV1"
    assert params == {"expand": "lineItems"}


async def test_clover_verifier_missing_order_is_unconfirmed(fake_clover):
    fake_clover.responses = [_Resp(404)]
    result = await pf.verify_fulfillment(
        "clover", "CLVGONE", "tok", "MID", attempts=2, delay_seconds=0,
    )
    assert result["supported"] is True
    assert result["confirmed"] is False
    assert result["state"] == "not_found"
    assert len(fake_clover.calls) == 2  # kept polling through the 404s


async def test_clover_verifier_requires_token_and_merchant(fake_clover):
    no_tok = await pf.verify_fulfillment("clover", "CLV1", "", "MID", attempts=1)
    assert (no_tok["confirmed"], no_tok["state"]) == (False, "no_token")
    no_mid = await pf.verify_fulfillment("clover", "CLV1", "tok", "", attempts=1)
    assert (no_mid["confirmed"], no_mid["state"]) == (False, "no_merchant")
    assert fake_clover.calls == []  # never hit the API without creds


# ─── Row threading: kitchen_fired → phone_orders ─────────────────────────────


def _cfg(**kw):
    base = dict(
        merchant_id="m-clv-1",
        business_name="Clover Cafe",
        payment_mode="pay_at_pickup",
        sms_checkout_enabled=False,
        sms_pay_template="",
        transfer_number="",
        # POS leg only — SMS legs are covered by test_order_prove_out.py
        delivery_channels={"customer_sms": False, "merchant_sms": False},
        pos_system="clover",
        pos_access_token="tok",
        pos_location_id="MID",
        demo_safe=False,
        menu_items=[],
        language="en",
    )
    base.update(kw)
    return SimpleNamespace(**base)


def _order():
    return {
        "merchant_id": "m-clv-1",
        "customer_name": "Pat",
        "order_type": "pickup",
        "items": [{"name": "Coke", "quantity": 1, "unit_price": 3.0}],
        "subtotal": 3.0, "tax": 0.0, "total": 3.0,
        "currency": "usd",
        "delivery_address": "", "special_requests": "",
        "caller_phone": "",
        "pos_system": "clover",
    }


CLOVER_FIRED = {
    "success": True, "pos_order_id": "CLV1", "pos_system": "clover",
    "line_items_added": 1, "line_items_failed": 0,
    "kitchen_fired": True, "kitchen_fire_status": "200",
}


async def test_dispatch_threads_kitchen_fired_onto_row(monkeypatch):
    rows: list[dict] = []

    async def _fake_save(row):
        rows.append(row)
        return "row-uuid-clv"

    async def _fake_pos(order, config, pos_result=None):
        return dict(CLOVER_FIRED)

    monkeypatch.setattr(dc, "save_order_row", _fake_save)
    monkeypatch.setattr(pop, "save_order_row", _fake_save)
    monkeypatch.setattr(dc, "create_pos_for_config", _fake_pos)

    routed = await pop.dispatch_order(_order(), _cfg(), {"phone": ""})

    assert routed["pos_result"]["kitchen_fired"] is True
    row = rows[0]
    assert row["fulfillment_state"] == "kitchen_fired"
    # support sees the full kitchen-fire record in delivery_detail
    pos_detail = row["delivery_detail"]["pos"]["pos_result"]
    assert pos_detail["kitchen_fired"] is True
    assert pos_detail["kitchen_fire_status"] == "200"


async def test_dispatch_without_kitchen_fire_leaves_state_unset(monkeypatch):
    rows: list[dict] = []

    async def _fake_save(row):
        rows.append(row)
        return "row-uuid-clv2"

    async def _fake_pos(order, config, pos_result=None):
        return {**CLOVER_FIRED, "kitchen_fired": False, "kitchen_fire_status": "400"}

    monkeypatch.setattr(dc, "save_order_row", _fake_save)
    monkeypatch.setattr(pop, "save_order_row", _fake_save)
    monkeypatch.setattr(dc, "create_pos_for_config", _fake_pos)

    routed = await pop.dispatch_order(_order(), _cfg(), {"phone": ""})

    # order still succeeded — print failure is support-visible, not fatal
    assert routed["pos_result"]["success"] is True
    row = rows[0]
    assert "fulfillment_state" not in row  # verifier/webhook owns it from here
    assert row["delivery_detail"]["pos"]["pos_result"]["kitchen_fire_status"] == "400"
