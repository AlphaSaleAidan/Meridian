"""
Peak Basket Agent — Correlates traffic density with basket composition.

Finds how crowding affects what people buy, how much they spend,
and whether high-traffic periods produce different basket patterns.
"""
from collections import defaultdict
from .base import BaseCrossRefAgent


class PeakBasketAgent(BaseCrossRefAgent):
    name = "peak_basket"
    description = "Correlates traffic density with basket size and composition"
    tier = 3

    async def analyze(self) -> dict:
        converted = self.converted_journeys
        traffic = self.ctx.vision_traffic

        if not converted or len(converted) < 5:
            return self._insufficient_data("At least 5 converted journeys with traffic data")

        hourly_traffic: dict[int, int] = defaultdict(int)
        hourly_count: dict[int, int] = defaultdict(int)
        for t in traffic:
            bucket = t.get("bucket", "")
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(bucket.replace("Z", "+00:00"))
                hourly_traffic[dt.hour] += t.get("entries", 0)
                hourly_count[dt.hour] += 1
            except (ValueError, AttributeError):
                pass

        hourly_avg = {}
        for h in hourly_traffic:
            hourly_avg[h] = hourly_traffic[h] / max(hourly_count[h], 1)

        if not hourly_avg:
            return self._insufficient_data("Hourly traffic data")

        median_traffic = sorted(hourly_avg.values())[len(hourly_avg) // 2] if hourly_avg else 1
        peak_hours = {h for h, v in hourly_avg.items() if v > median_traffic * 1.5}
        quiet_hours = {h for h, v in hourly_avg.items() if v < median_traffic * 0.7}

        peak_baskets = []
        quiet_baskets = []
        for j in converted:
            entry = j.get("entry_time", "")
            total = j.get("transaction_total_cents", 0)
            if not entry or not total:
                continue
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(entry.replace("Z", "+00:00"))
                if dt.hour in peak_hours:
                    peak_baskets.append(total)
                elif dt.hour in quiet_hours:
                    quiet_baskets.append(total)
            except (ValueError, AttributeError):
                pass

        avg_peak = sum(peak_baskets) / max(len(peak_baskets), 1)
        avg_quiet = sum(quiet_baskets) / max(len(quiet_baskets), 1)

        insights = []
        recommendations = []

        if avg_peak and avg_quiet:
            diff_pct = (avg_peak / max(avg_quiet, 1) - 1) if avg_quiet else 0

            if diff_pct > 0.1:
                insights.append({
                    "type": "peak_premium",
                    "detail": (
                        f"Peak-hour customers spend {diff_pct:.0%} more "
                        f"(${avg_peak / 100:.2f} vs ${avg_quiet / 100:.2f} off-peak)"
                    ),
                })
            elif diff_pct < -0.1:
                insights.append({
                    "type": "peak_discount",
                    "detail": (
                        f"Peak-hour baskets are {abs(diff_pct):.0%} smaller — "
                        f"crowding may rush customers through"
                    ),
                })
                recommendations.append({
                    "action": "During peak hours, use express checkout or mobile POS to reduce perceived wait",
                    "impact_cents": int(abs(avg_peak - avg_quiet) * len(peak_baskets) * 0.1),
                })

        peak_conv = len(peak_baskets)
        quiet_conv = len(quiet_baskets)

        if peak_hours and quiet_hours:
            insights.append({
                "type": "traffic_split",
                "detail": (
                    f"Peak hours ({', '.join(f'{h}:00' for h in sorted(peak_hours))}): "
                    f"{peak_conv} sales. "
                    f"Quiet hours ({', '.join(f'{h}:00' for h in sorted(quiet_hours))}): "
                    f"{quiet_conv} sales."
                ),
            })

        score = min(100, 40 + min(len(converted), 30) + min(len(traffic), 20))

        return self._result(
            summary=f"Peak basket ${avg_peak / 100:.2f} vs quiet ${avg_quiet / 100:.2f}",
            score=score,
            insights=insights,
            recommendations=recommendations,
            data={
                "peak_hours": sorted(peak_hours),
                "quiet_hours": sorted(quiet_hours),
                "avg_peak_basket_cents": int(avg_peak),
                "avg_quiet_basket_cents": int(avg_quiet),
                "peak_transactions": peak_conv,
                "quiet_transactions": quiet_conv,
                "hourly_avg_traffic": {str(k): round(v, 1) for k, v in sorted(hourly_avg.items())},
            },
            confidence=min(0.75, 0.3 + len(converted) / 100),
        )
