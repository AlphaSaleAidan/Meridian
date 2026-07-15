"""
Perf backlog (2026-07-16): the phone-agent merchant-config loader now caches
successful lookups for a short TTL, so a single call's repeated resolutions
(assistant-request → submit_order → end-of-call → deferred POS push) collapse
to one Supabase round trip instead of 3-4.

Invariants pinned here:
  A. A second lookup within the TTL is served from cache (no 2nd network hit).
  B. Misses/None are NOT cached — a just-activated merchant resolves on the
     next call, not after the TTL.
  C. TTL=0 disables caching entirely (revert knob).
  D. invalidate_config_cache() forces a re-fetch.
"""
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
_PA = str(Path(__file__).resolve().parents[1] / "services" / "phone_agent")
if _PA not in sys.path:
    sys.path.insert(0, _PA)

aio = pytest.mark.asyncio


class _FakeResp:
    def __init__(self, rows):
        self.status_code = 200
        self._rows = rows

    def json(self):
        return self._rows


class _FakeClient:
    """Counts phone_agent_config GETs so we can assert the cache actually
    elides network hits. The loader also reads the menu_items / merchant_menus
    store tables on the same shared client (main's concurrent menu-store
    fan-out); those return [] here so the JSONB fallback holds and they don't
    skew the cache-hit accounting."""
    calls = 0
    rows = [{"merchant_id": "m1", "business_name": "Cafe One"}]
    # Shared-client model on main lazily reuses one AsyncClient; expose the
    # attributes _get_http_client() probes so it treats us as a live client.
    is_closed = False

    def __init__(self, *a, **k):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, url="", *a, **k):
        # Only the primary config read counts; menu-store reads return empty
        # so the loader keeps the JSONB menu (behaviour identical to no store).
        if "phone_agent_config" in url:
            type(self).calls += 1
            return _FakeResp(type(self).rows)
        return _FakeResp([])


def _patch(monkeypatch, mc, ttl=60.0):
    monkeypatch.setattr(mc, "SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setattr(mc, "SUPABASE_KEY", "service-key-not-real")
    monkeypatch.setattr(mc, "_CONFIG_CACHE_TTL_SEC", ttl)
    mc.invalidate_config_cache()
    _FakeClient.calls = 0
    _FakeClient.rows = [{"merchant_id": "m1", "business_name": "Cafe One"}]
    # Reset the module's shared-client singleton so each test gets a fresh
    # _FakeClient built from the patched httpx.AsyncClient.
    if hasattr(mc, "_http_client"):
        monkeypatch.setattr(mc, "_http_client", None)
        monkeypatch.setattr(mc, "_http_client_loop", None)
    import httpx
    monkeypatch.setattr(httpx, "AsyncClient", _FakeClient)


@aio
async def test_second_lookup_within_ttl_is_cached(monkeypatch):
    import merchant_config as mc
    _patch(monkeypatch, mc, ttl=60.0)

    a = await mc.get_merchant_config("m1")
    b = await mc.get_merchant_config("m1")
    assert a is not None and b is not None
    assert a.business_name == "Cafe One"
    assert _FakeClient.calls == 1  # second call served from cache


@aio
async def test_misses_are_not_cached(monkeypatch):
    import merchant_config as mc
    _patch(monkeypatch, mc, ttl=60.0)
    _FakeClient.rows = []  # no such merchant yet

    first = await mc.get_merchant_config("ghost")
    assert first is None
    # merchant gets configured; the very next call must see it (miss not pinned)
    _FakeClient.rows = [{"merchant_id": "ghost", "business_name": "Now Live"}]
    second = await mc.get_merchant_config("ghost")
    assert second is not None and second.business_name == "Now Live"
    assert _FakeClient.calls == 2


@aio
async def test_ttl_zero_disables_cache(monkeypatch):
    import merchant_config as mc
    _patch(monkeypatch, mc, ttl=0.0)

    await mc.get_merchant_config("m1")
    await mc.get_merchant_config("m1")
    assert _FakeClient.calls == 2  # no caching → every call hits the network


@aio
async def test_invalidate_forces_refetch(monkeypatch):
    import merchant_config as mc
    _patch(monkeypatch, mc, ttl=60.0)

    await mc.get_merchant_config("m1")
    assert _FakeClient.calls == 1
    mc.invalidate_config_cache("m1")
    await mc.get_merchant_config("m1")
    assert _FakeClient.calls == 2


@aio
async def test_phone_lookup_is_cached(monkeypatch):
    import merchant_config as mc
    _patch(monkeypatch, mc, ttl=60.0)
    _FakeClient.rows = [{"merchant_id": "m1"}]

    a = await mc.get_merchant_by_phone("+15551234567")
    b = await mc.get_merchant_by_phone("+15551234567")
    assert a == "m1" and b == "m1"
    assert _FakeClient.calls == 1
