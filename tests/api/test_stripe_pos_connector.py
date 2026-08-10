"""Stripe POS connector — registry config, charge mapping, sync + credentials.

Run: python -m pytest tests/api/test_stripe_pos_connector.py -q

Pins the contract for the Stripe 1-click connector (src/stripe_pos/ + the
`stripe` registry entry): the OAuth config matches the Stripe Apps OAuth
surface (stripe-app/), charges map to canonical `transactions` columns with
deterministic ids, the sync runner dispatches provider='stripe' to the Stripe
engine, and credential resolution refreshes app tokens (rolling refresh) with
legacy platform-key / stored-token fallbacks. No network calls.
"""
from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

os.environ.setdefault("TESTING", "1")
os.environ.setdefault("OAUTH_STATE_SECRET", "test-only-secret-not-for-production")
os.environ.setdefault("ENCRYPTION_KEY", "0" * 64)

from src.pos_connect.registry import get_provider  # noqa: E402
from src.pos_connect.oauth import GenericOAuthManager, sign_state, verify_state  # noqa: E402
from src.stripe_pos.mappers import StripePOSMapper  # noqa: E402
from src.stripe_pos.sync_engine import StripePOSSyncEngine  # noqa: E402
from src.services.pos_sync_runner import stripe_pos_credentials  # noqa: E402
from src.security.encryption import encrypt_token  # noqa: E402


def _run(coro):
    return asyncio.run(coro)


ORG = "11111111-2222-3333-4444-555555555555"


def _charge(**over):
    base = {
        "id": "ch_3Nabc123",
        "object": "charge",
        "amount": 4250,
        "amount_refunded": 0,
        "currency": "usd",
        "created": 1754500000,
        "status": "succeeded",
        "refunded": False,
        "customer": "cus_ABC",
        "receipt_email": "guest@example.com",
        "billing_details": {"email": "card@example.com"},
        "payment_method_details": {"type": "card_present"},
        "payment_intent": "pi_3Nabc123",
        "description": "Dinner order",
    }
    base.update(over)
    return base


# ─── Registry entry ──────────────────────────────────────────────────────────

def test_stripe_registry_entry_matches_apps_oauth():
    cfg = get_provider("stripe")
    assert cfg is not None
    # Stripe App OAuth surface — NOT classic Connect: support confirmed
    # 2026-08-08 that the `read_only` Connect scope is deprecated; permissions
    # now live in stripe-app/stripe-app.json, so no scope goes on the URL.
    assert cfg.authorize_url == "https://marketplace.stripe.com/oauth/v2/authorize"
    assert cfg.token_url == "https://api.stripe.com/v1/oauth/token"
    assert cfg.scopes == []
    assert cfg.token_basic_auth is True
    # App access tokens are fixed at 1h and the response omits expires_in.
    assert cfg.default_token_ttl == 3600
    # Stripe puts stripe_user_id (acct_…) straight in the token response.
    assert cfg.merchant_id_strategy == "token:stripe_user_id"
    # MUST be the POS-namespaced envs — STRIPE_SECRET_KEY belongs to the
    # payments rails (stripe_connect.py) and may be a different account.
    assert cfg.client_id_env == "STRIPE_POS_CLIENT_ID"
    assert cfg.client_secret_env == "STRIPE_POS_CLIENT_SECRET"
    assert cfg.uses_pkce is False
    # Validated against the real Stripe App (v1.0.2 on Meridian Integrations,
    # 2026-08-11) — `stripe` is in VALIDATED in test_pos_connect.py.
    assert cfg.verified is True


def test_stripe_authorize_url_and_state_roundtrip(monkeypatch):
    cfg = get_provider("stripe")
    monkeypatch.setenv("STRIPE_POS_CLIENT_ID", "app_client_test123")
    monkeypatch.setenv("STRIPE_POS_CLIENT_SECRET", "sk_test_x")
    state = sign_state("stripe", ORG, "/app/settings")
    url = GenericOAuthManager(cfg, "https://api.example.com/api/pos/stripe/callback").authorize_url(state)
    assert url.startswith("https://marketplace.stripe.com/oauth/v2/authorize?")
    assert "client_id=app_client_test123" in url
    # App permissions are manifest-declared — a scope param would be rejected.
    assert "scope=" not in url


def test_stripe_authorize_url_external_test_override(monkeypatch):
    """Pre-publish, installs go through the channel-scoped external-test link;
    STRIPE_POS_AUTHORIZE_URL swaps the base URL without touching the params."""
    cfg = get_provider("stripe")
    monkeypatch.setenv("STRIPE_POS_CLIENT_ID", "app_client_test123")
    monkeypatch.setenv("STRIPE_POS_CLIENT_SECRET", "sk_test_x")
    chnlink = "https://marketplace.stripe.com/oauth/v2/chnlink_abc123/authorize"
    monkeypatch.setenv("STRIPE_POS_AUTHORIZE_URL", chnlink)
    state = sign_state("stripe", ORG, "/app/settings")
    url = GenericOAuthManager(cfg, "https://api.example.com/api/pos/stripe/callback").authorize_url(state)
    assert url.startswith(chnlink + "?")
    assert "client_id=app_client_test123" in url
    # Unset → falls back to the canonical marketplace URL (post-publish).
    monkeypatch.delenv("STRIPE_POS_AUTHORIZE_URL")
    url2 = GenericOAuthManager(cfg, "https://api.example.com/api/pos/stripe/callback").authorize_url(state)
    assert url2.startswith("https://marketplace.stripe.com/oauth/v2/authorize?")
    verified = verify_state(state)
    assert verified == ("stripe", ORG, "/app/settings")
    # provider-scoped: a square-signed state must not pass for stripe
    other = sign_state("square", ORG, "")
    assert verify_state(other)[0] != "stripe"


def test_stripe_merchant_id_resolves_from_token_response():
    cfg = get_provider("stripe")
    mgr = GenericOAuthManager(cfg, "https://api.example.com/cb")
    tokens = {"access_token": "sk_x", "raw": {"stripe_user_id": "acct_1ABC"}}
    assert _run(mgr.resolve_merchant_id(tokens)) == "acct_1ABC"


# ─── Mapper ──────────────────────────────────────────────────────────────────

def test_map_charge_canonical_columns():
    row = StripePOSMapper(org_id=ORG).map_charge_to_transaction(_charge())
    assert row["org_id"] == ORG
    assert row["external_id"] == "ch_3Nabc123"
    assert row["provider"] == "stripe"  # transient hint, stripped by the db layer
    assert row["type"] == "sale"
    assert row["total_cents"] == 4250
    assert row["subtotal_cents"] == 4250
    assert row["payment_method"] == "card"
    assert row["currency"] == "USD"
    assert row["customer_email"] == "card@example.com"
    # canonical NOT NULL column is transaction_at (not transaction_time)
    assert row["transaction_at"] == datetime.fromtimestamp(
        1754500000, tz=timezone.utc).isoformat()


def test_map_charge_deterministic_id_and_refund_semantics():
    mapper = StripePOSMapper(org_id=ORG)
    a = mapper.map_charge_to_transaction(_charge())
    b = mapper.map_charge_to_transaction(_charge())
    assert a["id"] == b["id"], "re-sync must upsert the SAME row"
    other = mapper.map_charge_to_transaction(_charge(id="ch_other"))
    assert other["id"] != a["id"]

    full_refund = mapper.map_charge_to_transaction(
        _charge(refunded=True, amount_refunded=4250))
    assert full_refund["type"] == "void"

    partial = mapper.map_charge_to_transaction(_charge(amount_refunded=1000))
    assert partial["type"] == "sale"
    assert partial["metadata"]["stripe"]["amount_refunded_cents"] == 1000


def test_map_charge_payment_method_variants():
    mapper = StripePOSMapper(org_id=ORG)
    assert mapper.map_charge_to_transaction(
        _charge(payment_method_details={"type": "interac_present"}))["payment_method"] == "debit"
    assert mapper.map_charge_to_transaction(
        _charge(payment_method_details={"type": "us_bank_account"}))["payment_method"] == "other"
    assert mapper.map_charge_to_transaction(
        _charge(payment_method_details=None))["payment_method"] == "unknown"


# ─── Sync engine ─────────────────────────────────────────────────────────────

class _FakeClient:
    def __init__(self, charges):
        self._charges = charges
        self.calls = []

    async def iter_charges(self, created_gte=None, created_lte=None):
        self.calls.append({"created_gte": created_gte, "created_lte": created_lte})
        for c in self._charges:
            yield c


def test_incremental_sync_filters_non_succeeded_and_windows_since():
    charges = [
        _charge(),
        _charge(id="ch_failed", status="failed"),
        _charge(id="ch_pending", status="pending"),
    ]
    client = _FakeClient(charges)
    engine = StripePOSSyncEngine(client=client, org_id=ORG, pos_connection_id="conn-1")
    since = datetime(2026, 8, 1, tzinfo=timezone.utc)
    result = _run(engine.run_incremental_sync(since=since))
    assert [t["external_id"] for t in result.transactions] == ["ch_3Nabc123"]
    assert result.transaction_items == []
    # 5-minute overlap below `since` so boundary charges aren't skipped
    assert client.calls[0]["created_gte"] == int(since.timestamp()) - 300


def test_backfill_folds_fatal_errors_instead_of_raising():
    class _ExplodingClient:
        async def iter_charges(self, **kw):
            raise RuntimeError("boom")
            yield  # pragma: no cover

    engine = StripePOSSyncEngine(client=_ExplodingClient(), org_id=ORG, pos_connection_id="conn-1")
    result = _run(engine.run_initial_backfill())
    assert result.transactions == []
    assert result.errors and result.errors[0].startswith("fatal:"), (
        "backfill wrapper gates on the 'fatal:' prefix — a bare raise would "
        "mark the connection complete with no data")


# ─── Credential resolution (runner) ──────────────────────────────────────────

def test_credentials_app_oauth_uses_fresh_token_bare(monkeypatch):
    """App-OAuth rows (refresh_token_enc present) return the stored access
    token bare while it's comfortably inside its 1h lifetime — no platform
    key, no Stripe-Account header."""
    from datetime import timedelta
    monkeypatch.setenv("STRIPE_POS_CLIENT_SECRET", "sk_live_platform")
    future = (datetime.now(timezone.utc) + timedelta(minutes=50)).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    conn = {"external_merchant_id": "acct_1ABC",
            "access_token_enc": encrypt_token("app_access_token"),
            "refresh_token_enc": encrypt_token("app_refresh_token"),
            "token_expires_at": future}
    api_key, account_id = _run(stripe_pos_credentials(conn))
    assert (api_key, account_id) == ("app_access_token", "")


def test_credentials_app_oauth_refreshes_and_rolls(monkeypatch):
    """Near-expiry app tokens are refreshed; the ROLLED refresh token must be
    written back into the connection dict (Stripe kills the old one)."""
    from src.stripe_pos import tokens as st_tokens
    from src.security.encryption import decrypt_token as dec
    monkeypatch.setenv("STRIPE_POS_CLIENT_SECRET", "sk_live_platform")

    async def fake_exchange(refresh_token, secret_key):
        assert refresh_token == "old_refresh"
        assert secret_key == "sk_live_platform"
        return {"access_token": "new_access", "refresh_token": "new_refresh"}

    monkeypatch.setattr(st_tokens, "_exchange_refresh_token", fake_exchange)
    conn = {"id": "", "external_merchant_id": "acct_1ABC",
            "access_token_enc": encrypt_token("stale_access"),
            "refresh_token_enc": encrypt_token("old_refresh"),
            "token_expires_at": "2026-01-01T00:00:00Z"}
    api_key, account_id = _run(stripe_pos_credentials(conn))
    assert (api_key, account_id) == ("new_access", "")
    assert dec(conn["refresh_token_enc"]) == "new_refresh"
    assert conn["token_expires_at"] > "2026-01-01"


def test_credentials_legacy_prefer_platform_key_with_account_header(monkeypatch):
    """Pre-app Connect rows (no refresh token) keep the old contract."""
    monkeypatch.setenv("STRIPE_POS_CLIENT_SECRET", "sk_live_platform")
    conn = {"external_merchant_id": "acct_1ABC",
            "access_token_enc": encrypt_token("sk_stored_fallback")}
    api_key, account_id = _run(stripe_pos_credentials(conn))
    assert (api_key, account_id) == ("sk_live_platform", "acct_1ABC")


def test_credentials_legacy_fall_back_to_stored_token(monkeypatch):
    monkeypatch.delenv("STRIPE_POS_CLIENT_SECRET", raising=False)
    conn = {"external_merchant_id": "acct_1ABC",
            "access_token_enc": encrypt_token("sk_stored_fallback")}
    api_key, account_id = _run(stripe_pos_credentials(conn))
    assert api_key == "sk_stored_fallback"
    assert account_id == "", "stored per-account token is used bare (no header)"


def test_runner_dispatches_stripe(monkeypatch):
    """run_incremental(provider='stripe') must reach the Stripe engine — not
    fall through to _sync_generic (whose credentials_encrypted the OAuth
    callback never populates)."""
    from src.services import pos_sync_runner

    seen = {}

    async def fake_sync_stripe(org_id, conn_id, connection, since):
        seen["args"] = (org_id, conn_id, connection.get("provider"))

        class _R:
            transactions = []
            transaction_items = []
        return _R()

    class _FakeDB:
        async def update(self, *a, **k):
            return []

        async def batch_upsert(self, *a, **k):
            return []

        async def refresh_views(self):
            return None

    monkeypatch.setattr(pos_sync_runner, "_sync_stripe", fake_sync_stripe)
    monkeypatch.setattr("src.db.get_db", lambda: _FakeDB())
    conn = {"id": "conn-1", "provider": "stripe", "last_sync_at": None}
    _run(pos_sync_runner.run_incremental(ORG, "stripe", conn))
    assert seen["args"] == (ORG, "conn-1", "stripe")
