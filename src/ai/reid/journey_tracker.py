"""
Journey Tracker — Builds per-person zone visit timelines.

Consumes PersonSighting events from the ReID service and assembles
CustomerJourney objects with zone stops, dwell times, and optional
skeletal pose moments (when FreeMoCap is available).
"""
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger("meridian.ai.reid.journey")

JOURNEY_TIMEOUT_SECONDS = 600


@dataclass
class ZoneStop:
    zone_name: str
    enter_time: datetime
    exit_time: datetime | None = None
    dwell_seconds: float = 0.0

    def close(self, exit_at: datetime | None = None):
        self.exit_time = exit_at or datetime.now(timezone.utc)
        self.dwell_seconds = (self.exit_time - self.enter_time).total_seconds()


@dataclass
class SkeletalMoment:
    timestamp: datetime
    pose_landmarks: dict[str, list[float]]
    gesture: str | None = None
    confidence: float = 0.0


@dataclass
class CustomerJourney:
    journey_id: str
    person_id: str
    org_id: str
    entry_time: datetime
    exit_time: datetime | None = None
    zone_stops: list[ZoneStop] = field(default_factory=list)
    skeletal_moments: list[SkeletalMoment] = field(default_factory=list)
    transaction_id: str | None = None
    transaction_total_cents: int | None = None
    cameras_seen: set[str] = field(default_factory=set)
    total_dwell_seconds: float = 0.0
    converted: bool = False

    @property
    def zones_visited(self) -> list[str]:
        return [s.zone_name for s in self.zone_stops]

    @property
    def current_zone(self) -> str | None:
        if self.zone_stops and self.zone_stops[-1].exit_time is None:
            return self.zone_stops[-1].zone_name
        return None

    @property
    def is_active(self) -> bool:
        return self.exit_time is None

    def close(self, exit_at: datetime | None = None):
        self.exit_time = exit_at or datetime.now(timezone.utc)
        for stop in self.zone_stops:
            if stop.exit_time is None:
                stop.close(self.exit_time)
        self.total_dwell_seconds = sum(s.dwell_seconds for s in self.zone_stops)

    def attach_transaction(self, txn_id: str, total_cents: int):
        self.transaction_id = txn_id
        self.transaction_total_cents = total_cents
        self.converted = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "journey_id": self.journey_id,
            "person_id": self.person_id,
            "org_id": self.org_id,
            "entry_time": self.entry_time.isoformat(),
            "exit_time": self.exit_time.isoformat() if self.exit_time else None,
            "zone_stops": [
                {
                    "zone_name": s.zone_name,
                    "enter_time": s.enter_time.isoformat(),
                    "exit_time": s.exit_time.isoformat() if s.exit_time else None,
                    "dwell_seconds": round(s.dwell_seconds, 1),
                }
                for s in self.zone_stops
            ],
            "cameras_seen": list(self.cameras_seen),
            "total_dwell_seconds": round(self.total_dwell_seconds, 1),
            "transaction_id": self.transaction_id,
            "transaction_total_cents": self.transaction_total_cents,
            "converted": self.converted,
            "zones_visited": self.zones_visited,
        }


class JourneyTracker:

    def __init__(self, org_id: str, timeout_seconds: int = JOURNEY_TIMEOUT_SECONDS):
        self._org_id = org_id
        self._timeout = timeout_seconds
        self._active: dict[str, CustomerJourney] = {}
        self._completed: list[CustomerJourney] = []

    @property
    def active_count(self) -> int:
        return len(self._active)

    @property
    def completed_count(self) -> int:
        return len(self._completed)

    def process_sighting(self, person_id: str, camera_id: str, zone: str | None, timestamp: datetime | None = None):
        """Update or create a journey based on a person sighting."""
        ts = timestamp or datetime.now(timezone.utc)

        if person_id in self._active:
            journey = self._active[person_id]
            journey.cameras_seen.add(camera_id)
            self._update_zone(journey, zone, ts)
        else:
            journey = CustomerJourney(
                journey_id=f"j-{uuid.uuid4().hex[:12]}",
                person_id=person_id,
                org_id=self._org_id,
                entry_time=ts,
                cameras_seen={camera_id},
            )
            if zone:
                journey.zone_stops.append(ZoneStop(zone_name=zone, enter_time=ts))
            self._active[person_id] = journey

    def add_skeletal_moment(self, person_id: str, moment: SkeletalMoment):
        if person_id in self._active:
            self._active[person_id].skeletal_moments.append(moment)

    def correlate_transaction(self, txn_id: str, total_cents: int, txn_time: datetime, window_seconds: int = 120) -> str | None:
        """Try to match a POS transaction to an active journey near checkout."""
        best_match = None
        best_score = -1.0

        for pid, journey in self._active.items():
            if journey.converted:
                continue

            time_diff = abs((txn_time - journey.entry_time).total_seconds())
            if time_diff > self._timeout:
                continue

            score = 0.0
            zones = journey.zones_visited
            if "checkout" in zones:
                score += 5.0
            if "browse" in zones:
                score += 1.0
            score += min(journey.total_dwell_seconds / 60, 5.0)

            current = journey.current_zone
            if current == "checkout":
                score += 3.0

            score -= time_diff / 60.0

            if score > best_score:
                best_score = score
                best_match = journey

        if best_match and best_score > 0:
            best_match.attach_transaction(txn_id, total_cents)
            logger.info(
                f"Correlated txn {txn_id} → journey {best_match.journey_id} "
                f"(person={best_match.person_id}, score={best_score:.1f})"
            )
            return best_match.journey_id

        return None

    def flush_stale(self) -> list[CustomerJourney]:
        """Close and archive journeys that have timed out."""
        now = datetime.now(timezone.utc)
        flushed = []

        stale_pids = []
        for pid, journey in self._active.items():
            last_activity = journey.entry_time
            if journey.zone_stops:
                latest_stop = journey.zone_stops[-1]
                last_activity = latest_stop.exit_time or latest_stop.enter_time
            if (now - last_activity).total_seconds() > self._timeout:
                stale_pids.append(pid)

        for pid in stale_pids:
            journey = self._active.pop(pid)
            journey.close(now)
            self._completed.append(journey)
            flushed.append(journey)

        if flushed:
            logger.debug(f"Flushed {len(flushed)} stale journeys")
        return flushed

    def get_active_journeys(self) -> list[CustomerJourney]:
        return list(self._active.values())

    def drain_completed(self) -> list[CustomerJourney]:
        """Return and clear completed journeys for persistence."""
        result = list(self._completed)
        self._completed.clear()
        return result

    def _update_zone(self, journey: CustomerJourney, zone: str | None, ts: datetime):
        if not zone:
            return

        current = journey.current_zone
        if current == zone:
            return

        if journey.zone_stops and journey.zone_stops[-1].exit_time is None:
            journey.zone_stops[-1].close(ts)

        journey.zone_stops.append(ZoneStop(zone_name=zone, enter_time=ts))
