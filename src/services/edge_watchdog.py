"""Edge watchdog — down-alerting for the Contabo-hosted frontend surfaces.

The probe deliberately runs from the Railway backend rather than from the box it
watches: if Contabo goes down, Railway is still up to notice and send the email.

Every sweep GETs each watched URL. A surface is DOWN after FAILURE_THRESHOLD
consecutive failures (non-2xx/3xx or an exception), which sends exactly one
alert; the next success sends exactly one recovery notice. State lives in this
process — Railway runs a single instance, so a restart resets to "up" and the
next real outage re-alerts.

Env:
  MERIDIAN_EDGE_WATCH           "1" to enable — OFF by default
  MERIDIAN_EDGE_WATCH_URLS      comma-separated surfaces to probe
  MERIDIAN_EDGE_WATCH_INTERVAL  seconds between sweeps (default 300)
  MERIDIAN_EDGE_WATCH_EMAIL     recipient (default aidanpierce72@gmail.com)

Started by the FastAPI lifespan handler in app.py.
"""
import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger("meridian.services.edge_watchdog")

FAILURE_THRESHOLD = 3
PROBE_TIMEOUT = 15
DEFAULT_INTERVAL = 300
DEFAULT_EMAIL = "aidanpierce72@gmail.com"

_watch_task: asyncio.Task | None = None
_running = False
_states: dict[str, "SurfaceState"] = {}


@dataclass
class SurfaceState:
    """Per-surface health, carried across sweeps."""

    url: str
    consecutive_failures: int = 0
    is_down: bool = False
    last_detail: str = ""
    down_since: datetime | None = None
    last_checked: datetime | None = None
    alerts_sent: int = 0
    recoveries_sent: int = 0
    history: list[bool] = field(default_factory=list)


def is_enabled() -> bool:
    return os.environ.get("MERIDIAN_EDGE_WATCH", "0") == "1"


def watched_urls() -> list[str]:
    raw = os.environ.get("MERIDIAN_EDGE_WATCH_URLS", "")
    return [u.strip() for u in raw.split(",") if u.strip()]


def alert_recipient() -> str:
    return os.environ.get("MERIDIAN_EDGE_WATCH_EMAIL", "").strip() or DEFAULT_EMAIL


def watch_interval() -> int:
    try:
        return max(30, int(os.environ.get("MERIDIAN_EDGE_WATCH_INTERVAL", DEFAULT_INTERVAL)))
    except ValueError:
        return DEFAULT_INTERVAL


def record_probe(
    state: SurfaceState,
    ok: bool,
    detail: str = "",
    *,
    now: datetime | None = None,
) -> str | None:
    """Fold one probe result into a surface's state.

    Returns "down" or "recovered" only on the sweep that crosses the boundary,
    so the caller sends exactly one email per transition; None otherwise.
    """
    now = now or datetime.now(timezone.utc)
    state.last_checked = now
    state.history = (state.history + [ok])[-20:]

    if ok:
        state.consecutive_failures = 0
        state.last_detail = ""
        if state.is_down:
            state.is_down = False
            state.recoveries_sent += 1
            return "recovered"
        return None

    state.consecutive_failures += 1
    state.last_detail = detail
    if not state.is_down and state.consecutive_failures >= FAILURE_THRESHOLD:
        state.is_down = True
        state.down_since = now
        state.alerts_sent += 1
        return "down"
    return None


def format_downtime(state: SurfaceState, now: datetime) -> str:
    """Human-readable span since the surface first went down."""
    if not state.down_since:
        return "unknown"
    seconds = int((now - state.down_since).total_seconds())
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m"
    hours, minutes = divmod(seconds // 60, 60)
    return f"{hours}h {minutes}m"


async def probe(client, url: str) -> tuple[bool, str]:
    """GET one surface. Any non-2xx/3xx or exception counts as a failure."""
    try:
        resp = await client.get(url, follow_redirects=False)
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"[:300]
    if 200 <= resp.status_code < 400:
        return True, ""
    return False, f"HTTP {resp.status_code}"


async def _notify(transition: str, state: SurfaceState, now: datetime) -> None:
    """Send the one email a transition warrants. Never raises."""
    from ..email.send import send_edge_down_alert, send_edge_recovered_alert

    to = alert_recipient()
    checked_at = now.isoformat()
    try:
        if transition == "down":
            await send_edge_down_alert(
                to=to,
                url=state.url,
                detail=state.last_detail or "no response",
                consecutive_failures=state.consecutive_failures,
                checked_at=checked_at,
            )
            logger.error("[edge-watch] DOWN %s (%s) — alert sent to %s",
                         state.url, state.last_detail, to)
            # DEFCON 2 — a public surface is down: page all responders.
            try:
                from .defcon_alert import notify_defcon
                await notify_defcon(
                    2, f"Surface down: {state.url}",
                    state.last_detail or "no response",
                    protocol="server-down.md",
                    event_key=f"surface-down:{state.url}")
            except Exception as exc:  # noqa: BLE001
                logger.error("[edge-watch] DEFCON page failed: %s", exc)
        else:
            await send_edge_recovered_alert(
                to=to,
                url=state.url,
                downtime=format_downtime(state, now),
                checked_at=checked_at,
            )
            logger.info("[edge-watch] RECOVERED %s — notice sent to %s", state.url, to)
    except Exception as exc:
        logger.error("[edge-watch] Failed to send %s email for %s: %s", transition, state.url, exc)


async def run_sweep() -> dict[str, str | None]:
    """Probe every watched surface once and send any transition emails."""
    import httpx

    urls = watched_urls()
    if not urls:
        logger.warning("[edge-watch] Enabled but MERIDIAN_EDGE_WATCH_URLS is empty")
        return {}

    for url in urls:
        _states.setdefault(url, SurfaceState(url=url))
    for stale in set(_states) - set(urls):
        _states.pop(stale, None)

    transitions: dict[str, str | None] = {}
    now = datetime.now(timezone.utc)
    async with httpx.AsyncClient(timeout=PROBE_TIMEOUT) as client:
        results = await asyncio.gather(*(probe(client, url) for url in urls))

    for url, (ok, detail) in zip(urls, results):
        state = _states[url]
        transition = record_probe(state, ok, detail, now=now)
        transitions[url] = transition
        if transition:
            await _notify(transition, state, now)

    return transitions


async def _watch_loop() -> None:
    global _running
    _running = True
    interval = watch_interval()
    logger.info("[edge-watch] Watching %s every %ds", ", ".join(watched_urls()), interval)

    while _running:
        try:
            await run_sweep()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("[edge-watch] Sweep failed: %s", exc, exc_info=True)
        try:
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            raise


def get_watchdog_status() -> dict:
    """Current state of every watched surface — for /health-style introspection."""
    return {
        "enabled": is_enabled(),
        "running": _running,
        "interval_seconds": watch_interval(),
        "failure_threshold": FAILURE_THRESHOLD,
        "recipient": alert_recipient(),
        "surfaces": [
            {
                "url": s.url,
                "is_down": s.is_down,
                "consecutive_failures": s.consecutive_failures,
                "last_detail": s.last_detail,
                "down_since": s.down_since.isoformat() if s.down_since else None,
                "last_checked": s.last_checked.isoformat() if s.last_checked else None,
                "alerts_sent": s.alerts_sent,
                "recoveries_sent": s.recoveries_sent,
            }
            for s in _states.values()
        ],
    }


def start_edge_watchdog() -> bool:
    """Start the background watcher. Call from app lifespan. Never raises."""
    global _watch_task
    if not is_enabled():
        logger.info("[edge-watch] Disabled (set MERIDIAN_EDGE_WATCH=1 to enable)")
        return False
    if not watched_urls():
        logger.warning("[edge-watch] Enabled but no URLs configured — not starting")
        return False
    if _watch_task is not None:
        return True
    _watch_task = asyncio.create_task(_watch_loop())
    return True


def stop_edge_watchdog() -> None:
    global _running, _watch_task
    _running = False
    if _watch_task:
        _watch_task.cancel()
        _watch_task = None
    logger.info("[edge-watch] Stopped")
