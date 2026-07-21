"""
Phone orders to Clover must ride the SAME kitchen path website orders use.

The generic dispatcher previously pushed Clover phone orders through the
single-POST /atomic_order/orders endpoint: no per-unit line items, no
print_event, so nothing ever printed in the kitchen. create_pos_order now
routes system_key == "clover" through submit_clover_kitchen_order (tag +
kitchen note + inventory mapping + print), keeping the dispatcher's existing
API → SMS → email fallback chain for failures.
"""
import pytest

from src.services.pos_connectors import order_dispatcher as od
from src.services.pos_connectors.base import POSConnectionConfig

aio = pytest.mark.asyncio

ORDER = {
    "customer_name": "Caller One",
    "order_type": "pickup",
    "items": [{"name": "Pad Thai", "quantity": 2, "price": 14.0}],
    "special_instructions": "extra lime",
    "merchant_phone": "+16045550000",
    "merchant_email": "owner@example.com",
    "merchant_name": "Thai Place",
}


def _config(org_id="org-uuid-1"):
    return POSConnectionConfig(
        system_key="clover",
        system_name="Clover",
        tier=1,
        auth_method="bearer",
        base_url="https://api.clover.com/v3/merchants/{merchant_id}",
        credentials={"access_token": "tok-123", "merchant_id": "EXTMID1"},
        merchant_id="EXTMID1",
        org_id=org_id,
        supports_order_creation=True,
        order_creation_endpoint="/atomic_order/orders",
    )


def _patch_kitchen(monkeypatch, result, calls):
    import src.services.pos_connectors.clover_kitchen as ck

    async def fake_submit(**kw):
        calls.append(kw)
        return result
    monkeypatch.setattr(ck, "submit_clover_kitchen_order", fake_submit)


def _patch_inventory_map(monkeypatch, mapping, calls):
    import src.services.pos_connectors.website_order_dispatch as wod

    async def fake_map(org_id):
        calls.append(org_id)
        return mapping
    monkeypatch.setattr(wod, "_clover_inventory_map", fake_map)


@aio
async def test_clover_phone_order_routes_through_kitchen_submitter(monkeypatch):
    kitchen_calls, map_calls = [], []
    _patch_kitchen(monkeypatch, {"success": True, "pos_order_id": "CLV_PH_1",
                                 "kitchen_print_fired": True}, kitchen_calls)
    _patch_inventory_map(monkeypatch, {"pad thai": "ITEM9"}, map_calls)

    res = await od.create_pos_order("clover", dict(ORDER), config=_config())

    assert res.success is True
    assert res.order_id == "CLV_PH_1"
    assert res.pos_system == "clover"
    assert len(kitchen_calls) == 1
    kw = kitchen_calls[0]
    assert kw["access_token"] == "tok-123"
    assert kw["external_merchant_id"] == "EXTMID1"
    assert kw["source_tag"] == "Meridian Phone Order"
    assert kw["item_id_map"] == {"pad thai": "ITEM9"}
    assert map_calls == ["org-uuid-1"]


@aio
async def test_clover_kitchen_failure_falls_to_notify_chain(monkeypatch):
    kitchen_calls = []
    _patch_kitchen(monkeypatch, {"success": False, "reason": "clover_order_http_401"},
                   kitchen_calls)
    _patch_inventory_map(monkeypatch, {}, [])

    fallback_calls = []

    async def fake_fallback(system_key, order_data, api_config, api_result=None):
        fallback_calls.append((system_key, api_result))
        from src.services.pos_connectors.base import OrderResult
        return OrderResult(success=True, order_id="FB1", pos_system=system_key,
                           fallback_used=True)
    monkeypatch.setattr(od, "_fallback_order", fake_fallback)

    res = await od.create_pos_order("clover", dict(ORDER), config=_config())

    assert res.fallback_used is True
    assert fallback_calls and fallback_calls[0][0] == "clover"
    assert "clover_order_http_401" in str(fallback_calls[0][1])


@aio
async def test_non_clover_never_touches_kitchen_submitter(monkeypatch):
    kitchen_calls = []
    _patch_kitchen(monkeypatch, {"success": True, "pos_order_id": "X"}, kitchen_calls)

    class _FakeConnector:
        def __init__(self, *a, **k):
            pass

        async def create_order(self, order_data):
            from src.services.pos_connectors.base import OrderResult
            return OrderResult(success=True, order_id="SQ1", pos_system="square")
    monkeypatch.setattr(od, "GenericRESTConnector", _FakeConnector)

    cfg = _config()
    cfg = POSConnectionConfig(**{**cfg.__dict__, "system_key": "square"})
    res = await od.create_pos_order("square", dict(ORDER), config=cfg)

    assert res.success is True
    assert kitchen_calls == []


@aio
async def test_missing_org_id_skips_inventory_map_but_still_submits(monkeypatch):
    kitchen_calls, map_calls = [], []
    _patch_kitchen(monkeypatch, {"success": True, "pos_order_id": "CLV_PH_2"},
                   kitchen_calls)
    _patch_inventory_map(monkeypatch, {"x": "y"}, map_calls)

    res = await od.create_pos_order("clover", dict(ORDER), config=_config(org_id=""))

    assert res.success is True
    assert map_calls == []
    assert kitchen_calls[0]["item_id_map"] == {}
