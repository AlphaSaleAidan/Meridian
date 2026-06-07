"""
Weather correlation service — Open-Meteo (free, no API key).

Fetches historical + forecast weather, correlates with daily revenue,
and produces weather-aware insights for the AI engine.
"""
import json
import logging
import os
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger("meridian.services.weather")

DEFAULT_LAT = float(os.getenv("MERIDIAN_LAT", "25.7617"))
DEFAULT_LON = float(os.getenv("MERIDIAN_LON", "-80.1918"))
DB_PATH = Path(os.getenv("WEATHER_DB_PATH", "data/weather.db"))

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

DAILY_PARAMS = "temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max,weathercode"

WMO_WEATHER_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Depositing rime fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    56: "Light freezing drizzle", 57: "Dense freezing drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    66: "Light freezing rain", 67: "Heavy freezing rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
    77: "Snow grains", 80: "Slight rain showers", 81: "Moderate rain showers",
    82: "Violent rain showers", 85: "Slight snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail",
}

RAIN_CODES = {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99}
SEVERE_CODES = {65, 67, 75, 82, 86, 95, 96, 99}


def _pearson(x: list[float], y: list[float]) -> float:
    n = len(x)
    if n < 3:
        return 0.0
    try:
        import numpy as np
        r = np.corrcoef(x, y)[0, 1]
        return 0.0 if np.isnan(r) else float(r)
    except ImportError:
        pass
    mx, my = sum(x) / n, sum(y) / n
    num = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    dx = sum((xi - mx) ** 2 for xi in x) ** 0.5
    dy = sum((yi - my) ** 2 for yi in y) ** 0.5
    return num / (dx * dy) if dx * dy > 0 else 0.0


class WeatherService:

    def __init__(self, lat: float = DEFAULT_LAT, lon: float = DEFAULT_LON):
        self.lat = lat
        self.lon = lon
        self._init_db()

    def _init_db(self):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(str(DB_PATH))
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("""
            CREATE TABLE IF NOT EXISTS weather_observations (
                org_id TEXT NOT NULL,
                date TEXT NOT NULL,
                temp_max REAL, temp_min REAL,
                precipitation REAL, windspeed_max REAL,
                weathercode INTEGER,
                PRIMARY KEY (org_id, date)
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS weather_correlations (
                org_id TEXT NOT NULL,
                computed_at TEXT NOT NULL,
                rain_impact_pct REAL,
                temp_sweet_spot_min REAL, temp_sweet_spot_max REAL,
                worst_weather_code INTEGER,
                correlations_json TEXT,
                PRIMARY KEY (org_id)
            )
        """)
        con.commit()
        con.close()

    def _conn(self) -> sqlite3.Connection:
        con = sqlite3.connect(str(DB_PATH))
        con.row_factory = sqlite3.Row
        return con

    async def fetch_forecast(self, lat: float | None = None, lon: float | None = None, days: int = 7) -> list[dict]:
        import httpx
        params = {
            "latitude": lat or self.lat,
            "longitude": lon or self.lon,
            "daily": DAILY_PARAMS,
            "forecast_days": min(days, 16),
            "timezone": "auto",
        }
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(FORECAST_URL, params=params)
            if resp.status_code != 200:
                logger.warning("Open-Meteo forecast returned %d", resp.status_code)
                return []
            return self._parse_daily_response(resp.json())

    async def fetch_historical(self, start_date: str, end_date: str, lat: float | None = None, lon: float | None = None) -> list[dict]:
        import httpx
        params = {
            "latitude": lat or self.lat,
            "longitude": lon or self.lon,
            "daily": DAILY_PARAMS,
            "start_date": start_date,
            "end_date": end_date,
            "timezone": "auto",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(ARCHIVE_URL, params=params)
            if resp.status_code != 200:
                logger.warning("Open-Meteo archive returned %d", resp.status_code)
                return []
            return self._parse_daily_response(resp.json())

    def _parse_daily_response(self, data: dict) -> list[dict]:
        daily = data.get("daily", {})
        dates = daily.get("time", [])
        rows = []
        for i, d in enumerate(dates):
            rows.append({
                "date": d,
                "temp_max": daily.get("temperature_2m_max", [None])[i],
                "temp_min": daily.get("temperature_2m_min", [None])[i],
                "precipitation": daily.get("precipitation_sum", [0])[i],
                "windspeed_max": daily.get("windspeed_10m_max", [None])[i],
                "weathercode": daily.get("weathercode", [0])[i],
            })
        return rows

    def store_observations(self, org_id: str, observations: list[dict]):
        con = self._conn()
        for obs in observations:
            con.execute(
                "INSERT OR REPLACE INTO weather_observations VALUES (?,?,?,?,?,?,?)",
                (org_id, obs["date"], obs.get("temp_max"), obs.get("temp_min"),
                 obs.get("precipitation", 0), obs.get("windspeed_max"), obs.get("weathercode", 0)),
            )
        con.commit()
        con.close()
        logger.info("Stored %d weather observations for %s", len(observations), org_id)

    def correlate_with_revenue(self, org_id: str, daily_revenue: list[dict]) -> dict:
        """daily_revenue: list of {date, revenue_cents}"""
        rev_map = {r["date"]: r["revenue_cents"] for r in daily_revenue}
        con = self._conn()
        rows = con.execute(
            "SELECT * FROM weather_observations WHERE org_id = ? ORDER BY date", (org_id,)
        ).fetchall()
        con.close()

        paired: list[dict] = []
        for r in rows:
            if r["date"] in rev_map:
                paired.append({**dict(r), "revenue": rev_map[r["date"]]})

        if len(paired) < 7:
            return {"error": "insufficient_data", "paired_days": len(paired)}

        revenues = [p["revenue"] for p in paired]
        correlations = {
            "precipitation": _pearson([p["precipitation"] or 0 for p in paired], revenues),
            "temp_max": _pearson([p["temp_max"] or 0 for p in paired], revenues),
            "temp_min": _pearson([p["temp_min"] or 0 for p in paired], revenues),
            "windspeed": _pearson([p["windspeed_max"] or 0 for p in paired], revenues),
        }

        rain_days = [p for p in paired if (p["precipitation"] or 0) > 0.1]
        dry_days = [p for p in paired if (p["precipitation"] or 0) <= 0.1]
        rain_avg = sum(p["revenue"] for p in rain_days) / len(rain_days) if rain_days else 0
        dry_avg = sum(p["revenue"] for p in dry_days) / len(dry_days) if dry_days else 0
        rain_impact_pct = round((rain_avg - dry_avg) / dry_avg * 100, 1) if dry_avg else 0

        # temperature sweet spot — find 5°F range with highest avg revenue
        temp_buckets: dict[int, list[float]] = {}
        for p in paired:
            if p["temp_max"] is not None:
                bucket = int(p["temp_max"] // 5) * 5
                temp_buckets.setdefault(bucket, []).append(p["revenue"])
        best_bucket = max(temp_buckets, key=lambda b: sum(temp_buckets[b]) / len(temp_buckets[b])) if temp_buckets else 75

        code_buckets: dict[int, list[float]] = {}
        for p in paired:
            code_buckets.setdefault(p["weathercode"] or 0, []).append(p["revenue"])
        worst_code = min(code_buckets, key=lambda c: sum(code_buckets[c]) / len(code_buckets[c])) if code_buckets else 0

        result = {
            "rain_impact_pct": rain_impact_pct,
            "temp_sweet_spot": {"min": best_bucket, "max": best_bucket + 5},
            "worst_weather_code": worst_code,
            "worst_weather_label": WMO_WEATHER_CODES.get(worst_code, "Unknown"),
            "correlations": correlations,
            "paired_days": len(paired),
        }

        con = self._conn()
        con.execute(
            "INSERT OR REPLACE INTO weather_correlations VALUES (?,?,?,?,?,?,?)",
            (org_id, datetime.utcnow().isoformat(), rain_impact_pct,
             best_bucket, best_bucket + 5, worst_code, json.dumps(correlations)),
        )
        con.commit()
        con.close()

        return result

    async def get_weather_insights(self, org_id: str, daily_revenue: list[dict] | None = None) -> dict:
        try:
            forecast = await self.fetch_forecast()
        except Exception as e:
            logger.warning("Failed to fetch forecast: %s", e)
            forecast = []

        forecast_alerts = []
        for day in forecast:
            code = day.get("weathercode", 0)
            precip = day.get("precipitation", 0)
            if code in SEVERE_CODES or precip > 10:
                forecast_alerts.append({
                    "date": day["date"],
                    "condition": WMO_WEATHER_CODES.get(code, "Unknown"),
                    "precipitation_mm": precip,
                    "severity": "severe" if code in SEVERE_CODES else "moderate",
                })
            elif code in RAIN_CODES or precip > 2:
                forecast_alerts.append({
                    "date": day["date"],
                    "condition": WMO_WEATHER_CODES.get(code, "Unknown"),
                    "precipitation_mm": precip,
                    "severity": "light",
                })

        result: dict[str, Any] = {"forecast_alerts": forecast_alerts, "forecast_days": len(forecast)}

        if daily_revenue and len(daily_revenue) >= 7:
            end = date.today()
            start = end - timedelta(days=len(daily_revenue) + 7)
            try:
                historical = await self.fetch_historical(start.isoformat(), end.isoformat())
                if historical:
                    self.store_observations(org_id, historical)
            except Exception as e:
                logger.warning("Failed to fetch historical weather: %s", e)

            corr = self.correlate_with_revenue(org_id, daily_revenue)
            result.update(corr)

        return result
