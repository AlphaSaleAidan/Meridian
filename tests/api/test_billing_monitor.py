"""Billing reconciliation monitor — sweep logic, dedupe, and fail-quiet."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.services import billing_monitor as bm  # noqa: E402

aio = pytest.mark.asyncio


def _session(sid, pos_order_id, amount, merchant="m1", currency="cad"):
    return {"id": sid, "amount_total": amount, "currency": currency,
            "metadata": {"pos_order_id": pos_order_id, "merchant_id": merchant}}


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    bm._alerted_sessions.clear()
    for k in ("sweeps", "sessions_checked", "mismatches_found"):
        bm._status[k] = 0
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_platform")
    monkeypatch.delenv("STRIPE_PHONE_SECRET_KEY", raising=False)
    yield


def _wire(monkeypatch, sessions, rows):
    async def fake_list(key, since):
        return sessions

    async def fake_row(pos_order_id):
        return rows.get(pos_order_id)

    monkeypatch.setattr(bm, "_list_completed_sessions", fake_list)
    monkeypatch.setattr(bm, "_fetch_order_row", fake_row)


@aio
async def test_underpaid_session_is_flagged(monkeypatch, caplog):
    _wire(monkeypatch,
          [_session("cs_1", "po-1", 4900)],
          {"po-1": {"merchant_id": "m1", "business_name": "Bistro", "total": 55.37}})
    found = await bm._sweep_once()
    assert len(found) == 1
    assert found[0]["paid_cents"] == 4900 and found[0]["expected_cents"] == 5537
    assert "BILLING MONITOR" in caplog.text


@aio
async def test_exact_and_overpaid_are_silent(monkeypatch, caplog):
    _wire(monkeypatch,
          [_session("cs_2", "po-2", 5537), _session("cs_3", "po-3", 5837)],
          {"po-2": {"total": 55.37}, "po-3": {"total": 55.37}})
    assert await bm._sweep_once() == []
    assert "BILLING MONITOR" not in caplog.text


@aio
async def test_demo_sessions_skipped(monkeypatch):
    _wire(monkeypatch,
          [_session("cs_4", "po-4", 75, merchant="demo")],
          {"po-4": {"total": 29.38}})
    assert await bm._sweep_once() == []


@aio
async def test_alerted_session_not_reflagged(monkeypatch):
    _wire(monkeypatch,
          [_session("cs_5", "po-5", 4900)],
          {"po-5": {"total": 55.37}})
    assert len(await bm._sweep_once()) == 1
    assert await bm._sweep_once() == []  # deduped for process lifetime


@aio
async def test_stripe_failure_does_not_kill_sweep(monkeypatch):
    async def boom(key, since):
        raise RuntimeError("stripe down")

    monkeypatch.setattr(bm, "_list_completed_sessions", boom)
    assert await bm._sweep_once() == []
    assert "stripe down" in bm._status["last_error"]


@aio
async def test_db_failure_skips_session_only(monkeypatch):
    async def fake_list(key, since):
        return [_session("cs_6", "po-6", 4900), _session("cs_7", "po-7", 4900)]

    calls = {"n": 0}

    async def flaky_row(pos_order_id):
        calls["n"] += 1
        if pos_order_id == "po-6":
            raise RuntimeError("db blip")
        return {"total": 55.37}

    monkeypatch.setattr(bm, "_list_completed_sessions", fake_list)
    monkeypatch.setattr(bm, "_fetch_order_row", flaky_row)
    found = await bm._sweep_once()
    assert [f["pos_order_id"] for f in found] == ["po-7"]


def test_disabled_by_env(monkeypatch):
    monkeypatch.setenv("MERIDIAN_BILLING_MONITOR", "0")
    assert bm.start_billing_monitor() is False


def test_no_keys_no_start(monkeypatch):
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    monkeypatch.delenv("STRIPE_PHONE_SECRET_KEY", raising=False)
    assert bm.start_billing_monitor() is False


def test_both_keys_deduped(monkeypatch):
    monkeypatch.setenv("STRIPE_PHONE_SECRET_KEY", "sk_test_platform")  # same key
    assert [lbl for lbl, _ in bm._stripe_keys()] == ["platform"]
    monkeypatch.setenv("STRIPE_PHONE_SECRET_KEY", "sk_test_phone")
    assert [lbl for lbl, _ in bm._stripe_keys()] == ["platform", "phone"]
