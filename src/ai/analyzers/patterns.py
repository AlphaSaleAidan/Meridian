"""
Pattern Analyzer — Peak hours, seasonality, staffing optimization.

Analyzes hourly/daily transaction patterns to produce:
  • Peak and slow hours (revenue heatmap)
  • Day-of-week patterns
  • Staffing optimization suggestions
  • Seasonality indicators
  • Customer traffic patterns
"""
import logging
import math
from collections import defaultdict
from datetime import datetime

logger = logging.getLogger("meridian.ai.analyzers.patterns")


class PatternAnalyzer:
    """Produces temporal pattern analysis from transaction data."""

    def analyze(self, ctx) -> dict:
        """
        Run full pattern analysis.
        
        Returns:
            {
                "peak_hours": {best/worst hours with revenue data},
                "day_of_week": {per-day-of-week stats},
                "heatmap": [[hour x day grid]],
                "staffing": {suggestions based on traffic patterns},
                "seasonality": {weekly/monthly patterns},
            }
        """
        result = {}

        # Use hourly data if available, fall back to raw transactions
        if ctx.hourly_revenue:
            result["peak_hours"] = self._analyze_peak_hours(ctx.hourly_revenue)
            result["heatmap"] = self._build_heatmap(ctx.hourly_revenue)
            result["staffing"] = self._staffing_optimization(ctx.hourly_revenue)
        
        if ctx.daily_revenue:
            result["day_of_week"] = self._day_of_week_analysis(ctx.daily_revenue)
            result["seasonality"] = self._detect_seasonality(ctx.daily_revenue)

        if ctx.transactions:
            result["payment_patterns"] = self._payment_patterns(ctx.transactions)
            result["ticket_distribution"] = self._ticket_distribution(ctx.transactions)

        logger.info(
            f"Pattern analysis complete: "
            f"{len(result.get('peak_hours', {}).get('peak', []))} peak hours, "
            f"best day={result.get('day_of_week', {}).get('best_day', 'N/A')}"
        )
        return result

    def _analyze_peak_hours(self, hourly: list[dict]) -> dict:
        """
        Find peak and slow hours across the period.
        
        Groups by hour-of-day, averages revenue and transactions.
        """
        hour_stats = defaultdict(lambda: {
            "total_revenue": 0, "total_txns": 0, "days": 0
        })
        
        for row in hourly:
            hour_bucket = row.get("hour_bucket")
            if hour_bucket is None:
                continue
            
            # Extract hour from timestamp
            if isinstance(hour_bucket, str):
                try:
                    dt = datetime.fromisoformat(hour_bucket.replace("Z", "+00:00"))
                    hour = dt.hour
                except (ValueError, AttributeError):
                    continue
            elif isinstance(hour_bucket, datetime):
                hour = hour_bucket.hour
            else:
                continue
            
            stats = hour_stats[hour]
            stats["total_revenue"] += (row.get("total_revenue_cents") or 0)
            stats["total_txns"] += (row.get("transaction_count") or 0)
            stats["days"] += 1
        
        if not hour_stats:
            return {}
        
        # Compute averages per hour
        hourly_avgs = []
        for hour, stats in sorted(hour_stats.items()):
            days = max(stats["days"], 1)
            hourly_avgs.append({
                "hour": hour,
                "hour_label": self._format_hour(hour),
                "avg_revenue_cents": int(stats["total_revenue"] / days),
                "avg_transactions": round(stats["total_txns"] / days, 1),
                "total_revenue_cents": stats["total_revenue"],
                "total_transactions": stats["total_txns"],
                "sample_days": days,
            })
        
        # Sort by revenue
        by_revenue = sorted(
            hourly_avgs, key=lambda x: x["avg_revenue_cents"], reverse=True
        )
        
        peak = by_revenue[:3]
        slow = [h for h in by_revenue[-3:] if h["avg_revenue_cents"] > 0]
        dead = [h for h in hourly_avgs if h["avg_transactions"] < 1]
        
        # Find the golden window (consecutive peak hours)
        sorted_by_hour = sorted(hourly_avgs, key=lambda x: x["hour"])
        golden_window = self._find_golden_window(sorted_by_hour)
        
        return {
            "peak": peak,
            "slow": slow,
            "dead_hours": dead,
            "golden_window": golden_window,
            "hourly_breakdown": hourly_avgs,
        }

    def _find_golden_window(self, hourly_avgs: list[dict]) -> dict:
        """Find the best 3-4 hour consecutive window."""
        if len(hourly_avgs) < 3:
            return {}
        
        best_window_start = 0
        best_window_revenue = 0
        window_size = 3
        
        for i in range(len(hourly_avgs) - window_size + 1):
            window_rev = sum(
                hourly_avgs[j]["avg_revenue_cents"] 
                for j in range(i, i + window_size)
            )
            if window_rev > best_window_revenue:
                best_window_revenue = window_rev
                best_window_start = i
        
        start_hour = hourly_avgs[best_window_start]["hour"]
        end_hour = hourly_avgs[min(best_window_start + window_size - 1, len(hourly_avgs) - 1)]["hour"]
        
        return {
            "start_hour": start_hour,
            "end_hour": end_hour + 1,  # exclusive
            "label": f"{self._format_hour(start_hour)} - {self._format_hour(end_hour + 1)}",
            "avg_revenue_cents": int(best_window_revenue / window_size),
            "total_revenue_share_pct": round(
                best_window_revenue / max(
                    sum(h["avg_revenue_cents"] for h in hourly_avgs), 1
                ) * 100, 1
            ),
        }

    def _build_heatmap(self, hourly: list[dict]) -> list[list[int]]:
        """
        Build 7x24 heatmap grid (day-of-week × hour-of-day).
        
        Values are average revenue in cents.
        Index: [day_of_week][hour] where Monday=0, Sunday=6.
        """
        # Grid: accumulate revenue per cell
        grid = [[0] * 24 for _ in range(7)]
        counts = [[0] * 24 for _ in range(7)]
        
        for row in hourly:
            hour_bucket = row.get("hour_bucket")
            if hour_bucket is None:
                continue
            
            if isinstance(hour_bucket, str):
                try:
                    dt = datetime.fromisoformat(hour_bucket.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    continue
            elif isinstance(hour_bucket, datetime):
                dt = hour_bucket
            else:
                continue
            
            dow = dt.weekday()  # Monday=0
            hour = dt.hour
            
            grid[dow][hour] += (row.get("total_revenue_cents") or 0)
            counts[dow][hour] += 1
        
        # Average
        for d in range(7):
            for h in range(24):
                if counts[d][h] > 0:
                    grid[d][h] = int(grid[d][h] / counts[d][h])
        
        return grid

    def _day_of_week_analysis(self, daily: list[dict]) -> dict:
        """Analyze revenue patterns by day of week."""
        dow_stats = defaultdict(lambda: {"revenue": 0, "txns": 0, "days": 0})
        
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday",
                     "Friday", "Saturday", "Sunday"]
        
        for row in daily:
            date = row.get("date")
            if not date:
                continue
            
            if isinstance(date, str):
                try:
                    dt = datetime.fromisoformat(date)
                except ValueError:
                    continue
            elif isinstance(date, datetime):
                dt = date
            else:
                # Handle date objects
                try:
                    dt = datetime(date.year, date.month, date.day)
                except (AttributeError, TypeError):
                    continue
            
            dow = dt.weekday()
            stats = dow_stats[dow]
            stats["revenue"] += (row.get("total_revenue_cents") or 0)
            stats["txns"] += (row.get("transaction_count") or 0)
            stats["days"] += 1
        
        breakdown = []
        for dow in range(7):
            stats = dow_stats[dow]
            days = max(stats["days"], 1)
            breakdown.append({
                "day": day_names[dow],
                "day_index": dow,
                "avg_revenue_cents": int(stats["revenue"] / days),
                "avg_transactions": round(stats["txns"] / days, 1),
                "total_revenue_cents": stats["revenue"],
                "sample_days": stats["days"],
            })
        
        # Find best/worst
        by_revenue = sorted(breakdown, key=lambda x: x["avg_revenue_cents"], reverse=True)
        
        return {
            "breakdown": breakdown,
            "best_day": by_revenue[0]["day"] if by_revenue else None,
            "worst_day": by_revenue[-1]["day"] if by_revenue else None,
            "best_day_avg_cents": by_revenue[0]["avg_revenue_cents"] if by_revenue else 0,
            "worst_day_avg_cents": by_revenue[-1]["avg_revenue_cents"] if by_revenue else 0,
            "weekend_vs_weekday_pct": self._weekend_vs_weekday(breakdown),
        }

    def _weekend_vs_weekday(self, breakdown: list[dict]) -> float:
        """Weekend revenue as % of weekday average."""
        weekday_avg = sum(
            b["avg_revenue_cents"] for b in breakdown if b["day_index"] < 5
        ) / 5
        weekend_avg = sum(
            b["avg_revenue_cents"] for b in breakdown if b["day_index"] >= 5
        ) / 2
        
        if weekday_avg == 0:
            return 0
        return round((weekend_avg / weekday_avg - 1) * 100, 1)

    def _staffing_optimization(self, hourly: list[dict]) -> dict:
        """
        Staffing suggestions based on transaction volume patterns.
        
        Identifies hours that are over/understaffed relative to 
        transaction volume.
        """
        hour_txns = defaultdict(list)
        
        for row in hourly:
            hour_bucket = row.get("hour_bucket")
            if hour_bucket is None:
                continue
            
            if isinstance(hour_bucket, str):
                try:
                    dt = datetime.fromisoformat(hour_bucket.replace("Z", "+00:00"))
                    hour = dt.hour
                except (ValueError, AttributeError):
                    continue
            elif isinstance(hour_bucket, datetime):
                hour = hour_bucket.hour
            else:
                continue
            
            hour_txns[hour].append((row.get("transaction_count") or 0))
        
        if not hour_txns:
            return {}
        
        # Compute average + peak for each hour
        suggestions = []
        for hour in sorted(hour_txns.keys()):
            txns = hour_txns[hour]
            avg = sum(txns) / len(txns)
            peak = max(txns)
            
            # Simple heuristic: 1 staff per 8 transactions/hour
            min_staff = max(1, math.ceil(avg / 8))
            peak_staff = max(1, math.ceil(peak / 6))  # Peak needs more
            
            suggestions.append({
                "hour": hour,
                "hour_label": self._format_hour(hour),
                "avg_transactions": round(avg, 1),
                "peak_transactions": peak,
                "recommended_min_staff": min_staff,
                "recommended_peak_staff": peak_staff,
            })
        
        # Total daily staff-hours
        total_staff_hours = sum(s["recommended_min_staff"] for s in suggestions)
        
        return {
            "hourly_staffing": suggestions,
            "total_daily_staff_hours": total_staff_hours,
            "busiest_hour": max(suggestions, key=lambda x: x["avg_transactions"]),
            "slowest_hour": min(suggestions, key=lambda x: x["avg_transactions"]),
        }

    def _detect_seasonality(self, daily: list[dict]) -> dict:
        """
        Basic seasonality detection.
        
        Looks for weekly patterns (7-day cycles).
        """
        if len(daily) < 14:
            return {"detected": False, "note": "Need 14+ days for seasonality"}
        
        revenues = [(d.get("total_revenue_cents") or 0) for d in daily]
        
        # Check if there's a consistent weekly pattern
        # Compare each day to same-day-of-week average
        weekly_pattern = [0.0] * 7
        weekly_counts = [0] * 7
        
        for i, rev in enumerate(revenues):
            dow = i % 7
            weekly_pattern[dow] += rev
            weekly_counts[dow] += 1
        
        for i in range(7):
            if weekly_counts[i] > 0:
                weekly_pattern[i] /= weekly_counts[i]
        
        # Check variance between days (high = strong weekly pattern)
        if not any(weekly_pattern):
            return {"detected": False}
        
        avg_all = sum(weekly_pattern) / 7
        variance = sum((x - avg_all) ** 2 for x in weekly_pattern) / 7
        cv = math.sqrt(variance) / max(avg_all, 1)  # coefficient of variation
        
        return {
            "detected": cv > 0.15,  # >15% CV suggests weekly pattern
            "weekly_coefficient_of_variation": round(cv, 3),
            "weekly_pattern_strength": (
                "strong" if cv > 0.3 else "moderate" if cv > 0.15 else "weak"
            ),
            "weekly_revenue_pattern": [int(x) for x in weekly_pattern],
        }

    def _payment_patterns(self, transactions: list[dict]) -> dict:
        """Payment method distribution and trends."""
        method_counts = defaultdict(int)
        method_revenue = defaultdict(int)
        total = len(transactions)
        
        for txn in transactions:
            method = txn.get("payment_method", "unknown")
            method_counts[method] += 1
            method_revenue[method] += (txn.get("total_cents") or 0)
        
        breakdown = []
        for method, count in sorted(
            method_counts.items(), key=lambda x: x[1], reverse=True
        ):
            breakdown.append({
                "method": method,
                "count": count,
                "share_pct": round(count / max(total, 1) * 100, 1),
                "revenue_cents": method_revenue[method],
            })
        
        return {
            "breakdown": breakdown,
            "dominant_method": breakdown[0]["method"] if breakdown else None,
            "cash_pct": round(
                (method_counts.get("cash") or 0) / max(total, 1) * 100, 1
            ),
            "card_pct": round(
                ((method_counts.get("credit_card") or 0) + (method_counts.get("debit_card") or 0))
                / max(total, 1) * 100, 1
            ),
        }

    def _ticket_distribution(self, transactions: list[dict]) -> dict:
        """Transaction size distribution analysis."""
        amounts = [(txn.get("total_cents") or 0) for txn in transactions if (txn.get("total_cents") or 0) > 0]
        
        if not amounts:
            return {}
        
        amounts.sort()
        n = len(amounts)
        
        return {
            "count": n,
            "min_cents": amounts[0],
            "max_cents": amounts[-1],
            "avg_cents": int(sum(amounts) / n),
            "median_cents": amounts[n // 2],
            "p25_cents": amounts[n // 4],
            "p75_cents": amounts[3 * n // 4],
            "p90_cents": amounts[int(n * 0.9)],
            "under_1000_cents_pct": round(
                len([a for a in amounts if a < 1000]) / n * 100, 1
            ),
            "over_5000_cents_pct": round(
                len([a for a in amounts if a > 5000]) / n * 100, 1
            ),
        }

    # ─── Helpers ──────────────────────────────────────────────

    @staticmethod
    def _format_hour(hour: int) -> str:
        """Format hour as '9 AM', '2 PM' etc."""
        if hour == 0:
            return "12 AM"
        elif hour < 12:
            return f"{hour} AM"
        elif hour == 12:
            return "12 PM"
        else:
            return f"{hour - 12} PM"
