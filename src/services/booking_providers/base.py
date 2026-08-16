"""The provider contract — how Meridian talks to a booking tool it doesn't own.

Most merchants already run something. A barbershop has Square Appointments, a
restaurant has an OpenTable page, an owner has a Google Calendar they actually
look at. Replacing that is not on offer and would not be accepted; the phone
agent has to work alongside it.

WHAT A PROVIDER CAN DO IS A PROPERTY OF THE VENDOR, NOT OF OUR AMBITION.
Some vendors publish a self-serve write API. Some publish read-only. Many
publish nothing and gate everything behind a partnership. The Capabilities
record below makes that concrete rather than aspirational, so the portal can
tell a merchant the truth about what connecting will actually do, and so the
engine never attempts a write that was always going to fail.

READ-ONLY IS NOT A CONSOLATION PRIZE. A connection that only imports busy
time still solves the expensive half of the problem: it stops the phone agent
booking a chair that was filled in the merchant's other system. Being unable
to push a booking out costs the merchant one manual entry. Being unable to
read means double-booking a paying customer.

Implementations live beside this file and are resolved through registry.py.
Every one of them must be fail-soft: a provider outage degrades booking to
our own calendar, it never takes the phone line down.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class Capabilities:
    """What this integration can honestly do."""

    # Import the merchant's existing commitments as busy time.
    read_busy: bool = False
    # Push a booking we took into their tool.
    write_booking: bool = False
    # Cancel, in their tool, a booking we pushed.
    cancel_booking: bool = False
    # Tell us when something changes on their side without polling.
    webhooks: bool = False
    # Whether a small platform can obtain credentials without a signed
    # partnership. False here means "do not build this yet, no matter how
    # attractive the logo is".
    self_serve: bool = True
    # Shown to the merchant in the portal, in plain language.
    summary: str = ""


@dataclass(frozen=True)
class BusyBlock:
    """A span in which a resource is not available."""
    starts_at: datetime           # tz-aware
    ends_at: datetime             # tz-aware
    external_id: str
    summary: str = ""
    resource_hint: str = ""       # provider's staff/table id, mapped by config


@dataclass(frozen=True)
class ProviderRef:
    """What the provider called the booking we pushed."""
    provider_booking_id: str
    raw: dict | None = None


class ProviderError(Exception):
    """A provider call failed. Always caught by the sync layer."""


@runtime_checkable
class BookingProvider(Protocol):
    """One merchant's connection to one external booking tool."""

    key: str
    label: str
    capabilities: Capabilities

    async def fetch_busy(self, connection: dict, start: datetime,
                         end: datetime) -> list[BusyBlock]:
        """Their commitments in a window. [] when unsupported."""
        ...

    async def push_booking(self, connection: dict, booking: dict) -> ProviderRef | None:
        """Mirror one of our bookings into their tool. None when unsupported."""
        ...

    async def cancel_booking(self, connection: dict, provider_booking_id: str) -> bool:
        """Cancel a pushed booking on their side. False when unsupported."""
        ...
