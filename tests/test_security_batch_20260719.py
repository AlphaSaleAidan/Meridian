"""Security batch 2026-07-19 — red tests first, one section per confirmed hole.

  1. SPACES BOLA        — /api/spaces/{id}/status, /{id}/zones, /{id}/model were
                          keyed only by space_id (zones returned 200 UNAUTHENTICATED
                          in the live probe). Now: require_service_auth + the
                          caller's org must match the space row's org_id.
  2. COMPLIANCE AUTH    — POST /api/compliance/accept had no auth and trusted
                          payload user_id. Now: require_jwt; user_id from session.
  3. SPAM RATE LIMITS   — /api/careers/apply, /api/canada/careers/apply,
                          /api/quote-request get per-IP hourly limits + a 24h
                          email dedup (200, but no duplicate row / email).
  4. SERVICE-KEY LEAK   — garry_tools / llm_client error text masks key material;
                          garry run_query PostgREST filter is allowlist-sanitized.
  5. LLM COST CAP       — rebuild-all honors MERIDIAN_REBUILD_MAX_CALLS (default
                          200); endpoint returns 429 + partial result when hit.
  6. SERVICE-AUTH BOLA  — billing create-invoice / update-payment-method /
                          notify-payment-failed and onboarding checklist /
                          send-welcome now verify org scope (member, active
                          sales rep, or machine principal).

Pattern mirrors tests/api/test_tenant_isolation_bola.py: monkeypatch the
`_verify_supabase_token` / `_check_org_membership` seams, fake DB, direct
route calls or a minimal TestClient app per router.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.pop("TENANCY_ENFORCEMENT_DISABLED", None)

import src.db as db_mod  # noqa: E402
from src.api import auth  # noqa: E402

ORG = "168b6df2-e9af-4b00-8fec-51e51149ff19"
OTHER_ORG = "0d6a1b2c-3e4f-4a5b-8c7d-9e0f1a2b3c4d"
SPACE_ID = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
USER_ID = "11111111-2222-4333-8444-555555555555"

MEMBER = {"id": USER_ID, "email": "owner@acme.test"}
OUTSIDER = {"id": "99999999-8888-4777-8666-555555555555", "email": "intruder@evil.test"}


def _set_token_user(monkeypatch, user):
    async def _verify(_token):
        return user
    monkeypatch.setattr(auth, "_verify_supabase_token", _verify)


def _set_member(monkeypatch, is_member: bool):
    async def _check(_user, _org):
        return is_member
    monkeypatch.setattr(auth, "_check_org_membership", _check)


class FakeDB:
    """Canned rows + write recording."""

    def __init__(self, rows_by_table=None):
        self.rows_by_table = rows_by_table or {}
        self.inserts: list = []
        self.updates: list = []
        self.selects: list = []

    async def select(self, table, columns="*", filters=None, limit=None,
                     order=None, offset=None):
        self.selects.append((table, filters))
        return self.rows_by_table.get(table, [])

    async def insert(self, table, row):
        self.inserts.append((table, row))
        return [row]

    async def update(self, table, vals, filters=None):
        self.updates.append((table, vals, filters))
        return []

    async def delete(self, table, filters=None):
        return []


# ═══════════════════ 1. SPACES BOLA ═══════════════════

from src.api.routes import spaces as spaces_mod  # noqa: E402


def _spaces_client():
    app = FastAPI()
    app.include_router(spaces_mod.router)
    return TestClient(app, raise_server_exceptions=False)


def _space_db(org=ORG):
    return FakeDB({"spaces": [{"id": SPACE_ID, "org_id": org, "status": "processing"}]})


def test_spaces_zones_unauthenticated_rejected(monkeypatch):
    """Live probe: POST /api/spaces/{id}/zones returned 200 with NO auth."""
    monkeypatch.setattr(db_mod, "_db_instance", None)
    c = _spaces_client()
    r = c.post(f"/api/spaces/{SPACE_ID}/zones", json={"zones": [
        {"zone_id": "z1", "label": "Counter", "position": [0, 0, 0], "radius": 1.0}]})
    assert r.status_code in (401, 403), r.text


def test_spaces_status_unauthenticated_rejected(monkeypatch):
    monkeypatch.setattr(db_mod, "_db_instance", None)
    c = _spaces_client()
    r = c.patch(f"/api/spaces/{SPACE_ID}/status", params={"status": "ready"})
    assert r.status_code in (401, 403), r.text


def test_spaces_model_unauthenticated_rejected(monkeypatch):
    monkeypatch.setattr(db_mod, "_db_instance", None)
    c = _spaces_client()
    r = c.get(f"/api/spaces/{SPACE_ID}/model")
    assert r.status_code in (401, 403), r.text


def test_spaces_status_cross_tenant_403(monkeypatch):
    """A valid session user who is NOT a member of the space's org is denied."""
    db = _space_db(org=ORG)
    monkeypatch.setattr(db_mod, "_db_instance", db)
    _set_token_user(monkeypatch, OUTSIDER)
    _set_member(monkeypatch, False)
    monkeypatch.setattr(auth, "ADMIN_EMAILS", [], raising=False)
    c = _spaces_client()
    r = c.patch(f"/api/spaces/{SPACE_ID}/status", params={"status": "failed"},
                headers={"Authorization": "Bearer usertoken"})
    assert r.status_code == 403, r.text
    assert db.updates == []          # nothing mutated cross-tenant


def test_spaces_zones_cross_tenant_403(monkeypatch):
    db = _space_db(org=ORG)
    monkeypatch.setattr(db_mod, "_db_instance", db)
    _set_token_user(monkeypatch, OUTSIDER)
    _set_member(monkeypatch, False)
    monkeypatch.setattr(auth, "ADMIN_EMAILS", [], raising=False)
    c = _spaces_client()
    r = c.post(f"/api/spaces/{SPACE_ID}/zones",
               json={"zones": [{"zone_id": "z1", "label": "x",
                                "position": [0, 0, 0], "radius": 1.0}]},
               headers={"Authorization": "Bearer usertoken"})
    assert r.status_code == 403, r.text
    assert db.inserts == []


def test_spaces_status_member_passes(monkeypatch):
    db = _space_db(org=ORG)
    monkeypatch.setattr(db_mod, "_db_instance", db)
    _set_token_user(monkeypatch, MEMBER)
    _set_member(monkeypatch, True)
    c = _spaces_client()
    r = c.patch(f"/api/spaces/{SPACE_ID}/status", params={"status": "ready"},
                headers={"Authorization": "Bearer usertoken"})
    assert r.status_code == 200, r.text
    assert db.updates, "member update should be applied"


def test_spaces_status_admin_key_passes(monkeypatch):
    db = _space_db(org=ORG)
    monkeypatch.setattr(db_mod, "_db_instance", db)
    monkeypatch.setenv("MERIDIAN_ADMIN_KEY", "topsecret-test")
    c = _spaces_client()
    r = c.patch(f"/api/spaces/{SPACE_ID}/status", params={"status": "ready"},
                headers={"X-Admin-Key": "topsecret-test"})
    assert r.status_code == 200, r.text


def test_spaces_upload_body_org_guard_unchanged():
    """/upload + /upload-splat keep the VERIFIED body-org require_org_access path."""
    deps = [d.dependency for d in spaces_mod.router.dependencies]
    assert auth.require_org_access in deps


# ═══════════════════ 2. COMPLIANCE ACCEPT AUTH ═══════════════════

from src.api.routes import compliance as compliance_mod  # noqa: E402


def _compliance_client():
    app = FastAPI()
    app.include_router(compliance_mod.router)
    return TestClient(app, raise_server_exceptions=False)


def _accept_payload(user_id):
    return {"user_id": user_id, "user_type": "customer",
            "document_type": "tos", "document_version": "1.0"}


def test_compliance_accept_unauthenticated_rejected(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "http://supabase.test")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "dummy-service-key-not-real")
    c = _compliance_client()
    r = c.post("/api/compliance/accept", json=_accept_payload(USER_ID))
    assert r.status_code in (401, 403), r.text


def test_compliance_accept_user_id_comes_from_session(monkeypatch):
    """Payload names ANOTHER user — the recorded acceptance must use the session user."""
    monkeypatch.setenv("SUPABASE_URL", "http://supabase.test")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "dummy-service-key-not-real")
    _set_token_user(monkeypatch, MEMBER)

    captured = {}

    class _FakeResp:
        status_code = 201
        text = ""
        def json(self):
            return [{}]

    class _FakeClient:
        def __init__(self, *a, **k): ...
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            return False
        async def post(self, url, headers=None, json=None):
            captured["payload"] = json
            return _FakeResp()

    monkeypatch.setattr(compliance_mod.httpx, "AsyncClient", _FakeClient)
    c = _compliance_client()
    r = c.post("/api/compliance/accept",
               json=_accept_payload(OUTSIDER["id"]),   # forged victim id
               headers={"Authorization": "Bearer usertoken"})
    assert r.status_code == 200, r.text
    assert captured["payload"]["user_id"] == USER_ID   # session wins, not payload


# ═══════════════════ 3. SPAM RATE LIMITS + DEDUP ═══════════════════

from src.api.middleware.rate_limiter import _get_limit  # noqa: E402
from src.api.routes import careers as careers_mod  # noqa: E402
from src.api.routes import quote as quote_mod  # noqa: E402


def test_rate_limits_cover_spam_routes():
    for path, cap in (("/api/careers/apply", 5),
                      ("/api/canada/careers/apply", 5),
                      ("/api/quote-request", 10)):
        max_req, window = _get_limit(path)
        assert max_req <= cap, f"{path} has no tight limit ({max_req}/{window}s)"
        assert window >= 3600, f"{path} window should be hourly"


def _career_app(email="dup@test.com"):
    return careers_mod.CareerApplication(
        name="Dup Tester", email=email, position="sales_rep", city="Halifax")


@pytest.mark.asyncio
async def test_careers_dedup_same_email_24h(monkeypatch):
    """Second application with the same email+position within 24h → 200, no new row."""
    db = FakeDB({"career_applications": [
        {"id": "existing-1", "email": "dup@test.com", "position": "sales_rep",
         "created_at": "2999-01-01T00:00:00+00:00"}]})
    monkeypatch.setattr(careers_mod, "get_db", lambda: db)

    sent = []
    import src.email.send as email_send

    async def _no_email(*a, **k):
        sent.append(1)
    monkeypatch.setattr(email_send, "send_career_application", _no_email)

    result = await careers_mod.submit_application(_career_app(), country="US")
    assert result["status"] == "received"          # bot sees success
    assert db.inserts == []                        # but no duplicate row
    assert sent == []                              # and no duplicate email


@pytest.mark.asyncio
async def test_careers_fresh_application_still_inserts(monkeypatch):
    db = FakeDB({"career_applications": []})
    monkeypatch.setattr(careers_mod, "get_db", lambda: db)
    import src.email.send as email_send

    async def _no_email(*a, **k): ...
    monkeypatch.setattr(email_send, "send_career_application", _no_email)

    result = await careers_mod.submit_application(_career_app("new@test.com"), country="CA")
    assert result["status"] == "received"
    assert len(db.inserts) == 1


@pytest.mark.asyncio
async def test_quote_dedup_same_email_24h(monkeypatch):
    db = FakeDB({"quote_requests": [
        {"id": "q-1", "email": "dup@test.com",
         "created_at": "2999-01-01T00:00:00+00:00"}]})
    monkeypatch.setattr(quote_mod, "get_db", lambda: db)
    sent = []

    async def _no_email(*a, **k):
        sent.append(1)
    monkeypatch.setattr(quote_mod, "send_quote_request", _no_email)

    req = quote_mod.QuoteRequest(full_name="D T", business_name="Dup Cafe",
                                 email="dup@test.com", phone="+17823585534")
    result = await quote_mod.create_quote_request(req)
    assert result == {"ok": True}
    assert db.inserts == []
    assert sent == []


@pytest.mark.asyncio
async def test_quote_fresh_request_still_inserts(monkeypatch):
    db = FakeDB({"quote_requests": []})
    monkeypatch.setattr(quote_mod, "get_db", lambda: db)

    async def _no_email(*a, **k): ...
    monkeypatch.setattr(quote_mod, "send_quote_request", _no_email)

    req = quote_mod.QuoteRequest(full_name="N T", business_name="New Cafe",
                                 email="new@test.com", phone="+17823585534")
    result = await quote_mod.create_quote_request(req)
    assert result == {"ok": True}
    assert len(db.inserts) == 1


# ═══════════════════ 4. SERVICE-KEY MASKING + FILTER SANITIZER ═══════════════════

FAKE_KEY = "sbtest-supersecret-service-key-1234abcd"


def test_mask_secrets_hides_key_material(monkeypatch):
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", FAKE_KEY)
    from src.security.secret_mask import mask_secrets
    out = mask_secrets(f"401 unauthorized apikey={FAKE_KEY} for host x")
    assert FAKE_KEY not in out
    assert "abcd" in out            # last 4 chars max survive
    # non-secret text untouched
    assert mask_secrets("plain message") == "plain message"


@pytest.mark.asyncio
async def test_garry_error_text_is_masked(monkeypatch):
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", FAKE_KEY)
    from src.ai import garry_tools

    def _boom(_args):
        raise RuntimeError(f"Invalid API key: {FAKE_KEY}")
    monkeypatch.setattr(garry_tools, "_tool_read_file", _boom)
    out = await garry_tools.execute_tool("read_file", {"path": "src/x.py"})
    assert FAKE_KEY not in out
    assert "error" in json.loads(out)


def test_garry_filter_sanitizer_allowlist():
    from src.ai.garry_tools import _sanitize_filters
    # simple column filters pass
    assert _sanitize_filters("is_active=eq.true&region=eq.canada") is True
    assert _sanitize_filters("amount=gte.100") is True
    assert _sanitize_filters("name=ilike.*taco*") is True
    assert _sanitize_filters("id=in.(1,2,3)") is True
    assert _sanitize_filters("") is True
    # injection shapes rejected
    assert _sanitize_filters("select=*,secrets(*)") is False           # select override
    assert _sanitize_filters("id=eq.1&select=service_role_key") is False
    assert _sanitize_filters("rpc/exec_sql?x=1") is False              # rpc
    assert _sanitize_filters("orders(id)=eq.1") is False               # embedded resource
    assert _sanitize_filters("user.email=eq.x") is False               # non-word column
    assert _sanitize_filters("or=(id.eq.1,id.eq.2)") is False          # boolean tree
    assert _sanitize_filters("id=eq.1&limit=1000") is False            # unknown op


@pytest.mark.asyncio
async def test_garry_run_query_rejects_injected_filters(monkeypatch):
    from src.ai import garry_tools
    monkeypatch.setenv("SUPABASE_URL", "http://supabase.test")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", FAKE_KEY)

    import httpx as _httpx

    class _NeverClient:
        def __init__(self, *a, **k):
            raise AssertionError("HTTP request must NOT be made for rejected filters")
    monkeypatch.setattr(_httpx, "AsyncClient", _NeverClient)

    out = json.loads(await garry_tools._tool_run_query(
        {"table": "businesses", "filters": "id=eq.1&select=*,pos_connections(*)"}))
    assert "error" in out

    out2 = json.loads(await garry_tools._tool_run_query(
        {"table": "businesses", "select": "id,secrets(*)"}))
    assert "error" in out2


@pytest.mark.asyncio
async def test_llm_client_error_masks_key(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", FAKE_KEY)
    from src.services import llm_client as lc

    class _Resp:
        status_code = 401
        text = f"Authentication failed for key {FAKE_KEY}"

    class _FakeClient:
        def __init__(self, *a, **k): ...
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            return False
        async def post(self, *a, **k):
            return _Resp()
    monkeypatch.setattr(lc.httpx, "AsyncClient", _FakeClient)

    with pytest.raises(RuntimeError) as e:
        await lc.LLMClient._call_provider(
            lc.PROVIDERS["deepseek"], [{"role": "user", "content": "hi"}], None, 10)
    assert FAKE_KEY not in str(e.value)


# ═══════════════════ 5. LLM COST CAP ═══════════════════


def test_local_llm_budget_caps_calls(monkeypatch):
    from src.inference import local_llm

    class _FakeLlama:
        def create_chat_completion(self, **k):
            return {"choices": [{"message": {"content": "ok"}}]}
    monkeypatch.setattr(local_llm, "get_llm", lambda *a, **k: _FakeLlama())

    local_llm.set_llm_call_budget(2)
    try:
        assert local_llm.generate("a") == "ok"
        assert local_llm.generate("b") == "ok"
        with pytest.raises(local_llm.LLMBudgetExceeded):
            local_llm.generate("c")
        assert local_llm.llm_calls_used() == 2
        assert local_llm.llm_budget_exceeded() is True
    finally:
        local_llm.clear_llm_call_budget()


def test_rebuild_all_sets_budget_from_env(monkeypatch):
    from src.inference import context_engine, local_llm
    import src.inference.file_digest as fd
    import src.inference.diff_summarizer as ds
    import src.inference.session_compressor as sc

    monkeypatch.setenv("MERIDIAN_REBUILD_MAX_CALLS", "7")
    seen = {}

    def _fake_rebuild_context(use_llm=True):
        seen["remaining"] = local_llm._budget["remaining"]
        return {"status": "complete"}
    monkeypatch.setattr(context_engine, "rebuild_context", _fake_rebuild_context)
    monkeypatch.setattr(fd, "rebuild_file_digest", lambda use_llm=True: {})
    monkeypatch.setattr(ds, "rebuild_diff_summaries", lambda count=10, use_llm=True: {})
    monkeypatch.setattr(sc, "rebuild_session_learnings", lambda max_sessions=3, use_llm=True: {})
    monkeypatch.setattr(context_engine, "_update_memory_index", lambda: None)

    results = context_engine.rebuild_all(use_llm=True)
    assert seen["remaining"] == 7                       # env cap applied
    assert "llm_calls_used" in results
    assert results["llm_budget_exceeded"] is False
    assert local_llm._budget["remaining"] is None       # budget cleared after run


def test_rebuild_all_endpoint_429_when_budget_exceeded(monkeypatch):
    from src.api.routes import inference as inference_mod
    import src.inference.context_engine as ce

    monkeypatch.setenv("MERIDIAN_ADMIN_KEY", "topsecret-test")
    monkeypatch.setattr(
        ce, "rebuild_all",
        lambda use_llm=True: {"llm_budget_exceeded": True, "llm_calls_used": 200,
                              "context": {"status": "complete"}})
    app = FastAPI()
    app.include_router(inference_mod.router)
    c = TestClient(app, raise_server_exceptions=False)
    r = c.post("/api/inference/rebuild-all", headers={"X-Admin-Key": "topsecret-test"})
    assert r.status_code == 429, r.text
    assert r.json()["llm_calls_used"] == 200            # partial result returned


# ═══════════════════ 6. SERVICE-AUTH ORG SCOPE (billing + onboarding) ═══════════════════

from src.api.routes import billing as billing_mod  # noqa: E402
from src.api.routes import onboarding as onboarding_mod  # noqa: E402


def _billing_client():
    app = FastAPI()
    app.include_router(billing_mod.router)
    return TestClient(app, raise_server_exceptions=False)


def _no_rep(monkeypatch):
    async def _rep(_user):
        return False
    monkeypatch.setattr(billing_mod, "_is_active_sales_rep", _rep)


def _yes_rep(monkeypatch):
    async def _rep(_user):
        return True
    monkeypatch.setattr(billing_mod, "_is_active_sales_rep", _rep)


def _invoice_body(org=OTHER_ORG):
    return {"org_id": org, "amount_cents": 5000, "customer_email": "v@x.test"}


def test_billing_create_invoice_cross_tenant_403(monkeypatch):
    _set_token_user(monkeypatch, OUTSIDER)
    _set_member(monkeypatch, False)
    monkeypatch.setattr(auth, "ADMIN_EMAILS", [], raising=False)
    _no_rep(monkeypatch)
    c = _billing_client()
    r = c.post("/api/billing/create-invoice", json=_invoice_body(),
               headers={"Authorization": "Bearer usertoken"})
    assert r.status_code == 403, r.text


def test_billing_update_payment_method_cross_tenant_403(monkeypatch):
    _set_token_user(monkeypatch, OUTSIDER)
    _set_member(monkeypatch, False)
    monkeypatch.setattr(auth, "ADMIN_EMAILS", [], raising=False)
    _no_rep(monkeypatch)
    c = _billing_client()
    r = c.post("/api/billing/update-payment-method",
               json={"org_id": OTHER_ORG, "customer_email": "v@x.test",
                     "customer_name": "V", "business_name": "Victim Cafe"},
               headers={"Authorization": "Bearer usertoken"})
    assert r.status_code == 403, r.text


def test_billing_notify_payment_failed_cross_tenant_403(monkeypatch):
    _set_token_user(monkeypatch, OUTSIDER)
    _set_member(monkeypatch, False)
    monkeypatch.setattr(auth, "ADMIN_EMAILS", [], raising=False)
    _no_rep(monkeypatch)
    c = _billing_client()
    r = c.post("/api/billing/notify-payment-failed",
               json={"org_id": OTHER_ORG, "customer_email": "v@x.test",
                     "contact_name": "V", "business_name": "Victim Cafe"},
               headers={"Authorization": "Bearer usertoken"})
    assert r.status_code == 403, r.text


def test_billing_create_invoice_active_rep_passes(monkeypatch):
    """Rep portals drive these routes — an ACTIVE sales rep must keep working."""
    _set_token_user(monkeypatch, {"id": "rep-1", "email": "rep@meridian.tips"})
    _set_member(monkeypatch, False)
    monkeypatch.setattr(auth, "ADMIN_EMAILS", [], raising=False)
    _yes_rep(monkeypatch)

    import src.billing.billing_service as bs

    class _StubService:
        def __init__(self, _db): ...
        async def create_invoice(self, **k):
            return SimpleNamespace(success=True, invoice_id="inv-1",
                                   invoice_url="http://sq.test/inv-1")
    monkeypatch.setattr(bs, "BillingService", _StubService)
    monkeypatch.setattr(billing_mod, "get_db", lambda: FakeDB())
    c = _billing_client()
    r = c.post("/api/billing/create-invoice", json=_invoice_body(),
               headers={"Authorization": "Bearer usertoken"})
    assert r.status_code == 200, r.text
    assert r.json()["invoice_id"] == "inv-1"


def test_billing_create_invoice_admin_key_passes(monkeypatch):
    monkeypatch.setenv("MERIDIAN_ADMIN_KEY", "topsecret-test")

    import src.billing.billing_service as bs

    class _StubService:
        def __init__(self, _db): ...
        async def create_invoice(self, **k):
            return SimpleNamespace(success=True, invoice_id="inv-2",
                                   invoice_url="u")
    monkeypatch.setattr(bs, "BillingService", _StubService)
    monkeypatch.setattr(billing_mod, "get_db", lambda: FakeDB())
    c = _billing_client()
    r = c.post("/api/billing/create-invoice", json=_invoice_body(),
               headers={"X-Admin-Key": "topsecret-test"})
    assert r.status_code == 200, r.text


def _onboarding_client():
    app = FastAPI()
    app.include_router(onboarding_mod.router)
    return TestClient(app, raise_server_exceptions=False)


def test_onboarding_checklist_unauthenticated_rejected(monkeypatch):
    monkeypatch.setattr(onboarding_mod, "get_db", lambda: FakeDB())
    c = _onboarding_client()
    r = c.get("/api/onboarding/checklist", params={"org_id": ORG})
    assert r.status_code in (401, 403), r.text


def test_onboarding_checklist_member_passes(monkeypatch):
    db = FakeDB({"organizations": [{"id": ORG}], "pos_connections": [],
                 "notifications": []})
    monkeypatch.setattr(onboarding_mod, "get_db", lambda: db)
    _set_token_user(monkeypatch, MEMBER)
    _set_member(monkeypatch, True)
    c = _onboarding_client()
    r = c.get("/api/onboarding/checklist", params={"org_id": ORG},
              headers={"Authorization": "Bearer usertoken"})
    assert r.status_code == 200, r.text
    assert r.json()["org_id"] == ORG


def test_onboarding_send_welcome_unauthenticated_rejected(monkeypatch):
    monkeypatch.setattr(onboarding_mod, "get_db", lambda: FakeDB())
    c = _onboarding_client()
    r = c.post("/api/onboarding/send-welcome",
               json={"org_id": ORG, "email": "victim@x.test"})
    assert r.status_code in (401, 403), r.text


@pytest.mark.asyncio
async def test_onboarding_internal_welcome_path_still_works(monkeypatch):
    """handle_subscription_payment's direct call must not require a principal."""
    db = FakeDB({"organizations": [{"id": ORG, "name": "Acme Cafe"}]})
    monkeypatch.setattr(onboarding_mod, "get_db", lambda: db)

    import src.email.send as email_send

    async def _fake_welcome(**k):
        return {"status": "sent"}
    monkeypatch.setattr(email_send, "send_welcome_email", _fake_welcome)

    result = await onboarding_mod._send_welcome_impl(
        onboarding_mod.SendWelcomeRequest(org_id=ORG, email="new@example.com"))
    assert result["status"] == "sent"
    assert any(t == "notifications" for t, _ in db.inserts)


# ═══════════════════ 7. AUDIT IOUs: pos_connections + predictive body-org ═══════════════════
# pos_connections.py and predictive.py carried "P1 follow-up" comments saying
# body-org endpoints "must enforce internally". Since the CA-1/CA-2 fix,
# require_org_access resolves org_id from the request BODY too (auth.py
# _org_id_from_body) and both routers mount it router-wide — these tests pin
# that the flagged endpoints are actually covered, not open.


def test_pos_test_connection_body_org_requires_auth():
    from src.api.routes import pos_connections as pos_mod
    app = FastAPI()
    app.include_router(pos_mod.router)
    c = TestClient(app, raise_server_exceptions=False)
    r = c.post("/api/pos/test-connection",
               json={"org_id": ORG, "pos_system": "toast", "credentials": {"api_key": "x"}})
    assert r.status_code == 401, r.text


def test_pos_test_connection_cross_tenant_403(monkeypatch):
    from src.api.routes import pos_connections as pos_mod
    _set_token_user(monkeypatch, OUTSIDER)
    _set_member(monkeypatch, False)
    monkeypatch.setattr(auth, "ADMIN_EMAILS", [], raising=False)
    app = FastAPI()
    app.include_router(pos_mod.router)
    c = TestClient(app, raise_server_exceptions=False)
    r = c.post("/api/pos/test-connection",
               json={"org_id": ORG, "pos_system": "toast", "credentials": {"api_key": "x"}},
               headers={"Authorization": "Bearer usertoken"})
    assert r.status_code == 403, r.text


def test_predictive_scenario_body_org_requires_auth():
    from src.api.routes import predictive as pred_mod
    app = FastAPI()
    app.include_router(pred_mod.router)
    c = TestClient(app, raise_server_exceptions=False)
    r = c.post("/api/predictive/scenario",
               json={"org_id": ORG, "scenario_type": "price_change", "params": {}})
    assert r.status_code == 401, r.text


def test_predictive_scenario_cross_tenant_403(monkeypatch):
    from src.api.routes import predictive as pred_mod
    _set_token_user(monkeypatch, OUTSIDER)
    _set_member(monkeypatch, False)
    monkeypatch.setattr(auth, "ADMIN_EMAILS", [], raising=False)
    app = FastAPI()
    app.include_router(pred_mod.router)
    c = TestClient(app, raise_server_exceptions=False)
    r = c.post("/api/predictive/scenario",
               json={"org_id": ORG, "scenario_type": "price_change", "params": {}},
               headers={"Authorization": "Bearer usertoken"})
    assert r.status_code == 403, r.text
