"""Ad-spot pipeline invariants — the 30-second spot sold in both rep portals.

This is a PAID deliverable (US$1,000 / CA$1,400), so the things worth pinning
down are the ones that would either take money for nothing or overstate what a
merchant has received:

  * the boarded spot is always exactly SHOT_COUNT shots — a short board means a
    short ad, and the rep already sold 30 seconds
  * a dead LLM degrades to a structural board rather than failing the order
  * every route requires a session; delivery requires an admin
  * "delivered" is never reachable without a master to deliver

Run: python -m pytest tests/api/test_ad_spot_pipeline.py -v
"""
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.api import auth as auth_mod  # noqa: E402
import src.api.routes.ad_spot as ad_spot  # noqa: E402

ORDER_ID = "aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa"
REP = {"id": "rep-1", "email": "rep@acme.test"}
ADMIN = {"id": "admin-1", "email": "aidanpierce72@gmail.com"}
AUTHED = {"Authorization": "Bearer usertoken"}

BRIEF = {
    "market": "us",
    "businessName": "The Corner Bistro",
    "businessType": "restaurant",
    "goal": "Fill tables on weeknights with the $19 steak-frites special",
    "placement": "instagram_reel",
    "audio": "voiceover_music",
    "priceCents": 100000,
}


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(ad_spot.router)
    return TestClient(app, raise_server_exceptions=False)


def _as_user(monkeypatch, user):
    async def _verify(_token):
        return user

    monkeypatch.setattr(auth_mod, "_verify_supabase_token", _verify)


# ── Boarding ─────────────────────────────────────────────────────────────────

def _req(**over):
    return ad_spot.AdSpotOrderRequest(**{**BRIEF, **over})


@pytest.mark.asyncio
async def test_board_pads_a_short_llm_answer_to_the_full_shot_count(monkeypatch):
    """Three beats back from the LLM must not become a 15-second ad."""
    async def _short(_messages, **_kw):
        return {"shots": [{"shot": i + 1, "beat": f"beat {i}", "voiceover": "line"} for i in range(3)]}

    monkeypatch.setattr("src.ai.llm_layer._call_llm", _short)
    shots = await ad_spot._board_spot(_req())

    assert len(shots) == ad_spot.SHOT_COUNT
    assert [s["shot"] for s in shots] == list(range(1, ad_spot.SHOT_COUNT + 1))
    assert all(s.get("beat") for s in shots)


@pytest.mark.asyncio
async def test_board_falls_back_when_the_llm_is_down(monkeypatch):
    """A dead LLM degrades to a structural board — the sold order still runs."""
    async def _boom(_messages, **_kw):
        raise RuntimeError("router unavailable")

    monkeypatch.setattr("src.ai.llm_layer._call_llm", _boom)
    shots = await ad_spot._board_spot(_req())

    assert len(shots) == ad_spot.SHOT_COUNT
    assert all("The Corner Bistro" in s["beat"] or s["beat"] for s in shots)


@pytest.mark.asyncio
async def test_board_drops_malformed_shots_rather_than_generating_them(monkeypatch):
    async def _junk(_messages, **_kw):
        return {"shots": [{"shot": 1, "beat": "good"}, {"shot": 2}, "not a dict", {"beat": ""}]}

    monkeypatch.setattr("src.ai.llm_layer._call_llm", _junk)
    shots = await ad_spot._board_spot(_req())

    assert len(shots) == ad_spot.SHOT_COUNT
    assert all(isinstance(s, dict) and s["beat"] for s in shots)


def test_runtime_matches_what_the_portals_sell():
    """SHOT_COUNT × SHOT_SECONDS is the 30 seconds AD_SPOT_SERVICE quotes."""
    assert ad_spot.SHOT_COUNT * ad_spot.SHOT_SECONDS == 30


def test_generation_models_are_a_bounded_allowlist():
    """A $1,000 deliverable must not route itself onto an unknown endpoint."""
    assert all(m in ad_spot.VIDEO_MODELS for m in ad_spot.ALLOWED_MODELS)
    assert ad_spot._pick_model("veo-3.1") == "veo-3.1"
    assert ad_spot._pick_model("some-model-that-does-not-exist") == ad_spot.DEFAULT_MODEL
    assert ad_spot._pick_model(None) in ad_spot.VIDEO_MODELS


def test_every_placement_carries_an_aspect_ratio():
    """Placement ids are shared with the frontend; an unmapped one would
    silently board a landscape ad in vertical."""
    assert set(ad_spot.PLACEMENT_ASPECT) == {"instagram_reel", "instagram_feed", "youtube_video"}
    from src.ai.commercial_director import PLATFORM_CONFIG
    for placement, aspect in ad_spot.PLACEMENT_ASPECT.items():
        assert placement in PLATFORM_CONFIG, f"{placement} missing from the director's config"
        assert PLATFORM_CONFIG[placement]["aspect_ratio"] == aspect


# ── Request validation ───────────────────────────────────────────────────────

@pytest.mark.parametrize("bad", [
    {"goal": "too short"},
    {"market": "uk"},
    {"placement": "billboard"},
    {"businessName": "   "},
    {"priceCents": -1},
])
def test_brief_validation_rejects_unrunnable_orders(bad):
    with pytest.raises(Exception):
        _req(**bad)


def test_currency_follows_the_market(monkeypatch, client):
    """A Canadian order must never be recorded in USD — the price the rep
    quoted was CA$1,400."""
    _as_user(monkeypatch, REP)
    captured = {}

    class _Resp:
        status_code = 201

        @staticmethod
        def json():
            return [{"id": ORDER_ID}]

    class _Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return False

        async def post(self, _url, **kw):
            captured.update(kw.get("json") or {})
            return _Resp()

    monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-key")
    monkeypatch.setattr(ad_spot.httpx, "AsyncClient", lambda **_: _Client())
    monkeypatch.setattr(ad_spot.asyncio, "create_task", lambda coro: coro.close())

    res = client.post("/api/content/ad-spot/order", headers=AUTHED,
                      json={**BRIEF, "market": "ca", "priceCents": 140000})
    assert res.status_code == 200
    assert captured["currency"] == "CAD"
    assert captured["price_cents"] == 140000
    assert captured["status"] == "boarding"


# ── Route auth ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("method,path", [
    ("post", "/api/content/ad-spot/order"),
    ("get", f"/api/content/ad-spot/{ORDER_ID}"),
    ("get", "/api/content/ad-spot"),
    ("post", f"/api/content/ad-spot/{ORDER_ID}/assemble"),
    ("post", f"/api/content/ad-spot/{ORDER_ID}/shots/1/retry"),
    ("post", f"/api/content/ad-spot/{ORDER_ID}/deliver"),
])
def test_anonymous_is_rejected(client, method, path):
    kwargs = {"json": {}} if method == "post" else {}
    assert getattr(client, method)(path, **kwargs).status_code == 401


def test_delivery_is_admin_only(client, monkeypatch):
    """Marking a merchant's ad delivered is a record that they got what they
    paid for — a rep cannot write it."""
    _as_user(monkeypatch, REP)
    assert client.post(f"/api/content/ad-spot/{ORDER_ID}/deliver", headers=AUTHED, json={}).status_code == 403


def test_bad_ids_are_rejected_before_any_query(client, monkeypatch):
    _as_user(monkeypatch, ADMIN)
    assert client.get("/api/content/ad-spot/not-a-uuid", headers=AUTHED).status_code == 400
    assert client.post("/api/content/ad-spot/not-a-uuid/assemble", headers=AUTHED).status_code == 400
    _as_user(monkeypatch, REP)
    assert client.post(
        f"/api/content/ad-spot/{ORDER_ID}/shots/99/retry", headers=AUTHED
    ).status_code == 400


def test_deliver_refuses_when_there_is_no_master(client, monkeypatch):
    """No assembled cut and no supplied URL → 409, never a delivered record
    pointing at nothing."""
    _as_user(monkeypatch, ADMIN)
    monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-key")

    async def _fetch(*_a, **_kw):
        return {"id": ORDER_ID, "master_url": None}

    monkeypatch.setattr(ad_spot, "_fetch_order", _fetch)
    res = client.post(f"/api/content/ad-spot/{ORDER_ID}/deliver", headers=AUTHED, json={})
    assert res.status_code == 409


def test_deliver_defaults_to_the_assembled_master(client, monkeypatch):
    _as_user(monkeypatch, ADMIN)
    monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-key")
    master = "https://x.supabase.co/storage/v1/object/public/ad-spots/o/master.mp4"
    patched = {}

    async def _fetch(*_a, **_kw):
        return {"id": ORDER_ID, "master_url": master}

    async def _patch(table, row_id, patch):
        patched.update(patch)

    monkeypatch.setattr(ad_spot, "_fetch_order", _fetch)
    monkeypatch.setattr(ad_spot, "_sb_patch", _patch)

    res = client.post(f"/api/content/ad-spot/{ORDER_ID}/deliver", headers=AUTHED, json={})
    assert res.status_code == 200
    assert res.json()["deliveredUrl"] == master
    assert patched["status"] == "delivered"
    assert patched["delivered_url"] == master


# ── Work order (the shared Setup Services path) ──────────────────────────────

def _patch_capture(monkeypatch):
    patched = {}

    async def _patch(_table, _row_id, patch):
        patched.update(patch)

    monkeypatch.setattr(ad_spot, "_sb_patch", _patch)
    return patched


async def test_sold_spot_is_recorded_as_a_work_order(monkeypatch):
    """Every adder follows one rule: the sale records a work order, and the
    work order reaches the dev marketplace when the payment lands. The spot
    must carry its real brief and its real runtime into that record."""
    captured = {}

    async def _record(**kw):
        captured.update(kw)
        return {"id": "wo-1"}

    monkeypatch.setattr("src.services.setup_services.record_work_order", _record)
    patched = _patch_capture(monkeypatch)

    await ad_spot._open_foundry_contest(ORDER_ID, _req(contactEmail="owner@bistro.test"))

    assert captured["service_kind"] == "ad_spot"
    assert captured["brief"]["goal"] == BRIEF["goal"]
    assert captured["brief"]["placement"] == "instagram_reel"
    assert captured["brief"]["durationSeconds"] == ad_spot.SHOT_COUNT * ad_spot.SHOT_SECONDS
    assert captured["price_cents"] == BRIEF["priceCents"]
    assert "posts to the board when payment lands" in patched["foundry_detail"]


async def test_work_order_failure_never_breaks_a_paid_order(monkeypatch):
    """The spot is already generating — a recording failure is a note on the
    order, never an exception into the close."""
    async def _boom(**_kw):
        raise RuntimeError("supabase down")

    monkeypatch.setattr("src.services.setup_services.record_work_order", _boom)
    patched = _patch_capture(monkeypatch)

    await ad_spot._open_foundry_contest(ORDER_ID, _req())

    assert "not recorded" in patched["foundry_detail"]


async def test_duplicate_work_order_is_reported_not_retried(monkeypatch):
    """record_work_order returns None when one is already live — a re-close,
    not a second purchase."""
    async def _none(**_kw):
        return None

    monkeypatch.setattr("src.services.setup_services.record_work_order", _none)
    patched = _patch_capture(monkeypatch)

    await ad_spot._open_foundry_contest(ORDER_ID, _req())

    assert "may already be live" in patched["foundry_detail"] or "already be live" in patched["foundry_detail"]


def test_assemble_refuses_before_any_shot_lands(client, monkeypatch):
    """Nothing to cut → 409 with the order left where it was, not a failed
    order and not an empty master."""
    _as_user(monkeypatch, REP)
    monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-key")

    async def _fetch_order(*_a, **_kw):
        return {"id": ORDER_ID, "aspect_ratio": "9:16", "audio": "voiceover_music", "storyboard": {}}

    async def _fetch_shots(*_a, **_kw):
        return [{"shot_number": 1, "status": "generating", "video_url": None}]

    monkeypatch.setattr(ad_spot, "_fetch_order", _fetch_order)
    monkeypatch.setattr(ad_spot, "_fetch_shots", _fetch_shots)

    res = client.post(f"/api/content/ad-spot/{ORDER_ID}/assemble", headers=AUTHED)
    assert res.status_code == 409
