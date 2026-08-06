"""Edge watchdog: config gating, the down/recover state machine, and the sweep.

The watchdog probes the Contabo-hosted frontends from Railway, so these tests
mock both the HTTP probe and the email path — nothing here touches the network.

Run:  python -m pytest tests/services/test_edge_watchdog.py -v
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.services import edge_watchdog as ew  # noqa: E402

NOW = datetime(2026, 8, 6, 12, 0, tzinfo=timezone.utc)

EDGE_ENV = (
    "MERIDIAN_EDGE_WATCH",
    "MERIDIAN_EDGE_WATCH_URLS",
    "MERIDIAN_EDGE_WATCH_INTERVAL",
    "MERIDIAN_EDGE_WATCH_EMAIL",
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Every test starts from an unconfigured, empty-state watchdog."""
    for key in EDGE_ENV:
        monkeypatch.delenv(key, raising=False)
    ew._states.clear()
    yield
    ew._states.clear()


class _Resp:
    def __init__(self, status_code: int):
        self.status_code = status_code


class FakeClient:
    """Stands in for httpx.AsyncClient — replays a scripted response per URL."""

    def __init__(self, script: dict[str, list]):
        self.script = script
        self.calls: list[str] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get(self, url, **kwargs):
        self.calls.append(url)
        step = self.script[url].pop(0)
        if isinstance(step, Exception):
            raise step
        return _Resp(step)


class MailSpy:
    def __init__(self):
        self.down: list[dict] = []
        self.recovered: list[dict] = []

    def install(self, monkeypatch, *, fail: bool = False):
        import src.email.send as send_mod

        async def _down(**kwargs):
            if fail:
                raise RuntimeError("resend exploded")
            self.down.append(kwargs)
            return {"status": "sent"}

        async def _recovered(**kwargs):
            if fail:
                raise RuntimeError("resend exploded")
            self.recovered.append(kwargs)
            return {"status": "sent"}

        monkeypatch.setattr(send_mod, "send_edge_down_alert", _down)
        monkeypatch.setattr(send_mod, "send_edge_recovered_alert", _recovered)
        return self


def _install_client(monkeypatch, script: dict[str, list]) -> FakeClient:
    import httpx

    client = FakeClient(script)
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: client)
    return client


# ── Configuration gating ──────────────────────────────────────────────────────

class TestConfig:
    def test_disabled_by_default(self):
        assert ew.is_enabled() is False

    def test_enabled_only_by_explicit_one(self, monkeypatch):
        for value, expected in (("1", True), ("0", False), ("true", False), ("", False)):
            monkeypatch.setenv("MERIDIAN_EDGE_WATCH", value)
            assert ew.is_enabled() is expected

    def test_start_is_a_noop_when_disabled(self):
        assert ew.start_edge_watchdog() is False
        assert ew._watch_task is None

    def test_start_is_a_noop_when_enabled_without_urls(self, monkeypatch):
        monkeypatch.setenv("MERIDIAN_EDGE_WATCH", "1")
        assert ew.start_edge_watchdog() is False
        assert ew._watch_task is None

    def test_urls_are_split_and_trimmed(self, monkeypatch):
        monkeypatch.setenv(
            "MERIDIAN_EDGE_WATCH_URLS",
            " https://meridian.tips , https://canada.meridian.tips ,, ",
        )
        assert ew.watched_urls() == ["https://meridian.tips", "https://canada.meridian.tips"]

    def test_recipient_defaults(self, monkeypatch):
        assert ew.alert_recipient() == "aidanpierce72@gmail.com"
        monkeypatch.setenv("MERIDIAN_EDGE_WATCH_EMAIL", "ops@meridian.tips")
        assert ew.alert_recipient() == "ops@meridian.tips"

    def test_interval_defaults_and_floor(self, monkeypatch):
        assert ew.watch_interval() == 300
        monkeypatch.setenv("MERIDIAN_EDGE_WATCH_INTERVAL", "600")
        assert ew.watch_interval() == 600
        monkeypatch.setenv("MERIDIAN_EDGE_WATCH_INTERVAL", "5")
        assert ew.watch_interval() == 30
        monkeypatch.setenv("MERIDIAN_EDGE_WATCH_INTERVAL", "not-a-number")
        assert ew.watch_interval() == 300


# ── State machine ─────────────────────────────────────────────────────────────

class TestStateMachine:
    def _state(self):
        return ew.SurfaceState(url="https://meridian.tips")

    def test_two_failures_are_not_yet_down(self):
        state = self._state()
        assert ew.record_probe(state, False, "HTTP 502", now=NOW) is None
        assert ew.record_probe(state, False, "HTTP 502", now=NOW) is None
        assert state.is_down is False

    def test_third_consecutive_failure_transitions_down(self):
        state = self._state()
        for _ in range(2):
            ew.record_probe(state, False, "HTTP 502", now=NOW)
        assert ew.record_probe(state, False, "HTTP 502", now=NOW) == "down"
        assert state.is_down is True
        assert state.down_since == NOW

    def test_staying_down_does_not_re_alert(self):
        state = self._state()
        for _ in range(3):
            ew.record_probe(state, False, "HTTP 502", now=NOW)
        for _ in range(10):
            assert ew.record_probe(state, False, "HTTP 502", now=NOW) is None
        assert state.alerts_sent == 1

    def test_recovery_fires_once(self):
        state = self._state()
        for _ in range(3):
            ew.record_probe(state, False, "HTTP 502", now=NOW)
        assert ew.record_probe(state, True, now=NOW) == "recovered"
        assert ew.record_probe(state, True, now=NOW) is None
        assert state.is_down is False
        assert state.consecutive_failures == 0
        assert state.recoveries_sent == 1

    def test_a_success_resets_the_failure_run(self):
        state = self._state()
        ew.record_probe(state, False, "HTTP 502", now=NOW)
        ew.record_probe(state, False, "HTTP 502", now=NOW)
        ew.record_probe(state, True, now=NOW)
        ew.record_probe(state, False, "HTTP 502", now=NOW)
        ew.record_probe(state, False, "HTTP 502", now=NOW)
        assert state.is_down is False
        assert state.alerts_sent == 0

    def test_healthy_surface_never_alerts(self):
        state = self._state()
        for _ in range(20):
            assert ew.record_probe(state, True, now=NOW) is None
        assert state.alerts_sent == 0 and state.recoveries_sent == 0

    def test_full_down_up_down_cycle(self):
        state = self._state()
        transitions = []
        for ok in [False, False, False, True, False, False, False, True]:
            transitions.append(ew.record_probe(state, ok, "HTTP 502", now=NOW))
        assert [t for t in transitions if t] == ["down", "recovered", "down", "recovered"]
        assert state.alerts_sent == 2 and state.recoveries_sent == 2

    def test_downtime_formatting(self):
        state = self._state()
        state.down_since = NOW
        assert ew.format_downtime(state, NOW + timedelta(seconds=45)) == "45s"
        assert ew.format_downtime(state, NOW + timedelta(minutes=7)) == "7m"
        assert ew.format_downtime(state, NOW + timedelta(hours=2, minutes=5)) == "2h 5m"
        assert ew.format_downtime(self._state(), NOW) == "unknown"


# ── Probe classification ──────────────────────────────────────────────────────

class TestProbe:
    @pytest.mark.parametrize("code,ok", [(200, True), (204, True), (301, True),
                                         (404, False), (500, False), (502, False)])
    async def test_status_code_classification(self, monkeypatch, code, ok):
        url = "https://meridian.tips"
        client = FakeClient({url: [code]})
        result_ok, detail = await ew.probe(client, url)
        assert result_ok is ok
        assert detail == ("" if ok else f"HTTP {code}")

    async def test_exception_is_a_failure_with_detail(self):
        url = "https://meridian.tips"
        client = FakeClient({url: [TimeoutError("read timed out")]})
        ok, detail = await ew.probe(client, url)
        assert ok is False
        assert "TimeoutError" in detail and "read timed out" in detail


# ── Sweep: probing + email dispatch together ──────────────────────────────────

class TestSweep:
    async def test_healthy_sweep_sends_nothing(self, monkeypatch):
        monkeypatch.setenv("MERIDIAN_EDGE_WATCH_URLS", "https://meridian.tips")
        _install_client(monkeypatch, {"https://meridian.tips": [200]})
        mail = MailSpy().install(monkeypatch)
        assert await ew.run_sweep() == {"https://meridian.tips": None}
        assert mail.down == [] and mail.recovered == []

    async def test_one_alert_at_threshold_then_one_recovery(self, monkeypatch):
        url = "https://canada.meridian.tips"
        monkeypatch.setenv("MERIDIAN_EDGE_WATCH_URLS", url)
        monkeypatch.setenv("MERIDIAN_EDGE_WATCH_EMAIL", "ops@meridian.tips")
        _install_client(monkeypatch, {url: [502, 502, 502, 502, 200, 200]})
        mail = MailSpy().install(monkeypatch)

        for _ in range(6):
            await ew.run_sweep()

        assert len(mail.down) == 1
        assert mail.down[0]["url"] == url
        assert mail.down[0]["to"] == "ops@meridian.tips"
        assert mail.down[0]["detail"] == "HTTP 502"
        assert mail.down[0]["consecutive_failures"] == 3
        assert len(mail.recovered) == 1
        assert mail.recovered[0]["url"] == url

    async def test_surfaces_are_tracked_independently(self, monkeypatch):
        up, down = "https://meridian.tips", "https://canada.meridian.tips"
        monkeypatch.setenv("MERIDIAN_EDGE_WATCH_URLS", f"{up},{down}")
        _install_client(monkeypatch, {up: [200, 200, 200], down: [500, 500, 500]})
        mail = MailSpy().install(monkeypatch)

        for _ in range(3):
            await ew.run_sweep()

        assert [m["url"] for m in mail.down] == [down]
        assert ew._states[up].is_down is False
        assert ew._states[down].is_down is True

    async def test_no_urls_configured_is_a_quiet_noop(self, monkeypatch):
        mail = MailSpy().install(monkeypatch)
        assert await ew.run_sweep() == {}
        assert mail.down == []

    async def test_email_failure_does_not_propagate(self, monkeypatch):
        url = "https://meridian.tips"
        monkeypatch.setenv("MERIDIAN_EDGE_WATCH_URLS", url)
        _install_client(monkeypatch, {url: [500, 500, 500]})
        MailSpy().install(monkeypatch, fail=True)

        for _ in range(3):
            await ew.run_sweep()  # must not raise

        assert ew._states[url].is_down is True

    async def test_removing_a_url_drops_its_state(self, monkeypatch):
        a, b = "https://a.meridian.tips", "https://b.meridian.tips"
        monkeypatch.setenv("MERIDIAN_EDGE_WATCH_URLS", f"{a},{b}")
        _install_client(monkeypatch, {a: [200], b: [200]})
        MailSpy().install(monkeypatch)
        await ew.run_sweep()
        assert set(ew._states) == {a, b}

        monkeypatch.setenv("MERIDIAN_EDGE_WATCH_URLS", a)
        _install_client(monkeypatch, {a: [200]})
        await ew.run_sweep()
        assert set(ew._states) == {a}

    async def test_status_reports_per_surface_health(self, monkeypatch):
        url = "https://meridian.tips"
        monkeypatch.setenv("MERIDIAN_EDGE_WATCH", "1")
        monkeypatch.setenv("MERIDIAN_EDGE_WATCH_URLS", url)
        _install_client(monkeypatch, {url: [503, 503, 503]})
        MailSpy().install(monkeypatch)
        for _ in range(3):
            await ew.run_sweep()

        status = ew.get_watchdog_status()
        assert status["enabled"] is True
        assert status["failure_threshold"] == 3
        surface = status["surfaces"][0]
        assert surface["url"] == url
        assert surface["is_down"] is True
        assert surface["consecutive_failures"] == 3
        assert surface["last_detail"] == "HTTP 503"
        assert surface["alerts_sent"] == 1


# ── Templates ─────────────────────────────────────────────────────────────────

class TestTemplates:
    def test_down_template_carries_the_diagnosis(self):
        from src.email.templates import edge_status

        html = edge_status.render_down(
            url="https://meridian.tips",
            detail="HTTP 502",
            consecutive_failures=3,
            checked_at="2026-08-06T12:00:00+00:00",
        )
        assert "https://meridian.tips" in html
        assert "HTTP 502" in html
        assert "Surface unreachable" in html

    def test_recovered_template_carries_the_downtime(self):
        from src.email.templates import edge_status

        html = edge_status.render_recovered(
            url="https://meridian.tips",
            downtime="15m",
            checked_at="2026-08-06T12:15:00+00:00",
        )
        assert "15m" in html
        assert "Surface recovered" in html
