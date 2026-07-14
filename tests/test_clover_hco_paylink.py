"""
Clover Hosted Checkout — tap-time (/p) + webhook coverage.

What must be right before real money flows on this rail:

  1. LAZY CREATE: tapping /p/{code} on a provider='clover' row with no live
     session creates the HCO session THEN (15-min expiry starts at tap),
     persists provider_ref/checkout_url/expires_at, and 303s to the href.
  2. EXPIRY RE-CREATE: a stored-but-expired session is transparently replaced;
     a live one is redirected to without a second create.
  3. NEVER STRAND: HCO failure at tap shows a friendly page (or the
     explicitly-configured Meridian checkout), never a 500/dead redirect.
  4. WEBHOOK: signature verified per-merchant (401 when no secret — fail
     closed), APPROVED PAYMENT → mark_order_paid (same release path as
     Stripe), idempotent under retries, DECLINED → NO release.
"""
import asyncio
import hashlib
import hmac
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.api.routes import clover_hco as hook  # noqa: E402
from src.api.routes import pay_redirect as pr  # noqa: E402
from src.services import clover_hco as svc  # noqa: E402

aio = pytest.mark.asyncio

NOW = datetime.now(timezone.utc)


def _clover_row(**kw):
    row = {
        "id": "row-1", "merchant_id": "m-clover", "provider": "clover",
        "provider_ref": None, "checkout_url": None, "status": "created",
        "payload": {
            "hco_request": {
                "customer": {"firstName": "Priya", "phoneNumber": "+16045550123"},
                "shoppingCart": {"lineItems": [
                    {"name": "Butter Chicken", "price": 1550, "unitQty": 2},
                    {"name": "Tax", "price": 442, "unitQty": 1},
                ]},
            },
            "clover_merchant_id": "CLOVERMID1",
        },
        "expires_at": None,
        "caller_phone": "+16045550123", "pos_order_id": "POS-77",
    }
    row.update(kw)
    return row


class FakeDB:
    def __init__(self, tables: dict[str, list[dict]]):
        self.tables = tables
        self.updates: list[tuple[str, dict, dict]] = []

    async def select(self, table, columns="*", filters=None, order=None,
                     limit=None, offset=None):
        rows = self.tables.get(table, [])
        out = []
        for row in rows:
            ok = True
            for col, expr in (filters or {}).items():
                want = expr[3:] if expr.startswith("eq.") else expr
                if str(row.get(col, "")) != want:
                    ok = False
                    break
            if ok:
                out.append(dict(row))
        return out[:limit] if limit else out

    async def update(self, table, data, filters):
        self.updates.append((table, dict(data), dict(filters)))
        for row in self.tables.get(table, []):
            ok = all(str(row.get(c, "")) == e[3:] for c, e in filters.items())
            if ok:
                row.update(data)
        return []


def _install_db(monkeypatch, db):
    monkeypatch.setattr(pr, "get_db", lambda: db)
    monkeypatch.setattr(hook, "get_db", lambda: db)


def _install_hco_create(monkeypatch, calls, fail=False):
    async def fake_create(token, mid, body):
        calls.append({"token": token, "mid": mid, "body": body})
        if fail:
            raise RuntimeError("clover_hco_create_500")
        return {"href": "https://checkout.clover.com/pay/HCO123",
                "checkoutSessionId": "HCO123",
                "expirationTime": (NOW + timedelta(minutes=15)).isoformat()}
    monkeypatch.setattr(svc, "create_hco_session", fake_create)


def _install_manual_creds(db):
    db.tables.setdefault("phone_agent_config", []).append({
        "merchant_id": "m-clover", "pos_system": "clover",
        "pos_access_token": "clover-tok", "pos_location_id": "CLOVERMID1",
    })


# ── /p tap-time lazy creation ────────────────────────────────────────────────

@aio
async def test_tap_creates_hco_session_persists_and_redirects(monkeypatch):
    db = FakeDB({"checkout_sessions": [_clover_row(short_code="abcd1234")],
                 "pos_connections": []})
    _install_manual_creds(db)
    _install_db(monkeypatch, db)
    calls = []
    _install_hco_create(monkeypatch, calls)

    res = await pr.pay_redirect("abcd1234")

    assert res.status_code == 303
    assert res.headers["location"] == "https://checkout.clover.com/pay/HCO123"
    assert calls == [{"token": "clover-tok", "mid": "CLOVERMID1",
                      "body": _clover_row()["payload"]["hco_request"]}]
    table, data, filters = db.updates[0]
    assert table == "checkout_sessions"
    assert data["provider_ref"] == "HCO123"
    assert data["checkout_url"] == "https://checkout.clover.com/pay/HCO123"
    assert data["expires_at"]                      # expiry persisted
    assert filters == {"id": "eq.row-1"}


@aio
async def test_tap_live_session_redirects_without_recreate(monkeypatch):
    row = _clover_row(short_code="abcd1234", provider_ref="HCO-LIVE",
                      checkout_url="https://checkout.clover.com/pay/HCO-LIVE",
                      expires_at=(NOW + timedelta(minutes=10)).isoformat())
    db = FakeDB({"checkout_sessions": [row]})
    _install_db(monkeypatch, db)
    calls = []
    _install_hco_create(monkeypatch, calls)

    res = await pr.pay_redirect("abcd1234")
    assert res.status_code == 303
    assert res.headers["location"].endswith("HCO-LIVE")
    assert calls == []                             # no second create
    assert db.updates == []


@aio
async def test_tap_expired_session_recreates(monkeypatch):
    row = _clover_row(short_code="abcd1234", provider_ref="HCO-OLD",
                      checkout_url="https://checkout.clover.com/pay/HCO-OLD",
                      expires_at=(NOW - timedelta(minutes=1)).isoformat())
    db = FakeDB({"checkout_sessions": [row], "pos_connections": []})
    _install_manual_creds(db)
    _install_db(monkeypatch, db)
    calls = []
    _install_hco_create(monkeypatch, calls)

    res = await pr.pay_redirect("abcd1234")
    assert res.status_code == 303
    assert res.headers["location"].endswith("HCO123")      # fresh session
    assert len(calls) == 1


@aio
async def test_tap_resolves_oauth_token_from_pos_connections(monkeypatch):
    """OAuth merchants: token decrypted from pos_connections at tap time
    (never stored in the checkout row)."""
    row = _clover_row(short_code="abcd1234")
    row["payload"]["clover_merchant_id"] = ""              # resolve mid too
    db = FakeDB({
        "checkout_sessions": [row],
        "pos_connections": [{"org_id": "m-clover", "provider": "clover",
                             "status": "connected", "external_merchant_id": "EXTMID9",
                             "access_token_enc": "enc-blob"}],
        "phone_agent_config": [],
    })
    _install_db(monkeypatch, db)
    calls = []
    _install_hco_create(monkeypatch, calls)

    import src.api.routes.phone_dashboard as pd
    monkeypatch.setattr(pd, "_decrypt_connection_token", lambda conn: "decrypted-tok")

    res = await pr.pay_redirect("abcd1234")
    assert res.status_code == 303
    assert calls[0]["token"] == "decrypted-tok"
    assert calls[0]["mid"] == "EXTMID9"


@aio
async def test_tap_hco_failure_shows_friendly_page_not_500(monkeypatch):
    db = FakeDB({"checkout_sessions": [_clover_row(short_code="abcd1234")],
                 "pos_connections": []})
    _install_manual_creds(db)
    _install_db(monkeypatch, db)
    _install_hco_create(monkeypatch, [], fail=True)
    monkeypatch.delenv("MERIDIAN_CHECKOUT_URL", raising=False)

    res = await pr.pay_redirect("abcd1234")
    assert res.status_code == 503
    assert b"couldn't open the payment page" in res.body


@aio
async def test_tap_paid_row_shows_already_paid(monkeypatch):
    db = FakeDB({"checkout_sessions": [_clover_row(short_code="abcd1234", status="paid")]})
    _install_db(monkeypatch, db)
    res = await pr.pay_redirect("abcd1234")
    assert res.status_code == 200
    assert b"Already paid" in res.body


@aio
async def test_stripe_rows_unchanged(monkeypatch):
    """provider='stripe' keeps today's behavior: straight 303 to the stored URL."""
    db = FakeDB({"checkout_sessions": [{
        "id": "s1", "provider": "stripe", "short_code": "beef0001",
        "checkout_url": "https://checkout.stripe.com/pay/cs_1", "status": "created",
    }]})
    _install_db(monkeypatch, db)
    res = await pr.pay_redirect("beef0001")
    assert res.status_code == 303
    assert res.headers["location"].startswith("https://checkout.stripe.com")


# ── webhook ──────────────────────────────────────────────────────────────────

SECRET = "whsec_clover_test"


def _event(status="APPROVED", session="HCO123", **kw):
    ev = {"status": status, "type": "PAYMENT", "id": "pay-uuid-1",
          "merchantId": "CLOVERMID1", "data": session,
          "createdTime": 1760000000000, "message": status.title()}
    ev.update(kw)
    return ev


def _signed_request(event: dict, secret=SECRET, ts="1760000000"):
    body = json.dumps(event).encode()
    sig = hmac.new(secret.encode(), f"{ts}.".encode() + body, hashlib.sha256).hexdigest()
    return FakeRequest(body, {"Clover-Signature": f"t={ts},v1={sig}"})


class FakeRequest:
    def __init__(self, body: bytes, headers: dict):
        self._body = body
        self.headers = {k.lower(): v for k, v in headers.items()}

    async def body(self):
        return self._body


def _webhook_db(session_status="created"):
    return FakeDB({
        "checkout_sessions": [_clover_row(provider_ref="HCO123", status=session_status,
                                          checkout_url="https://x", short_code="abcd1234")],
        "phone_agent_config": [{"merchant_id": "m-clover",
                                "clover_hco_webhook_secret": SECRET}],
    })


def _install_mark_paid(monkeypatch, calls):
    async def fake_mark_paid(**kw):
        calls.append(kw)
        return {"released": True, "matched_by": "pos_order_id", "pos_pushed": True}

    _PA = str(Path(__file__).resolve().parents[1] / "services" / "phone_agent")
    if _PA not in sys.path:
        sys.path.insert(0, _PA)
    import pay_on_phone
    monkeypatch.setattr(pay_on_phone, "mark_order_paid", fake_mark_paid)


@aio
async def test_webhook_approved_marks_paid_and_releases(monkeypatch):
    db = _webhook_db()
    _install_db(monkeypatch, db)
    calls = []
    _install_mark_paid(monkeypatch, calls)

    out = await hook.hco_webhook(_signed_request(_event()))

    assert out == {"received": True, "released": True}
    assert ("checkout_sessions", {"status": "paid"}, {"id": "eq.row-1"}) in db.updates
    assert calls == [{
        "merchant_id": "m-clover", "caller_phone": "+16045550123",
        "pos_order_id": "POS-77", "method": "clover", "payment_txn_id": "pay-uuid-1",
    }]


@aio
async def test_webhook_retry_is_idempotent(monkeypatch):
    """Second delivery of the same APPROVED event → no second release."""
    db = _webhook_db(session_status="paid")
    _install_db(monkeypatch, db)
    calls = []
    _install_mark_paid(monkeypatch, calls)

    out = await hook.hco_webhook(_signed_request(_event()))
    assert out == {"received": True, "already_paid": True}
    assert calls == []
    assert db.updates == []


@aio
async def test_webhook_declined_never_releases(monkeypatch):
    db = _webhook_db()
    _install_db(monkeypatch, db)
    calls = []
    _install_mark_paid(monkeypatch, calls)

    out = await hook.hco_webhook(_signed_request(_event(status="DECLINED")))
    assert out.get("declined") is True
    assert calls == []                                     # NO release
    assert ("checkout_sessions", {"status": "paid"}, {"id": "eq.row-1"}) not in db.updates


@aio
async def test_webhook_bad_signature_rejected(monkeypatch):
    db = _webhook_db()
    _install_db(monkeypatch, db)
    calls = []
    _install_mark_paid(monkeypatch, calls)

    body = json.dumps(_event()).encode()
    req = FakeRequest(body, {"Clover-Signature": "t=1,v1=" + "0" * 64})
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await hook.hco_webhook(req)
    assert exc.value.status_code == 401
    assert calls == []
    assert db.updates == []


@aio
async def test_webhook_no_secret_configured_rejects_401(monkeypatch):
    db = _webhook_db()
    db.tables["phone_agent_config"][0]["clover_hco_webhook_secret"] = ""
    _install_db(monkeypatch, db)
    calls = []
    _install_mark_paid(monkeypatch, calls)

    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await hook.hco_webhook(_signed_request(_event()))
    assert exc.value.status_code == 401
    assert calls == []


@aio
async def test_webhook_unknown_session_acked_but_inert(monkeypatch):
    db = _webhook_db()
    _install_db(monkeypatch, db)
    calls = []
    _install_mark_paid(monkeypatch, calls)

    out = await hook.hco_webhook(_signed_request(_event(session="HCO-NOPE")))
    assert out["ignored"] == "unknown_session"
    assert calls == []


# ── signature helper (tolerant formats, documented assumption) ──────────────

def test_signature_timestamped_scheme_verifies():
    body = b'{"x":1}'
    sig = hmac.new(SECRET.encode(), b"123." + body, hashlib.sha256).hexdigest()
    assert svc.verify_hco_signature(SECRET, body, f"t=123,v1={sig}")


def test_signature_bare_body_scheme_verifies():
    body = b'{"x":1}'
    sig = hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()
    assert svc.verify_hco_signature(SECRET, body, f"v1={sig}")
    assert svc.verify_hco_signature(SECRET, body, sig)      # bare hex digest


def test_signature_fails_closed():
    body = b'{"x":1}'
    good = hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()
    assert not svc.verify_hco_signature("", body, f"v1={good}")   # no secret
    assert not svc.verify_hco_signature(SECRET, body, "")         # no header
    assert not svc.verify_hco_signature(SECRET, body, "v1=" + "0" * 64)
    assert not svc.verify_hco_signature("wrong", body, f"v1={good}")


def test_parse_expiration_accepts_iso_and_epoch_ms():
    iso = svc.parse_expiration("2026-07-14T12:00:00.000Z")
    assert iso == datetime(2026, 7, 14, 12, 0, tzinfo=timezone.utc)
    ms = svc.parse_expiration(1784030400000)
    assert ms is not None and ms.tzinfo is not None
    assert svc.parse_expiration("garbage") is None
    assert svc.parse_expiration(None) is None


def test_hco_base_url_follows_clover_environment(monkeypatch):
    monkeypatch.delenv("CLOVER_HCO_BASE", raising=False)
    monkeypatch.setenv("CLOVER_ENVIRONMENT", "sandbox")
    assert svc.hco_base_url() == "https://apisandbox.dev.clover.com"
    monkeypatch.setenv("CLOVER_ENVIRONMENT", "production")
    monkeypatch.setenv("CLOVER_REGION", "na")
    assert svc.hco_base_url() == "https://api.clover.com"
