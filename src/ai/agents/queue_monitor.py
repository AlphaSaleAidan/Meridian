from .base import BaseAgent
from collections import defaultdict


class QueueMonitorAgent(BaseAgent):
    name = "queue_monitor"
    description = "Real-time queue length, wait time estimates, staffing alert triggers"
    tier = 1

    async def analyze(self) -> dict:
        traffic = getattr(self.ctx, "vision_traffic", [])

        if not traffic:
            return self._insufficient_data("Vision traffic data (connect cameras)")

        rows_with_queue = [
            r for r in traffic
            if r.get("queue_length_avg", 0) > 0 or r.get("queue_wait_avg_sec", 0) > 0
        ]

        if not rows_with_queue:
            return self._result(
                summary="No queue data detected — queues may not be in camera zones",
                score=50,
                insights=[{
                    "type": "no_queue_data",
                    "detail": "No queue activity detected. Ensure a camera covers the checkout/register area.",
                }],
                recommendations=[{
                    "action": "Configure a checkout zone in camera settings to enable queue monitoring",
                    "impact_cents": 0,
                }],
                data={"queue_data_available": False},
                confidence=0.3,
                calculation_path="minimal",
            )

        queue_lengths = [r["queue_length_avg"] for r in rows_with_queue]
        wait_times = [r["queue_wait_avg_sec"] for r in rows_with_queue]

        avg_queue = sum(queue_lengths) / len(queue_lengths)
        max_queue = max(queue_lengths)
        avg_wait = sum(wait_times) / len(wait_times)
        max_wait = max(wait_times)

        hourly_queue = defaultdict(list)
        hourly_wait = defaultdict(list)
        for r in rows_with_queue:
            bucket = r.get("bucket", "")
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(bucket.replace("Z", "+00:00"))
                hourly_queue[dt.hour].append(r["queue_length_avg"])
                hourly_wait[dt.hour].append(r["queue_wait_avg_sec"])
            except (ValueError, AttributeError):
                pass

        hourly_avg_queue = {
            h: round(sum(v) / len(v), 1)
            for h, v in sorted(hourly_queue.items())
        }
        hourly_avg_wait = {
            h: round(sum(v) / len(v), 1)
            for h, v in sorted(hourly_wait.items())
        }

        peak_queue_hour = max(hourly_avg_queue, key=hourly_avg_queue.get) if hourly_avg_queue else None

        long_wait_buckets = [r for r in rows_with_queue if r.get("queue_wait_avg_sec", 0) > 180]
        long_wait_pct = len(long_wait_buckets) / max(len(rows_with_queue), 1)

        entries_during_long_wait = sum(r.get("entries", 0) for r in long_wait_buckets)
        walkaway_est_rate = 0.15
        walkaway_est = int(entries_during_long_wait * walkaway_est_rate)

        avg_ticket = 800
        for t in (self.ctx.transactions or [])[:100]:
            if t.get("total_cents"):
                avg_ticket = t["total_cents"]
                break

        walkaway_cost_monthly = walkaway_est * avg_ticket * 30 // max(self.ctx.analysis_days, 1)

        insights = []
        recommendations = []

        if avg_wait > 120:
            insights.append({
                "type": "high_wait_time",
                "detail": (
                    f"Average wait time is {avg_wait:.0f}s ({avg_wait/60:.1f} min). "
                    f"Target: under 2 minutes. Long waits drive 15% walkaway rate."
                ),
            })

        if max_queue > 5:
            insights.append({
                "type": "peak_queue_buildup",
                "detail": (
                    f"Queue peaks at {max_queue:.0f} people "
                    f"(hour {peak_queue_hour}:00). Consider opening a second register."
                ),
            })

        if long_wait_pct > 0.2:
            insights.append({
                "type": "frequent_long_waits",
                "detail": (
                    f"{long_wait_pct:.0%} of time periods have wait >3 min. "
                    f"Estimated {walkaway_est} walkaways costing ~${walkaway_cost_monthly/100:,.0f}/month."
                ),
            })

        if walkaway_cost_monthly > 0:
            recommendations.append({
                "action": (
                    f"Reduce peak-hour queue times — add register or expediter during "
                    f"{peak_queue_hour}:00. Potential recovery: ${walkaway_cost_monthly/100:,.0f}/month"
                ),
                "impact_cents": walkaway_cost_monthly,
            })

        if avg_wait < 60:
            insights.append({
                "type": "healthy_queue",
                "detail": f"Average wait {avg_wait:.0f}s is excellent — customers spend minimal time in line",
            })

        alerts = []
        recent = rows_with_queue[-4:] if rows_with_queue else []
        for r in recent:
            if r.get("queue_length_avg", 0) > 6:
                alerts.append({
                    "severity": "warning",
                    "message": f"Queue length {r['queue_length_avg']:.0f} at {r.get('bucket', '')}",
                    "bucket": r.get("bucket"),
                })
            if r.get("queue_wait_avg_sec", 0) > 300:
                alerts.append({
                    "severity": "urgent",
                    "message": f"Wait time {r['queue_wait_avg_sec']:.0f}s at {r.get('bucket', '')}",
                    "bucket": r.get("bucket"),
                })

        score = max(0, 100 - int(avg_wait / 3) - int(max_queue * 5))
        confidence = min(0.85, 0.4 + len(rows_with_queue) / 200)

        return self._result(
            summary=f"Avg wait {avg_wait:.0f}s, avg queue {avg_queue:.1f}, peak {max_queue:.0f} people",
            score=max(0, score),
            insights=insights,
            recommendations=recommendations,
            data={
                "avg_queue_length": round(avg_queue, 1),
                "max_queue_length": round(max_queue, 1),
                "avg_wait_seconds": round(avg_wait, 1),
                "max_wait_seconds": round(max_wait, 1),
                "peak_queue_hour": peak_queue_hour,
                "long_wait_pct": round(long_wait_pct, 3),
                "walkaway_estimate": walkaway_est,
                "walkaway_cost_monthly_cents": walkaway_cost_monthly,
                "hourly_avg_queue": hourly_avg_queue,
                "hourly_avg_wait": hourly_avg_wait,
                "active_alerts": alerts,
            },
            confidence=confidence,
            calculation_path="full" if len(rows_with_queue) >= 50 else "partial",
        )
