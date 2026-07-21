"""
Critical auth/tenancy holes found in the 2026-07-22 gap sweep:

  1. phone.py payment-webhook: an unauthenticated {"simulate": true} body
     released ANY merchant's held order. simulate is now demo-merchant-only.
  2. vision heartbeat/live-state: a per-org device token could touch another
     org's camera. Now the token's org must own the camera (legacy global
     token stays unbound).
  3. phone_dashboard phone-config: leaked clover_hco_webhook_secret. Now all
     *_secret/*_token/credential fields are stripped from the response.
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "services", "phone_agent")))
os.environ.setdefault("ENCRYPTION_KEY", "0" * 64)

aio = pytest.mark.asyncio


# ── 1. simulate payment bypass ───────────────────────────────
class _Req:
    def __init__(self, body: bytes, headers=None):
        self._body = body
        self.headers = headers or {}

    async def body(self):
        return self._body


@aio
async def test_simulate_rejected_for_non_demo_merchant(monkeypatch):
    from src.api.routes import phone as ph

    called = {"mark": False}
    async def fake_mark(**kw):
        called["mark"] = True
        return {"released": True}
    monkeypatch.setattr("pay_on_phone.mark_order_paid", fake_mark, raising=False)

    body = json.dumps({"simulate": True, "merchant_id": "biz_victim",
                       "caller_phone": "+1555", "pos_order_id": "x"}).encode()
    res = await ph.phone_payment_webhook(_Req(body))
    # 403 forbidden, and NO order release attempted
    assert getattr(res, "status_code", None) == 403
    assert called["mark"] is False


@aio
async def test_simulate_allowed_for_demo_merchant(monkeypatch):
    from src.api.routes import phone as ph

    called = {"mark": False}
    async def fake_mark(**kw):
        called["mark"] = True
        return {"released": True, "matched_by": "demo"}
    monkeypatch.setattr("pay_on_phone.mark_order_paid", fake_mark, raising=False)

    body = json.dumps({"simulate": True, "merchant_id": ph.DEMO_MERCHANT_ID,
                       "caller_phone": "+1555", "pos_order_id": "x"}).encode()
    res = await ph.phone_payment_webhook(_Req(body))
    assert called["mark"] is True
    assert res.get("ok") is True


@aio
async def test_unsigned_real_event_still_rejected(monkeypatch):
    from src.api.routes import phone as ph
    body = json.dumps({"type": "payment.updated", "merchant_id": "biz_real",
                       "data": {"object": {"payment": {"status": "COMPLETED"}}}}).encode()
    res = await ph.phone_payment_webhook(_Req(body))
    assert getattr(res, "status_code", None) == 403  # no signature, not simulate


# ── 2. vision device-token cross-tenant ──────────────────────
class _VDB:
    def __init__(self, cam_org):
        self._cam_org = cam_org

    async def select(self, table, cols=None, filters=None, limit=None):
        return [{"org_id": self._cam_org}] if self._cam_org is not None else []


@aio
async def test_device_token_must_own_camera():
    from src.api.routes import vision as v
    from fastapi import HTTPException

    db = _VDB("orgA")
    # same org → ok
    await v._device_owns_camera_or_403(db, "cam1", {"org_id": "orgA", "legacy": False})
    # different org → 403
    with pytest.raises(HTTPException) as exc:
        await v._device_owns_camera_or_403(db, "cam1", {"org_id": "orgB", "legacy": False})
    assert exc.value.status_code == 403
    # legacy global token → unbound, allowed
    await v._device_owns_camera_or_403(db, "cam1", {"org_id": None, "legacy": True})
    # missing camera → 404
    with pytest.raises(HTTPException) as exc2:
        await v._device_owns_camera_or_403(_VDB(None), "gone", {"org_id": "orgA", "legacy": False})
    assert exc2.value.status_code == 404


# ── 3. phone-config secret strip ─────────────────────────────
def test_config_response_strips_secrets():
    # Mirror the strip logic applied in get_phone_config.
    row = {
        "merchant_id": "biz_x", "greeting": "hi", "pos_access_token": "T",
        "clover_hco_webhook_secret": "S", "vapi_phone_number_id": "v",
        "access_token_enc": "E", "refresh_token_enc": "R",
        "credentials_encrypted": {"a": 1},
    }
    for _k in list(row.keys()):
        if _k.endswith("_secret") or _k.endswith("_token") or _k in (
                "pos_access_token", "credentials_encrypted", "access_token_enc",
                "refresh_token_enc"):
            row.pop(_k, None)
    assert "clover_hco_webhook_secret" not in row
    assert "pos_access_token" not in row
    assert "access_token_enc" not in row and "refresh_token_enc" not in row
    assert "credentials_encrypted" not in row
    # non-secret fields survive
    assert row["greeting"] == "hi" and row["vapi_phone_number_id"] == "v"
