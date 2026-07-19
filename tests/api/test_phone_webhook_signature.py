"""/twilio/* TwiML webhooks must reject forged (unsigned) requests."""
import base64
import hashlib
import hmac
import os

import pytest

from src.api.routes import phone


class _FakeReq:
    def __init__(self, headers, path="/twilio/gather", query=""):
        self.headers = headers
        class _U:
            def __init__(s):
                s.path = path; s.query = query; s.scheme = "https"; s.netloc = "api.meridian.tips"
        self.url = _U()


FORM = {"CallSid": "CA1", "SpeechResult": "two large pizzas confirm"}


def _sign(token, form, url="https://api.meridian.tips/twilio/gather"):
    payload = url + "".join(f"{k}{form[k]}" for k in sorted(form))
    return base64.b64encode(hmac.new(token.encode(), payload.encode(), hashlib.sha1).digest()).decode()


@pytest.fixture(autouse=True)
def _token(monkeypatch):
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "testtoken")
    monkeypatch.delenv("PHONE_SKIP_WEBHOOK_VERIFY", raising=False)


def test_forged_no_signature_rejected():
    assert phone._verify_twilio_signature(_FakeReq({"host": "api.meridian.tips"}), FORM) is False


def test_valid_signature_accepted():
    sig = _sign("testtoken", FORM)
    req = _FakeReq({"host": "api.meridian.tips", "X-Twilio-Signature": sig})
    assert phone._verify_twilio_signature(req, FORM) is True


def test_wrong_signature_rejected():
    req = _FakeReq({"host": "api.meridian.tips", "X-Twilio-Signature": "not-the-sig"})
    assert phone._verify_twilio_signature(req, FORM) is False


def test_fail_closed_when_token_unset(monkeypatch):
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "")
    sig = _sign("testtoken", FORM)
    req = _FakeReq({"host": "api.meridian.tips", "X-Twilio-Signature": sig})
    assert phone._verify_twilio_signature(req, FORM) is False


def test_dev_bypass(monkeypatch):
    monkeypatch.setenv("PHONE_SKIP_WEBHOOK_VERIFY", "1")
    assert phone._verify_twilio_signature(_FakeReq({}), FORM) is True


def test_forwarded_proto_host_reconstructs_url():
    # Behind Railway/nginx the signed URL uses x-forwarded-* headers.
    sig = _sign("testtoken", FORM)
    req = _FakeReq({"x-forwarded-proto": "https", "x-forwarded-host": "api.meridian.tips",
                    "host": "internal:8080", "X-Twilio-Signature": sig})
    assert phone._verify_twilio_signature(req, FORM) is True
