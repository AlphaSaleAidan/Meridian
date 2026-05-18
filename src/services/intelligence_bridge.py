"""
Intelligence bridge — wires weather + camera into the AI engine.

Cross-references POS data with weather conditions and vision analytics
to produce insights that only exist at the intersection of all three.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("meridian.services.intelligence_bridge")


def _classify_insight(insight: dict) -> str:
    title = (insight.get("title", "") + " " + insight.get("type", "")).lower()
    if any(k in title for k in ("revenue", "anomaly", "spike", "drop", "gap")):
        return "revenue"
    if any(k in title for k in ("staff", "labor", "schedule", "peak")):
        return "staffing"
    if any(k in title for k in ("product", "menu", "item", "stock", "inventory")):
        return "product"
    if any(k in title for k in ("price", "margin", "discount")):
        return "pricing"
    return "general"


def _weather_enrichment(insight: dict, weather: dict) -> dict | None:
    alerts = weather.get("forecast_alerts", [])
    rain_impact = weather.get("rain_impact_pct")
    if not alerts and rain_impact is None:
        return None
    return {
        "rain_impact_pct": rain_impact,
        "upcoming_alerts": alerts[:3],
        "correlation_strength": abs(weather.get("correlations", {}).get("precipitation", 0)),
    }


def _vision_enrichment(insight: dict, vision: dict) -> dict | None:
    if not vision or not vision.get("total_foot_traffic"):
        return None
    return {
        "conversion_rate": vision.get("conversion_rate"),
        "total_traffic": vision.get("total_foot_traffic"),
        "peak_hours": vision.get("peak_traffic_hours", [])[:3],
    }


def _zone_enrichment(insight: dict, vision: dict) -> dict | None:
    zones = vision.get("zone_performance", [])
    if not zones:
        return None
    return {
        "top_zones": zones[:3],
        "browse_to_purchase_pct": vision.get("gesture_signals", {}).get("browse_to_purchase_pct"),
    }


class IntelligenceBridge:

    def __init__(self, org_id: str, lat: float | None = None, lon: float | None = None):
        self.org_id = org_id
        self._weather = None
        self._camera = None

        try:
            from .weather_service import WeatherService
            kwargs = {}
            if lat is not None:
                kwargs["lat"] = lat
            if lon is not None:
                kwargs["lon"] = lon
            self._weather = WeatherService(**kwargs)
        except Exception as e:
            logger.warning("Weather service unavailable: %s", e)

        try:
            from .camera_interpreter import CameraInterpreter
            self._camera = CameraInterpreter()
        except Exception as e:
            logger.warning("Camera interpreter unavailable: %s", e)

    async def gather_external_context(self, daily_revenue: list[dict] | None = None, pos_tx_count: int = 0) -> dict:
        tasks = {}

        if self._weather:
            tasks["weather"] = self._weather.get_weather_insights(self.org_id, daily_revenue)
        if self._camera:
            loop = asyncio.get_event_loop()
            tasks["vision"] = loop.run_in_executor(
                None, lambda: self._camera.generate_vision_insights(self.org_id, pos_tx_count)
            )

        results: dict[str, Any] = {"weather": {}, "vision": {}, "sources_available": 0}

        if tasks:
            gathered = await asyncio.gather(*tasks.values(), return_exceptions=True)
            for key, result in zip(tasks.keys(), gathered):
                if isinstance(result, Exception):
                    logger.warning("Failed to gather %s context: %s", key, result)
                else:
                    results[key] = result
                    results["sources_available"] += 1

        return results

    async def enrich_insights(self, raw_insights: list[dict], daily_revenue: list[dict] | None = None, pos_tx_count: int = 0) -> list[dict]:
        ctx = await self.gather_external_context(daily_revenue, pos_tx_count)
        weather = ctx.get("weather", {})
        vision = ctx.get("vision", {})

        for insight in raw_insights:
            category = _classify_insight(insight)

            if category == "revenue" and weather:
                enrichment = _weather_enrichment(insight, weather)
                if enrichment:
                    insight["weather_context"] = enrichment

            if category == "staffing" and vision:
                enrichment = _vision_enrichment(insight, vision)
                if enrichment:
                    insight["vision_context"] = enrichment

            if category == "product" and vision:
                enrichment = _zone_enrichment(insight, vision)
                if enrichment:
                    insight["zone_dwell_context"] = enrichment

        return raw_insights

    async def generate_cross_intelligence(self, daily_revenue: list[dict] | None = None, pos_tx_count: int = 0) -> list[dict]:
        ctx = await self.gather_external_context(daily_revenue, pos_tx_count)
        weather = ctx.get("weather", {})
        vision = ctx.get("vision", {})
        cross_insights: list[dict] = []

        if weather.get("forecast_alerts"):
            rain_impact = weather.get("rain_impact_pct", -15)
            for alert in weather["forecast_alerts"][:2]:
                cross_insights.append({
                    "type": "weather_forecast",
                    "source": "weather+pos",
                    "title": f"Weather alert: {alert['condition']} forecast for {alert['date']}",
                    "summary": (
                        f"{alert['condition']} expected on {alert['date']} "
                        f"({alert['precipitation_mm']:.1f}mm precipitation). "
                        f"Historical data shows {abs(rain_impact):.0f}% revenue impact on similar days. "
                        f"Reduce perishable prep by 20% and boost delivery/pickup promotions."
                    ),
                    "severity": alert["severity"],
                    "impact_pct": rain_impact,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                })

        if vision.get("total_foot_traffic") and pos_tx_count:
            conv = vision["conversion_rate"]
            traffic = vision["total_foot_traffic"]
            benchmark = 30.0
            if conv < benchmark:
                gap = benchmark - conv
                lost_tx = int(traffic * gap / 100)
                avg_ticket = 1200
                cross_insights.append({
                    "type": "conversion_gap",
                    "source": "camera+pos",
                    "title": f"Conversion gap: {conv:.1f}% vs {benchmark:.0f}% benchmark",
                    "summary": (
                        f"Camera tracked {traffic:,} visitors but only {pos_tx_count:,} transactions "
                        f"({conv:.1f}% conversion). Industry benchmark is {benchmark:.0f}%. "
                        f"Closing the gap would capture ~{lost_tx} additional transactions "
                        f"(~${lost_tx * avg_ticket / 100:,.0f} revenue). "
                        f"Check greeting protocol, queue wait times, and product visibility."
                    ),
                    "conversion_rate": conv,
                    "benchmark": benchmark,
                    "est_lost_revenue_cents": lost_tx * avg_ticket,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                })

        zones = vision.get("zone_performance", [])
        for zone in zones:
            if zone.get("avg_dwell_sec", 0) > 120 and zone.get("conversion_pct", 0) < 10:
                cross_insights.append({
                    "type": "zone_mismatch",
                    "source": "camera+heatmap",
                    "title": f"Zone '{zone['zone']}': high dwell ({zone['avg_dwell_sec']:.0f}s) but low conversion ({zone['conversion_pct']:.0f}%)",
                    "summary": (
                        f"Visitors spend {zone['avg_dwell_sec']:.0f}s in {zone['zone']} zone "
                        f"but only {zone['conversion_pct']:.0f}% convert. "
                        f"This suggests interest without purchase — check pricing, signage, or product availability."
                    ),
                    "zone": zone["zone"],
                    "created_at": datetime.now(timezone.utc).isoformat(),
                })

        queue = vision.get("queue_impact", {})
        if queue.get("est_revenue_lost_cents", 0) > 5000:
            cross_insights.append({
                "type": "queue_walkaway",
                "source": "camera+gesture",
                "title": f"Queue walkaway: ~${queue['est_revenue_lost_cents'] / 100:,.0f} estimated lost revenue",
                "summary": (
                    f"Camera detected {queue['waiting_events']} queue events. "
                    f"At {queue['est_walkaway_pct'] * 100:.0f}% estimated walkaway rate, "
                    f"~${queue['est_revenue_lost_cents'] / 100:,.0f} in revenue is at risk. "
                    f"Consider adding a second register during peak hours or implementing mobile ordering."
                ),
                "waiting_events": queue["waiting_events"],
                "created_at": datetime.now(timezone.utc).isoformat(),
            })

        return cross_insights

    def format_for_swarm(self, context: dict) -> str:
        sections = []

        weather = context.get("weather", {})
        if weather:
            lines = ["[WEATHER INTELLIGENCE]"]
            if weather.get("rain_impact_pct") is not None:
                lines.append(f"Rain impact on revenue: {weather['rain_impact_pct']:.1f}%")
            if weather.get("temp_sweet_spot"):
                ts = weather["temp_sweet_spot"]
                lines.append(f"Optimal temperature range: {ts['min']}-{ts['max']}°F")
            for alert in weather.get("forecast_alerts", [])[:3]:
                lines.append(f"Alert: {alert['date']} — {alert['condition']} ({alert['severity']})")
            sections.append("\n".join(lines))

        vision = context.get("vision", {})
        if vision:
            lines = ["[CAMERA / VISION INTELLIGENCE]"]
            if vision.get("total_foot_traffic"):
                lines.append(f"Foot traffic: {vision['total_foot_traffic']:,}")
            if vision.get("conversion_rate"):
                lines.append(f"Conversion rate: {vision['conversion_rate']:.1f}%")
            for zone in vision.get("zone_performance", [])[:3]:
                lines.append(f"Zone '{zone['zone']}': {zone['avg_dwell_sec']:.0f}s dwell, {zone['conversion_pct']:.0f}% conversion")
            gs = vision.get("gesture_signals", {})
            if gs.get("browse_to_purchase_pct"):
                lines.append(f"Browse-to-purchase ratio: {gs['browse_to_purchase_pct']:.1f}%")
            sections.append("\n".join(lines))

        return "\n\n".join(sections) if sections else ""
