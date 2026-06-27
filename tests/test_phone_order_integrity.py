"""Order-integrity regression tests.

Guards the rule: the phone agent must never confirm an order that didn't actually
reach the merchant. Previously the fallback dispatcher returned success=True even
when nothing was delivered ("queued"), so the caller heard a confirmation with a
fabricated order id while the order vanished.
"""

import pytest

from src.services.pos_connectors import order_dispatcher as od


@pytest.mark.asyncio
async def test_fallback_undelivered_is_failure(monkeypatch):
    """No POS API and no merchant phone/email → must report FAILURE."""
    async def _no_sms(_p, _m):
        return False

    async def _no_email(_e, _s, _b):
        return False

    monkeypatch.setattr(od, "_send_sms", _no_sms)
    monkeypatch.setattr(od, "_send_email", _no_email)

    res = await od._fallback_order("toast", {"items": [{"name": "Pizza", "quantity": 1}]}, {})
    assert res.success is False
    assert res.raw_response.get("delivery_method") == "none"


@pytest.mark.asyncio
async def test_fallback_sms_delivered_is_success(monkeypatch):
    """Order delivered to the merchant via SMS → success."""
    async def _ok_sms(_p, _m):
        return True

    monkeypatch.setattr(od, "_send_sms", _ok_sms)

    res = await od._fallback_order(
        "toast",
        {"items": [{"name": "Pizza", "quantity": 1}], "merchant_phone": "+15551234567"},
        {},
    )
    assert res.success is True
    assert res.raw_response.get("delivery_method") == "sms"


@pytest.mark.asyncio
async def test_fallback_sms_fail_no_email_is_failure(monkeypatch):
    """SMS send fails and no email on file → failure (nothing delivered)."""
    async def _bad_sms(_p, _m):
        return False

    monkeypatch.setattr(od, "_send_sms", _bad_sms)

    res = await od._fallback_order(
        "toast",
        {"items": [{"name": "Pizza", "quantity": 1}], "merchant_phone": "+15551234567"},
        {},
    )
    assert res.success is False
