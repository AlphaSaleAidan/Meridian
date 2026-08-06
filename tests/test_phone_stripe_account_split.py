"""
PHONE-ORDER STRIPE ACCOUNT SPLIT — phone order checkouts on their own Stripe
account (STRIPE_PHONE_SECRET_KEY), separate from the platform account that bills
subscriptions.

Connected accounts belong to the platform that created them, so every
stripe_account_id minted under the old key is an INVALID transfer destination
under the new one. These pin the three things that must hold:

  1. env unset  → byte-identical to the single-account behavior (no extra Stripe
     calls, platform key on the session).
  2. phone key + FOREIGN connected account → warn and take the direct
     platform charge (the unboarded-merchant path), never fail the payment.
  3. phone key + OWNED connected account → destination charge exactly as today.

Plus the dual webhook signing secret and the onboarding key selection.
Stripe is mocked throughout; no key value ever appears here.
"""
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("ENCRYPTION_KEY", "0" * 64)

_DIR = str(Path(__file__).resolve().parents[1] / "services" / "phone_agent")
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)

import payment_links as pl  # noqa: E402
from src.api.routes import stripe_connect as sc  # noqa: E402

aio = pytest.mark.asyncio

PLATFORM_KEY = "sk_test_platform"
PHONE_KEY = "sk_test_phone"

ORDER = {
    "merchant_id": "m1", "caller_phone": "+15551234567", "currency": "cad",
    "items": [{"name": "Burger", "quantity": 1, "unit_price": 20.0}],
    "total": 20.0,
}


def _cfg(**kw):
    base = dict(stripe_account_id="", stripe_charges_enabled=False,
                pos_system="square", pos_access_token="tok", pos_location_id="loc")
    base.update(kw)
    return SimpleNamespace(**base)


class _StripeObj:
    """Subscript-only, like a real StripeObject (no .get)."""
    def __init__(self, **d):
        self._d = d

    def __getitem__(self, k):
        return self._d[k]


class _StripeErr(Exception):
    """Stands in for stripe.error.PermissionError etc. — what matters to the
    guard is the http_status attribute the SDK puts on its exceptions."""
    def __init__(self, msg, http_status=None):
        super().__init__(msg)
        self.http_status = http_status


class _FakeStripe:
    """Account.retrieve answers per `owned`; everything is counted so the cache
    can be asserted on."""
    captured: dict = {}
    retrieves: list = []
    owned: set = set()
    raise_status = 403

    class checkout:
        class Session:
            @staticmethod
            def create(**kwargs):
                _FakeStripe.captured = kwargs
                return _StripeObj(id="cs_1", url="https://checkout.stripe.com/pay/cs_1")

    class Account:
        @staticmethod
        def retrieve(acct, **kw):
            _FakeStripe.retrieves.append((acct, kw.get("api_key", "")))
            if acct in _FakeStripe.owned:
                return _StripeObj(id=acct)
            raise _StripeErr("No such account", http_status=_FakeStripe.raise_status)


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    """Fresh module state per test — the membership cache is process-wide."""
    _FakeStripe.captured = {}
    _FakeStripe.retrieves = []
    _FakeStripe.owned = set()
    _FakeStripe.raise_status = 403
    pl._connect_membership.clear()
    monkeypatch.setattr(pl, "UNIFIED_PAYMENTS_ENABLED", True)
    monkeypatch.setattr(pl, "STRIPE_SECRET_KEY", PLATFORM_KEY)
    monkeypatch.setattr(pl, "STRIPE_PHONE_SECRET_KEY", "")
    monkeypatch.setattr(pl, "_stripe", lambda: _FakeStripe)

    async def no_record(*a, **k):
        return False
    monkeypatch.setattr(pl, "_record_checkout_session", no_record)

    async def no_link(*a, **k):
        raise AssertionError("must not fall back to the per-POS link")
    monkeypatch.setattr(pl, "create_payment_link", no_link)
    yield
    pl._connect_membership.clear()


# ── 1. phone key UNSET → nothing changes ──────────────────────────────────

def test_key_selection_defaults_to_platform():
    assert pl._active_stripe_key() == PLATFORM_KEY


def test_key_selection_prefers_phone_key(monkeypatch):
    monkeypatch.setattr(pl, "STRIPE_PHONE_SECRET_KEY", PHONE_KEY)
    assert pl._active_stripe_key() == PHONE_KEY


def test_no_phone_key_skips_the_membership_check():
    """One platform → no reason to ask Stripe who owns the account."""
    assert pl._connect_account_owned("acct_merchant") is True
    assert _FakeStripe.retrieves == []


@aio
async def test_unset_still_destination_charges_on_platform_key():
    out = await pl.create_checkout(
        ORDER, _cfg(stripe_account_id="acct_merchant", stripe_charges_enabled=True), "ord_1")
    assert out["method"] == "stripe"
    cap = _FakeStripe.captured
    assert cap["payment_intent_data"]["transfer_data"]["destination"] == "acct_merchant"
    # on_behalf_of makes the merchant the settlement merchant → their money
    # settles in their own currency (no cross-border FX on the order amount).
    assert cap["payment_intent_data"]["on_behalf_of"] == "acct_merchant"
    assert cap["api_key"] == PLATFORM_KEY
    assert _FakeStripe.retrieves == []  # no membership probe at all


@aio
async def test_direct_charge_has_no_on_behalf_of():
    # Unboarded/demo merchant → direct charge on the platform, no connected
    # account to settle on behalf of.
    out = await pl.create_checkout(ORDER, _cfg(), "ord_obo_direct")
    assert out["method"] == "stripe"
    assert "payment_intent_data" not in _FakeStripe.captured


@aio
async def test_unset_platform_direct_when_not_onboarded():
    out = await pl.create_checkout(ORDER, _cfg(), "ord_2")
    assert out["method"] == "stripe"
    assert "payment_intent_data" not in _FakeStripe.captured


# ── 2. phone key + FOREIGN account → direct charge, never a failure ───────

@aio
async def test_foreign_account_falls_back_to_direct_charge(monkeypatch, caplog):
    """The merchant's Connect account was created by the OLD platform: Stripe
    403s on retrieve, so we must charge directly instead of building a
    destination charge Stripe would reject."""
    monkeypatch.setattr(pl, "STRIPE_PHONE_SECRET_KEY", PHONE_KEY)
    with caplog.at_level("WARNING"):
        out = await pl.create_checkout(
            ORDER, _cfg(stripe_account_id="acct_old_platform", stripe_charges_enabled=True), "ord_3")
    assert out["method"] == "stripe"
    cap = _FakeStripe.captured
    assert "payment_intent_data" not in cap        # no transfer_data, no app fee
    assert cap["api_key"] == PHONE_KEY             # charged on the new account
    assert "acct_old_platform" in caplog.text
    assert _FakeStripe.retrieves == [("acct_old_platform", PHONE_KEY)]


@aio
async def test_foreign_account_membership_answer_is_cached(monkeypatch):
    monkeypatch.setattr(pl, "STRIPE_PHONE_SECRET_KEY", PHONE_KEY)
    cfg = _cfg(stripe_account_id="acct_old_platform", stripe_charges_enabled=True)
    for i in range(3):
        await pl.create_checkout(ORDER, cfg, f"ord_c{i}")
    assert len(_FakeStripe.retrieves) == 1  # one probe covers the TTL window


def test_transient_failure_is_not_cached(monkeypatch):
    """A 500/network blip must not pin the merchant to platform-direct charges
    for the whole TTL — only definitive 4xx answers are remembered."""
    monkeypatch.setattr(pl, "STRIPE_PHONE_SECRET_KEY", PHONE_KEY)
    _FakeStripe.raise_status = 500
    assert pl._connect_account_owned("acct_x") is False
    assert pl._connect_account_owned("acct_x") is False
    assert len(_FakeStripe.retrieves) == 2
    assert "acct_x" not in pl._connect_membership


def test_expired_cache_entry_is_rechecked(monkeypatch):
    monkeypatch.setattr(pl, "STRIPE_PHONE_SECRET_KEY", PHONE_KEY)
    monkeypatch.setattr(pl, "CONNECT_MEMBERSHIP_TTL_S", 0)
    _FakeStripe.owned = {"acct_new"}
    assert pl._connect_account_owned("acct_new") is True
    assert pl._connect_account_owned("acct_new") is True
    assert len(_FakeStripe.retrieves) == 2


# ── 3. phone key + OWNED account → destination charge, unchanged ──────────

@aio
async def test_owned_account_still_destination_charges(monkeypatch):
    monkeypatch.setattr(pl, "STRIPE_PHONE_SECRET_KEY", PHONE_KEY)
    monkeypatch.setattr(pl, "PLATFORM_FEE_BPS", 100)
    _FakeStripe.owned = {"acct_new_platform"}
    out = await pl.create_checkout(
        ORDER, _cfg(stripe_account_id="acct_new_platform", stripe_charges_enabled=True), "ord_4")
    assert out["method"] == "stripe"
    pi = _FakeStripe.captured["payment_intent_data"]
    assert pi["transfer_data"]["destination"] == "acct_new_platform"
    assert pi["application_fee_amount"] > 0          # Meridian's fee still taken
    assert _FakeStripe.captured["api_key"] == PHONE_KEY


@aio
async def test_website_checkout_uses_the_same_guard(monkeypatch):
    """create_website_checkout shares _stripe_checkout; it must not build a
    destination charge to a foreign account either (it cannot fall back to a
    POS link — it raises — so a rejected transfer would strand the order)."""
    monkeypatch.setattr(pl, "STRIPE_PHONE_SECRET_KEY", PHONE_KEY)
    out = await pl.create_website_checkout(
        ORDER, _cfg(stripe_account_id="acct_old_platform", stripe_charges_enabled=True), "web_1")
    assert out["method"] == "stripe"
    assert "payment_intent_data" not in _FakeStripe.captured
    assert _FakeStripe.captured["metadata"]["website_order_id"] == "web_1"


@aio
async def test_phone_key_alone_enables_stripe_checkout(monkeypatch):
    """Phone key set, platform key absent → still a real Stripe checkout."""
    monkeypatch.setattr(pl, "STRIPE_SECRET_KEY", "")
    monkeypatch.setattr(pl, "STRIPE_PHONE_SECRET_KEY", PHONE_KEY)
    out = await pl.create_checkout(ORDER, _cfg(), "ord_5")
    assert out["method"] == "stripe"
    assert _FakeStripe.captured["api_key"] == PHONE_KEY


@aio
async def test_no_key_at_all_falls_back_to_pos_link(monkeypatch):
    monkeypatch.setattr(pl, "STRIPE_SECRET_KEY", "")
    monkeypatch.setattr(pl, "STRIPE_PHONE_SECRET_KEY", "")

    async def fake_link(*a, **k):
        return {"url": "x", "method": "square"}
    monkeypatch.setattr(pl, "create_payment_link", fake_link)
    out = await pl.create_checkout(ORDER, _cfg(), "ord_6")
    assert out["method"] == "square"


# ── 4. webhook: two signing secrets, one handler ──────────────────────────

class _WebhookStripe:
    """construct_event succeeds only for the secret that signed the payload."""
    class Webhook:
        @staticmethod
        def construct_event(payload, sig, secret):
            if sig != f"signed_by:{secret}":
                raise ValueError("Invalid signature")
            return {"type": "account.updated",
                    "data": {"object": {"id": "acct_1", "charges_enabled": True}}}


_WEBHOOK_EVENT_BODY = json.dumps(
    {"type": "account.updated",
     "data": {"object": {"id": "acct_1", "charges_enabled": True}}}).encode()


class _Req:
    def __init__(self, sig, body=None):
        self.headers = {"stripe-signature": sig}
        # The handler reads the VERIFIED payload as a dict (json.loads), not the
        # construct_event return, so the body must carry the event.
        self._body = body if body is not None else _WEBHOOK_EVENT_BODY

    async def body(self):
        return self._body


class _WebhookDB:
    def __init__(self):
        self.updates = []

    async def select(self, *a, **k):
        return [{"merchant_id": "m1"}]

    async def update(self, table, patch, filters=None):
        self.updates.append((table, patch, filters))
        return [patch]


@pytest.fixture
def _wh(monkeypatch):
    db = _WebhookDB()
    monkeypatch.setattr(sc, "_stripe", lambda *a, **k: _WebhookStripe)
    monkeypatch.setattr(sc, "get_db", lambda: db)
    monkeypatch.setattr(sc, "CONNECT_WEBHOOK_SECRET", "whsec_platform")
    monkeypatch.setattr(sc, "PHONE_WEBHOOK_SECRET", "whsec_phone")
    return db


@aio
async def test_webhook_accepts_primary_secret(_wh):
    res = await sc.connect_webhook(_Req("signed_by:whsec_platform"))
    assert res == {"received": True}
    assert _wh.updates == [("phone_agent_config", {"stripe_charges_enabled": True},
                            {"stripe_account_id": "eq.acct_1"})]


@aio
async def test_webhook_accepts_phone_secret_and_processes_identically(_wh):
    res = await sc.connect_webhook(_Req("signed_by:whsec_phone"))
    assert res == {"received": True}
    assert _wh.updates == [("phone_agent_config", {"stripe_charges_enabled": True},
                            {"stripe_account_id": "eq.acct_1"})]


@aio
async def test_webhook_rejects_when_neither_secret_matches(_wh):
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as e:
        await sc.connect_webhook(_Req("signed_by:whsec_attacker"))
    assert e.value.status_code == 400
    assert _wh.updates == []


@aio
async def test_webhook_fails_closed_with_no_secrets_configured(monkeypatch):
    from fastapi import HTTPException
    monkeypatch.setattr(sc, "_stripe", lambda *a, **k: _WebhookStripe)
    monkeypatch.setattr(sc, "CONNECT_WEBHOOK_SECRET", "")
    monkeypatch.setattr(sc, "PHONE_WEBHOOK_SECRET", "")
    with pytest.raises(HTTPException) as e:
        await sc.connect_webhook(_Req("signed_by:anything"))
    assert e.value.status_code == 503


@aio
async def test_webhook_unchanged_when_phone_secret_unset(monkeypatch):
    """Phone secret absent → exactly the pre-split single-secret behavior."""
    from fastapi import HTTPException
    db = _WebhookDB()
    monkeypatch.setattr(sc, "_stripe", lambda *a, **k: _WebhookStripe)
    monkeypatch.setattr(sc, "get_db", lambda: db)
    monkeypatch.setattr(sc, "CONNECT_WEBHOOK_SECRET", "whsec_platform")
    monkeypatch.setattr(sc, "PHONE_WEBHOOK_SECRET", "")
    assert await sc.connect_webhook(_Req("signed_by:whsec_platform")) == {"received": True}
    with pytest.raises(HTTPException):
        await sc.connect_webhook(_Req("signed_by:whsec_phone"))


# ── 5. onboarding key selection ───────────────────────────────────────────

def test_onboarding_uses_platform_key_by_default(monkeypatch):
    monkeypatch.setattr(sc, "STRIPE_SECRET_KEY", PLATFORM_KEY)
    monkeypatch.setattr(sc, "STRIPE_PHONE_SECRET_KEY", PHONE_KEY)
    monkeypatch.setattr(sc, "PHONE_ONBOARDING", False)
    assert sc._onboarding_key() == PLATFORM_KEY


def test_onboarding_uses_phone_key_when_opted_in(monkeypatch):
    monkeypatch.setattr(sc, "STRIPE_SECRET_KEY", PLATFORM_KEY)
    monkeypatch.setattr(sc, "STRIPE_PHONE_SECRET_KEY", PHONE_KEY)
    monkeypatch.setattr(sc, "PHONE_ONBOARDING", True)
    assert sc._onboarding_key() == PHONE_KEY


def test_onboarding_flag_without_phone_key_is_inert(monkeypatch):
    monkeypatch.setattr(sc, "STRIPE_SECRET_KEY", PLATFORM_KEY)
    monkeypatch.setattr(sc, "STRIPE_PHONE_SECRET_KEY", "")
    monkeypatch.setattr(sc, "PHONE_ONBOARDING", True)
    assert sc._onboarding_key() == PLATFORM_KEY


def test_status_reads_accounts_from_either_platform(monkeypatch):
    """A merchant onboarded under the phone key must still resolve on the
    status endpoint, which tries the platform key first."""
    seen = []

    class _S:
        class Account:
            @staticmethod
            def retrieve(acct, api_key=""):
                seen.append(api_key)
                if api_key != PHONE_KEY:
                    raise _StripeErr("No such account", http_status=403)
                return {"charges_enabled": True}

    monkeypatch.setattr(sc, "_stripe", lambda *a, **k: _S)
    monkeypatch.setattr(sc, "STRIPE_SECRET_KEY", PLATFORM_KEY)
    monkeypatch.setattr(sc, "STRIPE_PHONE_SECRET_KEY", PHONE_KEY)
    assert sc._retrieve_account("acct_new")["charges_enabled"] is True
    assert seen == [PLATFORM_KEY, PHONE_KEY]
