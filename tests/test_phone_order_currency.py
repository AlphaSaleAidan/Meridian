"""Phone orders are CANADA-FIRST — they must be billed in CAD (Aidan 2026-08-07).

WHY THIS FILE EXISTS. The normalizer picks the charge currency for every phone
order, and its fallback used to be a hardcoded 'usd'. That was live: the real
MerchantPhoneConfig has no `country` and no `currency` field — only `language`
— so both getattr() probes in normalize_order() missed and EVERY English
merchant, the Canadian pilot included, was normalized to USD while
order_router's own comment said "Stripe (CAD…)".

It hid because the existing normalizer tests build config as a SimpleNamespace
carrying `currency="cad", country="CA"` — attributes the production dataclass
does not have. A fixture richer than reality cannot catch a bug that only
appears when those attributes are absent.

So these tests deliberately use the REAL MerchantPhoneConfig (via the real
_demo_config builder) rather than a hand-rolled namespace. If someone later
adds a country/currency field, these still pass; if someone flips the fallback
back to USD, they fail.
"""
import os
import sys
from pathlib import Path

import pytest

_DIR = str(Path(__file__).resolve().parents[1] / "services" / "phone_agent")
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)

import order_normalizer as on  # noqa: E402
from merchant_config import _demo_config  # noqa: E402
from order_normalizer import normalize_order  # noqa: E402

ITEMS = {"items": [{"name": "Pepperoni Pizza", "quantity": 1, "size": "medium"}]}


def _real_config():
    """The production dataclass — NOT a SimpleNamespace. This is the whole
    point: it has no `country` and no `currency` attribute."""
    return _demo_config("m-currency-test")


def test_real_config_has_no_country_or_currency_field():
    """Pins the premise of this file. If this ever fails, the config grew a
    market field and the fallback below is no longer the deciding branch —
    revisit normalize_order()."""
    cfg = _real_config()
    assert not hasattr(cfg, "country")
    assert not hasattr(cfg, "currency")


def test_phone_order_is_cad_by_default():
    """The live default: no market signal anywhere → CAD, not USD."""
    order = normalize_order(dict(ITEMS), _real_config())
    assert order["currency"] == "cad"


def test_default_is_not_usd_regression_guard():
    """Explicit guard on the exact regression: a silent 'usd' fallback charged
    Canadian merchants in US dollars."""
    assert on.PHONE_DEFAULT_CURRENCY == "cad"
    assert normalize_order(dict(ITEMS), _real_config())["currency"] != "usd"


def test_env_can_flip_the_default_when_us_phone_orders_launch(monkeypatch):
    """The Canada-first default is 'for now' — one env flip, no code change."""
    monkeypatch.setattr(on, "PHONE_DEFAULT_CURRENCY", "usd")
    assert normalize_order(dict(ITEMS), _real_config())["currency"] == "usd"


@pytest.mark.parametrize("country,expected", [
    ("CA", "cad"), ("CAN", "cad"), ("CANADA", "cad"),
    ("US", "usd"), ("USA", "usd"), ("UNITED STATES", "usd"),
])
def test_explicit_country_still_wins_over_the_default(country, expected):
    """A merchant that DOES carry a market signal is routed by it — so adding
    a country field later routes US merchants to USD without another change."""
    cfg = _real_config()
    cfg.country = country
    assert normalize_order(dict(ITEMS), cfg)["currency"] == expected


def test_explicit_config_currency_beats_everything():
    cfg = _real_config()
    cfg.country = "CA"
    cfg.currency = "USD"
    assert normalize_order(dict(ITEMS), cfg)["currency"] == "usd"


def test_french_language_implies_cad():
    cfg = _real_config()
    cfg.language = "fr"
    assert normalize_order(dict(ITEMS), cfg)["currency"] == "cad"


def test_module_default_reads_the_env(monkeypatch):
    """The knob is real: reloading with the env set changes the default."""
    import importlib
    monkeypatch.setenv("MERIDIAN_PHONE_DEFAULT_CURRENCY", "usd")
    reloaded = importlib.reload(on)
    try:
        assert reloaded.PHONE_DEFAULT_CURRENCY == "usd"
    finally:
        monkeypatch.delenv("MERIDIAN_PHONE_DEFAULT_CURRENCY", raising=False)
        importlib.reload(on)
    assert on.PHONE_DEFAULT_CURRENCY == "cad"
