"""
Security batch (2026-07-15 bug hunt) — each test pins one hole closed:

  A. POS webhook connection lookup DECRYPTS the access token (raw ciphertext
     silently broke Square/Toast/Clover order sync).
  B. Admin / service-token auth uses constant-time compare (no timing leak).
  C. SMS inbound webhook verifies the Twilio signature (no order injection /
     credit drain from a forged POST).
  D. SMS inbound honors a prior marketing opt-out before replying (CASL).
"""
import base64
import hashlib
import hmac
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
_PA = str(Path(__file__).resolve().parents[1] / "services" / "phone_agent")
if _PA not in sys.path:
    sys.path.insert(0, _PA)

aio = pytest.mark.asyncio


# ── A. POS webhook token decryption ───────────────────────────


def test_webhook_conn_token_is_decrypted(monkeypatch):
    monkeypatch.setenv("ENCRYPTION_KEY", "0" * 64)   # 32-byte hex test key
    import src.security.encryption as enc_mod
    # reset the module-level cipher cache so it picks up the test key
    enc_mod._AESGCM_INSTANCE = None
    enc_mod._ENCRYPTION_KEY_HEX = None
    import src.api.routes.webhooks as wh
    from src.security.encryption import encrypt_token

    plain = "FAKE-pos-token-for-test"
    enc = encrypt_token(plain)
    assert enc != plain and ":" in enc          # actually ciphertext
    assert wh._decrypt_conn_token({"access_token_enc": enc}) == plain
    # credentials_encrypted dict shape
    enc2 = encrypt_token("api-key-123")
    assert wh._decrypt_conn_token({"credentials_encrypted": {"access_token": enc2}}) == "api-key-123"
    # legacy/garbage ciphertext → "" (never the raw ciphertext)
    assert wh._decrypt_conn_token({"access_token_enc": "not-encrypted"}) == ""
    assert wh._decrypt_conn_token({}) == ""


# ── B. constant-time admin compare ────────────────────────────


@aio
async def test_admin_auth_constant_time(monkeypatch):
    import src.api.auth as auth
    monkeypatch.setenv("MERIDIAN_ADMIN_KEY", "dummy-admin-not-real")
    # right key passes
    assert (await auth.require_admin("dummy-admin-not-real")) is None
    # wrong key → 403
    with pytest.raises(Exception) as e:
        await auth.require_admin("wrong")
    assert "403" in str(e.value) or "Invalid" in str(e.value)
    # uses compare_digest, not ==
    import inspect
    src = inspect.getsource(auth.require_admin)
    assert "compare_digest" in src and "key != expected" not in src


# ── C. Twilio signature verification ──────────────────────────


def _twilio_sig(token: str, url: str, params: dict) -> str:
    payload = url + "".join(f"{k}{params[k]}" for k in sorted(params))
    return base64.b64encode(
        hmac.new(token.encode(), payload.encode(), hashlib.sha1).digest()).decode()


class _Req:
    def __init__(self, sig, host="api.meridian.tips", path="/sms/inbound"):
        self.headers = {"X-Twilio-Signature": sig, "x-forwarded-proto": "https",
                        "x-forwarded-host": host}
        self.url = SimpleNamespace(scheme="http", netloc=host, path=path, query="")


def test_twilio_signature_gate(monkeypatch):
    import sms_order
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "dummy-twilio-not-real")
    monkeypatch.delenv("SMS_SKIP_TWILIO_VERIFY", raising=False)
    params = {"From": "+16045551234", "To": "+17805550100", "Body": "pizza"}
    url = "https://api.meridian.tips/sms/inbound"

    good = _twilio_sig("dummy-twilio-not-real", url, params)
    assert sms_order._verify_twilio_signature(_Req(good), params) is True
    # forged / missing signature rejected
    assert sms_order._verify_twilio_signature(_Req("AAAAforged"), params) is False
    assert sms_order._verify_twilio_signature(_Req(""), params) is False
    # tampered body → signature no longer matches
    assert sms_order._verify_twilio_signature(_Req(good), {**params, "Body": "free stuff"}) is False


def test_twilio_verify_rejects_when_token_unset(monkeypatch):
    import sms_order
    monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("SMS_SKIP_TWILIO_VERIFY", raising=False)
    assert sms_order._verify_twilio_signature(_Req("x"), {"Body": "hi"}) is False
    # explicit dev bypass
    monkeypatch.setenv("SMS_SKIP_TWILIO_VERIFY", "1")
    assert sms_order._verify_twilio_signature(_Req("x"), {"Body": "hi"}) is True


# ── D. SMS opt-out gate (integration through the handler) ──────


@aio
async def test_inbound_sms_honors_optout(monkeypatch):
    import sms_order
    monkeypatch.setenv("SMS_SKIP_TWILIO_VERIFY", "1")   # isolate the opt-out path

    cfg = SimpleNamespace(active=True, sms_ordering_enabled=True,
                          business_name="Maple Tandoor", phone_number="+17805550100")

    async def merch(_p): return "m1"
    async def getcfg(_m): return cfg
    monkeypatch.setattr(sms_order, "get_merchant_by_phone", merch)
    monkeypatch.setattr(sms_order, "get_merchant_config", getcfg)
    monkeypatch.setattr(sms_order, "classify_keyword", lambda b: None)

    called = {"llm": False}

    async def optout(_m, _p):
        return {"marketing_optout": True, "transactional_optout": False}
    monkeypatch.setattr(sms_order, "fetch_optout_status", optout)

    class _LLM:
        async def complete(self, *a, **k):
            called["llm"] = True
            return SimpleNamespace(text="hi", tool_calls=[], provider_used="x")
    monkeypatch.setattr(sms_order, "_sms_llm", _LLM())

    class _Form(dict):
        async def _noop(self): pass

    class _R:
        headers = {}
        url = SimpleNamespace(scheme="https", netloc="x", path="/sms/inbound", query="")
        async def form(self):
            return {"From": "+16045551234", "To": "+17805550100",
                    "Body": "I want a pizza", "MessageSid": "SM1"}

    resp = await sms_order.handle_inbound_sms(_R())
    txt = resp.body.decode()
    assert "unsubscribed" in txt and "START" in txt
    assert called["llm"] is False        # opted-out caller never reaches the LLM
