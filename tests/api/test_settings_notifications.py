"""GET/PUT /api/settings/notifications — the route the Settings page always
called but that never existed (silent 404, prefs lived only in localStorage).

Prefs persist under organizations.metadata.notification_prefs; sibling
metadata keys must survive a PUT untouched.
"""
import pytest
from fastapi import HTTPException

from src.api.routes import settings as settings_routes

OWNER = {"id": "u-owner", "email": "owner@example.com"}
ORG = "org-1"


class _FakeDB:
    def __init__(self, metadata):
        self.metadata = metadata
        self.last_update = None

    async def select(self, table, columns="*", filters=None, order=None,
                     limit=None, offset=None):
        assert table == "organizations"
        return [{"metadata": self.metadata}]

    async def update(self, table, data, filters=None):
        assert table == "organizations"
        self.last_update = data
        return [data]


def _allow(monkeypatch):
    async def _member(user, org_id):
        return None
    monkeypatch.setattr(settings_routes, "require_org_member", _member)


@pytest.mark.asyncio
async def test_get_returns_only_known_pref_keys(monkeypatch):
    _allow(monkeypatch)
    monkeypatch.setattr(settings_routes, "get_db", lambda: _FakeDB(
        {"notification_prefs": {"deal_stage": False, "org_id": "evil", "extra": 1},
         "stripe_thing": "keep"}))
    out = await settings_routes.get_notification_prefs(ORG, user=OWNER)
    assert out == {"deal_stage": False}


@pytest.mark.asyncio
async def test_get_empty_when_never_saved(monkeypatch):
    _allow(monkeypatch)
    monkeypatch.setattr(settings_routes, "get_db", lambda: _FakeDB({}))
    assert await settings_routes.get_notification_prefs(ORG, user=OWNER) == {}


@pytest.mark.asyncio
async def test_put_merges_and_preserves_sibling_metadata(monkeypatch):
    _allow(monkeypatch)
    db = _FakeDB({"stripe_thing": "keep", "notification_prefs": {"low_stock": False}})
    monkeypatch.setattr(settings_routes, "get_db", lambda: db)
    req = settings_routes.NotificationPrefs(org_id=ORG, deal_stage=False)
    out = await settings_routes.put_notification_prefs(req, user=OWNER)
    assert out == {"low_stock": False, "deal_stage": False}
    assert db.last_update["metadata"]["stripe_thing"] == "keep"
    assert db.last_update["metadata"]["notification_prefs"] == out


@pytest.mark.asyncio
async def test_non_member_denied(monkeypatch):
    async def _deny(user, org_id):
        raise HTTPException(403, "Access denied")
    monkeypatch.setattr(settings_routes, "require_org_member", _deny)
    monkeypatch.setattr(settings_routes, "get_db", lambda: _FakeDB({}))
    with pytest.raises(HTTPException) as exc:
        await settings_routes.get_notification_prefs(ORG, user=OWNER)
    assert exc.value.status_code == 403
