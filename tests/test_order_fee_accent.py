"""
Rep fee slider (per-merchant order-fee override) + agent accent feature.

Money invariants:
  1. phone_agent_config.order_fee_cents overrides the tier/env per-order fee
     on EVERY rail (split surcharge, legacy application fee, Clover-native,
     phone-order ledger credit) — and None everywhere means "default rate",
     so existing merchants are byte-for-byte unchanged.
  2. The redline is enforced server-side: create-customer clamps to the tier
     floor (premium 65¢, command 45¢) no matter what the client sends.

Accent invariants:
  3. The wizard may write Vapi voice names or legacy kokoro ids — both resolve
     to a live Vapi voice; unknowns fall back to Elliot.
  4. language=multi turns on Deepgram multilingual transcription; the default
     assistant payload is unchanged otherwise.
"""
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
_PA = str(Path(__file__).resolve().parents[1] / "services" / "phone_agent")
if _PA not in sys.path:
    sys.path.insert(0, _PA)

import payment_links as pl  # noqa: E402
import src.api.routes.pay_redirect as pr  # noqa: E402
import src.api.routes.stripe_connect as sc  # noqa: E402
from src.api.routes.canada import _clamp_order_fee_cents  # noqa: E402
from src.api.routes.vapi_webhook import (  # noqa: E402
    _assistant_for, _transcriber_for, _vapi_voice,
)

aio = pytest.mark.asyncio


# ── 1. override plumbing ──────────────────────────────────────


def test_surcharge_uses_override_when_set():
    base = pl.customer_surcharge_cents("premium", "cad")
    assert base == pl.tier_order_fee_cents("premium", "cad") + pl.CUSTOMER_FIXED_FEE_CENTS
    assert pl.customer_surcharge_cents("premium", "cad", override_cents=65) == 65 + pl.CUSTOMER_FIXED_FEE_CENTS
    # None → unchanged default path
    assert pl.customer_surcharge_cents("premium", "cad", override_cents=None) == base


def test_application_fee_uses_override(monkeypatch):
    monkeypatch.setattr(pl, "STRIPE_GROSSUP_ENABLED", False)
    monkeypatch.setattr(pl, "PLATFORM_FEE_BPS", 0)
    monkeypatch.setattr(pl, "SERVICE_FEE_CENTS", 149)
    assert pl.application_fee_cents(3400) == 149
    assert pl.application_fee_cents(3400, service_fee_cents=65) == 65
    assert pl.application_fee_cents(3400, service_fee_cents=None) == 149


def test_merchant_order_fee_cents_resolution():
    cfg_override = SimpleNamespace(order_fee_cents=65, plan_tier="premium")
    cfg_default = SimpleNamespace(order_fee_cents=None, plan_tier="premium")
    cfg_negative = SimpleNamespace(order_fee_cents=-10, plan_tier="premium")
    assert pl.merchant_order_fee_cents(cfg_override, "cad") == 65
    assert pl.merchant_order_fee_cents(cfg_default, "cad") == pl.tier_order_fee_cents("premium", "cad")
    assert pl.merchant_order_fee_cents(cfg_negative, "cad") == 0


class _Resp:
    def __init__(self, status, data):
        self.status_code, self._d, self.text = status, data, ""

    def json(self):
        return self._d


class _HcoClient:
    def __init__(self, calls):
        self.calls = calls

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, json=None, headers=None):
        self.calls.append((url, json))
        return _Resp(200, {"href": "https://x/chk", "checkoutSessionId": "C1"})


def test_clover_hco_fee_line_uses_override(monkeypatch):
    # #322's unified lazy rail: the override reaches the HCO cart's fee line
    # via _clover_hco_line_items (called at /p tap time with the payload's
    # fee_override_cents).
    monkeypatch.setattr(pl, "FEE_SPLIT_ENABLED", True)
    order = {"merchant_id": "m1", "currency": "cad", "total": 10.0,
             "items": [{"name": "Samosa", "quantity": 1, "unit_price": 10.0}]}
    items, _total = pl._clover_hco_line_items(order, plan_tier="premium",
                                              fee_override_cents=65)
    fee_line = items[-1]
    assert fee_line["name"] == "Service & processing fee"
    assert fee_line["price"] == 65 + pl.CUSTOMER_FIXED_FEE_CENTS  # NOT the CA$1.99 tier rate


class _CfgDB:
    def __init__(self, row):
        self.row = row

    async def select(self, table, columns=None, filters=None, limit=None):
        return [dict(self.row)] if self.row is not None else []


@aio
async def test_webhook_ledger_credit_uses_override(monkeypatch):
    monkeypatch.setenv("MERIDIAN_SERVICE_FEE_CENTS", "149")
    monkeypatch.setattr(sc, "get_db", lambda: _CfgDB({"order_fee_cents": 65}))
    assert await sc._merchant_service_fee_cents("m1") == 65

    monkeypatch.setattr(sc, "get_db", lambda: _CfgDB({"order_fee_cents": None}))
    assert await sc._merchant_service_fee_cents("m1") == 149

    class _BoomDB:
        async def select(self, *a, **k):
            raise RuntimeError("column does not exist")  # pre-migration schema
    monkeypatch.setattr(sc, "get_db", lambda: _BoomDB())
    assert await sc._merchant_service_fee_cents("m1") == 149


def test_clover_native_fee_uses_override(monkeypatch):
    # #322's settlement reads the override from the session PAYLOAD (written
    # at order time) — billing books the exact negotiated fee even if the
    # config changes between order and payment.
    from src.services.clover_hco import clover_fee_cents
    monkeypatch.setattr(pl, "FEE_SPLIT_ENABLED", True)
    sess = {"merchant_id": "m1", "amount_cents": 3400, "currency": "cad",
            "payload": {"plan_tier": "premium", "fee_override_cents": 77}}
    surcharge = pl.customer_surcharge_cents("premium", "cad", override_cents=77)
    assert clover_fee_cents(sess) == pl.split_application_fee_cents(3400 - surcharge, surcharge)

    # flat model → the negotiated override STILL wins (bug-hunt fix: the env
    # fee only applies when no override travels in the payload)
    monkeypatch.setenv("MERIDIAN_SERVICE_FEE_CENTS", "149")
    monkeypatch.setattr(pl, "FEE_SPLIT_ENABLED", False)
    assert clover_fee_cents(sess) == 77
    assert clover_fee_cents({**sess, "payload": {}}) == 149


# ── 2. redline enforcement ────────────────────────────────────


def test_clamp_enforces_tier_redlines():
    # Default floors are CANADA's (CA$0.85 premium / CA$0.65 command) — higher
    # than US because CA$ is worth less while per-call costs bill in USD.
    assert _clamp_order_fee_cents(50, "premium") == 85    # below premium floor → 85
    assert _clamp_order_fee_cents(85, "premium") == 85
    assert _clamp_order_fee_cents(149, "premium") == 149  # in range untouched
    assert _clamp_order_fee_cents(10, "command") == 65    # command floor 65
    assert _clamp_order_fee_cents(0, None) == 65          # unknown plan → lowest non-zero floor
    assert _clamp_order_fee_cents(0, "standard") == 0     # standard has no phone agent fee
    assert _clamp_order_fee_cents(99999, "premium") == 500  # cap


def test_clamp_us_floors_unchanged():
    from src.api.routes.canada import _ORDER_FEE_FLOOR_CENTS_USD as US
    assert _clamp_order_fee_cents(50, "premium", floors=US) == 65
    assert _clamp_order_fee_cents(10, "command", floors=US) == 45
    assert _clamp_order_fee_cents(0, None, floors=US) == 45
    assert _clamp_order_fee_cents(0, "standard", floors=US) == 0


# ── 3+4. accent / voice / multilingual ────────────────────────


def test_vapi_voice_passthrough_and_legacy_map():
    assert _vapi_voice("Naina") == "Naina"          # direct Vapi name
    assert _vapi_voice("naina") == "Naina"          # case-tolerant
    assert _vapi_voice("af_nicole") == "Naina"      # legacy kokoro id still maps
    assert _vapi_voice("bm_george") == "Neil"
    assert _vapi_voice("Harry") == "Elliot"         # retired voice → safe default
    assert _vapi_voice("") == "Elliot"


def test_transcriber_multilingual_gate():
    en = _transcriber_for(SimpleNamespace(language="en"))
    assert en == {"provider": "deepgram", "model": "nova-3"}
    multi = _transcriber_for(SimpleNamespace(language="multi"))
    assert multi["language"] == "multi"
    # unset language → default payload, no language key
    assert "language" not in _transcriber_for(SimpleNamespace())


def test_assistant_payload_wires_accent_voice_and_language():
    cfg = SimpleNamespace(
        merchant_id="m1", business_name="Maple Tandoor", business_type="restaurant",
        greeting="", voice="Naina", language="multi", accent="indian",
        menu_items=[], order_types=["pickup"], business_hours={}, personality=None,
        transfer_number="", special_instructions_enabled=True,
        reservation_config=None, restaurant_brief="",
    )
    a = _assistant_for(cfg)
    assert a["voice"]["voiceId"] == "Naina"
    assert a["transcriber"]["language"] == "multi"

    cfg.language, cfg.voice = "en", "af_bella"
    a = _assistant_for(cfg)
    assert a["voice"]["voiceId"] == "Savannah"
    assert "language" not in a["transcriber"]


# ── 5. hard call cap (auto-drop at 5 min) ─────────────────────


def _cap_cfg():
    return SimpleNamespace(
        merchant_id="m1", business_name="Maple Tandoor", business_type="restaurant",
        greeting="", voice="Naina", language="en", accent="",
        menu_items=[], order_types=["pickup"], business_hours={}, personality=None,
        transfer_number="", special_instructions_enabled=True,
        reservation_config=None, restaurant_brief="",
    )


def test_assistant_caps_call_at_max_minutes(monkeypatch):
    import src.api.routes.vapi_webhook as vw
    monkeypatch.setattr(vw, "VOICE_MAX_CALL_MIN", 5)
    a = _assistant_for(_cap_cfg())
    # advertised cap + confirmation grace; billing clamps to the advertised cap
    assert a["maxDurationSeconds"] == 300 + vw.VOICE_CAP_GRACE_SEC
    # the agent is told about the cap so it lands orders before the drop
    prompt = a["model"]["messages"][0]["content"]
    assert "end automatically at 5 minutes" in prompt


def test_cap_disabled_when_zero(monkeypatch):
    import src.api.routes.vapi_webhook as vw
    monkeypatch.setattr(vw, "VOICE_MAX_CALL_MIN", 0)
    a = _assistant_for(_cap_cfg())
    assert "maxDurationSeconds" not in a
    assert "end automatically" not in a["model"]["messages"][0]["content"]


def test_worst_case_overage_under_cap():
    """With a 5-min cap and 3 included minutes, the max billable overage per
    call is 2 min × 45¢ = 90¢ — the number disclosed on the rep pages."""
    import math
    import src.api.routes.vapi_webhook as vw
    cap_min, over_rate, included = 5, vw.VOICE_OVERAGE_CENTS_PER_MIN, vw.VOICE_INCLUDED_MIN
    worst = max(0, math.ceil(cap_min) - included) * over_rate
    assert worst == 90


@aio
async def test_fees_endpoint_exposes_cap(monkeypatch):
    monkeypatch.setenv("MERIDIAN_VOICE_MAX_CALL_MIN", "5")
    from src.api.routes.phone_dashboard import get_fee_settings
    fees = await get_fee_settings()
    assert fees["max_call_minutes"] == 5
    assert fees["included_minutes"] == 3
    monkeypatch.setenv("MERIDIAN_VOICE_MAX_CALL_MIN", "0")
    fees = await get_fee_settings()
    assert fees["max_call_minutes"] == 0
