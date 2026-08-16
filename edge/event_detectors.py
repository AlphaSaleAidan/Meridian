"""Camera EVENT detection, on the edge.

The traffic pipeline answers "how busy was it". This answers "does somebody
need to go and deal with something" — a spill by the machine, a case opened
with nothing sold, four minutes on a handset at the till.

HONESTY ABOUT WHAT THESE ARE. Three of the six are real detections and three
are heuristics:

    phone_use     REAL. YOLO already ships COCO class 67 ("cell phone"). A
                  handset box overlapping a person inside a work zone, held
                  for long enough, is a detection rather than a guess.
    unattended    REAL. Derived from person positions and zones — no new model.
    after_hours   REAL. Motion outside the camera's own active hours.

    spill         HEURISTIC. A persistent, static, non-person change low in the
                  frame. A dropped coat reads the same as a puddle.
    product_loss  HEURISTIC. A persistent change in a shelf zone shortly after
                  somebody stood at it. Cannot see whether it was sold — the
                  POS join happens server-side, later, if at all.
    blocked_exit  HEURISTIC. A static blob overlapping an exit zone for minutes.

The heuristics ship at Aidan's explicit call, knowing the risk: a feed full of
phantom spills is what kills this feature, not a missed one. Three things keep
that survivable and all three are deliberate.

    1. PER-KIND CONFIDENCE. The heuristics report a confidence they can
       actually stand behind (0.55-0.7), the real detections report theirs.
       The server drops anything under its own floor.
    2. PERSISTENCE BEFORE REPORTING. Nothing fires on one frame. A spill has
       to still be there seconds later, which removes almost everything that
       is really a person walking past.
    3. DEDUPE KEYS. One spill is one row no matter how many frames see it.

NOTHING HERE IDENTIFIES ANYONE. Events carry a zone and a duration. There is
no face, no track id, no staff attribution — the API has no column for one.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone

import cv2
import numpy as np

logger = logging.getLogger("meridian.edge.events")

PERSON_CLASS_ID = 0
PHONE_CLASS_ID = 67  # COCO "cell phone"

# How long a thing must persist before it is worth telling anyone about.
# These are the difference between a detector and an alarm that cries wolf.
HOLD_SECONDS = {
    "spill": 25.0,          # a person standing still reads as a blob for a few seconds
    "product_loss": 8.0,    # the shelf must STAY changed after they walk off
    "phone_use": 45.0,      # glancing at a phone is not phone use
    "unattended": 90.0,     # somebody stepping into the back is not abandonment
    "blocked_exit": 180.0,  # a crate being carried through is not an obstruction
    "after_hours": 3.0,     # motion in a closed shop needs no patience
}

# What each detector is willing to claim. The heuristics are quieter on
# purpose — this number is what the merchant sees next to the event.
CONFIDENCE = {
    "spill": 0.58,
    "product_loss": 0.60,
    "phone_use": 0.86,
    "unattended": 0.90,
    "blocked_exit": 0.62,
    "after_hours": 0.88,
}

# Zone names the setup wizard produces, mapped to what each detector watches.
# A camera with none of these zones runs only the detectors that need no zone.
FLOOR_ZONES = ("floor", "dining", "seating", "aisle", "bay", "service_counter")
SHELF_ZONES = ("display", "shelf", "high_value", "impulse", "retail")
EXIT_ZONES = ("exit", "fire_exit", "entrance")
WORK_ZONES = ("checkout", "register", "counter", "service_counter", "prep", "bar")
WAIT_ZONES = ("waiting_area", "queue", "entrance")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _rect(zone: dict, w: int, h: int) -> tuple[int, int, int, int] | None:
    """A zone as integer pixel bounds, accepting normalised or native configs."""
    if not zone:
        return None
    vals = [zone.get(k, 0) for k in ("x1", "y1", "x2", "y2")]
    if all(0 <= v <= 1.0 for v in vals) and any(v > 0 for v in vals):
        x1, y1, x2, y2 = (vals[0] * w, vals[1] * h, vals[2] * w, vals[3] * h)
    else:
        x1, y1, x2, y2 = vals
    x1, y1 = max(0, int(x1)), max(0, int(y1))
    x2, y2 = min(w, int(x2)), min(h, int(y2))
    if x2 - x1 < 8 or y2 - y1 < 8:
        return None
    return x1, y1, x2, y2


def _overlaps(a: tuple, b: tuple) -> bool:
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


class EventDetectors:
    """Per-camera event detection. One instance per CameraProcessor.

    Stateful by necessity: every rule here is about something PERSISTING, and
    persistence cannot be seen in a single frame.
    """

    def __init__(self, camera_id: str, zone_config: dict | None, active_hours: dict | None):
        self.camera_id = camera_id
        self.zones = zone_config or {}
        self.active_hours = active_hours or {"start": "07:00", "end": "22:00"}

        # Background model per watched zone. History is long and the learning
        # rate low: a puddle that sits there for a minute must NOT be absorbed
        # into the background before the hold time elapses.
        self._bg: dict[str, cv2.BackgroundSubtractorMOG2] = {}

        # When each candidate was first seen, keyed by (kind, zone).
        self._first_seen: dict[tuple[str, str], datetime] = {}
        # When we last reported it, so one spill is one event.
        self._last_emitted: dict[tuple[str, str], datetime] = {}

        self._phone_since: dict[str, datetime] = {}
        self._unattended_since: dict[str, datetime] = {}

    # ── zone helpers ────────────────────────────────────────────────────
    def _zones_named(self, names: tuple[str, ...], w: int, h: int) -> dict[str, tuple]:
        out = {}
        for zone_name, zone in self.zones.items():
            if any(n in zone_name.lower() for n in names):
                r = _rect(zone, w, h)
                if r:
                    out[zone_name] = r
        return out

    def _is_open(self, at: datetime) -> bool:
        try:
            start = self.active_hours.get("start", "07:00")
            end = self.active_hours.get("end", "22:00")
            now = at.astimezone().strftime("%H:%M")
            if start <= end:
                return start <= now <= end
            # Crosses midnight (a late bar): open if after start OR before end.
            return now >= start or now <= end
        except Exception:
            return True

    # ── persistence bookkeeping ────────────────────────────────────────
    def _hold(self, kind: str, zone: str, present: bool, at: datetime) -> float | None:
        """Track a candidate. Returns its age in seconds once it qualifies.

        Returns None while it is too young, and clears the moment it stops
        being present — which is what stops a person walking past from
        accumulating toward a spill.
        """
        key = (kind, zone)
        if not present:
            self._first_seen.pop(key, None)
            return None
        first = self._first_seen.setdefault(key, at)
        age = (at - first).total_seconds()
        if age < HOLD_SECONDS.get(kind, 30.0):
            return None
        # Already told them about this one, and it has not gone away.
        last = self._last_emitted.get(key)
        if last and (at - last).total_seconds() < 900:
            return None
        self._last_emitted[key] = at
        return age

    def _event(self, kind: str, zone: str, detail: str, at: datetime,
               duration: float | None = None) -> dict:
        return {
            "kind": kind,
            "zone": zone,
            "detail": detail,
            "detected_at": at.isoformat(),
            "duration_sec": int(duration) if duration else None,
            "confidence": CONFIDENCE.get(kind, 0.6),
            # Stable for the whole 15-minute window, so a detector that keeps
            # firing updates one row instead of creating forty.
            "dedupe_key": f"{self.camera_id}:{kind}:{zone}:{at.strftime('%Y-%m-%dT%H:%M')[:15]}",
        }

    # ── the detectors ───────────────────────────────────────────────────
    def run(self, frame: np.ndarray, person_boxes: list, phone_boxes: list) -> list[dict]:
        """One pass over a frame. Returns zero or more events to report."""
        at = _now()
        h, w = frame.shape[:2]
        events: list[dict] = []

        people = [tuple(int(v) for v in b[:4]) for b in person_boxes]
        phones = [tuple(int(v) for v in b[:4]) for b in phone_boxes]

        try:
            if not self._is_open(at):
                events += self._after_hours(people, at)
                # Everything below is about serving customers. A closed shop
                # has none, and running them would report an unattended
                # counter every night.
                return events

            events += self._phone_use(people, phones, w, h, at)
            events += self._unattended(people, w, h, at)
            events += self._static_blobs(frame, people, w, h, at)
        except Exception as e:  # noqa: BLE001
            # A detector must never take the traffic pipeline down with it.
            logger.debug("event detection failed on %s: %s", self.camera_id, e)

        return events

    def _after_hours(self, people: list, at: datetime) -> list[dict]:
        age = self._hold("after_hours", "premises", bool(people), at)
        if age is None:
            return []
        return [self._event(
            "after_hours", "premises",
            f"{len(people)} person(s) detected with the shop closed.", at, age)]

    def _phone_use(self, people: list, phones: list, w: int, h: int,
                   at: datetime) -> list[dict]:
        """A handset held in a work zone, for long enough to matter.

        The phone must overlap a PERSON as well as the zone: a handset on the
        counter is not somebody using it, and reporting that would be the
        fastest way to lose the merchant's trust in the whole feed.
        """
        work = self._zones_named(WORK_ZONES, w, h)
        if not work or not phones:
            for zone_name in list(self._phone_since):
                self._hold("phone_use", zone_name, False, at)
            return []

        out = []
        for zone_name, rect in work.items():
            held = any(
                _overlaps(p, rect) and any(_overlaps(p, person) for person in people)
                for p in phones
            )
            age = self._hold("phone_use", zone_name, held, at)
            if age is not None:
                out.append(self._event(
                    "phone_use", zone_name,
                    f"Handset in use at the {zone_name} for {int(age // 60)} min.",
                    at, age))
        return out

    def _unattended(self, people: list, w: int, h: int, at: datetime) -> list[dict]:
        """Customers waiting with nobody on the counter.

        Needs BOTH zones to mean anything. Without a waiting area we cannot
        tell an unattended counter from a quiet afternoon, and reporting the
        quiet afternoon is noise.
        """
        work = self._zones_named(WORK_ZONES, w, h)
        wait = self._zones_named(WAIT_ZONES, w, h)
        if not work or not wait:
            return []

        waiting = sum(1 for person in people
                      if any(_overlaps(person, r) for r in wait.values()))
        staffed = any(_overlaps(person, r)
                      for person in people for r in work.values())

        out = []
        for zone_name in work:
            age = self._hold("unattended", zone_name, waiting > 0 and not staffed, at)
            if age is not None:
                out.append(self._event(
                    "unattended", zone_name,
                    f"{waiting} waiting with nobody at the {zone_name} "
                    f"for {int(age // 60)} min.", at, age))
        return out

    def _static_blobs(self, frame: np.ndarray, people: list, w: int, h: int,
                      at: datetime) -> list[dict]:
        """Spills, product loss and blocked exits, from one shared mechanism.

        All three are "something changed in this zone, it is not a person, and
        it is still there". Background subtraction per zone, with every person
        box painted out first — otherwise the detector reports the customer.

        THIS IS THE HEURISTIC HALF of the feature and it is labelled as such:
        a dropped coat and a puddle look identical to it. The confidence it
        reports says so.
        """
        out: list[dict] = []
        targets = [
            ("spill", self._zones_named(FLOOR_ZONES, w, h), 0.012,
             "Persistent change on the floor in {zone} — looks like something spilled."),
            ("product_loss", self._zones_named(SHELF_ZONES, w, h), 0.008,
             "The {zone} display changed and stayed changed, with no sale seen."),
            ("blocked_exit", self._zones_named(EXIT_ZONES, w, h), 0.05,
             "Something is sitting in front of the {zone} and has not moved."),
        ]

        # Paint out people once: every detector below should ignore them.
        mask_people = np.zeros((h, w), dtype=np.uint8)
        for (x1, y1, x2, y2) in people:
            cv2.rectangle(mask_people, (max(0, x1 - 8), max(0, y1 - 8)),
                          (min(w, x2 + 8), min(h, y2 + 8)), 255, -1)

        for kind, zones, min_area_frac, template in targets:
            for zone_name, (x1, y1, x2, y2) in zones.items():
                key = f"{kind}:{zone_name}"
                bg = self._bg.get(key)
                if bg is None:
                    # varThreshold high and shadows off: we want objects that
                    # ARRIVED, not lighting drifting across the afternoon.
                    bg = cv2.createBackgroundSubtractorMOG2(
                        history=900, varThreshold=48, detectShadows=False)
                    self._bg[key] = bg

                crop = frame[y1:y2, x1:x2]
                if crop.size == 0:
                    continue
                fg = bg.apply(crop, learningRate=0.0005)
                fg[mask_people[y1:y2, x1:x2] > 0] = 0
                fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN,
                                      cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))

                area = float(np.count_nonzero(fg)) / float(fg.size or 1)
                age = self._hold(kind, zone_name, area >= min_area_frac, at)
                if age is not None:
                    out.append(self._event(
                        kind, zone_name, template.format(zone=zone_name), at, age))
        return out
