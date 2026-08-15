"""Recurring appointments — "same time, every four weeks".

THE SERIES IS THE INTENTION; THE BOOKINGS ARE REAL ROWS.

That is the one decision everything else follows from. Storing a rule and
computing occurrences at read time is tidier and wrong here, because the
double-booking guarantee is a Postgres exclusion constraint over actual rows.
A virtual occurrence occupies nothing, so the phone agent would cheerfully
sell the same chair to a walk-in and tell both of them yes.

So generation materialises a bounded number of bookings ahead. Each one is an
ordinary booking: it blocks the resource, shows up in the book, and can be
moved or cancelled on its own without touching the series.

WHAT HAPPENS ON A CLASH, which is the question that decides whether merchants
trust this: the series SKIPS. It does not fail, and it never evicts the
booking already there. A regular losing one week is recoverable and a walk-in
being silently cancelled is not — and the skipped date is recorded so a human
can offer them something rather than nobody finding out.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

from src.services import booking_engine as be
from src.services.booking_store import BookingStoreError, SlotTaken, get_booking_store

logger = logging.getLogger("meridian.services.booking_series")

# Never materialise beyond this, whatever a series asks for. A year of rows
# locks a calendar nobody has planned and creates work for a human every time
# one has to move.
MAX_GENERATE_WEEKS = 52


def occurrence_dates(
    series: dict, *, today: date | None = None, weeks: int | None = None,
) -> list[date]:
    """The dates this series wants, inside its generation window.

    Computed from starts_on and the interval rather than from "the last one we
    made", so a series that stopped generating for a month resumes on its own
    rhythm instead of drifting by however long the gap was.
    """
    today = today or datetime.now(timezone.utc).date()
    interval = max(1, int(series.get("interval_weeks") or 4))
    horizon_weeks = min(
        MAX_GENERATE_WEEKS,
        int(weeks if weeks is not None else series.get("generate_weeks") or 12),
    )

    starts_on = _as_date(series.get("starts_on")) or today
    ends_on = _as_date(series.get("ends_on"))
    weekday = int(series.get("weekday") or 0)

    # First occurrence on or after starts_on that falls on the right weekday.
    # Python's weekday() is Monday=0; ours is Sunday=0, matching booking_hours.
    first = starts_on
    while ((first.weekday() + 1) % 7) != weekday:
        first += timedelta(days=1)

    horizon = today + timedelta(weeks=horizon_weeks)
    out: list[date] = []
    cursor = first
    while cursor <= horizon:
        if cursor >= today and (ends_on is None or cursor <= ends_on):
            out.append(cursor)
        cursor += timedelta(weeks=interval)
    return out


class SeriesService:
    def __init__(self):
        self._store = get_booking_store()

    async def generate(
        self, series: dict, setup, *, today: date | None = None,
    ) -> dict:
        """Materialise this series' upcoming occurrences.

        Idempotent: a unique index on (series_id, date) means running twice
        produces one booking per date, so this can be a scheduled sweep without
        bookkeeping.
        """
        if (series.get("status") or "active") != "active":
            return {"created": 0, "skipped": [], "reason": "not active"}

        wanted = occurrence_dates(series, today=today)
        if not wanted:
            return {"created": 0, "skipped": [], "reason": "nothing due"}

        existing = await self._existing_dates(str(series["id"]))
        created = 0
        skipped: list[str] = []

        for day in wanted:
            if day.isoformat() in existing:
                continue
            try:
                await self._create_one(series, setup, day)
                created += 1
            except SlotTaken:
                # The resource is genuinely occupied. Record it and move on —
                # never bump whoever is already there.
                skipped.append(day.isoformat())
                logger.info("series %s skipped %s: slot taken",
                            series.get("id"), day.isoformat())
            except be.NoAvailability:
                skipped.append(day.isoformat())
            except be.BookingClosed:
                # The shop changed its hours after the series was set up. Also
                # a skip, and also worth a human seeing.
                skipped.append(day.isoformat())
            except BookingStoreError as e:
                logger.warning("series %s failed on %s: %s",
                               series.get("id"), day.isoformat(), e)
                skipped.append(day.isoformat())

        await self._record_run(series, skipped)
        return {"created": created, "skipped": skipped}

    async def _create_one(self, series: dict, setup, day: date):
        """One occurrence, placed through the normal engine.

        Deliberately NOT a direct insert: going through reserve() means a
        recurring booking obeys opening hours, pacing, service duration and the
        exclusion constraint exactly like every other booking. A series that
        could bypass those would be a hole straight through the guarantee.
        """
        local_time = _as_time(series.get("local_time"))
        starts_at = datetime.combine(day, local_time).replace(tzinfo=setup.tz)

        return await be.reserve(
            setup,
            starts_at.astimezone(timezone.utc),
            int(series.get("party_size") or 1),
            series.get("customer_name") or "",
            customer_phone=series.get("customer_phone"),
            customer_email=series.get("customer_email"),
            notes=series.get("notes"),
            service_id=series.get("service_id"),
            source="portal",
            extra={
                "series_id": str(series["id"]),
                # Honour the preferred resource when the merchant insisted;
                # otherwise let the engine seat them wherever fits, because a
                # regular would rather see somebody else than lose the week.
                **({"resource_id": series.get("resource_id")}
                   if series.get("resource_strict") and series.get("resource_id") else {}),
            },
        )

    async def _existing_dates(self, series_id: str) -> set[str]:
        rows = await self._store._req(
            "GET", "bookings",
            params={
                "series_id": f"eq.{series_id}",
                "status": "in.(offered,confirmed,seated,completed)",
                "select": "starts_at",
                "limit": "500",
            },
        )
        return {str(r.get("starts_at", ""))[:10] for r in rows or []}

    async def _record_run(self, series: dict, skipped: list[str]) -> None:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        fields: dict = {"last_generated_at": now}
        if skipped:
            # Union rather than overwrite: a date skipped last week is still a
            # week that customer never got.
            previous = set(series.get("skipped_dates") or [])
            fields["skipped_dates"] = sorted(previous | set(skipped))
        try:
            await self._store._req(
                "PATCH", "booking_series",
                params={"id": f"eq.{series['id']}"},
                json=fields,
                prefer="return=minimal",
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("could not record series run for %s: %s", series.get("id"), e)

    async def cancel(self, series_id: str, *, future_only: bool = True) -> dict:
        """Stop a series. Past visits stay; upcoming ones are released.

        future_only is the default and the safe one: cancelling somebody's
        standing appointment must not erase the haircuts they already had.
        """
        await self._store._req(
            "PATCH", "booking_series",
            params={"id": f"eq.{series_id}"},
            json={"status": "cancelled"},
            prefer="return=minimal",
        )

        cutoff = datetime.now(timezone.utc).isoformat(timespec="seconds")
        params = {
            "series_id": f"eq.{series_id}",
            "status": "in.(offered,confirmed)",
            "select": "id,starts_at",
            "limit": "500",
        }
        if future_only:
            params["starts_at"] = f"gte.{cutoff}"
        rows = await self._store._req("GET", "bookings", params=params)

        released = 0
        for row in rows or []:
            try:
                await self._store.cancel_booking(str(row["id"]), reason="series cancelled")
                released += 1
            except Exception as e:  # noqa: BLE001
                logger.warning("could not release %s: %s", row.get("id"), e)
        return {"cancelled": True, "released": released}


def _as_date(value) -> date | None:
    if not value:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value)[:10]).date()
    except ValueError:
        return None


def _as_time(value):
    from datetime import time as _time
    if isinstance(value, _time):
        return value
    text = str(value or "09:00")[:8]
    parts = text.split(":")
    try:
        return _time(int(parts[0]), int(parts[1]) if len(parts) > 1 else 0)
    except (ValueError, IndexError):
        return _time(9, 0)


_service: SeriesService | None = None


def get_series_service() -> SeriesService:
    global _service
    if _service is None:
        _service = SeriesService()
    return _service
