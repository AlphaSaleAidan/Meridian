"""
Subscription wind-down MVP (flag-gated): a cancelled merchant past their paid
period loses member access. Default OFF; admins + flag-off exempt; fail-open.
"""
import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("ENCRYPTION_KEY", "0" * 64)

from src.api import auth  # noqa: E402

aio = pytest.mark.asyncio
USER = {"email": "merchant@x.com"}


class _DB:
    def __init__(self, access_until):
        self._access_until = access_until

    async def select(self, *a, **k):
        if self._access_until is _NONE:
            return []
        return [{"access_until": self._access_until}]


_NONE = object()


def _patch_db(monkeypatch, access_until):
    import src.db as dbmod
    monkeypatch.setattr(dbmod, "get_db", lambda: _DB(access_until), raising=False)


@aio
async def test_flag_off_is_never_wound_down(monkeypatch):
    monkeypatch.delenv("SUBSCRIPTION_WINDDOWN_ENFORCED", raising=False)
    _patch_db(monkeypatch, (datetime.now(timezone.utc) - timedelta(days=1)).isoformat())
    assert await auth._subscription_wound_down(USER, "biz_x") is False


@aio
async def test_no_cancellation_row(monkeypatch):
    monkeypatch.setenv("SUBSCRIPTION_WINDDOWN_ENFORCED", "1")
    _patch_db(monkeypatch, _NONE)
    assert await auth._subscription_wound_down(USER, "biz_x") is False


@aio
async def test_still_in_paid_period(monkeypatch):
    monkeypatch.setenv("SUBSCRIPTION_WINDDOWN_ENFORCED", "1")
    _patch_db(monkeypatch, (datetime.now(timezone.utc) + timedelta(days=5)).isoformat())
    assert await auth._subscription_wound_down(USER, "biz_x") is False


@aio
async def test_past_period_is_wound_down(monkeypatch):
    monkeypatch.setenv("SUBSCRIPTION_WINDDOWN_ENFORCED", "1")
    _patch_db(monkeypatch, (datetime.now(timezone.utc) - timedelta(days=1)).isoformat())
    assert await auth._subscription_wound_down(USER, "biz_x") is True


@aio
async def test_admin_exempt(monkeypatch):
    monkeypatch.setenv("SUBSCRIPTION_WINDDOWN_ENFORCED", "1")
    monkeypatch.setattr(auth, "ADMIN_EMAILS", ["admin@x.com"])
    _patch_db(monkeypatch, (datetime.now(timezone.utc) - timedelta(days=1)).isoformat())
    assert await auth._subscription_wound_down({"email": "admin@x.com"}, "biz_x") is False


@aio
async def test_lookup_error_fails_open(monkeypatch):
    monkeypatch.setenv("SUBSCRIPTION_WINDDOWN_ENFORCED", "1")
    import src.db as dbmod
    def boom():
        raise RuntimeError("db down")
    monkeypatch.setattr(dbmod, "get_db", boom, raising=False)
    assert await auth._subscription_wound_down(USER, "biz_x") is False


@aio
async def test_require_org_member_402s_when_wound_down(monkeypatch):
    from fastapi import HTTPException
    monkeypatch.setenv("SUBSCRIPTION_WINDDOWN_ENFORCED", "1")

    async def is_member(u, o):
        return True
    monkeypatch.setattr(auth, "_check_org_membership", is_member)
    _patch_db(monkeypatch, (datetime.now(timezone.utc) - timedelta(days=1)).isoformat())

    with pytest.raises(HTTPException) as exc:
        await auth.require_org_member(USER, "biz_x")
    assert exc.value.status_code == 402
