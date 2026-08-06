"""Embedded onboarding: the AccountSession endpoint that powers the in-portal
Stripe Connect embedded component. Creates the connected account once (the
merchant needs NO Stripe account of their own), then an AccountSession with the
account_onboarding component, returning the client_secret + publishable key."""
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("ENCRYPTION_KEY", "0" * 64)

from src.api.routes import stripe_connect as sc  # noqa: E402

aio = pytest.mark.asyncio


class _StripeObj:
    def __init__(self, **d):
        self._d = d

    def __getitem__(self, k):
        return self._d[k]


class _FakeStripe:
    created = []
    sessions = []

    class Account:
        @staticmethod
        def create(**kw):
            _FakeStripe.created.append(kw)
            return _StripeObj(id="acct_new")

    class AccountSession:
        @staticmethod
        def create(**kw):
            _FakeStripe.sessions.append(kw)
            return _StripeObj(client_secret="acs_secret_123")


class _DB:
    def __init__(self, acct=None):
        self.row = {"merchant_id": "m1", "business_name": "Debug Bistro"}
        if acct:
            self.row["stripe_account_id"] = acct
        self.updates = []

    async def select(self, *a, **k):
        return [self.row]

    async def update(self, table, patch, filters=None):
        self.updates.append((table, patch, filters))
        return [patch]


async def _member(principal, merchant_id):
    return True


@pytest.fixture(autouse=True)
def _wire(monkeypatch):
    _FakeStripe.created = []
    _FakeStripe.sessions = []
    monkeypatch.setattr(sc, "_stripe", lambda *a, **k: _FakeStripe)
    monkeypatch.setattr(sc, "_onboarding_key", lambda: "sk_live_phone")
    monkeypatch.setattr(sc, "CONNECT_PUBLISHABLE_KEY", "pk_live_phone")
    monkeypatch.setattr(sc, "enforce_service_member", _member)
    yield


@aio
async def test_creates_account_and_session(monkeypatch):
    monkeypatch.setattr(sc, "get_db", lambda: _DB())
    out = await sc.account_session("m1", principal=object())
    assert out["account_id"] == "acct_new"
    assert out["client_secret"] == "acs_secret_123"
    assert out["publishable_key"] == "pk_live_phone"
    # account created as express w/ daily payouts + transfers
    assert _FakeStripe.created[0]["type"] == "express"
    assert _FakeStripe.created[0]["capabilities"]["transfers"] == {"requested": True}
    # session enabled the onboarding component for that account
    assert _FakeStripe.sessions[0]["account"] == "acct_new"
    assert _FakeStripe.sessions[0]["components"] == {"account_onboarding": {"enabled": True}}


@aio
async def test_reuses_existing_account(monkeypatch):
    monkeypatch.setattr(sc, "get_db", lambda: _DB(acct="acct_existing"))
    out = await sc.account_session("m1", principal=object())
    assert out["account_id"] == "acct_existing"
    assert _FakeStripe.created == []  # no new account minted
    assert _FakeStripe.sessions[0]["account"] == "acct_existing"


@aio
async def test_503_when_publishable_key_missing(monkeypatch):
    monkeypatch.setattr(sc, "CONNECT_PUBLISHABLE_KEY", "")
    monkeypatch.setattr(sc, "get_db", lambda: _DB())
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as ei:
        await sc.account_session("m1", principal=object())
    assert ei.value.status_code == 503


@aio
async def test_status_reads_account_as_dict_not_stripeobject(monkeypatch):
    """Regression: _retrieve_account must return a plain dict. This SDK's
    StripeObject has no .get(), so the status endpoint's acc.get(...) would
    500 the polling endpoint the onboarding UI depends on — the same bug class
    the webhooks hit."""
    import stripe as stripe_sdk
    acct_obj = stripe_sdk.Account.construct_from(
        {"id": "acct_x", "charges_enabled": True, "payouts_enabled": True,
         "details_submitted": True}, "sk")

    class _S:
        class Account:
            @staticmethod
            def retrieve(a, **k):
                return acct_obj
    monkeypatch.setattr(sc, "_stripe", lambda *a, **k: _S)
    monkeypatch.setattr(sc, "STRIPE_SECRET_KEY", "sk_live_x")
    d = sc._retrieve_account("acct_x")
    assert isinstance(d, dict)
    # the exact access the status endpoint does — must not raise
    assert d.get("charges_enabled") is True
    assert d.get("payouts_enabled") is True


@aio
async def test_502_when_session_create_fails(monkeypatch):
    monkeypatch.setattr(sc, "get_db", lambda: _DB(acct="acct_x"))

    def _boom(**kw):
        raise RuntimeError("stripe down")
    monkeypatch.setattr(_FakeStripe.AccountSession, "create", staticmethod(_boom))
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as ei:
        await sc.account_session("m1", principal=object())
    assert ei.value.status_code == 502
