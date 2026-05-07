from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import supervision as sv

logger = logging.getLogger("meridian.camera.line_counter")


@dataclass
class LineConfig:
    camera_id: str
    start: tuple[float, float]
    end: tuple[float, float]
    entry_direction: str = "in"


class EntryExitCounter:

    def __init__(self, line_configs: list[dict[str, Any]]) -> None:
        self._configs: list[LineConfig] = []
        for cfg in line_configs:
            self._configs.append(LineConfig(
                camera_id=cfg["camera_id"],
                start=tuple(cfg["start"]),
                end=tuple(cfg["end"]),
                entry_direction=cfg.get("entry_direction", "in"),
            ))

        self._zones: dict[str, sv.LineZone] = {}
        self._built_for: dict[str, tuple[int, int]] = {}

    def _build_zones(self, camera_id: str, frame_w: int, frame_h: int) -> None:
        cache_key = camera_id
        if cache_key in self._built_for and self._built_for[cache_key] == (frame_w, frame_h):
            return

        for cfg in self._configs:
            if cfg.camera_id != camera_id:
                continue

            start_px = sv.Point(
                x=int(cfg.start[0] * frame_w),
                y=int(cfg.start[1] * frame_h),
            )
            end_px = sv.Point(
                x=int(cfg.end[0] * frame_w),
                y=int(cfg.end[1] * frame_h),
            )
            key = f"{camera_id}:{cfg.start}:{cfg.end}"
            self._zones[key] = sv.LineZone(start=start_px, end=end_px)

        self._built_for[cache_key] = (frame_w, frame_h)

    def process_detections(
        self,
        detections: sv.Detections,
        camera_id: str,
        frame_w: int,
        frame_h: int,
    ) -> dict[str, Any]:
        self._build_zones(camera_id, frame_w, frame_h)

        total_in = 0
        total_out = 0

        for cfg in self._configs:
            if cfg.camera_id != camera_id:
                continue

            key = f"{camera_id}:{cfg.start}:{cfg.end}"
            zone = self._zones.get(key)
            if zone is None:
                continue

            crossed_in, crossed_out = zone.trigger(detections)
            count_in = int(crossed_in.sum())
            count_out = int(crossed_out.sum())

            # Swap if entry_direction is reversed
            if cfg.entry_direction == "out":
                count_in, count_out = count_out, count_in

            total_in += count_in
            total_out += count_out

        return {
            "camera_id": camera_id,
            "entries": total_in,
            "exits": total_out,
            "net": total_in - total_out,
        }
