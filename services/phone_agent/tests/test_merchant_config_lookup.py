"""
Tests for the merchant-config Supabase lookup (no network).

key selection:
  - service-role key preferred over anon (phone_agent_config is service-only
    under RLS; anon-only reads made every live lookup fall back to demo)
  - anon still used when no service key is present

phone lookup encoding:
  - E.164 dialed numbers go out percent-encoded (%2B), never a literal "+"
    (a literal "+" in the query string decodes to a space and matches nothing)
"""
import importlib
import sys
from pathlib import Path

import pytest

_DIR = str(Path(__file__).resolve().parents[1])
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)

import merchant_config  # noqa: E402

aio = pytest.mark.asyncio


def _reload_with_env(monkeypatch, **env):
    for k in ("SUPABASE_URL", "SUPABASE_ANON_KEY",
              "SUPABASE_SERVICE_KEY", "SUPABASE_SERVICE_ROLE_KEY"):
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    return importlib.reload(merchant_config)


def test_service_key_preferred_over_anon(monkeypatch):
    mod = _reload_with_env(
        monkeypatch,
        SUPABASE_URL="https://x.supabase.co",
        SUPABASE_ANON_KEY="anon-key",
        SUPABASE_SERVICE_KEY="service-key",
    )
    assert mod.SUPABASE_KEY == "service-key"


def test_anon_key_is_fallback(monkeypatch):
    mod = _reload_with_env(
        monkeypatch,
        SUPABASE_URL="https://x.supabase.co",
        SUPABASE_ANON_KEY="anon-key",
    )
    assert mod.SUPABASE_KEY == "anon-key"


class _CapturingClient:
    """Stands in for httpx.AsyncClient; records the fully-encoded request URL."""
    last_url = ""

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get(self, url, params=None, headers=None):
        import httpx
        _CapturingClient.last_url = str(httpx.URL(url, params=params))

        class _Res:
            status_code = 200

            @staticmethod
            def json():
                return [{"merchant_id": "m-1"}]

        return _Res()


@aio
async def test_phone_lookup_percent_encodes_plus(monkeypatch):
    mod = _reload_with_env(
        monkeypatch,
        SUPABASE_URL="https://x.supabase.co",
        SUPABASE_ANON_KEY="anon-key",
    )
    import httpx
    monkeypatch.setattr(httpx, "AsyncClient", _CapturingClient)
    merchant = await mod.get_merchant_by_phone("+12368324333")
    assert merchant == "m-1"
    assert "%2B12368324333" in _CapturingClient.last_url
    assert "+12368324333" not in _CapturingClient.last_url
