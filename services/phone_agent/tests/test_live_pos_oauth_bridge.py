"""Live Vapi POS dispatch must resolve an OAuth-connected merchant's token.

OAuth stores the POS token in pos_connections, NOT
phone_agent_config.pos_access_token. create_pos_for_config used to read only the
manual token + a global SQUARE env fallback, so an OAuth-connected merchant's
live phone order silently missed their real POS. It must fall back to the
pos_connections OAuth token (the same two-tier resolution the Twilio path uses).
"""
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_DIR = str(Path(__file__).resolve().parents[1])
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)
_ROOT = str(Path(__file__).resolve().parents[3])
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import delivery_channels as dc  # noqa: E402

pytestmark = pytest.mark.asyncio


async def test_oauth_token_resolved_from_pos_connections(monkeypatch):
    captured = {}

    async def fake_create_pos_order(order, pos_system, token, location, demo_safe=False):
        captured.update(system=pos_system, token=token, location=location)
        return {"success": True, "pos_order_id": "X1"}

    import pos_connector
    monkeypatch.setattr(pos_connector, "create_pos_order", fake_create_pos_order)

    # DB returns a connected OAuth row; token comes back fresh via the helper.
    class _DB:
        async def select(self, table, filters=None, order=None, limit=None):
            assert table == "pos_connections"
            return [{"provider": "square", "external_location_id": "LOC-9",
                     "access_token_encrypted": "enc"}]

    import src.db as srcdb
    import src.api.routes.phone_dashboard as pd
    monkeypatch.setattr(srcdb, "get_db", lambda: _DB())

    async def fake_fresh(conn):
        return "oauth-token-123"
    monkeypatch.setattr(pd, "_fresh_connection_token", fake_fresh)

    # config: OAuth merchant → NO manual pos_access_token
    config = SimpleNamespace(merchant_id="biz_abc0000000000000",
                             pos_system="", pos_access_token="",
                             pos_location_id="", demo_safe=False)

    res = await dc.create_pos_for_config({"items": []}, config)
    assert res["success"] is True
    assert captured["token"] == "oauth-token-123"   # NOT "" / global env
    assert captured["system"] == "square"
    assert captured["location"] == "LOC-9"


async def test_manual_token_wins_no_oauth_lookup(monkeypatch):
    captured = {}

    async def fake_create_pos_order(order, pos_system, token, location, demo_safe=False):
        captured.update(token=token)
        return {"success": True}

    import pos_connector
    monkeypatch.setattr(pos_connector, "create_pos_order", fake_create_pos_order)

    # If OAuth lookup were attempted it'd blow up — assert it's NOT called.
    import src.db as srcdb
    def _boom():
        raise AssertionError("pos_connections lookup must be skipped when a manual token exists")
    monkeypatch.setattr(srcdb, "get_db", _boom)

    config = SimpleNamespace(merchant_id="biz_abc0000000000000",
                             pos_system="square", pos_access_token="manual-tok",
                             pos_location_id="LOC-1", demo_safe=False)
    await dc.create_pos_for_config({"items": []}, config)
    assert captured["token"] == "manual-tok"
