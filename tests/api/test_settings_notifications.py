"""GET/PUT /api/settings/notifications — the route the Settings page always
called but that never existed (silent 404, prefs lived only in localStorage).

Prefs persist in the notification_prefs table (migration 024), keyed by org id
with no parent-table FK — Canada merchants live in `businesses`, US-era orgs in
`organizations` (entity split), so binding to either table misses the other
(the first cut of this route did exactly that and 404'd for Canada merchants).
"""
import pytest
from fastapi import HTTPException

from src.api.routes import settings as settings_routes

OWNER = {"id": "u-owner", "email": "owner@example.com"}
ORG = "org-1"


class _FakeDB:
    def __init__(self, prefs_row=None):
        self.prefs_row = prefs_row  # None = no row yet (never saved)
        self.last_upsert = None

    async def select(self, table, columns="*", filters=None, order=None,
                     limit=None, offset=None):
        assert table == "notification_prefs"
        return [{"prefs": self.prefs_row}] if self.prefs_row is not None else []

    async def upsert(self, table, data, on_conflict="", **kw):
        assert table == "notification_prefs"
        assert on_conflict == "org_id"
        self.last_upsert = data
        return [data]


def _allow(monkeypatch):
    async def _member(user, org_id):
        return None
    monkeypatch.setattr(settings_routes, "require_org_member", _member)


@pytest.mark.asyncio
async def test_get_returns_only_known_pref_keys(monkeypatch):
    _allow(monkeypatch)
    monkeypatch.setattr(settings_routes, "get_db", lambda: _FakeDB(
        {"deal_stage": False, "org_id": "evil", "extra": 1}))
    out = await settings_routes.get_notification_prefs(ORG, user=OWNER)
    assert out == {"deal_stage": False}


@pytest.mark.asyncio
async def test_get_empty_when_never_saved(monkeypatch):
    _allow(monkeypatch)
    monkeypatch.setattr(settings_routes, "get_db", lambda: _FakeDB(None))
    assert await settings_routes.get_notification_prefs(ORG, user=OWNER) == {}


@pytest.mark.asyncio
async def test_put_merges_partial_update_over_saved(monkeypatch):
    _allow(monkeypatch)
    db = _FakeDB({"low_stock": False})
    monkeypatch.setattr(settings_routes, "get_db", lambda: db)
    req = settings_routes.NotificationPrefs(org_id=ORG, deal_stage=False)
    out = await settings_routes.put_notification_prefs(req, user=OWNER)
    assert out == {"low_stock": False, "deal_stage": False}
    assert db.last_upsert == {"org_id": ORG, "prefs": out}


@pytest.mark.asyncio
async def test_put_first_save_creates_row(monkeypatch):
    _allow(monkeypatch)
    db = _FakeDB(None)
    monkeypatch.setattr(settings_routes, "get_db", lambda: db)
    req = settings_routes.NotificationPrefs(org_id=ORG, ai_anomaly=True)
    out = await settings_routes.put_notification_prefs(req, user=OWNER)
    assert out == {"ai_anomaly": True}
    assert db.last_upsert["org_id"] == ORG


@pytest.mark.asyncio
async def test_non_member_denied(monkeypatch):
    async def _deny(user, org_id):
        raise HTTPException(403, "Access denied")
    monkeypatch.setattr(settings_routes, "require_org_member", _deny)
    monkeypatch.setattr(settings_routes, "get_db", lambda: _FakeDB(None))
    with pytest.raises(HTTPException) as exc:
        await settings_routes.get_notification_prefs(ORG, user=OWNER)
    assert exc.value.status_code == 403
