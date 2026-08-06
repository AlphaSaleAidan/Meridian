"""DEFCON pager: threshold gating, multi-responder fan-out, cooldown dedupe,
and fail-quiet. The pager is the thing that wakes people up — it must never be
noisy, never miss a DEFCON-1/2, and never break its caller."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.services import defcon_alert as da  # noqa: E402

aio = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    da._last_paged.clear()
    monkeypatch.delenv("MERIDIAN_DEFCON_RESPONDERS", raising=False)
    monkeypatch.delenv("MERIDIAN_DEFCON_PAGE_LEVEL", raising=False)
    monkeypatch.delenv("MERIDIAN_DEFCON_SMS", raising=False)
    yield


@pytest.fixture
def sent(monkeypatch):
    calls = []

    async def fake_alert(to, business, title, body, severity="medium", **kw):
        calls.append({"to": to, "title": title, "severity": severity, "body": body})
        return {"status": "sent"}

    import src.email.send as send_mod
    monkeypatch.setattr(send_mod, "send_anomaly_alert", fake_alert)
    return calls


def test_default_responders_are_both_operators():
    r = da.responders()
    assert "aidanpierce72@gmail.com" in r
    assert "nathaniel.t.wong@gmail.com" in r


@aio
async def test_defcon1_pages_all_responders(sent):
    res = await da.notify_defcon(1, "Underpayment", "detail", protocol="pay-mismatch.md")
    assert res["paged"] is True
    assert len(sent) == 2  # both responders
    assert all("DEFCON 1" in c["title"] for c in sent)
    assert all("pay-mismatch.md" in c["body"] for c in sent)


@aio
async def test_defcon2_pages(sent):
    res = await da.notify_defcon(2, "Surface down", "url", protocol="server-down.md")
    assert res["paged"] is True and len(sent) == 2


@aio
async def test_defcon3_does_not_page(sent):
    res = await da.notify_defcon(3, "One rail degraded", "detail")
    assert res["paged"] is False
    assert sent == []
    assert "threshold" in res["reason"]


@aio
async def test_cooldown_suppresses_repage(sent):
    await da.notify_defcon(1, "Underpayment", event_key="k", now=1000.0)
    res = await da.notify_defcon(1, "Underpayment", event_key="k", now=1000.0 + 60)
    assert res["paged"] is False and res["reason"] == "cooldown"
    assert len(sent) == 2  # only the first paged both


@aio
async def test_cooldown_expires(sent):
    await da.notify_defcon(1, "X", event_key="k", now=1000.0)
    await da.notify_defcon(1, "X", event_key="k", now=1000.0 + da._cooldown_s() + 1)
    assert len(sent) == 4  # two pages, two responders each


@aio
async def test_custom_responder_list(monkeypatch, sent):
    monkeypatch.setenv("MERIDIAN_DEFCON_RESPONDERS", "a@x.com, b@x.com ,c@x.com")
    await da.notify_defcon(1, "X")
    assert {c["to"] for c in sent} == {"a@x.com", "b@x.com", "c@x.com"}


@aio
async def test_page_level_override(monkeypatch, sent):
    monkeypatch.setenv("MERIDIAN_DEFCON_PAGE_LEVEL", "1")  # only DEFCON 1 pages
    r2 = await da.notify_defcon(2, "critical but level 1 only")
    assert r2["paged"] is False
    assert sent == []


@aio
async def test_one_bad_recipient_does_not_block_others(monkeypatch):
    calls = []

    async def flaky(to, *a, **k):
        if to == "bad@x.com":
            raise RuntimeError("smtp down")
        calls.append(to)
        return {"status": "sent"}

    monkeypatch.setenv("MERIDIAN_DEFCON_RESPONDERS", "bad@x.com,good@x.com")
    import src.email.send as send_mod
    monkeypatch.setattr(send_mod, "send_anomaly_alert", flaky)
    res = await da.notify_defcon(1, "X")
    assert res["paged"] is True
    assert calls == ["good@x.com"]


@aio
async def test_never_raises_on_total_failure(monkeypatch):
    async def boom(*a, **k):
        raise RuntimeError("everything is down")

    import src.email.send as send_mod
    monkeypatch.setattr(send_mod, "send_anomaly_alert", boom)
    res = await da.notify_defcon(1, "X")  # must not raise
    assert res["paged"] is True  # attempted; individual sends swallowed
