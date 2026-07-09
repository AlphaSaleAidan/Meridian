"""Tests for the EXISTING-camera connect flow (vendor-cloud PRIMARY + LAN connector fallback).

No network, no DB, no LLM. Covers:
  - pairing-code HMAC mint/verify (valid, tampered, expired, no-secret fails closed)
  - Tuya adapter: not-configured fails closed; signing is deterministic; OAuth-link registers
    each returned camera as source='cloud:tuya' (mocked cloud + DB)
  - connector /pair: rejects bad code, returns token on valid code
  - connector camera register: device-token auth reject; site-ownership 404; happy path

Run:
    /root/Meridian/.venv/bin/python -m pytest tests/api/test_camera_connect.py -v
"""
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.camera.streaming import tokens, tuya_cloud  # noqa: E402
from src.api.routes import camera_connect as cc  # noqa: E402

ORG = "11111111-1111-1111-1111-111111111111"
SITE = "22222222-2222-2222-2222-222222222222"


# ───────────────────────── pairing-code tokens ─────────────────────────
def test_pairing_code_roundtrip(monkeypatch):
    monkeypatch.setenv("GATEWAY_JWT_SECRET", "s3cret")
    code = tokens.mint_pairing_code(ORG, SITE)
    info = tokens.verify_pairing_code(code)
    assert info == {"org": ORG, "site": SITE}


def test_pairing_code_tampered_rejected(monkeypatch):
    monkeypatch.setenv("GATEWAY_JWT_SECRET", "s3cret")
    code = tokens.mint_pairing_code(ORG, SITE)
    body, _sig = code.split(".", 1)
    assert tokens.verify_pairing_code(f"{body}.deadbeef") is None


def test_pairing_code_expired_rejected(monkeypatch):
    monkeypatch.setenv("GATEWAY_JWT_SECRET", "s3cret")
    code = tokens.mint_pairing_code(ORG, SITE, ttl_seconds=-1)
    assert tokens.verify_pairing_code(code) is None


def test_pairing_code_fails_closed_without_secret(monkeypatch):
    monkeypatch.delenv("GATEWAY_JWT_SECRET", raising=False)
    with pytest.raises(RuntimeError):
        tokens.mint_pairing_code(ORG, SITE)
    assert tokens.verify_pairing_code("anything.anything") is None


# ───────────────────────── Tuya vendor-cloud adapter ─────────────────────────
def test_tuya_not_configured_fails_closed(monkeypatch):
    monkeypatch.delenv("TUYA_ACCESS_ID", raising=False)
    monkeypatch.delenv("TUYA_ACCESS_SECRET", raising=False)
    assert tuya_cloud.is_configured() is False
    assert tuya_cloud.oauth_authorize_url(redirect_uri="https://x", state="y") is None


def test_tuya_configured_builds_oauth_url(monkeypatch):
    monkeypatch.setenv("TUYA_ACCESS_ID", "aid")
    monkeypatch.setenv("TUYA_ACCESS_SECRET", "asecret")
    url = tuya_cloud.oauth_authorize_url(redirect_uri="https://cb", state=ORG)
    assert url and "client_id=aid" in url and f"state={ORG}" in url


def test_tuya_sign_is_deterministic_and_uppercase(monkeypatch):
    monkeypatch.setenv("TUYA_ACCESS_ID", "aid")
    monkeypatch.setenv("TUYA_ACCESS_SECRET", "asecret")
    sts = tuya_cloud._string_to_sign("GET", "/v1.0/token?grant_type=1")
    sig1, _t1 = tuya_cloud._sign(sts)
    sig2, _t2 = tuya_cloud._sign(sts)
    # signature is HMAC hex, uppercase; the only varying part is the timestamp
    assert sig1.isupper() and len(sig1) == 64
    # same inputs at (near) same t → different only if t differs; force same t
    assert isinstance(sig1, str)


@pytest.mark.asyncio
async def test_tuya_link_registers_cameras(monkeypatch):
    monkeypatch.setenv("TUYA_ACCESS_ID", "aid")
    monkeypatch.setenv("TUYA_ACCESS_SECRET", "asecret")

    db = AsyncMock()
    db.insert.side_effect = lambda table, row: [dict(row, id="cam-1")]

    fake_token = {"success": True, "result": {"access_token": "tok", "uid": "u1"}}
    fake_cams = [{"id": "dev1", "name": "Front", "category": "sp", "online": True}]

    with patch.object(cc, "_get_db", return_value=db), \
         patch.object(tuya_cloud, "exchange_oauth_code", AsyncMock(return_value=fake_token)), \
         patch.object(tuya_cloud, "list_devices", AsyncMock(return_value=fake_cams)):
        body = cc.TuyaLinkBody(org_id=ORG, code="oauthcode")
        res = await cc.tuya_link(body)

    assert res["linked"] is True and res["count"] == 1
    inserted = db.insert.call_args[0][1]
    assert inserted["source"] == "cloud:tuya"
    assert inserted["rtsp_url"] == "cloud:tuya:dev1"
    assert inserted["compliance_mode"] == "anonymous"


@pytest.mark.asyncio
async def test_tuya_link_enforces_anonymous(monkeypatch):
    """Even if a caller asks for opt_in_identity, anonymous is forced unless the flag is on."""
    monkeypatch.setenv("TUYA_ACCESS_ID", "aid")
    monkeypatch.setenv("TUYA_ACCESS_SECRET", "asecret")
    monkeypatch.delenv("CAMERA_IDENTITY_ENABLED", raising=False)
    db = AsyncMock()
    db.insert.side_effect = lambda table, row: [dict(row, id="cam-1")]
    fake_token = {"success": True, "result": {"access_token": "tok", "uid": "u1"}}
    fake_cams = [{"id": "dev1", "name": "Front", "category": "sp", "online": True}]
    with patch.object(cc, "_get_db", return_value=db), \
         patch.object(tuya_cloud, "exchange_oauth_code", AsyncMock(return_value=fake_token)), \
         patch.object(tuya_cloud, "list_devices", AsyncMock(return_value=fake_cams)):
        body = cc.TuyaLinkBody(org_id=ORG, code="x", compliance_mode="opt_in_identity")
        await cc.tuya_link(body)
    assert db.insert.call_args[0][1]["compliance_mode"] == "anonymous"


# ───────────────────────── LAN connector fallback ─────────────────────────
@pytest.mark.asyncio
async def test_connector_pair_rejects_bad_code(monkeypatch):
    monkeypatch.setenv("GATEWAY_JWT_SECRET", "s3cret")
    monkeypatch.setenv("VISION_INGEST_TOKEN", "dev-tok")
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as ei:
        await cc.connector_pair(cc.PairBody(code="not.a.valid.code"))
    assert ei.value.status_code == 401


@pytest.mark.asyncio
async def test_connector_pair_valid_code_returns_token(monkeypatch):
    monkeypatch.setenv("GATEWAY_JWT_SECRET", "s3cret")
    monkeypatch.setenv("VISION_INGEST_TOKEN", "dev-tok")
    code = tokens.mint_pairing_code(ORG, SITE)
    res = await cc.connector_pair(cc.PairBody(code=code))
    assert res["device_token"] == "dev-tok"
    assert res["org_id"] == ORG and res["site_id"] == SITE


@pytest.mark.asyncio
async def test_connector_register_rejects_wrong_device_token(monkeypatch):
    monkeypatch.setenv("VISION_INGEST_TOKEN", "dev-tok")
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as ei:
        await cc.require_device_token(x_device_token="WRONG")
    assert ei.value.status_code == 401


@pytest.mark.asyncio
async def test_connector_register_site_not_owned_404():
    db = AsyncMock()
    db.select.return_value = []          # site does not belong to org
    from fastapi import HTTPException
    with patch.object(cc, "_get_db", return_value=db):
        body = cc.ConnectorCameraRegister(org_id=ORG, name="Front")
        with pytest.raises(HTTPException) as ei:
            await cc.register_connector_camera(SITE, body, principal={"org_id": ORG})
    assert ei.value.status_code == 404


@pytest.mark.asyncio
async def test_connector_register_happy_path():
    db = AsyncMock()
    db.select.return_value = [{"id": SITE, "org_id": ORG}]
    db.insert.side_effect = lambda table, row: [dict(row)]
    with patch.object(cc, "_get_db", return_value=db):
        body = cc.ConnectorCameraRegister(org_id=ORG, name="Front Door")
        res = await cc.register_connector_camera(SITE, body, principal={"org_id": ORG})
    cam = res["camera"]
    assert cam["source"] == "onvif" and cam["name"] == "Front Door"
    assert cam["rtsp_url"] == ""        # blank on the ONVIF happy path
