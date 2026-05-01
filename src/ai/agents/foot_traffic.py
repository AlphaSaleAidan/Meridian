from .base import BaseAgent
from collections import defaultdict


class FootTrafficAgent(BaseAgent):
    name = "foot_traffic"
    description = "Hourly/daily footfall, entry patterns, conversion rate vs POS transactions"
    tier = 1

    async def analyze(self) -> dict:
        traffic = getattr(self.ctx, "vision_traffic", [])
        transactions = self.ctx.transactions or []

        if not traffic:
            return self._insufficient_data("Vision traffic data (connect cameras)")

        total_entries = sum(r.get("entries", 0) for r in traffic)
        total_exits = sum(r.get("exits", 0) for r in traffic)
        total_txns = len(transactions)

        conversion_rate = total_txns / max(total_entries, 1)

        hourly = defaultdict(lambda: {"entries": 0, "count": 0})
        daily = defaultdict(lambda: {"entries": 0, "count": 0})
        for r in traffic:
            bucket = r.get("bucket", "")
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(bucket.replace("Z", "+00:00"))
                hour = dt.hour
                dow = dt.strftime("%A")
                hourly[hour]["entries"] += r.get("entries", 0)
                hourly[hour]["count"] += 1
                daily[dow]["entries"] += r.get("entries", 0)
                daily[dow]["count"] += 1
            except (ValueError, AttributeError):
                pass

        hourly_avg = {
            h: round(d["entries"] / max(d["count"], 1), 1)
            for h, d in sorted(hourly.items())
        }
        daily_avg = {
            d: round(v["entries"] / max(v["count"], 1), 1)
            for d, v in daily.items()
        }

        peak_hour = max(hourly_avg, key=hourly_avg.get) if hourly_avg else None
        slowest_hour = min(hourly_avg, key=hourly_avg.get) if hourly_avg else None
        peak_day = max(daily_avg, key=daily_avg.get) if daily_avg else None

        insights = []
        recommendations = []

        if conversion_rate < 0.3:
            missed = int(total_entries * (0.3 - conversion_rate))
            avg_ticket = 0
            for t in transactions[:100]:
                if t.get("total_cents"):
                    avg_ticket = t["total_cents"]
                    break
            avg_ticket = avg_ticket or 800
            opportunity_cents = missed * avg_ticket
            insights.append({
                "type": "low_conversion",
                "detail": (
                    f"Only {conversion_rate:.0%} of foot traffic converts to sales. "
                    f"Industry benchmark: 30%. ~{missed} missed customers in this period."
                ),
            })
            recommendations.append({
                "action": "Improve in-store conversion with greeting protocol and product placement",
                "impact_cents": opportunity_cents,
            })

        if peak_hour is not None and slowest_hour is not None:
            peak_traffic = hourly_avg[peak_hour]
            slow_traffic = hourly_avg[slowest_hour]
            if peak_traffic > slow_traffic * 3:
                insights.append({
                    "type": "traffic_concentration",
                    "detail": (
                        f"Traffic is 3x+ higher at {peak_hour}:00 vs {slowest_hour}:00. "
                        f"Ensure peak-hour staffing matches demand."
                    ),
                })
                recommendations.append({
                    "action": f"Add staff during {peak_hour}:00 peak — currently {peak_traffic:.0f} entries/bucket vs {slow_traffic:.0f} off-peak",
                    "impact_cents": 0,
                })

        score = min(100, 40 + int(conversion_rate * 100) + min(len(traffic), 30))
        confidence = min(0.85, 0.4 + len(traffic) / 500)

        return self._result(
            summary=f"{total_entries} visitors, {conversion_rate:.0%} conversion, peak hour: {peak_hour}:00",
            score=score,
            insights=insights,
            recommendations=recommendations,
            data={
                "total_entries": total_entries,
                "total_exits": total_exits,
                "total_transactions": total_txns,
                "conversion_rate": round(conversion_rate, 3),
                "hourly_avg_traffic": hourly_avg,
                "daily_avg_traffic": daily_avg,
                "peak_hour": peak_hour,
                "slowest_hour": slowest_hour,
                "peak_day": peak_day,
            },
            confidence=confidence,
            calculation_path="full" if len(traffic) >= 100 else "partial",
        )
