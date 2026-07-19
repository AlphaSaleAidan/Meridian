"""_is_active_sales_rep must match sales_reps.email case-INSENSITIVELY.

Regression: prod had an active rep stored as `Saar@buddypaysolutions.com`
while the JWT claim (Supabase-lowercased) is `saar@...`. The old eq.<lower>
filter missed the row and fail-closed the rep out of billing routes.
"""
import pytest

from src.api.routes import billing


class _FakeDB:
    def __init__(self, rows):
        self._rows = rows
        self.last_filters = None

    async def select(self, table, columns="*", filters=None, order=None,
                     limit=None, offset=None):
        assert table == "sales_reps"
        self.last_filters = filters
        # Mirror PostgREST ilike.<x>: case-insensitive match on the stored email.
        want = (filters or {}).get("email", "")
        if want.startswith("ilike."):
            needle = want.removeprefix("ilike.").lower()
            return [r for r in self._rows if (r.get("email") or "").lower() == needle][:limit]
        needle = want.removeprefix("eq.")
        return [r for r in self._rows if r.get("email") == needle][:limit]


@pytest.mark.asyncio
async def test_active_rep_matches_mixed_case_email(monkeypatch):
    db = _FakeDB([{"id": "r1", "email": "Saar@buddypaysolutions.com", "is_active": True}])
    monkeypatch.setattr(billing, "get_db", lambda: db)
    # JWT claim arrives lowercased.
    assert await billing._is_active_sales_rep({"email": "saar@buddypaysolutions.com"}) is True
    # And it queried case-insensitively (ilike), not eq.<lower>.
    assert db.last_filters["email"].startswith("ilike.")


@pytest.mark.asyncio
async def test_non_rep_still_false(monkeypatch):
    db = _FakeDB([{"id": "r1", "email": "saar@buddypaysolutions.com", "is_active": True}])
    monkeypatch.setattr(billing, "get_db", lambda: db)
    assert await billing._is_active_sales_rep({"email": "stranger@nowhere.com"}) is False


@pytest.mark.asyncio
async def test_no_email_false(monkeypatch):
    monkeypatch.setattr(billing, "get_db", lambda: _FakeDB([]))
    assert await billing._is_active_sales_rep({"email": ""}) is False
