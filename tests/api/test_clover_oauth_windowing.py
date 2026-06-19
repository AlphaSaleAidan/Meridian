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
