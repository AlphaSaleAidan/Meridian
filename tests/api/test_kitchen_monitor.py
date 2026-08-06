"""Paid-without-kitchen-push monitor — the "charged, no food" watch.

Covers what must page (paid order past grace with no ticket on any channel),
what must stay silent (pushed, SMS-fallback delivered, still in grace, unpaid,
demo), dedupe, and fail-quiet under a dead DB.
"""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.services import defcon_alert as dc  # noqa: E402
from src.services import kitchen_monitor as km  # noqa: E402

aio = pytest.mark.asyncio

NOW = datetime(2026, 8, 7, 18, 0, tzinfo=timezone.utc)


def _iso(minutes_ago: float) -> str:
    return (NOW - timedelta(minutes=minutes_ago)).isoformat()


def _order(oid, *, minutes_ago=30, paid=True, pos_status=None, pos_order_id="",
           pos_success=False, notify=None, merchant="m1", detail=None,
           fulfillment_state=None, fulfillment_at=None):
    """A phone_orders row shaped exactly like PostgREST returns it."""
    return {
        "id": oid,
        "merchant_id": merchant,
        "caller_phone": "+15550100",
        "customer_name": "Sam",
        "total": 42.75,
        "created_at": _iso(minutes_ago),
        "status": "paid" if paid else "awaiting_payment",
        "payment_status": "paid" if paid else "pending",
        "kitchen_released": paid,
        "payment_method": "link",
        "pos_order_id": pos_order_id,
        "pos_success": pos_success,
        "pos_system": "square",
        "pos_delivery_status": pos_status,
        "merchant_notify_status": notify,
        "fulfillment_state": fulfillment_state,
        "fulfillment_confirmed_at": fulfillment_at,
        "delivery_detail": detail or {},
        "source": "phone_agent",
    }


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    km._alerted_orders.clear()
    for k in ("sweeps", "orders_checked", "missing_tickets"):
        km._status[k] = 0
    km._status["last_error"] = ""
    dc._last_paged.clear()
    monkeypatch.setenv("SUPABASE_URL", "https://db.test")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "svc-key")
    monkeypatch.delenv("MERIDIAN_KITCHEN_MONITOR", raising=False)
    monkeypatch.delenv("MERIDIAN_KITCHEN_GRACE_MIN", raising=False)
    yield


@pytest.fixture
def paged(monkeypatch):
    """Capture notify_defcon calls (imported inside _page, so patch the source)."""
    calls = []

    async def fake_notify(level, event, detail="", protocol="", *,
                          event_key="", now=None):
        calls.append({"level": level, "event": event, "detail": detail,
                      "protocol": protocol, "event_key": event_key})
        return {"paged": True}

    monkeypatch.setattr(dc, "notify_defcon", fake_notify)
    return calls


def _wire(monkeypatch, rows):
    async def fake_fetch(since):
        return rows

    monkeypatch.setattr(km, "_fetch_paid_orders", fake_fetch)


@aio
async def test_paid_without_push_past_grace_is_flagged(monkeypatch, paged, caplog):
    _wire(monkeypatch, [_order("o-1", minutes_ago=30, pos_status="failed")])
    found = await km._sweep_once(now=NOW)
    assert len(found) == 1
    assert found[0]["order_id"] == "o-1"
    assert found[0]["age_minutes"] == pytest.approx(30, abs=0.1)
    assert "KITCHEN MONITOR" in caplog.text
    assert len(paged) == 1
    assert paged[0]["level"] == 1
    assert paged[0]["protocol"] == "payments-unconfirmed.md"
    assert paged[0]["event_key"] == "kitchen-push:o-1"
    assert "o-1" in paged[0]["event"]


@aio
async def test_push_never_recorded_at_all_is_flagged(monkeypatch, paged):
    """The post-claim PATCH never landed: paid, but no pos id and no statuses."""
    _wire(monkeypatch, [_order("o-2", minutes_ago=45)])
    found = await km._sweep_once(now=NOW)
    assert [f["order_id"] for f in found] == ["o-2"]
    assert "not recorded" in found[0]["reason"]
    assert len(paged) == 1


@aio
@pytest.mark.parametrize("healthy", [
    {"pos_status": "sent", "pos_order_id": "sq-1", "pos_success": True},
    {"pos_status": "sent", "pos_order_id": "sq-2"},
    {"pos_order_id": "sq-3"},                       # id present, no failure
    {"pos_status": "demo_safe"},                    # logs-only by design
    {"fulfillment_state": "kitchen_fired"},         # Clover printer fired
    {"fulfillment_at": _iso(20)},                   # prove-out confirmed
    {"notify": "sent"},                             # no POS: merchant texted
])
async def test_delivered_orders_are_silent(monkeypatch, paged, caplog, healthy):
    _wire(monkeypatch, [_order("o-ok", minutes_ago=60, **healthy)])
    assert await km._sweep_once(now=NOW) == []
    assert "KITCHEN MONITOR" not in caplog.text
    assert paged == []


@aio
async def test_within_grace_is_silent(monkeypatch, paged):
    """Just paid — the async push is still in flight, not broken."""
    _wire(monkeypatch, [_order("o-3", minutes_ago=2)])
    assert await km._sweep_once(now=NOW) == []
    assert paged == []


@aio
async def test_grace_runs_from_latest_leg_timestamp(monkeypatch, paged):
    """A link-paid order created hours ago whose push JUST failed is inside
    grace — age comes from the leg timestamp, not created_at."""
    row = _order("o-4", minutes_ago=180, pos_status="failed",
                 detail={"pos": {"status": "failed", "at": _iso(1)}})
    _wire(monkeypatch, [row])
    assert await km._sweep_once(now=NOW) == []
    assert paged == []
    # ...and once that failure ages past grace, it pages.
    km._alerted_orders.clear()
    row["delivery_detail"] = {"pos": {"status": "failed", "at": _iso(20)}}
    assert len(await km._sweep_once(now=NOW)) == 1


@aio
async def test_unpaid_order_is_silent(monkeypatch, paged):
    _wire(monkeypatch, [_order("o-5", minutes_ago=90, paid=False,
                               pos_status="deferred_pending_payment")])
    assert await km._sweep_once(now=NOW) == []
    assert paged == []


@aio
async def test_demo_merchant_is_skipped(monkeypatch, paged):
    _wire(monkeypatch, [_order("o-6", minutes_ago=90, merchant="demo")])
    assert await km._sweep_once(now=NOW) == []
    assert paged == []


@aio
async def test_finding_not_repeated_across_sweeps(monkeypatch, paged):
    _wire(monkeypatch, [_order("o-7", minutes_ago=30, pos_status="failed")])
    assert len(await km._sweep_once(now=NOW)) == 1
    assert await km._sweep_once(now=NOW) == []  # deduped for process lifetime
    assert len(paged) == 1


@aio
async def test_db_failure_does_not_kill_sweep(monkeypatch, paged):
    async def boom(since):
        raise RuntimeError("supabase down")

    monkeypatch.setattr(km, "_fetch_paid_orders", boom)
    assert await km._sweep_once(now=NOW) == []
    assert "supabase down" in km._status["last_error"]
    assert paged == []


@aio
async def test_paging_failure_does_not_kill_sweep(monkeypatch):
    async def boom(*a, **kw):
        raise RuntimeError("pager down")

    monkeypatch.setattr(dc, "notify_defcon", boom)
    _wire(monkeypatch, [_order("o-8", minutes_ago=30, pos_status="failed")])
    assert len(await km._sweep_once(now=NOW)) == 1  # finding still returned


@aio
async def test_digest_never_raises(monkeypatch):
    """Email transport down must not break the monitor."""
    import src.email.send as send_mod

    async def boom(*a, **kw):
        raise RuntimeError("resend down")

    monkeypatch.setattr(send_mod, "send_anomaly_alert", boom)
    await km._send_digest([km._finding(_order("o-9"), 30.0)])  # no exception


@aio
async def test_mixed_batch_flags_only_the_broken_one(monkeypatch, paged):
    _wire(monkeypatch, [
        _order("ok-1", minutes_ago=40, pos_status="sent", pos_order_id="sq-9"),
        _order("bad-1", minutes_ago=40, pos_status="failed"),
        _order("ok-2", minutes_ago=40, notify="sent"),
    ])
    found = await km._sweep_once(now=NOW)
    assert [f["order_id"] for f in found] == ["bad-1"]
    assert km._status["orders_checked"] == 3
    assert len(paged) == 1


def test_disabled_by_env(monkeypatch):
    monkeypatch.setenv("MERIDIAN_KITCHEN_MONITOR", "0")
    assert km.start_kitchen_monitor() is False


def test_no_db_credentials_no_start(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_KEY", raising=False)
    assert km.start_kitchen_monitor() is False


def test_env_tuning_and_status(monkeypatch):
    monkeypatch.setenv("MERIDIAN_KITCHEN_MONITOR_INTERVAL", "900")
    monkeypatch.setenv("MERIDIAN_KITCHEN_MONITOR_WINDOW_H", "6")
    monkeypatch.setenv("MERIDIAN_KITCHEN_GRACE_MIN", "12")
    status = km.get_kitchen_monitor_status()
    assert status["interval_s"] == 900
    assert status["window_h"] == 6
    assert status["grace_min"] == 12
    assert status["running"] is False
    # Junk values fall back to the defaults rather than crashing the loop.
    monkeypatch.setenv("MERIDIAN_KITCHEN_MONITOR_INTERVAL", "soon")
    monkeypatch.setenv("MERIDIAN_KITCHEN_GRACE_MIN", "later")
    assert km._interval() == km.DEFAULT_INTERVAL
    assert km._grace_minutes() == km.DEFAULT_GRACE_MIN
