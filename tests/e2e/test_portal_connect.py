"""
Deterministic in-process e2e for the Square POS-connect path (customer portal).

Drives the REAL FastAPI app through GET /api/square/authorize → GET /api/square/callback
with NO network and NO real DB, then asserts every row/flag the merchant dashboard
gates on actually got written.

Tiers monkeypatched away (the two network chokepoints + the DB singleton):
  • OAuthManager.exchange_code  → canned tokens          (no Square OAuth call)
  • SquareClient._request       → ported SQUARE_FIXTURES (no Square API calls)
  • src.db._db_instance         → FakeDB                 (no Supabase)
  • src.db.init_db              → no-op                  (lifespan can't clobber FakeDB)
  • src.workers.backfill.get_db → returns FakeDB         (backfill resolves db via get_db())

Run:  pytest tests/e2e/test_portal_connect.py -q
 or:  python -m tests.e2e.test_portal_connect
"""
import os
import sys
from urllib.parse import urlparse, parse_qs

# ── env MUST be set before importing the app / oauth module ──────────────
# TESTING=1 → oauth.py uses its deterministic test-only state secret.
os.environ.setdefault("TESTING", "1")
# Keep the FastAPI lifespan from spawning background schedulers/trainers that
# would touch the network or the real DB during startup.
os.environ.setdefault("ENABLE_SWARM_TRAINING", "0")
os.environ.setdefault("ENABLE_POS_SYNC", "0")
# Don't let the callback path try to encrypt against a real env; the encryption
# module has its own dev fallback, but make the run hermetic.
os.environ.setdefault("ENVIRONMENT", "test")

ORG = "e2e-test-org-0001"
OWNER = "owner-user-e2e-0001"
MERCHANT_ID = "MERCH_SQ_E2E"


# ─────────────────────────── FakeDB ───────────────────────────
class FakeDB:
    """In-memory stand-in for SupabaseREST.

    Implements ONLY the methods the connect + backfill paths exercise:
      select / insert / update / batch_upsert / get_pos_connection / close.
    Tables are dicts keyed by their PK ('id'); filters use PostgREST's
    "eq.<value>" convention (also tolerates a bare value).
    """

    # NOT NULL columns with no DB default — mirror the real Postgres schema so a
    # missing required column fails here the way it does in production. (Sourced
    # from the live PostgREST OpenAPI 'required' set.) This is what catches the
    # class of bug where the OAuth callback omitted organizations.vertical.
    REQUIRED_NOT_NULL: dict[str, set[str]] = {
        "organizations": {"id", "name", "slug", "vertical", "created_at", "updated_at"},
        "pos_connections": {"id", "org_id", "provider", "status", "created_at", "updated_at"},
        "notifications": {"id", "org_id", "user_id", "channel", "scheduled_for",
                          "title", "body", "status", "created_at"},
    }

    def __init__(self):
        # table -> list[dict rows]
        self.tables: dict[str, list[dict]] = {
            "organizations": [],
            "businesses": [],
            "pos_connections": [],
            "notifications": [],
            "transactions": [],
            "transaction_items": [],
            "locations": [],
            "products": [],
            "inventory_snapshots": [],
        }
        self.calls: list[tuple] = []  # audit trail to prove writes landed

    # filters use PostgREST "eq.<value>"; tolerate bare values too.
    @staticmethod
    def _match(row: dict, filters: dict | None) -> bool:
        if not filters:
            return True
        for col, raw in filters.items():
            want = raw
            if isinstance(raw, str) and raw.startswith("eq."):
                want = raw[3:]
            # compare as strings to dodge bool/str mismatches from query params
            if str(row.get(col)) != str(want):
                return False
        return True

    def _rows(self, table: str) -> list[dict]:
        return self.tables.setdefault(table, [])

    async def select(self, table, columns="*", filters=None, order=None,
                      limit=None, offset=None):
        self.calls.append(("select", table, filters))
        matched = [dict(r) for r in self._rows(table) if self._match(r, filters)]
        if offset:
            matched = matched[offset:]
        if limit:
            matched = matched[:limit]
        return matched

    async def insert(self, table, data, return_data=True):
        self.calls.append(("insert", table, data))
        rows = data if isinstance(data, list) else [data]
        stored = []
        required = self.REQUIRED_NOT_NULL.get(table, set())
        for row in rows:
            row = dict(row)
            missing = [c for c in required if row.get(c) in (None, "")]
            if missing:
                # Emulate Postgres 23502 NOT NULL violation, as PostgREST/SupabaseREST would raise.
                raise RuntimeError(
                    f"23502 null value in column(s) {missing} of table '{table}' violates not-null constraint"
                )
            self._rows(table).append(row)
            stored.append(row)
        return stored if return_data else []

    async def update(self, table, data, filters):
        self.calls.append(("update", table, {"data": data, "filters": filters}))
        updated = []
        for row in self._rows(table):
            if self._match(row, filters):
                row.update(data)
                updated.append(dict(row))
        return updated

    async def batch_upsert(self, table, rows, on_conflict="", chunk_size=500):
        self.calls.append(("batch_upsert", table, {"n": len(rows), "on_conflict": on_conflict}))
        if not rows:
            return 0
        keys = [k.strip() for k in on_conflict.split(",")] if on_conflict else []
        for incoming in rows:
            incoming = dict(incoming)
            existing = None
            if keys:
                for r in self._rows(table):
                    if all(str(r.get(k)) == str(incoming.get(k)) for k in keys):
                        existing = r
                        break
            if existing is not None:
                existing.update(incoming)
            else:
                self._rows(table).append(incoming)
        return len(rows)

    async def get_pos_connection(self, org_id):
        self.calls.append(("get_pos_connection", org_id, None))
        for r in self._rows("pos_connections"):
            if str(r.get("org_id")) == str(org_id) and r.get("status") == "connected":
                return dict(r)
        return None

    async def close(self):
        pass


# ─────────────────────────── canned token ───────────────────────────
CANNED_TOKENS = {
    "access_token": "EAAA-e2e-access-token",
    "refresh_token": "EAAA-e2e-refresh-token",
    "expires_at": "2027-01-01T00:00:00Z",
    "merchant_id": MERCHANT_ID,
    "token_type": "bearer",
}


def _build_client_and_db(monkeypatch):
    """Wire FakeDB + the two network stubs, return (TestClient, fakedb)."""
    from fastapi.testclient import TestClient

    import src.db as db_mod
    from src.tests.test_pos_ingestion import _stub_square
    import src.square.client as sq_client_mod
    import src.square.oauth as sq_oauth_mod

    fakedb = FakeDB()

    # 1) Stop init_db from clobbering our FakeDB during lifespan startup,
    #    and seat the FakeDB as the module global the route reads
    #    (oauth.callback does `from ...db import _db_instance` INSIDE the
    #    handler, so it re-reads this global on every request).
    async def _noop_init_db():
        return fakedb
    monkeypatch.setattr(db_mod, "init_db", _noop_init_db, raising=True)
    monkeypatch.setattr(db_mod, "_db_instance", fakedb, raising=False)

    # 2) backfill imports get_db at module import time → patch where it's USED.
    import src.workers.backfill as backfill_mod
    monkeypatch.setattr(backfill_mod, "get_db", lambda: fakedb, raising=True)
    # Neutralize the post-backfill AI pipeline (network/LLM); the connect
    # contract is the DB rows, not the analysis. backfill already wraps this
    # in try/except, but skip it cleanly so the test stays hermetic & fast.
    import src.live_pipeline as lp_mod

    class _NoPipeline:
        def __init__(self, *a, **k):
            pass

        async def run_analysis_only(self):
            return None
    monkeypatch.setattr(lp_mod, "MeridianPipeline", _NoPipeline, raising=True)

    # 3) Square network chokepoints.
    async def _fake_exchange_code(self, code):
        return dict(CANNED_TOKENS)
    monkeypatch.setattr(sq_oauth_mod.OAuthManager, "exchange_code",
                        _fake_exchange_code, raising=True)

    # SquareClient._request → ported fixtures. _stub_square sets it per-instance;
    # patch the class so every client built during backfill gets it.
    _probe = sq_client_mod.SquareClient(access_token="mock")
    _stub_square(_probe)
    fixture_request = _probe._request  # the path-routed async responder
    monkeypatch.setattr(sq_client_mod.SquareClient, "_request",
                        lambda self, method, path, json=None, params=None, **kw:
                        fixture_request(method, path, json=json, params=params, **kw),
                        raising=True)

    client = TestClient(db_mod and __import__("src.api.app", fromlist=["app"]).app)
    return client, fakedb


def _run_connect_flow(client, fakedb):
    """Seed, hit authorize, then callback. Returns parsed callback redirect."""
    # Seed the businesses row the dashboard gate reads.
    fakedb.tables["businesses"].append({
        "id": ORG,
        "owner_user_id": OWNER,
        "pos_connected": False,
    })

    # Step 1: authorize → 307 redirect to Square, carrying the signed state.
    r1 = client.get(
        "/api/square/authorize",
        params={"org_id": ORG, "return_to": "/canada/merchant/onboard"},
        follow_redirects=False,
    )
    assert r1.status_code == 307, f"authorize status {r1.status_code}: {r1.text[:300]}"
    loc = r1.headers["location"]
    state = parse_qs(urlparse(loc).query)["state"][0]
    # Sanity: 5-part state (org:nonce:expires:rt_b64:sig).
    assert len(state.split(":")) == 5, f"unexpected state shape: {state}"

    # Step 2: callback → exchanges code, writes rows, queues backfill.
    # TestClient runs BackgroundTasks synchronously after the response, so by
    # the time .get() returns the backfill (and its txn upserts) have run.
    r2 = client.get(
        "/api/square/callback",
        params={"code": "dummy-auth-code", "state": state},
        follow_redirects=False,
    )
    assert r2.status_code == 307, f"callback status {r2.status_code}: {r2.text[:300]}"
    cb = parse_qs(urlparse(r2.headers["location"]).query)
    return cb


def test_portal_square_connect_end_to_end(monkeypatch):
    client, fakedb = _build_client_and_db(monkeypatch)
    with client:  # enter lifespan (startup/shutdown) explicitly
        cb = _run_connect_flow(client, fakedb)

    # The callback landed on success (not denied/error/partial).
    assert cb.get("oauth") == ["success"], f"callback not success: {cb}"
    assert cb.get("merchant_id") == [MERCHANT_ID]

    # ── DB writes the dashboard depends on ───────────────────────
    orgs = fakedb.tables["organizations"]
    assert any(o["id"] == ORG for o in orgs), "organizations row not created for ORG"
    org_row = next(o for o in orgs if o["id"] == ORG)
    # only the columns the code inserts on first-create
    assert set(org_row) >= {"id", "name", "slug", "created_at", "updated_at"}

    conns = [c for c in fakedb.tables["pos_connections"] if c["org_id"] == ORG]
    assert conns, "no pos_connections row stored"
    conn = conns[0]
    assert conn["provider"] == "square"
    assert conn["status"] == "connected"
    assert conn["external_merchant_id"] == MERCHANT_ID

    biz = next(b for b in fakedb.tables["businesses"] if b["id"] == ORG)
    assert biz["pos_connected"] is True, "businesses.pos_connected not flipped True"

    assert org_row.get("pos_connection_status") == "connected", \
        "organizations.pos_connection_status != connected"
    assert org_row.get("pos_system") == "square"

    # ── transactions actually ingested via the backfill ─────────
    txns = [t for t in fakedb.tables["transactions"] if t.get("org_id") == ORG]
    # fixtures define 2 distinct orders (SQORDER1/2); the engine pages them.
    assert len(txns) >= 1, "no transactions ingested for ORG"
    for t in txns:
        assert t.get("total_cents") is not None, f"txn missing total_cents: {t}"
        assert isinstance(t["total_cents"], int)
        assert t.get("type"), f"txn missing type: {t}"
        assert t.get("transaction_at"), f"txn missing transaction_at: {t}"
    # the two canonical fixture orders are present
    ext_ids = {t.get("external_id") for t in txns}
    assert {"SQORDER1", "SQORDER2"} <= ext_ids, f"expected both fixture orders, got {ext_ids}"

    # historical_import_complete flipped by the backfill's final update
    assert conn["historical_import_complete"] is True, \
        "backfill did not mark historical_import_complete"

    # ── replicate the dashboard gate exactly ─────────────────────
    connected = bool(biz["pos_connected"]) or \
        (org_row.get("pos_connection_status") == "connected")
    assert connected is True, "dashboard connect-gate would read as NOT connected"

    # ── prove the FakeDB (not a real client) received the writes ──
    written_tables = {c[1] for c in fakedb.calls if c[0] in ("insert", "update", "batch_upsert")}
    assert {"organizations", "pos_connections", "businesses", "transactions"} <= written_tables, \
        f"FakeDB missing expected writes; saw {written_tables}"


if __name__ == "__main__":
    # Allow `python -m tests.e2e.test_portal_connect` without pytest.
    class _MP:
        """Minimal monkeypatch shim: records setattrs and restores on close."""
        def __init__(self):
            self._undo = []

        def setattr(self, target, name, value, raising=True):
            old = getattr(target, name, None)
            had = hasattr(target, name)
            self._undo.append((target, name, old, had))
            setattr(target, name, value)

        def close(self):
            for target, name, old, had in reversed(self._undo):
                if had:
                    setattr(target, name, old)
                else:
                    try:
                        delattr(target, name)
                    except AttributeError:
                        pass

    mp = _MP()
    try:
        test_portal_square_connect_end_to_end(mp)
        print("✅ PASS — portal Square connect e2e")
        sys.exit(0)
    except AssertionError as e:
        print(f"❌ FAIL — {e}")
        sys.exit(1)
    finally:
        mp.close()
