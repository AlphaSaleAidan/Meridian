"""
Clover client + OAuth correctness, three angles (Findings 1–3 from the docs review):

  1. Time filters are emitted as REPEATED `filter=` params, not `&`-joined into a
     single value (Clover's documented syntax). The old `"&".join(...)` made httpx
     URL-encode the inner `&`, so a start+end range arrived as one malformed filter.
  2. Ranges wider than Clover's 90-day cap are windowed into <=90-day slices and
     concatenated — otherwise older data is silently dropped (orders/payments/refunds
     and the 400-day reconcile query).
  3. v2/OAuth expiring tokens: createdTime/expiration parsing, inline refresh when
     the stored token is expired/near-expiry, and legacy (no refresh_token) pass-through.

Pattern mirrors the other api tests: call functions directly with fakes, run via
asyncio.run (no pytest-asyncio).

Run:  python -m pytest tests/api/test_clover_oauth_windowing.py -v
"""
from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
os.environ.setdefault("ENCRYPTION_KEY", "0" * 64)

import src.db as db_mod  # noqa: E402
from src.clover.client import CloverClient, _time_windows, CLOVER_MAX_WINDOW_DAYS  # noqa: E402
from src.clover import oauth as clover_oauth  # noqa: E402
from src.clover.oauth import _unix_to_iso, ensure_fresh_clover_token  # noqa: E402
from src.security.encryption import encrypt_token  # noqa: E402


def _run(coro):
    return asyncio.run(coro)


def _client():
    return CloverClient(access_token="tok", merchant_id="M1")


def _capture_get(client):
    """Replace client._get with a recorder that returns one empty page."""
    calls: list[tuple[str, dict]] = []

    async def fake_get(path, params=None):
        calls.append((path, dict(params or {})))
        return {"elements": []}

    client._get = fake_get
    return calls


# ── 1. Filter encoding: repeated params, never &-joined ───────────────────

def test_filter_is_a_list_of_repeated_params_not_joined():
    client = _client()
    calls = _capture_get(client)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end = datetime(2026, 1, 15, tzinfo=timezone.utc)  # <90d → single window

    _run(client.list_orders(start_time=start, end_time=end))

    assert len(calls) == 1
    _, params = calls[0]
    f = params["filter"]
    # The fix: a LIST (httpx → repeated filter=...), not a single "&"-joined string.
    assert isinstance(f, list), f"filter must be a list, got {type(f)}: {f!r}"
    assert len(f) == 2
    assert any(s.startswith("clientCreatedTime>=") for s in f)
    assert any(s.startswith("clientCreatedTime<=") for s in f)
    assert all("&" not in s for s in f), "no filter element may embed '&'"


def test_single_bound_emits_single_filter():
    client = _client()
    calls = _capture_get(client)
    _run(client.list_payments(start_time=datetime(2026, 1, 1, tzinfo=timezone.utc)))
    _, params = calls[0]
    assert params["filter"] == [f"createdTime>={int(datetime(2026,1,1,tzinfo=timezone.utc).timestamp()*1000)}"]


def test_no_bounds_emits_no_filter():
    client = _client()
    calls = _capture_get(client)
    _run(client.list_payments())
    _, params = calls[0]
    assert "filter" not in params


# ── 2. 90-day windowing ───────────────────────────────────────────────────

def test_time_windows_splits_wide_range():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end = start + timedelta(days=200)
    windows = list(_time_windows(start, end))
    # 200 days → 90 + 90 + 20 = 3 contiguous windows, none > 90 days.
    assert len(windows) == 3
    assert windows[0][0] == start
    assert windows[-1][1] == end
    for ws, we in windows:
        assert (we - ws) <= timedelta(days=CLOVER_MAX_WINDOW_DAYS)
    # contiguous, no gaps/overlaps
    for (_, a_end), (b_start, _) in zip(windows, windows[1:]):
        assert a_end == b_start


def test_time_windows_passthrough_when_unbounded():
    assert list(_time_windows(None, None)) == [(None, None)]
    s = datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert list(_time_windows(s, None)) == [(s, None)]


def test_wide_range_produces_multiple_windowed_calls():
    client = _client()
    calls = _capture_get(client)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end = start + timedelta(days=200)

    _run(client.list_refunds(start_time=start, end_time=end))

    assert len(calls) == 3, f"expected 3 windowed calls, got {len(calls)}"
    # each call carries its own <=90-day createdTime range
    for _, params in calls:
        f = params["filter"]
        assert isinstance(f, list) and len(f) == 2


def test_narrow_range_is_not_oversplit():
    client = _client()
    calls = _capture_get(client)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end = start + timedelta(days=30)
    _run(client.list_orders(start_time=start, end_time=end))
    assert len(calls) == 1


# ── 3. OAuth v2 expiry parsing + inline refresh ───────────────────────────

def test_unix_to_iso_seconds():
    # 1_700_000_000 = 2023-11-14T22:13:20Z
    iso = _unix_to_iso(1_700_000_000)
    assert iso.startswith("2023-11-14T22:13:20")


def test_unix_to_iso_blank_on_missing_or_bad():
    assert _unix_to_iso(None) == ""
    assert _unix_to_iso("") == ""
    assert _unix_to_iso("not-a-number") == ""


def test_ensure_fresh_token_legacy_passthrough(monkeypatch):
    # No refresh_token_enc → legacy non-expiring token, returned unchanged, no refresh.
    conn = {"id": "C1", "access_token_enc": encrypt_token("legacy-tok")}

    async def boom(self, rt):
        raise AssertionError("legacy must not refresh")

    monkeypatch.setattr(clover_oauth.CloverOAuthManager, "refresh_token", boom)
    out = _run(ensure_fresh_clover_token(conn))
    assert out == "legacy-tok"


def test_ensure_fresh_token_refreshes_when_expired(monkeypatch):
    # v2 connection whose access token is already expired → inline refresh + persist.
    class FakeDB:
        def __init__(self):
            self.updates = []

        async def update(self, table, vals, filters=None):
            self.updates.append((table, vals, filters))

    db = FakeDB()
    db_mod._db_instance = db

    conn = {
        "id": "C2",
        "access_token_enc": encrypt_token("stale-tok"),
        "refresh_token_enc": encrypt_token("refresh-tok"),
        "token_expires_at": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
    }

    async def fake_refresh(self, rt):
        assert rt == "refresh-tok"
        return {
            "access_token": "fresh-tok",
            "refresh_token": "new-refresh",
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat(),
        }

    monkeypatch.setattr(clover_oauth.CloverOAuthManager, "refresh_token", fake_refresh)
    out = _run(ensure_fresh_clover_token(conn))
    assert out == "fresh-tok"
    # rotation persisted to pos_connections
    assert db.updates and db.updates[0][0] == "pos_connections"
    vals = db.updates[0][1]
    assert "access_token_enc" in vals and "refresh_token_enc" in vals
    assert db.updates[0][2] == {"id": "eq.C2"}


def test_ensure_fresh_token_skips_refresh_when_valid(monkeypatch):
    # v2 connection with a token valid well beyond the 5-min buffer → no refresh.
    conn = {
        "id": "C3",
        "access_token_enc": encrypt_token("good-tok"),
        "refresh_token_enc": encrypt_token("refresh-tok"),
        "token_expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
    }

    async def boom(self, rt):
        raise AssertionError("valid token must not be refreshed")

    monkeypatch.setattr(clover_oauth.CloverOAuthManager, "refresh_token", boom)
    out = _run(ensure_fresh_clover_token(conn))
    assert out == "good-tok"


def test_ensure_fresh_token_falls_back_on_refresh_failure(monkeypatch):
    # Refresh hiccup → return the stored token (best-effort), don't hard-fail sync.
    db_mod._db_instance = None
    conn = {
        "id": "C4",
        "access_token_enc": encrypt_token("stored-tok"),
        "refresh_token_enc": encrypt_token("refresh-tok"),
        "token_expires_at": "",  # blank → would refresh
    }

    async def fail(self, rt):
        raise clover_oauth.CloverOAuthError("clover down")

    monkeypatch.setattr(clover_oauth.CloverOAuthManager, "refresh_token", fail)
    out = _run(ensure_fresh_clover_token(conn))
    assert out == "stored-tok"


# ── 4. exchange_code: v2-first with legacy fallback ───────────────────────

class _FakeResp:
    def __init__(self, status_code, json_data=None, text=""):
        self.status_code = status_code
        self._json = json_data or {}
        self.text = text
        self.headers = {"content-type": "application/json"}

    def json(self):
        return self._json


def _patch_httpx(monkeypatch, *, post=None, get=None, post_raises=False):
    """Replace httpx.AsyncClient in clover.oauth with a fake recording calls."""
    record = {"post": 0, "get": 0, "post_url": None, "get_url": None}

    class _FakeClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, **k):
            record["post"] += 1
            record["post_url"] = url
            if post_raises:
                raise clover_oauth.httpx.HTTPError("boom")
            return post

        async def get(self, url, **k):
            record["get"] += 1
            record["get_url"] = url
            return get

    monkeypatch.setattr(clover_oauth.httpx, "AsyncClient", _FakeClient)
    return record


def test_exchange_code_uses_v2_when_available(monkeypatch):
    rec = _patch_httpx(
        monkeypatch,
        post=_FakeResp(200, {
            "access_token": "v2-acc",
            "refresh_token": "v2-ref",
            "access_token_expiration": 1_700_000_000,
            "refresh_token_expiration": 1_800_000_000,
        }),
    )
    mgr = clover_oauth.CloverOAuthManager()
    out = _run(mgr.exchange_code("CODE", merchant_id="M1"))

    assert out["access_token"] == "v2-acc"
    assert out["refresh_token"] == "v2-ref"
    assert out["expires_at"].startswith("2023-11-14")
    assert "/oauth/v2/token" in rec["post_url"]
    assert rec["get"] == 0, "legacy GET must not run when v2 succeeds"


def test_exchange_code_falls_back_to_legacy(monkeypatch):
    rec = _patch_httpx(
        monkeypatch,
        post=_FakeResp(400, {"message": "unsupported_grant"}),
        get=_FakeResp(200, {"access_token": "legacy-acc"}),
    )
    mgr = clover_oauth.CloverOAuthManager()
    out = _run(mgr.exchange_code("CODE", merchant_id="M1"))

    assert out["access_token"] == "legacy-acc"
    assert out["refresh_token"] == ""        # legacy → no refresh token
    assert out["expires_at"] == ""           # legacy → no expiry
    assert rec["post"] == 1 and rec["get"] == 1
    assert "/oauth/token" in rec["get_url"] and "/v2/" not in rec["get_url"]


def test_exchange_code_falls_back_when_v2_network_errors(monkeypatch):
    rec = _patch_httpx(
        monkeypatch,
        post_raises=True,
        get=_FakeResp(200, {"access_token": "legacy-acc"}),
    )
    mgr = clover_oauth.CloverOAuthManager()
    out = _run(mgr.exchange_code("CODE"))
    assert out["access_token"] == "legacy-acc"
    assert rec["get"] == 1


def test_exchange_code_raises_when_both_fail(monkeypatch):
    _patch_httpx(
        monkeypatch,
        post=_FakeResp(400, {"message": "bad"}),
        get=_FakeResp(401, {"message": "invalid_code"}),
    )
    mgr = clover_oauth.CloverOAuthManager()
    try:
        _run(mgr.exchange_code("CODE"))
        assert False, "expected CloverOAuthError"
    except clover_oauth.CloverOAuthError:
        pass


# ── 5. Webhook auth: X-Clover-Auth == static Auth Code (NOT HMAC) ─────────

from types import SimpleNamespace  # noqa: E402

from fastapi import Request  # noqa: E402
import src.api.routes.webhooks as wh_mod  # noqa: E402


def _set_auth_code(monkeypatch, code: str):
    # cl_config is a frozen dataclass — swap the module-level reference instead.
    monkeypatch.setattr(wh_mod, "cl_config", SimpleNamespace(webhook_auth_code=code))


def _webhook_request(body: bytes, headers: dict) -> Request:
    raw = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
    scope = {"type": "http", "method": "POST", "headers": raw, "path": "/api/webhooks/clover"}

    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    return Request(scope, receive)


def _call_clover_webhook(body: bytes, headers: dict):
    from fastapi import BackgroundTasks
    req = _webhook_request(body, headers)
    return _run(wh_mod.clover_webhook(req, BackgroundTasks()))


def test_webhook_accepts_matching_auth_code(monkeypatch):
    _set_auth_code(monkeypatch,"AUTH-CODE-123")
    body = b'{"appId":"A","merchants":{}}'
    resp = _call_clover_webhook(body, {"X-Clover-Auth": "AUTH-CODE-123"})
    assert resp.status_code == 200


def test_webhook_rejects_wrong_auth_code(monkeypatch):
    _set_auth_code(monkeypatch,"AUTH-CODE-123")
    body = b'{"appId":"A","merchants":{"M1":[{"type":"ORDER"}]}}'
    resp = _call_clover_webhook(body, {"X-Clover-Auth": "WRONG"})
    assert resp.status_code == 403


def test_webhook_rejects_hmac_style_signature(monkeypatch):
    # Regression for Finding 4: the OLD code expected an HMAC of the body. A real
    # Clover webhook sends the static auth code verbatim; an HMAC value must fail.
    _set_auth_code(monkeypatch,"AUTH-CODE-123")
    import hashlib
    import hmac as _hmac
    body = b'{"merchants":{"M1":[{"type":"ORDER"}]}}'
    bogus = _hmac.new(b"AUTH-CODE-123", body, hashlib.sha256).hexdigest()
    resp = _call_clover_webhook(body, {"X-Clover-Auth": bogus})
    assert resp.status_code == 403


def test_webhook_fails_closed_without_configured_code(monkeypatch):
    _set_auth_code(monkeypatch,"")
    resp = _call_clover_webhook(b'{"merchants":{"M1":[]}}', {"X-Clover-Auth": "anything"})
    assert resp.status_code == 503


def test_webhook_verification_handshake_acks_without_auth(monkeypatch):
    # Initial callback-URL validation: {verificationCode} arrives with no auth
    # header — must ack 200 so the URL can be activated in the Dashboard.
    _set_auth_code(monkeypatch,"")
    resp = _call_clover_webhook(b'{"verificationCode":"abc123"}', {})
    assert resp.status_code == 200
