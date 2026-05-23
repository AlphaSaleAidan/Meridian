"""
Load zone polygon configs for people counting.

Reads from vision_cameras.zone_config in Supabase.
Falls back to sensible defaults by business type.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("meridian.camera.zone_loader")


def load_zones_for_camera(
    camera_config: dict[str, Any],
    frame_w: int = 1280,
    frame_h: int = 720,
    business_type: str = "restaurant",
) -> list[dict[str, Any]]:
    """Return zone definitions for a camera, falling back to defaults."""
    zone_cfg = camera_config.get("zone_config") or {}

    if isinstance(zone_cfg, dict) and zone_cfg:
        zones = []
        for name, polygon_norm in zone_cfg.items():
            zones.append({
                "zone_id": name,
                "name": name.replace("_", " ").title(),
                "type": _guess_zone_type(name),
                "polygon_coords": [
                    [int(pt[0] * frame_w), int(pt[1] * frame_h)]
                    for pt in polygon_norm
                ],
            })
        if zones:
            return zones

    if isinstance(zone_cfg, list) and zone_cfg:
        zones = []
        for z in zone_cfg:
            if z.get("polygon_coords"):
                zones.append({
                    "zone_id": z.get("zone_id", z.get("name", "zone")),
                    "name": z.get("name", "Zone"),
                    "type": z.get("type", "floor"),
                    "polygon_coords": z["polygon_coords"],
                })
        if zones:
            return zones

    return _default_zones(frame_w, frame_h, business_type)


def load_entry_lines(
    camera_config: dict[str, Any],
    frame_w: int = 1280,
    frame_h: int = 720,
) -> list[dict[str, Any]]:
    """Return entry/exit line configs for a camera."""
    lines = camera_config.get("entry_lines", [])
    if lines:
        result = []
        for line in lines:
            result.append({
                "camera_id": camera_config.get("camera_id", "default"),
                "start": [
                    int(line["start"][0] * frame_w),
                    int(line["start"][1] * frame_h),
                ],
                "end": [
                    int(line["end"][0] * frame_w),
                    int(line["end"][1] * frame_h),
                ],
                "entry_direction": line.get("entry_direction", "in"),
            })
        return result

    # Default: horizontal line at 15% from top
    y = int(frame_h * 0.15)
    return [{
        "camera_id": camera_config.get("camera_id", "default"),
        "start": [0, y],
        "end": [frame_w, y],
        "entry_direction": "in",
    }]


def _guess_zone_type(name: str) -> str:
    n = name.lower()
    if "entrance" in n or "entry" in n or "door" in n:
        return "entrance"
    if "checkout" in n or "register" in n or "counter" in n or "pos" in n:
        return "checkout"
    if "queue" in n or "wait" in n or "line" in n:
        return "queue"
    if "seat" in n or "dining" in n or "table" in n:
        return "seating"
    if "display" in n or "shelf" in n:
        return "display"
    return "floor"


def _default_zones(w: int, h: int, biz: str) -> list[dict[str, Any]]:
    if biz in ("restaurant", "fast_food"):
        return [
            {
                "zone_id": "entrance",
                "name": "Entrance",
                "type": "entrance",
                "polygon_coords": [[0, 0], [w, 0], [w, int(h * 0.2)], [0, int(h * 0.2)]],
            },
            {
                "zone_id": "dining_floor",
                "name": "Dining Floor",
                "type": "seating",
                "polygon_coords": [
                    [0, int(h * 0.2)], [w, int(h * 0.2)],
                    [w, int(h * 0.8)], [0, int(h * 0.8)],
                ],
            },
            {
                "zone_id": "counter",
                "name": "Counter",
                "type": "checkout",
                "polygon_coords": [[0, int(h * 0.8)], [w, int(h * 0.8)], [w, h], [0, h]],
            },
        ]

    if biz == "coffee_shop":
        return [
            {
                "zone_id": "order_counter",
                "name": "Order Counter",
                "type": "checkout",
                "polygon_coords": [[0, int(h * 0.6)], [w, int(h * 0.6)], [w, h], [0, h]],
            },
            {
                "zone_id": "wait_area",
                "name": "Wait Area",
                "type": "queue",
                "polygon_coords": [
                    [0, int(h * 0.3)], [w, int(h * 0.3)],
                    [w, int(h * 0.6)], [0, int(h * 0.6)],
                ],
            },
            {
                "zone_id": "seating",
                "name": "Seating",
                "type": "seating",
                "polygon_coords": [[0, 0], [w, 0], [w, int(h * 0.3)], [0, int(h * 0.3)]],
            },
        ]

    if biz == "auto_shop":
        return [
            {
                "zone_id": "reception",
                "name": "Reception",
                "type": "checkout",
                "polygon_coords": [
                    [0, int(h * 0.7)], [int(w * 0.4), int(h * 0.7)],
                    [int(w * 0.4), h], [0, h],
                ],
            },
            {
                "zone_id": "waiting_area",
                "name": "Waiting Area",
                "type": "seating",
                "polygon_coords": [
                    [int(w * 0.4), int(h * 0.7)], [w, int(h * 0.7)],
                    [w, h], [int(w * 0.4), h],
                ],
            },
            {
                "zone_id": "service_bays",
                "name": "Service Bays",
                "type": "floor",
                "polygon_coords": [[0, 0], [w, 0], [w, int(h * 0.7)], [0, int(h * 0.7)]],
            },
        ]

    # Generic retail / smoke shop
    return [
        {
            "zone_id": "retail_floor",
            "name": "Retail Floor",
            "type": "floor",
            "polygon_coords": [[0, 0], [w, 0], [w, int(h * 0.75)], [0, int(h * 0.75)]],
        },
        {
            "zone_id": "checkout",
            "name": "Checkout",
            "type": "checkout",
            "polygon_coords": [[0, int(h * 0.75)], [w, int(h * 0.75)], [w, h], [0, h]],
        },
    ]
