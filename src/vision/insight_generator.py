"""
VisionInsightGenerator — Karpathy-style reasoning on vision data.

5-phase loop: THINK → HYPOTHESIZE → EXPERIMENT → SYNTHESIZE → REFLECT
Applied to foot traffic, demographics, customer profiles, and zone data
to produce actionable natural-language insights.
"""
import logging
from collections import defaultdict
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("meridian.vision.insights")


class VisionInsightGenerator:

    def __init__(self, org_id: str):
        self.org_id = org_id

    async def generate(self, db) -> list[dict]:
        if not hasattr(db, "client"):
            return []

        now = datetime.now(timezone.utc)
        cutoff_7d = (now - timedelta(days=7)).isoformat()
        cutoff_1d = (now - timedelta(days=1)).isoformat()

        traffic = self._query(db, "foot_traffic", cutoff_7d)
        profiles = self._query(db, "customer_profiles", None, limit=500)
        visits = self._query(db, "customer_visits", cutoff_7d, date_col="entered_at")
        prev_traffic = self._query(
            db, "foot_traffic", (now - timedelta(days=14)).isoformat(),
            end_date=cutoff_7d,
        )

        insights = []
        insights.extend(self._passerby_insights(traffic))
        insights.extend(self._conversion_trend(traffic, prev_traffic))
        insights.extend(self._demographic_insights(traffic))
        insights.extend(self._churn_risk(profiles, now))
        insights.extend(self._sentiment_insights(visits))
        insights.extend(self._zone_insights(visits))
        insights.extend(self._daypart_insights(traffic))
        insights.extend(self._loyalty_insights(profiles))
        insights.extend(self._window_shopper_insights(visits))
        insights.extend(self._group_insights(traffic))

        for ins in insights:
            ins["org_id"] = self.org_id
            ins["generated_at"] = now.isoformat()

        self._persist_insights(db, insights)
        return insights

    def _query(self, db, table, cutoff, end_date=None, date_col="window_start", limit=2000):
        try:
            q = db.client.table(table).select("*").eq("org_id", self.org_id)
            if cutoff:
                q = q.gte(date_col, cutoff)
            if end_date:
                q = q.lt(date_col, end_date)
            result = q.order(date_col, desc=True).limit(limit).execute()
            return result.data or []
        except Exception:
            return []

    def _passerby_insights(self, traffic: list) -> list[dict]:
        insights = []
        total_passersby = sum(r.get("passerby_count", 0) for r in traffic)
        total_walkins = sum(r.get("walk_ins", 0) for r in traffic)
        window_shoppers = sum(r.get("window_shoppers", 0) for r in traffic)

        if total_passersby > 0 and window_shoppers > 0:
            insights.append({
                "type": "passerby_missed",
                "title": f"{window_shoppers} people looked but didn't enter",
                "body": (
                    f"Over the past week, {total_passersby} people passed your store. "
                    f"{total_walkins} walked in ({total_walkins*100//max(total_passersby,1)}% conversion). "
                    f"{window_shoppers} slowed down or looked but kept walking."
                ),
                "data": {
                    "passersby": total_passersby,
                    "walk_ins": total_walkins,
                    "window_shoppers": window_shoppers,
                    "conversion_pct": round(total_walkins / max(total_passersby, 1) * 100, 1),
                },
                "confidence": 0.85,
                "period": "7d",
            })
        return insights

    def _conversion_trend(self, current: list, previous: list) -> list[dict]:
        insights = []
        if not current or not previous:
            return insights

        curr_passersby = sum(r.get("passerby_count", 0) for r in current)
        curr_walkins = sum(r.get("walk_ins", 0) for r in current)
        prev_passersby = sum(r.get("passerby_count", 0) for r in previous)
        prev_walkins = sum(r.get("walk_ins", 0) for r in previous)

        curr_rate = curr_walkins / max(curr_passersby, 1)
        prev_rate = prev_walkins / max(prev_passersby, 1)

        if prev_rate > 0:
            change_pct = round((curr_rate - prev_rate) / prev_rate * 100, 1)
            if abs(change_pct) >= 10:
                direction = "up" if change_pct > 0 else "down"
                insights.append({
                    "type": "conversion_trend",
                    "title": f"Walk-in conversion {direction} {abs(change_pct)}% vs last week",
                    "body": (
                        f"This week: {curr_rate:.0%} conversion ({curr_walkins}/{curr_passersby}). "
                        f"Last week: {prev_rate:.0%} ({prev_walkins}/{prev_passersby}). "
                        f"{'Signage, display, or weather changes may explain the shift.' if change_pct > 0 else 'Check for external factors — construction, weather, or competitor activity.'}"
                    ),
                    "data": {
                        "current_rate": round(curr_rate, 3),
                        "previous_rate": round(prev_rate, 3),
                        "change_pct": change_pct,
                    },
                    "confidence": 0.75,
                    "period": "7d",
                })
        return insights

    def _demographic_insights(self, traffic: list) -> list[dict]:
        insights = []
        if not traffic:
            return insights

        male_total = sum(r.get("male_count", 0) for r in traffic)
        female_total = sum(r.get("female_count", 0) for r in traffic)
        total = male_total + female_total
        if total < 20:
            return insights

        male_pct = round(male_total / total * 100, 1)
        female_pct = round(female_total / total * 100, 1)

        age_buckets = defaultdict(int)
        for r in traffic:
            for bucket_name, count in (r.get("age_buckets") or {}).items():
                age_buckets[bucket_name] += count

        dominant_age = max(age_buckets, key=age_buckets.get) if age_buckets else None

        by_hour = defaultdict(lambda: {"male": 0, "female": 0, "ages": defaultdict(int)})
        for r in traffic:
            ws = r.get("window_start", "")
            try:
                dt = datetime.fromisoformat(ws.replace("Z", "+00:00"))
                hour = dt.hour
                by_hour[hour]["male"] += r.get("male_count", 0)
                by_hour[hour]["female"] += r.get("female_count", 0)
                for bucket_name, count in (r.get("age_buckets") or {}).items():
                    by_hour[hour]["ages"][bucket_name] += count
            except (ValueError, AttributeError):
                pass

        for hour, data in by_hour.items():
            h_total = data["male"] + data["female"]
            if h_total < 10:
                continue
            h_male_pct = data["male"] / h_total * 100
            dom_age = max(data["ages"], key=data["ages"].get) if data["ages"] else None
            if h_male_pct > 65 and dom_age:
                day_label = "morning" if hour < 12 else "afternoon" if hour < 17 else "evening"
                insights.append({
                    "type": "daypart_demographic",
                    "title": f"{day_label.title()}s are {h_male_pct:.0f}% male {dom_age}",
                    "body": (
                        f"Around {hour}:00, your traffic skews {h_male_pct:.0f}% male "
                        f"with dominant age group {dom_age}. "
                        f"Tailor promotions and menu specials to this segment."
                    ),
                    "data": {"hour": hour, "male_pct": h_male_pct, "dominant_age": dom_age},
                    "confidence": 0.7,
                    "period": "7d",
                })
                break

        if male_pct > 60 or female_pct > 60:
            dominant = "male" if male_pct > female_pct else "female"
            insights.append({
                "type": "gender_skew",
                "title": f"Your customers are {max(male_pct, female_pct):.0f}% {dominant}",
                "body": (
                    f"Of {total} detected visitors: {male_total} male ({male_pct}%), "
                    f"{female_total} female ({female_pct}%). "
                    f"{'Consider whether your brand and ambiance appeal equally.' if max(male_pct,female_pct)>70 else ''}"
                ),
                "data": {"male_pct": male_pct, "female_pct": female_pct, "total": total},
                "confidence": 0.8,
                "period": "7d",
            })

        return insights

    def _churn_risk(self, profiles: list, now: datetime) -> list[dict]:
        insights = []
        for p in profiles:
            visits = p.get("visit_count", 0)
            last_seen = p.get("last_seen", "")
            if visits < 4 or not last_seen:
                continue
            try:
                last_dt = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
                gap_days = (now - last_dt).days
                if gap_days >= 14:
                    emb_hash = p.get("embedding_hash", "")[:8]
                    insights.append({
                        "type": "churn_risk",
                        "title": f"Customer #{emb_hash} might be churning ({gap_days}-day gap)",
                        "body": (
                            f"This customer visited {visits} times (avg pattern: "
                            f"{p.get('visit_pattern', 'unknown')}). Last seen {gap_days} days ago. "
                            f"Predicted LTV: ${p.get('predicted_ltv', 0)/100:,.0f}/year."
                        ),
                        "data": {
                            "profile_hash": emb_hash,
                            "visit_count": visits,
                            "gap_days": gap_days,
                            "predicted_ltv": p.get("predicted_ltv", 0),
                        },
                        "confidence": 0.65,
                        "period": "snapshot",
                    })
            except (ValueError, AttributeError):
                continue

        if len(insights) > 5:
            insights = sorted(insights, key=lambda x: x["data"]["predicted_ltv"], reverse=True)[:5]
        return insights

    def _sentiment_insights(self, visits: list) -> list[dict]:
        insights = []
        sentiment_shifts = {"positive_to_negative": 0, "negative_to_positive": 0, "total": 0}

        for v in visits:
            entry = v.get("emotion_entry", "")
            exit_ = v.get("emotion_exit", "")
            if not entry or not exit_:
                continue
            sentiment_shifts["total"] += 1
            positive = {"happy", "surprise"}
            negative = {"sad", "angry", "fear", "disgust"}
            if entry in positive and exit_ in negative:
                sentiment_shifts["positive_to_negative"] += 1
            elif entry in negative and exit_ in positive:
                sentiment_shifts["negative_to_positive"] += 1

        total = sentiment_shifts["total"]
        if total >= 20:
            neg_shift = sentiment_shifts["positive_to_negative"]
            neg_pct = round(neg_shift / total * 100, 1)
            if neg_pct > 15:
                insights.append({
                    "type": "sentiment_decline",
                    "title": f"{neg_pct}% of customers leave less happy than they arrived",
                    "body": (
                        f"Of {total} visits with emotion data, {neg_shift} showed a mood decline "
                        f"(happy at entry, negative at exit). Check service speed, product availability, "
                        f"or environment issues."
                    ),
                    "data": sentiment_shifts,
                    "confidence": 0.6,
                    "period": "7d",
                })
        return insights

    def _zone_insights(self, visits: list) -> list[dict]:
        insights = []
        zone_counts = defaultdict(int)
        zone_dwell = defaultdict(list)

        for v in visits:
            for z in (v.get("zones_visited") or []):
                zone_counts[z] += 1
            dwell = v.get("dwell_seconds", 0)
            if dwell and v.get("zones_visited"):
                for z in v["zones_visited"]:
                    zone_dwell[z].append(dwell)

        if zone_counts:
            most_popular = max(zone_counts, key=zone_counts.get)
            least_popular = min(zone_counts, key=zone_counts.get)
            if zone_counts[most_popular] > zone_counts[least_popular] * 3 and len(zone_counts) >= 3:
                insights.append({
                    "type": "zone_imbalance",
                    "title": f"'{most_popular}' gets 3x+ more traffic than '{least_popular}'",
                    "body": (
                        f"{zone_counts[most_popular]} visits to {most_popular} vs "
                        f"{zone_counts[least_popular]} to {least_popular}. "
                        f"Consider layout changes or signage to distribute foot traffic."
                    ),
                    "data": dict(zone_counts),
                    "confidence": 0.75,
                    "period": "7d",
                })

        menu_dwell = zone_dwell.get("menu_board", [])
        if len(menu_dwell) >= 10:
            avg_menu = sum(menu_dwell) / len(menu_dwell)
            if avg_menu > 120:
                insights.append({
                    "type": "menu_confusion",
                    "title": f"Customers spend {avg_menu:.0f}s at the menu board — possible confusion",
                    "body": (
                        f"Average menu board dwell is {avg_menu:.0f} seconds ({len(menu_dwell)} observations). "
                        f"Over 2 minutes suggests decision fatigue. Simplify layout or add recommendations."
                    ),
                    "data": {"avg_dwell_sec": round(avg_menu, 1), "observations": len(menu_dwell)},
                    "confidence": 0.7,
                    "period": "7d",
                })

        return insights

    def _daypart_insights(self, traffic: list) -> list[dict]:
        insights = []
        dayparts = {"morning": (6, 11), "lunch": (11, 14), "afternoon": (14, 17), "evening": (17, 22)}
        dp_traffic = defaultdict(int)

        for r in traffic:
            ws = r.get("window_start", "")
            try:
                dt = datetime.fromisoformat(ws.replace("Z", "+00:00"))
                for name, (start, end) in dayparts.items():
                    if start <= dt.hour < end:
                        dp_traffic[name] += r.get("walk_ins", 0)
                        break
            except (ValueError, AttributeError):
                continue

        if dp_traffic:
            peak = max(dp_traffic, key=dp_traffic.get)
            dead = min(dp_traffic, key=dp_traffic.get)
            if dp_traffic[peak] > 0 and dp_traffic[dead] > 0:
                ratio = dp_traffic[peak] / dp_traffic[dead]
                if ratio > 3:
                    insights.append({
                        "type": "daypart_gap",
                        "title": f"{peak.title()} gets {ratio:.0f}x more walk-ins than {dead}",
                        "body": (
                            f"{peak.title()}: {dp_traffic[peak]} walk-ins. "
                            f"{dead.title()}: {dp_traffic[dead]}. "
                            f"Consider {dead} promotions or adjusted hours to balance traffic."
                        ),
                        "data": dict(dp_traffic),
                        "confidence": 0.8,
                        "period": "7d",
                    })
        return insights

    def _loyalty_insights(self, profiles: list) -> list[dict]:
        insights = []
        loyalists = [p for p in profiles if p.get("visit_count", 0) >= 4]
        total = len(profiles)

        if loyalists and total >= 20:
            loyalty_pct = len(loyalists) / total * 100
            total_ltv = sum(p.get("predicted_ltv", 0) for p in loyalists)
            avg_ltv = total_ltv // max(len(loyalists), 1)
            insights.append({
                "type": "loyalty_opportunity",
                "title": f"{len(loyalists)} regulars ({loyalty_pct:.0f}%) — your hidden loyalty program",
                "body": (
                    f"You have {len(loyalists)} customers with 4+ visits — they don't need a loyalty card, "
                    f"your cameras already recognize them. Combined predicted LTV: "
                    f"${total_ltv/100:,.0f}/year (avg ${avg_ltv/100:,.0f} per regular)."
                ),
                "data": {
                    "regulars": len(loyalists),
                    "loyalty_pct": round(loyalty_pct, 1),
                    "total_ltv": total_ltv,
                    "avg_ltv": avg_ltv,
                },
                "confidence": 0.75,
                "period": "snapshot",
            })
        return insights

    def _window_shopper_insights(self, visits: list) -> list[dict]:
        insights = []
        ws_who_converted = [
            v for v in visits
            if v.get("was_window_shopper") and v.get("converted_later")
        ]
        total_ws = sum(1 for v in visits if v.get("was_window_shopper"))

        if total_ws >= 10 and ws_who_converted:
            rate = len(ws_who_converted) / total_ws * 100
            insights.append({
                "type": "window_shopper_conversion",
                "title": f"{len(ws_who_converted)} window shoppers came back and bought ({rate:.0f}%)",
                "body": (
                    f"Of {total_ws} people who looked but didn't enter on first pass, "
                    f"{len(ws_who_converted)} returned and made a purchase. "
                    f"Your storefront is working as a billboard — invest in it."
                ),
                "data": {
                    "window_shoppers": total_ws,
                    "converted_later": len(ws_who_converted),
                    "conversion_rate": round(rate, 1),
                },
                "confidence": 0.7,
                "period": "7d",
            })
        return insights

    def _group_insights(self, traffic: list) -> list[dict]:
        insights = []
        total_walkins = sum(r.get("walk_ins", 0) for r in traffic)
        if total_walkins < 20:
            return insights

        returning = sum(r.get("returning_count", 0) for r in traffic)
        new_faces = sum(r.get("new_face_count", 0) for r in traffic)
        non_customers = sum(r.get("non_customer_count", 0) for r in traffic)

        if returning + new_faces > 0:
            returning_pct = round(returning / (returning + new_faces) * 100, 1)
            insights.append({
                "type": "new_vs_returning",
                "title": f"{returning_pct}% returning faces this week",
                "body": (
                    f"{returning} recognized returning visitors, {new_faces} new faces. "
                    f"{'Strong retention — your regulars keep coming back.' if returning_pct > 40 else 'Lots of new faces — great discovery, now focus on retention.'}"
                ),
                "data": {"returning": returning, "new_faces": new_faces, "returning_pct": returning_pct},
                "confidence": 0.8,
                "period": "7d",
            })

        if non_customers > 0:
            non_cust_pct = round(non_customers / max(total_walkins, 1) * 100, 1)
            if non_cust_pct > 20:
                insights.append({
                    "type": "non_customer_traffic",
                    "title": f"{non_customers} visitors ({non_cust_pct}%) browsed but didn't buy",
                    "body": (
                        f"These people entered your store but had no matching POS transaction. "
                        f"They're warm leads — greeting, samples, or time-limited offers may convert them."
                    ),
                    "data": {"non_customers": non_customers, "pct": non_cust_pct},
                    "confidence": 0.7,
                    "period": "7d",
                })
        return insights

    def _persist_insights(self, db, insights: list):
        if not insights:
            return
        try:
            rows = []
            for ins in insights:
                rows.append({
                    "org_id": self.org_id,
                    "type": ins["type"],
                    "title": ins["title"],
                    "body": ins["body"],
                    "data": ins.get("data", {}),
                    "confidence": ins.get("confidence", 0.5),
                    "period": ins.get("period", "7d"),
                })
            db.client.table("vision_insights").upsert(
                rows, on_conflict="org_id,type,period"
            ).execute()
        except Exception as e:
            logger.warning("Failed to persist vision insights: %s", e)
