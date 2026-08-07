"""Stripe POS connector — registry config, charge mapping, sync + credentials.

Run: python -m pytest tests/api/test_stripe_pos_connector.py -q

Pins the contract for the Stripe 1-click connector (src/stripe_pos/ + the
`stripe` registry entry): the OAuth config matches Stripe's Connect OAuth
surface, charges map to canonical `transactions` columns with deterministic
ids, the sync runner dispatches provider='stripe' to the Stripe engine, and
credential resolution prefers platform-key + Stripe-Account header with a
stored-token fallback. No network calls.
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

def test_stripe_registry_entry_matches_connect_oauth():
    cfg = get_provider("stripe")
    assert cfg is not None
    assert cfg.authorize_url == "https://connect.stripe.com/oauth/authorize"
    assert cfg.token_url == "https://connect.stripe.com/oauth/token"
    assert cfg.scopes == ["read_only"]
    # Stripe puts stripe_user_id (acct_…) straight in the token response.
    assert cfg.merchant_id_strategy == "token:stripe_user_id"
    # MUST be the POS-namespaced envs — STRIPE_SECRET_KEY belongs to the
    # payments rails (stripe_connect.py) and may be a different account.
    assert cfg.client_id_env == "STRIPE_POS_CLIENT_ID"
    assert cfg.client_secret_env == "STRIPE_POS_CLIENT_SECRET"
    assert cfg.uses_pkce is False
    # Stays unverified until the round-trip is validated against the real
    # Connect app (docs/POS_1CLICK_ONBOARDING.md) — enforced globally by
    # test_pos_connect.py::test_only_validated_providers_are_verified.
    assert cfg.verified is False


def test_stripe_authorize_url_and_state_roundtrip(monkeypatch):
    cfg = get_provider("stripe")
    monkeypatch.setenv("STRIPE_POS_CLIENT_ID", "ca_test123")
    monkeypatch.setenv("STRIPE_POS_CLIENT_SECRET", "sk_test_x")
    state = sign_state("stripe", ORG, "/app/settings")
    url = GenericOAuthManager(cfg, "https://api.example.com/api/pos/stripe/callback").authorize_url(state)
    assert url.startswith("https://connect.stripe.com/oauth/authorize?")
    assert "client_id=ca_test123" in url
    assert "scope=read_only" in url
    assert "stripe_landing=login" in url
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

def test_credentials_prefer_platform_key_with_account_header(monkeypatch):
    monkeypatch.setenv("STRIPE_POS_CLIENT_SECRET", "sk_live_platform")
    conn = {"external_merchant_id": "acct_1ABC",
            "access_token_enc": encrypt_token("sk_stored_fallback")}
    api_key, account_id = stripe_pos_credentials(conn)
    assert (api_key, account_id) == ("sk_live_platform", "acct_1ABC")


def test_credentials_fall_back_to_stored_token(monkeypatch):
    monkeypatch.delenv("STRIPE_POS_CLIENT_SECRET", raising=False)
    conn = {"external_merchant_id": "acct_1ABC",
            "access_token_enc": encrypt_token("sk_stored_fallback")}
    api_key, account_id = stripe_pos_credentials(conn)
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
