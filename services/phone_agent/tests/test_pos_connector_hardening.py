"""
Phone-sidecar POS hardening (2026-07-22 sweep):
  - Square Orders host honors SQUARE_ENVIRONMENT (no firing sandbox merchants
    at the production POS).
  - Toast routes to the notification fallback (its direct writer sends the
    wrong payload shape and 4xx's) instead of a doomed direct call.
"""
import os
import sys

import pytest

_HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, "..")))

import pos_connector as pc  # noqa: E402

aio = pytest.mark.asyncio


def test_square_url_prod_default(monkeypatch):
    monkeypatch.delenv("SQUARE_ENVIRONMENT", raising=False)
    assert pc._square_orders_url() == "https://connect.squareup.com/v2/orders"


def test_square_url_sandbox(monkeypatch):
    monkeypatch.setenv("SQUARE_ENVIRONMENT", "sandbox")
    assert pc._square_orders_url() == "https://connect.squareupsandbox.com/v2/orders"


def test_toast_not_in_direct_systems():
    assert "toast" not in pc.DIRECT_API_SYSTEMS
    assert {"square", "clover"} <= pc.DIRECT_API_SYSTEMS


@aio
async def test_toast_routes_to_notification(monkeypatch):
    monkeypatch.delenv("POS_ORDERS_DISABLED", raising=False)
    calls = {"toast": False, "notify": False}

    async def fake_toast(*a, **k):
        calls["toast"] = True
        return {"success": True}

    async def fake_notify(order, pos_system):
        calls["notify"] = True
        return {"success": True, "method": "notification"}

    monkeypatch.setattr(pc, "_create_toast_order", fake_toast, raising=False)
    monkeypatch.setattr(pc, "_create_notification_order", fake_notify)

    res = await pc.create_pos_order(
        {"items": [{"name": "X", "quantity": 1}], "merchant_id": "biz_x"},
        "toast", access_token="tok", location_id="loc",
    )
    assert calls["notify"] is True and calls["toast"] is False
    assert res.get("method") == "notification"
