"""Which booking integrations exist, and the honest truth about each.

This registry is also the product's answer to "can you work with what I
already use?" — so it deliberately carries the tools we CANNOT integrate
alongside the ones we can. A merchant on Booksy should be told plainly that
Booksy publishes no API and shown the calendar path that does work, rather
than being left to assume we simply haven't got round to it.

Findings are from a 2026-08-14 research pass and are dated for that reason:
this landscape moves, and an undated capability claim silently rots into a
lie. Re-verify before relying on any UNAVAILABLE entry — the highest-value
open question is whether Booksy/Vagaro/Fresha sync two-way with Google
Calendar, because if they do, the Google path already reaches them.
"""
from __future__ import annotations

from dataclasses import dataclass

from .base import BookingProvider, Capabilities
from .google_calendar import GoogleCalendarProvider, is_configured as google_configured
from .ics_feed import IcsFeedProvider
from .square_appointments import SquareAppointmentsProvider

_PROVIDERS: dict[str, BookingProvider] = {
    p.key: p for p in (
        SquareAppointmentsProvider(),
        GoogleCalendarProvider(),
        IcsFeedProvider(),
    )
}


def square_configured() -> bool:
    """True when the Square OAuth app credentials exist to authorize against."""
    try:
        from src.config import square as sq_config
        return bool(sq_config.app_id and sq_config.app_secret)
    except Exception:  # noqa: BLE001
        return False


def get_provider(key: str) -> BookingProvider | None:
    return _PROVIDERS.get((key or "").strip().lower())


def available_providers() -> list[dict]:
    """Connections a merchant can actually make right now.

    Google is filtered out when no OAuth client is configured: showing a
    connect button that cannot complete is worse than showing nothing,
    because the merchant reads the failure as our product being broken.
    """
    out = []
    for key, provider in _PROVIDERS.items():
        if key == "google_calendar" and not google_configured():
            continue
        if key == "square_appointments" and not square_configured():
            continue
        cap = provider.capabilities
        out.append({
            "key": key,
            "label": provider.label,
            "summary": cap.summary,
            "read_busy": cap.read_busy,
            "write_booking": cap.write_booking,
            "webhooks": cap.webhooks,
        })
    return out


@dataclass(frozen=True)
class UnavailableTool:
    """A tool merchants ask for that we cannot integrate, and why."""
    key: str
    label: str
    reason: str
    workaround: str


# Verified 2026-08-14. "No public API" means no developer portal was found at
# all — not that one is merely undocumented.
UNAVAILABLE: tuple[UnavailableTool, ...] = (
    UnavailableTool(
        "resy", "Resy",
        "Resy (American Express) publishes no third-party booking API.",
        "Connect the shop's Google Calendar instead, or let us take bookings "
        "directly and keep Resy for walk-up traffic.",
    ),
    UnavailableTool(
        "tock", "Tock",
        "Tock (Squarespace) has no public developer surface.",
        "Same as Resy — use the calendar path.",
    ),
    UnavailableTool(
        "booksy", "Booksy",
        "No public developer portal. Booksy exposes booking to Google's "
        "Reserve programme, not to other platforms.",
        "Connect Google Calendar if Booksy syncs to it, otherwise let us hold "
        "the calendar and keep Booksy for online self-booking.",
    ),
    UnavailableTool(
        "vagaro", "Vagaro",
        "No public developer portal. (Schedulicity is now part of Vagaro — "
        "schedulicity.com redirects there.)",
        "Use the Google Calendar path.",
    ),
    UnavailableTool(
        "fresha", "Fresha",
        "No public developer portal.",
        "Use the Google Calendar path.",
    ),
    UnavailableTool(
        "squire", "Squire",
        "Barbershop platform with no public developer portal.",
        "Use the Google Calendar path.",
    ),
    UnavailableTool(
        "opentable", "OpenTable",
        "Write access exists but only under a signed partner agreement; there "
        "is no self-serve developer portal.",
        "We can read the shop's calendar today. Ask us about OpenTable if it "
        "matters — the partnership takes lead time, not engineering.",
    ),
    UnavailableTool(
        "sevenrooms", "SevenRooms",
        "Partner-gated. The hold-then-confirm flow is documented but "
        "credentials require a commercial agreement.",
        "Same as OpenTable.",
    ),
    UnavailableTool(
        "urable", "Urable / Mobile Tech RX (detailing)",
        "Auto-detailing software runs no developer programme at all.",
        "Detailers should run bookings here directly, with Google Calendar "
        "connected so the owner sees them where they already look.",
    ),
)


def unavailable_tools() -> list[dict]:
    return [
        {"key": t.key, "label": t.label, "reason": t.reason,
         "workaround": t.workaround}
        for t in UNAVAILABLE
    ]
