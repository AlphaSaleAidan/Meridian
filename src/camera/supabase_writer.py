"""
Writes people-counting results to Supabase for the swarm agents.

Target tables (from 20260516_vision_cameras migration):
  vision_traffic — one row per (org, camera, 5-min bucket)
    columns: entries, exits, occupancy_avg, occupancy_peak,
             queue_length_avg, queue_wait_avg_sec, depth_zone_occupancy
  vision_visits — one row per completed visit
    columns: dwell_seconds, zones_visited, converted
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("meridian.camera.writer")


class CameraDataWriter:

    def __init__(self, org_id: str, camera_id: str) -> None:
        self._org_id = org_id
        self._camera_id = camera_id
        self._bucket_start = self._current_bucket()
        self._acc: dict[str, list[int]] = {}
        self._frame_counts: list[int] = []

    @staticmethod
    def _current_bucket() -> datetime:
        now = datetime.now(timezone.utc)
        m = (now.minute // 5) * 5
        return now.replace(minute=m, second=0, microsecond=0)

    def accumulate(self, zone_counts: dict[str, int], total: int) -> None:
        cur = self._current_bucket()
        if cur > self._bucket_start:
            self._flush()
            self._bucket_start = cur
            self._acc = {}
            self._frame_counts = []

        for zid, cnt in zone_counts.items():
            self._acc.setdefault(zid, []).append(cnt)
        self._frame_counts.append(total)

    def _flush(self) -> None:
        if not self._frame_counts:
            return

        avg_occ = sum(self._frame_counts) / len(self._frame_counts)
        peak_occ = max(self._frame_counts)

        zone_occ = {}
        for zid, counts in self._acc.items():
            zone_occ[zid] = {
                "avg": round(sum(counts) / len(counts), 2),
                "max": max(counts),
                "samples": len(counts),
            }

        record = {
            "org_id": self._org_id,
            "camera_id": self._camera_id,
            "bucket": self._bucket_start.isoformat(),
            "occupancy_avg": round(avg_occ, 2),
            "occupancy_peak": peak_occ,
            "depth_zone_occupancy": json.dumps(zone_occ),
        }

        try:
            from ..db import get_db
            db = get_db()
            if db and hasattr(db, "client"):
                db.client.table("vision_traffic").upsert(
                    record, on_conflict="org_id,camera_id,bucket"
                ).execute()
                logger.info("Flushed vision_traffic bucket for %s", self._org_id)
        except Exception as exc:
            logger.error("vision_traffic flush: %s", exc)

    def write_entry_exit(self, entries: int, exits: int) -> None:
        if entries == 0 and exits == 0:
            return

        bucket = self._current_bucket().isoformat()
        try:
            from ..db import get_db
            db = get_db()
            if db and hasattr(db, "client"):
                db.client.rpc("increment_vision_traffic", {
                    "p_org_id": self._org_id,
                    "p_camera_id": self._camera_id,
                    "p_bucket": bucket,
                    "p_entries": entries,
                    "p_exits": exits,
                }).execute()
        except Exception:
            # Fallback: upsert directly
            try:
                from ..db import get_db
                db = get_db()
                if db and hasattr(db, "client"):
                    db.client.table("vision_traffic").upsert({
                        "org_id": self._org_id,
                        "camera_id": self._camera_id,
                        "bucket": bucket,
                        "entries": entries,
                        "exits": exits,
                    }, on_conflict="org_id,camera_id,bucket").execute()
            except Exception as exc:
                logger.error("entry/exit write: %s", exc)

    def write_dwell_records(
        self,
        completions: list[dict[str, Any]],
        zone_configs: dict[str, dict],
    ) -> None:
        if not completions:
            return
        now = datetime.now(timezone.utc).isoformat()
        records = []
        for c in completions:
            zid = c["zone_id"]
            zones = [zone_configs.get(zid, {}).get("name", zid)]
            records.append({
                "org_id": self._org_id,
                "camera_id": self._camera_id,
                "entered_at": now,
                "dwell_seconds": int(c["dwell_seconds"]),
                "zones_visited": zones,
                "converted": False,
            })

        try:
            from ..db import get_db
            db = get_db()
            if db and hasattr(db, "client"):
                db.client.table("vision_visits").insert(records).execute()
        except Exception as exc:
            logger.error("dwell write: %s", exc)

    def write_queue_metrics(
        self,
        queue_length: float,
        wait_seconds: float,
    ) -> None:
        bucket = self._current_bucket().isoformat()
        try:
            from ..db import get_db
            db = get_db()
            if db and hasattr(db, "client"):
                db.client.table("vision_traffic").upsert({
                    "org_id": self._org_id,
                    "camera_id": self._camera_id,
                    "bucket": bucket,
                    "queue_length_avg": round(queue_length, 1),
                    "queue_wait_avg_sec": round(wait_seconds, 1),
                }, on_conflict="org_id,camera_id,bucket").execute()
        except Exception as exc:
            logger.error("queue metrics write: %s", exc)

    def force_flush(self) -> None:
        self._flush()
