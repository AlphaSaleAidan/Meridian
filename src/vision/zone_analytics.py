"""
ZoneAnalytics — Supervision-based spatial intelligence.

Defines zone polygons (sidewalk, entrance, bar, tables, menu_board),
detects zone crossings, tracks dwell time per person per zone,
generates heatmaps, and computes passerby/walk-in/conversion stats.
"""
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum

import numpy as np

logger = logging.getLogger("meridian.vision.zones")


class ZoneType(Enum):
    SIDEWALK = "sidewalk"
    ENTRANCE = "entrance"
    BAR = "bar"
    TABLES = "tables"
    MENU_BOARD = "menu_board"
    CHECKOUT = "checkout"
    BROWSE = "browse"
    CUSTOM = "custom"


@dataclass
class Zone:
    name: str
    zone_type: ZoneType
    polygon: list[tuple[float, float]]

    def contains(self, x: float, y: float) -> bool:
        n = len(self.polygon)
        if n < 3:
            return False
        inside = False
        j = n - 1
        for i in range(n):
            xi, yi = self.polygon[i]
            xj, yj = self.polygon[j]
            if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                inside = not inside
            j = i
        return inside


@dataclass
class ZoneCrossing:
    track_id: int
    from_zone: str
    to_zone: str
    timestamp: float


@dataclass
class ZoneDwell:
    track_id: int
    zone_name: str
    entered_at: float
    exited_at: float | None = None

    @property
    def duration_sec(self) -> float:
        if self.exited_at is None:
            return time.time() - self.entered_at
        return self.exited_at - self.entered_at


@dataclass
class PasserbyStats:
    total_passersby: int = 0
    window_shoppers: int = 0
    walk_ins: int = 0
    conversion_rate: float = 0.0
    avg_dwell_before_entry_sec: float = 0.0


class ZoneAnalytics:

    def __init__(self, zone_config: dict | None = None):
        self._zones: list[Zone] = []
        self._track_zones: dict[int, str | None] = {}
        self._crossings: list[ZoneCrossing] = []
        self._dwells: dict[int, dict[str, ZoneDwell]] = defaultdict(dict)
        self._heatmap_points: list[tuple[float, float]] = []
        self._sidewalk_tracks: set[int] = set()
        self._entrance_tracks: set[int] = set()

        if zone_config:
            self.load_zones(zone_config)

    def load_zones(self, config: dict):
        self._zones.clear()
        for name, spec in config.items():
            if isinstance(spec, dict) and "polygon" in spec:
                pts = [(p[0], p[1]) for p in spec["polygon"]]
                zone_type = self._infer_type(name)
                self._zones.append(Zone(name=name, zone_type=zone_type, polygon=pts))
            elif isinstance(spec, dict) and "x1" in spec:
                x1, y1 = spec["x1"], spec["y1"]
                x2, y2 = spec["x2"], spec["y2"]
                pts = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
                zone_type = self._infer_type(name)
                self._zones.append(Zone(name=name, zone_type=zone_type, polygon=pts))
        logger.info("Loaded %d zones: %s", len(self._zones), [z.name for z in self._zones])

    def _infer_type(self, name: str) -> ZoneType:
        name_lower = name.lower()
        for zt in ZoneType:
            if zt.value in name_lower:
                return zt
        return ZoneType.CUSTOM

    def update(self, tracks: list) -> list[ZoneCrossing]:
        now = time.time()
        new_crossings = []

        for track in tracks:
            cx, cy = track.center
            self._heatmap_points.append((cx, cy))

            current_zone = None
            for zone in self._zones:
                if zone.contains(cx, cy):
                    current_zone = zone.name
                    break

            prev_zone = self._track_zones.get(track.track_id)

            if current_zone != prev_zone:
                if prev_zone and prev_zone in self._dwells.get(track.track_id, {}):
                    self._dwells[track.track_id][prev_zone].exited_at = now

                if current_zone:
                    self._dwells[track.track_id][current_zone] = ZoneDwell(
                        track_id=track.track_id,
                        zone_name=current_zone,
                        entered_at=now,
                    )

                if prev_zone is not None and current_zone is not None:
                    crossing = ZoneCrossing(
                        track_id=track.track_id,
                        from_zone=prev_zone,
                        to_zone=current_zone,
                        timestamp=now,
                    )
                    self._crossings.append(crossing)
                    new_crossings.append(crossing)

            self._track_zones[track.track_id] = current_zone

            if current_zone:
                zone_obj = next((z for z in self._zones if z.name == current_zone), None)
                if zone_obj and zone_obj.zone_type == ZoneType.SIDEWALK:
                    self._sidewalk_tracks.add(track.track_id)
                elif zone_obj and zone_obj.zone_type == ZoneType.ENTRANCE:
                    self._entrance_tracks.add(track.track_id)

        return new_crossings

    def get_dwell_times(self) -> dict[str, list[float]]:
        result: dict[str, list[float]] = defaultdict(list)
        for track_dwells in self._dwells.values():
            for zone_name, dwell in track_dwells.items():
                if dwell.duration_sec > 1.0:
                    result[zone_name].append(dwell.duration_sec)
        return dict(result)

    def get_avg_dwell(self, zone_name: str) -> float:
        dwells = self.get_dwell_times().get(zone_name, [])
        if not dwells:
            return 0.0
        return sum(dwells) / len(dwells)

    def get_zone_counts(self) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for zone_name in self._track_zones.values():
            if zone_name:
                counts[zone_name] += 1
        return dict(counts)

    def get_crossings(
        self, from_zone: str | None = None, to_zone: str | None = None
    ) -> list[ZoneCrossing]:
        result = self._crossings
        if from_zone:
            result = [c for c in result if c.from_zone == from_zone]
        if to_zone:
            result = [c for c in result if c.to_zone == to_zone]
        return result

    def get_passerby_stats(self) -> PasserbyStats:
        total = len(self._sidewalk_tracks)
        walk_ins = len(self._sidewalk_tracks & self._entrance_tracks)
        window_shoppers = total - walk_ins

        sidewalk_dwells = self.get_dwell_times().get("sidewalk", [])
        walk_in_ids = self._sidewalk_tracks & self._entrance_tracks
        pre_entry_dwells = []
        for tid in walk_in_ids:
            if tid in self._dwells and "sidewalk" in self._dwells[tid]:
                pre_entry_dwells.append(self._dwells[tid]["sidewalk"].duration_sec)

        return PasserbyStats(
            total_passersby=total,
            window_shoppers=window_shoppers,
            walk_ins=walk_ins,
            conversion_rate=walk_ins / max(total, 1),
            avg_dwell_before_entry_sec=(
                sum(pre_entry_dwells) / len(pre_entry_dwells) if pre_entry_dwells else 0.0
            ),
        )

    def generate_heatmap(self, width: int, height: int, cell_size: int = 20) -> np.ndarray:
        cols = width // cell_size
        rows = height // cell_size
        grid = np.zeros((rows, cols), dtype=np.float32)
        for x, y in self._heatmap_points:
            col = min(int(x / cell_size), cols - 1)
            row = min(int(y / cell_size), rows - 1)
            if 0 <= row < rows and 0 <= col < cols:
                grid[row, col] += 1
        if grid.max() > 0:
            grid /= grid.max()
        return grid

    def get_flow_matrix(self) -> dict[str, dict[str, int]]:
        matrix: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for crossing in self._crossings:
            matrix[crossing.from_zone][crossing.to_zone] += 1
        return {k: dict(v) for k, v in matrix.items()}

    def get_zone_journey(self, track_id: int) -> list[str]:
        journey = []
        for crossing in self._crossings:
            if crossing.track_id == track_id:
                if not journey:
                    journey.append(crossing.from_zone)
                journey.append(crossing.to_zone)
        return journey

    def to_metrics(self) -> dict:
        dwell_times = self.get_dwell_times()
        passerby = self.get_passerby_stats()
        return {
            "zone_counts": self.get_zone_counts(),
            "avg_dwell_by_zone": {
                k: round(sum(v) / len(v), 1) for k, v in dwell_times.items() if v
            },
            "total_crossings": len(self._crossings),
            "flow_matrix": self.get_flow_matrix(),
            "passerby": {
                "total": passerby.total_passersby,
                "window_shoppers": passerby.window_shoppers,
                "walk_ins": passerby.walk_ins,
                "conversion_rate": round(passerby.conversion_rate, 3),
                "avg_dwell_before_entry_sec": round(passerby.avg_dwell_before_entry_sec, 1),
            },
            "unique_tracks": len(self._track_zones),
        }

    def reset(self):
        self._track_zones.clear()
        self._crossings.clear()
        self._dwells.clear()
        self._heatmap_points.clear()
        self._sidewalk_tracks.clear()
        self._entrance_tracks.clear()
