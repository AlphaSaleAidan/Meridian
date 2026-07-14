"""
Clover Hosted Checkout text-to-pay — order-time routing coverage.

What must be right before this touches a real merchant:

  1. TOGGLE: payment_link_provider defaults to "stripe" → existing checkout
     behavior byte-for-byte unchanged; only an explicit "clover" (with a real
     Clover connection) routes to the new path.
  2. LAZY: the clover path does NO Clover HTTP at order time — it only writes
     the checkout_sessions row (payload carries the ready-to-POST HCO body,
     NEVER the access token) and returns the branded /p short link, because
     HCO sessions expire 15 minutes after creation.
  3. MONEY: tax is computed INTO the cart (HCO ignores Clover tax config).
  4. NEVER STRAND: any failure on the clover path falls back to the existing
     checkout flow.
  5. The fabricated pay_links endpoint is GONE — the per-POS "clover" branch
     also routes through the lazy short-link flow.
"""
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_DIR = str(Path(__file__).resolve().parents[1])
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)

import payment_links as pl  # noqa: E402
from merchant_config import MerchantPhoneConfig, _norm_payment_link_provider  # noqa: E402

aio = pytest.mark.asyncio

ORDER = {
    "merchant_id": "m-clover", "caller_phone": "+16045550123", "currency": "cad",
    "customer_name": "Priya Sharma", "order_type": "pickup",
    "items": [
        {"name": "Butter Chicken", "quantity": 2, "unit_price": 15.5},
        {"name": "Naan", "quantity": 1, "unit_price": 3.0, "size": "garlic"},
    ],
    "subtotal": 34.0, "tax": 4.42, "total": 38.42,
}


def _cfg(**kw):
    base = dict(
        merchant_id="m-clover", payment_link_provider="clover",
        pos_system="clover", pos_access_token="clover-tok", pos_location_id="CLOVERMID1",
        stripe_account_id="", stripe_charges_enabled=False, plan_tier="",
    )
    base.update(kw)
    return SimpleNamespace(**base)


class _CaptureClient:
    """Fake httpx.AsyncClient capturing every request; programmable status."""
    posts: list = []
    gets: list = []
    post_status = 201
    get_json: list = []

    def __init__(self, *a, **k):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, json=None, headers=None, **kw):
        _CaptureClient.posts.append({"url": url, "json": json, "headers": headers})
        return SimpleNamespace(status_code=_CaptureClient.post_status, text="", json=lambda: {})

    async def get(self, url, params=None, headers=None, **kw):
        _CaptureClient.gets.append({"url": url, "params": params})
        return SimpleNamespace(status_code=200, json=lambda: _CaptureClient.get_json)


@pytest.fixture()
def capture(monkeypatch):
    _CaptureClient.posts, _CaptureClient.gets = [], []
    _CaptureClient.post_status, _CaptureClient.get_json = 201, []
    monkeypatch.setattr(pl, "SUPABASE_URL", "https://fake.supabase.co")
    monkeypatch.setattr(pl, "SUPABASE_KEY", "fake-key")
    monkeypatch.setattr(pl, "PUBLIC_PAY_BASE", "https://api.meridian.tips")
    monkeypatch.setattr(pl.httpx, "AsyncClient", _CaptureClient)
    return _CaptureClient


# ── toggle routing ───────────────────────────────────────────────────────────

def test_provider_normalizes_to_stripe():
    assert _norm_payment_link_provider(None) == "stripe"
    assert _norm_payment_link_provider("") == "stripe"
    assert _norm_payment_link_provider("square") == "stripe"
    assert _norm_payment_link_provider(" Clover ") == "clover"
    assert MerchantPhoneConfig.__dataclass_fields__["payment_link_provider"].default == "stripe"


@aio
async def test_default_stripe_merchant_never_touches_clover_path(monkeypatch, capture):
    """No toggle → the clover path must not run at all (existing behavior)."""
    monkeypatch.setattr(pl, "UNIFIED_PAYMENTS_ENABLED", False)

    async def fail_clover(*a, **k):
        raise AssertionError("clover path must not run for a stripe-provider merchant")

    monkeypatch.setattr(pl, "_clover_lazy_checkout", fail_clover)

    async def fake_link(*a, **k):
        return {"url": "x", "method": "square"}

    monkeypatch.setattr(pl, "create_payment_link", fake_link)
    out = await pl.create_checkout(ORDER, _cfg(payment_link_provider="stripe",
                                               pos_system="square"), "ord_1")
    assert out["method"] == "square"


@aio
async def test_clover_toggle_returns_lazy_short_link(capture):
    """Toggle ON + manual Clover creds → /p short link, method clover, and the
    ONLY HTTP is the checkout_sessions insert (no Clover call at order time)."""
    out = await pl.create_checkout(ORDER, _cfg(), "POS-77")
    assert out["method"] == "clover"
    assert out["url"] == f"https://api.meridian.tips/p/{out['short_code']}"
    assert len(out["short_code"]) == 8
    assert len(capture.posts) == 1
    assert "checkout_sessions" in capture.posts[0]["url"]
    assert all("clover.com" not in p["url"] for p in capture.posts)


@aio
async def test_clover_row_carries_hco_payload_but_never_the_token(capture):
    await pl.create_checkout(ORDER, _cfg(), "POS-77")
    row = capture.posts[0]["json"]
    assert row["provider"] == "clover"
    assert row["status"] == "created"
    assert row["provider_ref"] is None                      # set lazily at tap
    assert row["checkout_url"] is None
    assert row["pos_order_id"] == "POS-77"
    assert row["caller_phone"] == "+16045550123"
    payload = row["payload"]
    assert payload["clover_merchant_id"] == "CLOVERMID1"
    req = payload["hco_request"]
    assert req["customer"] == {"firstName": "Priya", "lastName": "Sharma",
                               "phoneNumber": "+16045550123"}
    lines = req["shoppingCart"]["lineItems"]
    assert {"name": "Butter Chicken", "price": 1550, "unitQty": 2} in lines
    assert {"name": "Naan (garlic)", "price": 300, "unitQty": 1} in lines
    # token must NEVER be persisted in the row
    assert "clover-tok" not in str(row)


@aio
async def test_clover_toggle_oauth_merchant_checks_pos_connections(capture):
    """OAuth merchants have no manual creds on the phone config — the gate
    checks pos_connections existence (token stays encrypted server-side)."""
    cfg = _cfg(pos_system="", pos_access_token="", pos_location_id="")
    capture.get_json = [{"id": "conn-1"}]
    out = await pl.create_checkout(ORDER, cfg, "POS-88")
    assert out["method"] == "clover"
    assert len(capture.gets) == 1
    assert "pos_connections" in capture.gets[0]["url"]
    assert capture.gets[0]["params"]["provider"] == "eq.clover"
    # merchant id resolved at tap time from pos_connections → hint empty
    assert capture.posts[0]["json"]["payload"]["clover_merchant_id"] == ""


@aio
async def test_clover_toggle_without_connection_falls_back(monkeypatch, capture):
    """Toggle ON but no Clover connection anywhere → default checkout path."""
    monkeypatch.setattr(pl, "UNIFIED_PAYMENTS_ENABLED", False)
    capture.get_json = []  # no pos_connections row

    async def fake_link(*a, **k):
        return {"url": "x", "method": "meridian"}

    monkeypatch.setattr(pl, "create_payment_link", fake_link)
    cfg = _cfg(pos_system="", pos_access_token="", pos_location_id="")
    out = await pl.create_checkout(ORDER, cfg, "ord_1")
    assert out["method"] == "meridian"
    assert capture.posts == []                              # no clover row written


@aio
async def test_clover_row_write_failure_falls_back_to_stripe(monkeypatch, capture):
    """checkout_sessions insert fails → never hand out a dead /p link; the
    order falls through to the (still-working) default checkout."""
    monkeypatch.setattr(pl, "UNIFIED_PAYMENTS_ENABLED", False)
    capture.post_status = 401

    async def fake_link(*a, **k):
        return {"url": "x", "method": "square"}

    monkeypatch.setattr(pl, "create_payment_link", fake_link)
    out = await pl.create_checkout(ORDER, _cfg(), "ord_1")
    assert out["method"] == "square"


# ── money math (tax INTO the cart — HCO ignores Clover tax config) ──────────

def test_hco_line_items_add_explicit_tax_line():
    lines, total = pl._clover_hco_line_items(ORDER)
    assert {"name": "Tax", "price": 442, "unitQty": 1} in lines
    assert total == 2 * 1550 + 300 + 442                    # 3842 = $38.42
    assert total == int(round(ORDER["total"] * 100))


def test_hco_line_items_unpriced_order_single_tax_inclusive_line():
    order = {"total": 38.42, "tax": 4.42, "items": [{"name": "Combo", "quantity": 1}]}
    lines, total = pl._clover_hco_line_items(order)
    assert lines == [{"name": "Phone order", "price": 3842, "unitQty": 1}]
    assert total == 3842


def test_hco_customer_never_empty():
    # HCO requires at least one of firstName/lastName/email
    assert pl._split_name("") == ("Guest", "")
    assert pl._split_name("Priya Sharma") == ("Priya", "Sharma")


# ── fabricated pay_links endpoint is gone ────────────────────────────────────

def test_fabricated_pay_links_call_is_deleted():
    assert not hasattr(pl, "_clover_payment_link")
    import ast
    import inspect

    # No CODE constructs the non-existent /pay_links URL (comments explaining
    # the history are fine — string literals are not).
    tree = ast.parse(inspect.getsource(pl))
    literals = [n.value for n in ast.walk(tree)
                if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    assert not any("pay_links" in s for s in literals)


@aio
async def test_create_payment_link_clover_routes_to_lazy_flow(capture):
    """The per-POS 'clover' branch also uses the lazy short link (location_id
    carries the Clover merchant id on this signature)."""
    out = await pl.create_payment_link(ORDER, "clover", "POS-9", "tok", "CLOVERMID1")
    assert out["method"] == "clover"
    assert "/p/" in out["url"]
    assert capture.posts[0]["json"]["payload"]["clover_merchant_id"] == "CLOVERMID1"
    assert all("clover.com" not in p["url"] for p in capture.posts)
