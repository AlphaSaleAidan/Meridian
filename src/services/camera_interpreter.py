"""
Camera intelligence interpreter — aggregates heatmap, gesture, and
traffic data into structured metrics the AI swarm can consume.
"""
import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("meridian.services.camera_interpreter")

DB_PATH = Path("data/vision_metrics.db")

ZONE_TYPES = {
    "entrance": "Primary entrance / exit point",
    "checkout": "Point of sale / register area",
    "display": "Product display / merchandise zone",
    "waiting_area": "Customer waiting / queue zone",
    "service_counter": "Service delivery area",
    "high_value": "Premium product display zone",
    "impulse": "Impulse purchase zone near checkout",
    "seating": "Dine-in / seating area",
}

GESTURE_PURCHASE_SIGNAL = {
    "reaching": 0.7,
    "browsing": 0.5,
    "pointing": 0.4,
    "carrying": 0.8,
    "waiting": 0.2,
    "walking": 0.1,
}


class CameraInterpreter:

    def __init__(self):
        self._init_db()

    def _init_db(self):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(str(DB_PATH))
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("""
            CREATE TABLE IF NOT EXISTS traffic_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id TEXT NOT NULL,
                camera_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                entries INTEGER DEFAULT 0,
                exits INTEGER DEFAULT 0,
                zone_occupancy_json TEXT
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS gesture_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id TEXT NOT NULL,
                camera_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                gesture TEXT NOT NULL,
                confidence REAL DEFAULT 0,
                zone TEXT
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS hourly_aggregates (
                org_id TEXT NOT NULL,
                hour TEXT NOT NULL,
                total_entries INTEGER DEFAULT 0,
                total_exits INTEGER DEFAULT 0,
                avg_dwell_seconds REAL DEFAULT 0,
                gesture_counts_json TEXT,
                zone_metrics_json TEXT,
                PRIMARY KEY (org_id, hour)
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS heatmap_data (
                org_id TEXT NOT NULL,
                camera_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                zone_name TEXT NOT NULL,
                avg_dwell_seconds REAL DEFAULT 0,
                visit_count INTEGER DEFAULT 0,
                conversion_pct REAL DEFAULT 0,
                PRIMARY KEY (org_id, camera_id, timestamp, zone_name)
            )
        """)
        con.commit()
        con.close()

    def _conn(self) -> sqlite3.Connection:
        con = sqlite3.connect(str(DB_PATH))
        con.row_factory = sqlite3.Row
        return con

    def ingest_traffic_snapshot(self, org_id: str, camera_id: str, snapshot: dict):
        ts = snapshot.get("timestamp", datetime.now(timezone.utc).isoformat())
        con = self._conn()
        con.execute(
            "INSERT INTO traffic_snapshots (org_id, camera_id, timestamp, entries, exits, zone_occupancy_json) VALUES (?,?,?,?,?,?)",
            (org_id, camera_id, ts, snapshot.get("entries", 0), snapshot.get("exits", 0),
             json.dumps(snapshot.get("zone_occupancy", {}))),
        )
        con.commit()
        con.close()

    def ingest_gesture_data(self, org_id: str, camera_id: str, gestures: list[dict]):
        con = self._conn()
        for g in gestures:
            con.execute(
                "INSERT INTO gesture_events (org_id, camera_id, timestamp, gesture, confidence, zone) VALUES (?,?,?,?,?,?)",
                (org_id, camera_id, g.get("timestamp", datetime.now(timezone.utc).isoformat()),
                 g["gesture"], g.get("confidence", 0), g.get("zone")),
            )
        con.commit()
        con.close()
        logger.info("Ingested %d gesture events for %s", len(gestures), org_id)

    def ingest_heatmap(self, org_id: str, camera_id: str, heatmap_data: dict[str, dict]):
        ts = datetime.now(timezone.utc).isoformat()
        con = self._conn()
        for zone_name, metrics in heatmap_data.items():
            con.execute(
                "INSERT OR REPLACE INTO heatmap_data VALUES (?,?,?,?,?,?,?)",
                (org_id, camera_id, ts, zone_name,
                 metrics.get("avg_dwell_seconds", 0),
                 metrics.get("visit_count", 0),
                 metrics.get("conversion_pct", 0)),
            )
        con.commit()
        con.close()

    def aggregate_hourly(self, org_id: str, hour_start: str, hour_end: str) -> dict:
        con = self._conn()

        traffic = con.execute(
            "SELECT COALESCE(SUM(entries),0) as ent, COALESCE(SUM(exits),0) as ext FROM traffic_snapshots WHERE org_id=? AND timestamp>=? AND timestamp<?",
            (org_id, hour_start, hour_end),
        ).fetchone()

        gestures = con.execute(
            "SELECT gesture, COUNT(*) as cnt FROM gesture_events WHERE org_id=? AND timestamp>=? AND timestamp<? GROUP BY gesture",
            (org_id, hour_start, hour_end),
        ).fetchall()
        gesture_counts = {g["gesture"]: g["cnt"] for g in gestures}

        heatmaps = con.execute(
            "SELECT zone_name, AVG(avg_dwell_seconds) as dwell, SUM(visit_count) as visits, AVG(conversion_pct) as conv "
            "FROM heatmap_data WHERE org_id=? AND timestamp>=? AND timestamp<? GROUP BY zone_name",
            (org_id, hour_start, hour_end),
        ).fetchall()
        zone_metrics = {
            h["zone_name"]: {"avg_dwell": round(h["dwell"], 1), "visits": h["visits"], "conversion_pct": round(h["conv"], 1)}
            for h in heatmaps
        }

        avg_dwell = sum(z["avg_dwell"] for z in zone_metrics.values()) / len(zone_metrics) if zone_metrics else 0

        agg = {
            "org_id": org_id,
            "hour": hour_start,
            "total_entries": traffic["ent"],
            "total_exits": traffic["ext"],
            "avg_dwell_seconds": round(avg_dwell, 1),
            "gesture_counts": gesture_counts,
            "zone_metrics": zone_metrics,
        }

        con.execute(
            "INSERT OR REPLACE INTO hourly_aggregates VALUES (?,?,?,?,?,?,?)",
            (org_id, hour_start, agg["total_entries"], agg["total_exits"],
             agg["avg_dwell_seconds"], json.dumps(gesture_counts), json.dumps(zone_metrics)),
        )
        con.commit()
        con.close()
        return agg

    def generate_vision_insights(self, org_id: str, pos_transaction_count: int = 0) -> dict:
        con = self._conn()

        total_traffic = con.execute(
            "SELECT COALESCE(SUM(total_entries),0) as total FROM hourly_aggregates WHERE org_id=?",
            (org_id,),
        ).fetchone()
        total_entries = total_traffic["total"] if total_traffic else 0

        conversion_rate = round(pos_transaction_count / total_entries * 100, 1) if total_entries > 0 else 0

        peak_hours = con.execute(
            "SELECT hour, total_entries FROM hourly_aggregates WHERE org_id=? ORDER BY total_entries DESC LIMIT 5",
            (org_id,),
        ).fetchall()

        zone_rows = con.execute(
            "SELECT zone_name, AVG(avg_dwell_seconds) as dwell, SUM(visit_count) as visits, AVG(conversion_pct) as conv "
            "FROM heatmap_data WHERE org_id=? GROUP BY zone_name ORDER BY conv DESC",
            (org_id,),
        ).fetchall()

        gesture_totals = con.execute(
            "SELECT gesture, COUNT(*) as cnt FROM gesture_events WHERE org_id=? GROUP BY gesture ORDER BY cnt DESC",
            (org_id,),
        ).fetchall()

        browsing = sum(g["cnt"] for g in gesture_totals if g["gesture"] in ("browsing", "reaching"))
        carrying = sum(g["cnt"] for g in gesture_totals if g["gesture"] == "carrying")
        browse_to_purchase = round(carrying / browsing * 100, 1) if browsing > 0 else 0

        # queue impact: count waiting gestures, estimate walkaway cost
        waiting_count = sum(g["cnt"] for g in gesture_totals if g["gesture"] == "waiting")
        est_walkaway_pct = 0.15
        avg_ticket_cents = 1200
        queue_revenue_lost = int(waiting_count * est_walkaway_pct * avg_ticket_cents)

        con.close()

        return {
            "conversion_rate": conversion_rate,
            "total_foot_traffic": total_entries,
            "pos_transactions": pos_transaction_count,
            "peak_traffic_hours": [{"hour": h["hour"], "entries": h["total_entries"]} for h in peak_hours],
            "zone_performance": [
                {"zone": z["zone_name"], "avg_dwell_sec": round(z["dwell"], 1),
                 "visits": z["visits"], "conversion_pct": round(z["conv"], 1)}
                for z in zone_rows
            ],
            "gesture_signals": {
                "browse_to_purchase_pct": browse_to_purchase,
                "total_browsing": browsing,
                "total_carrying": carrying,
                "totals": {g["gesture"]: g["cnt"] for g in gesture_totals},
            },
            "queue_impact": {
                "waiting_events": waiting_count,
                "est_walkaway_pct": est_walkaway_pct,
                "est_revenue_lost_cents": queue_revenue_lost,
            },
        }

    def get_swarm_context(self, org_id: str, pos_transaction_count: int = 0) -> dict:
        insights = self.generate_vision_insights(org_id, pos_transaction_count)
        return {
            "source": "camera_interpreter",
            "org_id": org_id,
            "vision_intelligence": insights,
            "available_zones": list(ZONE_TYPES.keys()),
            "gesture_labels": list(GESTURE_PURCHASE_SIGNAL.keys()),
        }
