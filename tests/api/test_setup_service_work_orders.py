"""Setup Services — one mechanism for every adder product.

    the merchant PAYS → a work order is created → it is posted to the Foundry
    dev marketplace → devs bid with actual work → the OWNER picks.

What is worth pinning down is the ordering and the money:

  * closing does NOT post — developers should never do spec work against a
    deal that never paid
  * the payment event DOES post, and posts everything that org bought
  * a webhook retry re-posts nothing
  * a marketplace outage never fails a verified payment
  * a service nobody registered still reaches the board

Run: python -m pytest tests/api/test_setup_service_work_orders.py -v
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.services import setup_services as ss  # noqa: E402

ORG = "11111111-1111-1111-1111-111111111111"


@pytest.fixture(autouse=True)
def _supabase_env(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-key")
    monkeypatch.setattr(ss, "POST_ON_CLOSE", False)
    monkeypatch.setattr(ss, "MARKETPLACE_ENABLED", True)


class _Resp:
    def __init__(self, status_code=200, body=None):
        self.status_code = status_code
        self._body = body if body is not None else {}
        self.content = b"x"
        self.text = str(self._body)

    def json(self):
        return self._body


def _http(monkeypatch, *, get=None, post=None, patch=None):
    """Stub httpx and record every call the module makes."""
    calls = {"get": [], "post": [], "patch": []}

    class _Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return False

        async def get(self, url, **kw):
            calls["get"].append((url, kw))
            return get(url) if callable(get) else (get or _Resp(200, []))

        async def post(self, url, **kw):
            calls["post"].append((url, kw))
            return post(url, kw) if callable(post) else (post or _Resp(201, [{"id": "wo-1"}]))

        async def patch(self, url, **kw):
            calls["patch"].append((url, kw))
            return patch or _Resp(204)

    monkeypatch.setattr(ss.httpx, "AsyncClient", lambda **_: _Client())
    return calls


# ── The catalog ──────────────────────────────────────────────────────────────

def test_every_registered_adder_has_a_posting_route():
    for kind, service in ss.CATALOG.items():
        assert service.endpoint.startswith("/api/"), kind
        assert callable(service.payload), kind


def test_an_unregistered_service_still_reaches_the_board():
    """A new adder must never be silently un-postable just because nobody
    added it to the catalog yet."""
    service = ss.service_for("something-invented-next-quarter")
    assert service.endpoint == "/api/work-orders/order"
    assert service is ss.GENERIC


def test_the_three_adders_sold_today_are_registered():
    assert set(ss.CATALOG) == {"website", "ad_spot", "crm"}
    # Custom CRM build is scoped per deal — it carries no catalog price.
    assert ss.CATALOG["crm"].fixed_price is False
    assert ss.CATALOG["website"].fixed_price is True


def test_payload_builders_survive_a_thin_brief():
    """A rep can close with the minimum filled in; nothing may KeyError on the
    way to the board."""
    order = {"business_name": "Acme", "service_kind": "crm", "price_cents": 120000, "currency": "USD"}
    for service in list(ss.CATALOG.values()) + [ss.GENERIC]:
        payload = service.payload(order, {})
        assert payload["company"] == "Acme"
        assert "email" in payload


def test_website_payload_normalises_a_bare_domain():
    payload = ss.CATALOG["website"].payload(
        {"business_name": "Acme"}, {"currentUrl": "acme.com", "pages": "Home, Menu, Contact"}
    )
    assert payload["currentUrl"] == "https://acme.com"
    assert payload["pages"] == ["Home", "Menu", "Contact"]


# ── Recording ────────────────────────────────────────────────────────────────

async def test_recording_at_close_does_not_post(monkeypatch):
    """The close records; the payment posts. Nothing reaches Foundry here."""
    calls = _http(monkeypatch)

    row = await ss.record_work_order(
        service_kind="crm", market="us", business_name="Acme",
        price_cents=120000, brief={"scope": "pipeline + follow-ups"}, org_id=ORG,
    )

    assert row == {"id": "wo-1"}
    posted = [u for u, _ in calls["post"] if "foundry" in u or "/agency/" in u]
    assert posted == []
    body = calls["post"][0][1]["json"]
    assert body["payment_status"] == "awaiting_payment"
    assert body["status"] == "awaiting_payment"
    assert body["currency"] == "USD"


async def test_canadian_sale_records_in_cad(monkeypatch):
    calls = _http(monkeypatch)
    await ss.record_work_order(
        service_kind="ad_spot", market="ca", business_name="Acme",
        price_cents=140000, brief={}, org_id=ORG,
    )
    assert calls["post"][0][1]["json"]["currency"] == "CAD"


async def test_a_duplicate_live_order_is_not_a_second_purchase(monkeypatch):
    """The unique index fires on a re-close — that returns None, not a row."""
    _http(monkeypatch, post=_Resp(409, {"message": "duplicate key"}))
    row = await ss.record_work_order(
        service_kind="website", market="us", business_name="Acme",
        price_cents=50000, brief={}, org_id=ORG,
    )
    assert row is None


async def test_post_on_close_switch_restores_the_old_timing(monkeypatch):
    """The switch exists because flipping a live product's timing deserves one."""
    monkeypatch.setattr(ss, "POST_ON_CLOSE", True)
    posted = {}

    async def _fake_post(order):
        posted["order"] = order
        return "job-1"

    monkeypatch.setattr(ss, "post_to_marketplace", _fake_post)
    _http(monkeypatch)

    await ss.record_work_order(
        service_kind="website", market="us", business_name="Acme",
        price_cents=50000, brief={}, org_id=ORG,
    )
    assert posted["order"]["id"] == "wo-1"


# ── Posting ──────────────────────────────────────────────────────────────────

async def test_posting_sends_the_brief_to_the_right_foundry_route(monkeypatch):
    calls = _http(monkeypatch, post=lambda url, kw: _Resp(200, {"jobId": "job-9"}))

    job_id = await ss.post_to_marketplace({
        "id": "wo-1", "service_kind": "ad_spot", "business_name": "Acme",
        "contact_email": "owner@acme.test", "price_cents": 100000, "currency": "USD",
        "brief": {"goal": "sell the special", "placement": "instagram_reel"},
    })

    assert job_id == "job-9"
    url, kw = calls["post"][0]
    assert url.endswith("/api/spots/order")
    assert kw["json"]["goal"] == "sell the special"


async def test_a_409_reuses_the_live_posting(monkeypatch):
    _http(monkeypatch, post=lambda url, kw: _Resp(409, {"jobId": "job-live", "error": "already running"}))
    assert await ss.post_to_marketplace(
        {"id": "wo-1", "service_kind": "website", "business_name": "Acme", "brief": {}}
    ) == "job-live"


async def test_a_failed_posting_is_recorded_not_swallowed(monkeypatch):
    calls = _http(monkeypatch, post=lambda url, kw: _Resp(500, {"error": "boom"}))

    assert await ss.post_to_marketplace(
        {"id": "wo-1", "service_kind": "crm", "business_name": "Acme", "brief": {}}
    ) is None

    last_patch = calls["patch"][-1][1]["json"]
    assert last_patch["status"] == "failed"
    assert "not posted" in last_patch["status_detail"]


async def test_a_brief_stored_as_json_text_still_posts(monkeypatch):
    """PostgREST can hand jsonb back as a string; that must not lose the brief."""
    calls = _http(monkeypatch, post=lambda url, kw: _Resp(200, {"jobId": "job-1"}))

    await ss.post_to_marketplace({
        "id": "wo-1", "service_kind": "ad_spot", "business_name": "Acme",
        "brief": '{"goal": "sell the special"}',
    })

    assert calls["post"][0][1]["json"]["goal"] == "sell the special"


async def test_marketplace_kill_switch(monkeypatch):
    monkeypatch.setattr(ss, "MARKETPLACE_ENABLED", False)
    calls = _http(monkeypatch)
    assert await ss.post_to_marketplace(
        {"id": "wo-1", "service_kind": "crm", "business_name": "Acme", "brief": {}}
    ) is None
    assert calls["post"] == []


# ── The payment trigger ──────────────────────────────────────────────────────

async def test_payment_posts_everything_that_org_bought(monkeypatch):
    """A merchant who bought a website AND a spot gets both on the board."""
    orders = [
        {"id": "wo-1", "service_kind": "website", "business_name": "Acme", "brief": {}},
        {"id": "wo-2", "service_kind": "ad_spot", "business_name": "Acme", "brief": {}},
    ]
    calls = _http(
        monkeypatch,
        get=lambda url: _Resp(200, orders),
        post=lambda url, kw: _Resp(200, {"jobId": "job-x"}),
    )

    posted = await ss.dispatch_paid_orders(org_id=ORG, session_id="cs_test_1")

    assert posted == 2
    # Only awaiting_payment orders are asked for — that is what makes a retry safe.
    assert "payment_status=eq.awaiting_payment" in calls["get"][0][0]
    paid_patches = [c[1]["json"] for c in calls["patch"] if c[1]["json"].get("payment_status") == "paid"]
    assert len(paid_patches) == 2
    assert all(p["stripe_session_id"] == "cs_test_1" for p in paid_patches)


async def test_a_webhook_retry_reposts_nothing(monkeypatch):
    """Second delivery of the same event: the orders are already paid, so the
    awaiting_payment query returns nothing and nothing is posted again."""
    calls = _http(monkeypatch, get=lambda url: _Resp(200, []))
    assert await ss.dispatch_paid_orders(org_id=ORG, session_id="cs_test_1") == 0
    assert calls["post"] == []


async def test_dispatch_without_an_org_does_nothing(monkeypatch):
    calls = _http(monkeypatch)
    assert await ss.dispatch_paid_orders(org_id=None) == 0
    assert calls["get"] == []


async def test_a_marketplace_outage_never_fails_the_payment(monkeypatch):
    """The money is verified and the org is active — a Foundry outage must not
    make Stripe retry the whole event."""
    orders = [{"id": "wo-1", "service_kind": "website", "business_name": "Acme", "brief": {}}]

    def _boom(_url, _kw):
        raise RuntimeError("connection refused")

    _http(monkeypatch, get=lambda url: _Resp(200, orders), post=_boom)

    assert await ss.dispatch_paid_orders(org_id=ORG, session_id="cs_1") == 0


async def test_orders_are_marked_paid_even_when_posting_fails(monkeypatch):
    """The merchant DID pay. That fact is recorded regardless of whether the
    board accepted the posting — otherwise a retry would re-charge nothing but
    would also never show the money arrived."""
    orders = [{"id": "wo-1", "service_kind": "website", "business_name": "Acme", "brief": {}}]
    calls = _http(
        monkeypatch,
        get=lambda url: _Resp(200, orders),
        post=lambda url, kw: _Resp(503, {"error": "down"}),
    )

    await ss.dispatch_paid_orders(org_id=ORG, session_id="cs_1")

    patches = [c[1]["json"] for c in calls["patch"]]
    assert any(p.get("payment_status") == "paid" for p in patches)
    assert any(p.get("status") == "failed" for p in patches)
