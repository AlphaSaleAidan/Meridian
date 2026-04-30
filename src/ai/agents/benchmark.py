from .base import BaseAgent


class BenchmarkAgent(BaseAgent):
    name = "benchmark"
    description = "You vs Industry scorecard with percentile estimates"
    tier = 5

    async def analyze(self) -> dict:
        # ── Phase 1: Data Discovery ──────────────────────────
        avail = self.get_data_availability()
        daily = self.ctx.daily_revenue or []
        txns = self.ctx.transactions or []
        agent_outputs = getattr(self.ctx, "agent_outputs", {})

        if len(daily) < 7 and not agent_outputs:
            return self._insufficient_data("At least 7 days of data for benchmarking")

        # ── Phase 2: Path Selection ──────────────────────────
        # Determine quality of upstream inputs
        input_paths = []
        input_qualities = []
        for out in agent_outputs.values():
            if isinstance(out, dict) and out.get("status") == "complete":
                input_paths.append(out.get("calculation_path", "minimal"))
                input_qualities.append(out.get("data_quality", 0.5))

        if avail.is_full and len(daily) >= 14:
            calc_path = "full"
        elif avail.has_transactions and len(daily) >= 7:
            calc_path = "partial"
        else:
            calc_path = "minimal"

        # Downgrade if most upstream agents used minimal path
        if input_paths:
            minimal_ratio = input_paths.count("minimal") / len(input_paths)
            if minimal_ratio > 0.5 and calc_path == "full":
                calc_path = "partial"

        # ── Phase 3: Dynamic Calculation ─────────────────────
        from ..economics.benchmarks import IndustryBenchmarks
        bench = IndustryBenchmarks(getattr(self.ctx, "business_vertical", "other"))

        total_rev = sum(d.get("revenue_cents", 0) for d in daily)
        days = max(len(daily), 1)
        avg_daily = total_rev // days
        total_txns = sum(d.get("transaction_count", 0) for d in daily)
        avg_ticket = total_rev // max(total_txns, 1)

        # Build comparisons using benchmark ranges
        comparisons = []
        metrics = [
            ("avg_daily_revenue_cents", avg_daily, "Avg Daily Revenue"),
            ("avg_ticket_cents", avg_ticket, "Avg Ticket Size"),
            ("median_transactions_per_day", total_txns // days, "Transactions/Day"),
        ]

        for metric_key, actual, label in metrics:
            rng = self.get_benchmark_range(metric_key)
            estimated = calc_path != "full"

            if rng is not None:
                percentile_rank = round(rng.percentile(actual), 2)
                if percentile_rank > 0.7:
                    status = "above_benchmark"
                elif percentile_rank > 0.3:
                    status = "at_benchmark"
                else:
                    status = "below_benchmark"

                comparisons.append({
                    "metric": label,
                    "actual": actual,
                    "benchmark": {
                        "low": rng.low,
                        "mid": rng.mid,
                        "high": rng.high,
                        "source": rng.source,
                    },
                    "percentile_rank": percentile_rank,
                    "status": status,
                    "estimated": estimated,
                })
            else:
                # Fallback to simple compare
                result = bench.compare(metric_key, actual)
                comparisons.append({
                    "metric": label,
                    "actual": actual,
                    "benchmark": {
                        "low": 0, "mid": bench.get(metric_key, 0),
                        "high": 0, "source": "Industry estimate",
                    },
                    "percentile_rank": result.get("percentile_rank", 0.5),
                    "status": result.get("status", "no_benchmark"),
                    "estimated": estimated,
                })

        # Identify strengths and weaknesses
        strengths = [c for c in comparisons if c["percentile_rank"] > 0.7]
        weaknesses = [c for c in comparisons if c["percentile_rank"] < 0.3]

        # Overall score from average percentile rank
        avg_rank = sum(c["percentile_rank"] for c in comparisons) / max(len(comparisons), 1)
        score = max(0, min(100, round(avg_rank * 100)))

        # Top gap-closing actions sorted by weakness severity
        sorted_by_rank = sorted(comparisons, key=lambda c: c["percentile_rank"])
        actions = []
        for comp in sorted_by_rank[:3]:
            if comp["percentile_rank"] < 0.5:
                mid_val = comp["benchmark"]["mid"]
                gap_val = mid_val - comp["actual"] if mid_val else 0
                if "ticket" in comp["metric"].lower():
                    daily_txns = total_txns // days
                    actions.append({
                        "action": f"Close ${gap_val/100:.2f} ticket gap vs industry — train upselling",
                        "metric": comp["metric"],
                        "impact_cents": int(gap_val * daily_txns),
                    })
                elif "revenue" in comp["metric"].lower():
                    actions.append({
                        "action": f"Revenue ${gap_val/100:,.0f}/day below benchmark — focus on traffic and ticket size",
                        "metric": comp["metric"],
                        "impact_cents": int(gap_val),
                    })
                else:
                    actions.append({
                        "action": f"Improve {comp['metric']} to match industry benchmark",
                        "metric": comp["metric"],
                        "impact_cents": 0,
                    })

        # Biggest opportunity = weakness with highest $ impact
        biggest_opportunity = None
        if actions:
            best = max(actions, key=lambda a: a.get("impact_cents", 0))
            biggest_opportunity = {
                "metric": best["metric"],
                "action": best["action"],
                "monthly_impact_cents": best["impact_cents"] * 30,
            }

        insights = []
        if strengths:
            insights.append({
                "type": "strengths",
                "detail": f"Above benchmark on: {', '.join(c['metric'] for c in strengths)}",
            })
        if weaknesses:
            insights.append({
                "type": "gaps",
                "detail": f"Below benchmark on: {', '.join(c['metric'] for c in weaknesses)}",
            })
        if biggest_opportunity:
            insights.append({
                "type": "biggest_opportunity",
                "detail": (
                    f"Biggest opportunity: {biggest_opportunity['metric']} — "
                    f"${biggest_opportunity['monthly_impact_cents']/100:,.0f}/month potential"
                ),
            })

        # Confidence: benchmarks are always estimates (base 0.6),
        # adjusted by input data quality
        if input_qualities:
            avg_input_quality = sum(input_qualities) / len(input_qualities)
        else:
            avg_input_quality = avail.quality_score
        confidence = round(min(0.9, 0.6 * (0.5 + 0.5 * avg_input_quality)), 2)

        return self._result(
            summary=f"{'Above' if avg_rank > 0.5 else 'Below'} industry benchmark — {len(strengths)} strengths, {len(weaknesses)} gaps",
            score=score,
            insights=insights,
            recommendations=actions,
            data={
                "comparisons": comparisons,
                "strengths": [c["metric"] for c in strengths],
                "weaknesses": [c["metric"] for c in weaknesses],
                "biggest_opportunity": biggest_opportunity,
                "vertical": getattr(self.ctx, "business_vertical", "other"),
                "avg_percentile_rank": round(avg_rank, 2),
            },
            confidence=confidence,
            calculation_path=calc_path,
        )
