"""
Grounded Top-Actions reasoner.

The legacy Top-Actions path is benchmark-templated, POS-only, dollar-sorted, and
the LLM (when enabled at all) only rewrites prose. This module replaces that with
a *grounded* reasoning step: it assembles a compact, structured evidence brief
from EVERY available signal (POS revenue/products/patterns, phone-agent calls and
orders, camera footfall, merchant-health, email engagement) plus the recent
accept/reject feedback loop, then asks the model to produce the next best actions
where **each action must cite the specific signals and values that justify it**.

Design rules:
  - Grounded, not generic. The system prompt forbids advice that isn't tied to a
    value in the brief, and requires the model to say so when a signal is absent
    rather than inventing one.
  - Cite-or-drop. Every action carries an `evidence` list naming the signals it
    used; actions with no evidence are discarded.
  - Feedback-aware. Action types the merchant recently rejected/completed are
    passed in so the model stops re-surfacing them.
  - Fail-soft. Any error returns [] and the caller keeps the rule-based insights.
  - Flag-gated by the caller (GROUNDED_ACTIONS_ENABLED); off by default.
"""
import logging
from datetime import datetime, timedelta, timezone
from uuid import uuid4

logger = logging.getLogger("meridian.ai.grounded_actions")

GROUNDED_MODEL_VERSION = "meridian-grounded-actions-v1"

SYSTEM_PROMPT = (
    "You are Meridian's senior operations analyst for a small business. You are "
    "given a STRUCTURED EVIDENCE BRIEF assembled from this specific merchant's "
    "own data across multiple systems: point-of-sale revenue/products/timing, "
    "phone-agent calls and orders, in-store camera footfall, a merchant-health "
    "score, and email engagement.\n\n"
    "Your job: produce the highest-value concrete actions the owner should take "
    "THIS WEEK. Rules you must follow exactly:\n"
    "1. GROUND EVERYTHING. Every action must be justified by specific numbers "
    "from the brief. In each action's `evidence`, name the signal and quote the "
    "value you used (e.g. {\"signal\": \"phone.missed_call_rate\", \"detail\": "
    "\"23% of 48 calls went unanswered\"}). An action with no evidence from the "
    "brief is forbidden.\n"
    "2. NO GENERIC PLAYBOOK ADVICE. Do not give advice that would apply to any "
    "business ('post on social media', 'run a promotion') unless a number in the "
    "brief specifically points to it.\n"
    "3. BE HONEST ABOUT GAPS. If a system has no data (e.g. no camera, no calls), "
    "do not invent activity for it and do not recommend acting on it.\n"
    "4. QUANTIFY IMPACT. Give `estimated_monthly_impact_cents` as an integer when "
    "the brief supports an estimate (show your basis in the evidence); use null "
    "when you genuinely cannot estimate. Do not fabricate precision.\n"
    "5. DON'T REPEAT REJECTED WORK. The brief lists action types the owner "
    "recently dismissed or completed — do not re-surface those angles.\n"
    "6. Each action: a short imperative `title`, a 1-2 sentence `summary` of WHY "
    "(with the numbers), and a concrete `action_item` (what to literally do).\n\n"
    "Return ONLY a JSON object of this exact shape (no prose outside it):\n"
    '{"actions": [{"type": "short_slug", "title": "...", "summary": "...", '
    '"action_item": "...", "estimated_monthly_impact_cents": 12345 or null, '
    '"confidence_score": 0.0-1.0, "evidence": [{"signal": "brief.key", '
    '"detail": "the value you used"}]}]}'
)

# json_object (not strict json_schema): the gateway's default tier is DeepSeek,
# which rejects json_schema response_format ("This response_format type is
# unavailable now"). json_object is supported by DeepSeek and OpenAI alike; the
# exact shape is specified in the prompt and parsing here is defensive
# (cite-or-drop + field coercion), so a slightly-off envelope degrades safely.
_RESPONSE_FORMAT = {"type": "json_object"}


def _safe_num(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _summarize_phone(calls: list[dict], orders: list[dict]) -> dict | None:
    if not calls and not orders:
        return None
    total_calls = len(calls)
    # A call is "unanswered/abandoned" if it never reached a completed status.
    answered = sum(1 for c in calls if (c.get("status") or "").lower() in ("completed", "complete", "order_placed"))
    durations = [int(c.get("duration_seconds") or 0) for c in calls if c.get("duration_seconds")]
    avg_dur = round(sum(durations) / len(durations), 1) if durations else None
    pos_pushed = sum(1 for o in orders if o.get("pos_success"))
    order_total = sum(_safe_num(o.get("total")) for o in orders)
    return {
        "total_calls": total_calls,
        "answered_calls": answered,
        "unanswered_rate_pct": round((total_calls - answered) / total_calls * 100, 1) if total_calls else None,
        "avg_call_duration_sec": avg_dur,
        "phone_orders": len(orders),
        "phone_orders_pushed_to_pos": pos_pushed,
        "phone_order_revenue_dollars": round(order_total, 2),
    }


def _summarize_vision(traffic: list[dict]) -> dict | None:
    if not traffic:
        return None
    entries = sum(int(t.get("entries") or 0) for t in traffic)
    convs = [_safe_num(t.get("conversion_rate")) for t in traffic if t.get("conversion_rate") is not None]
    peak_occ = max((int(t.get("occupancy_peak") or 0) for t in traffic), default=0)
    waits = [_safe_num(t.get("queue_wait_avg_sec")) for t in traffic if t.get("queue_wait_avg_sec")]
    return {
        "buckets": len(traffic),
        "total_entries": entries,
        "avg_conversion_rate_pct": round(sum(convs) / len(convs) * 100, 1) if convs else None,
        "peak_occupancy": peak_occ,
        "avg_queue_wait_sec": round(sum(waits) / len(waits), 1) if waits else None,
    }


def _summarize_health(rows: list[dict]) -> dict | None:
    if not rows:
        return None
    # Most recent score per category.
    latest: dict[str, dict] = {}
    for r in rows:
        cat = r.get("category") or "overall"
        if cat not in latest:
            latest[cat] = r
    return {
        cat: {"score": r.get("score"), "trend": r.get("trend")}
        for cat, r in latest.items()
    }


def _summarize_email(rows: list[dict]) -> dict | None:
    if not rows:
        return None
    sent = len(rows)
    opened = sum(1 for r in rows if r.get("opened_at"))
    clicked = sum(1 for r in rows if r.get("clicked_at"))
    bounced = sum(1 for r in rows if r.get("bounced_at"))
    return {
        "sent": sent,
        "open_rate_pct": round(opened / sent * 100, 1) if sent else None,
        "click_rate_pct": round(clicked / sent * 100, 1) if sent else None,
        "bounce_rate_pct": round(bounced / sent * 100, 1) if sent else None,
    }


def _summarize_feedback(rows: list[dict]) -> dict | None:
    """Action types the merchant recently dismissed or completed — so we don't
    re-surface them."""
    if not rows:
        return None
    dismissed, completed = set(), set()
    for r in rows:
        status = (r.get("action_status") or "").lower()
        t = r.get("type") or ""
        if status in ("rejected", "dismissed"):
            dismissed.add(t)
        elif status == "completed":
            completed.add(t)
    if not dismissed and not completed:
        return None
    return {
        "recently_dismissed_types": sorted(dismissed),
        "recently_completed_types": sorted(completed),
    }


def build_evidence_brief(ctx, revenue, products, patterns, money_left, candidate_insights) -> dict:
    """Assemble the compact multi-source brief handed to the model. Everything is
    optional; absent signals are simply omitted so the model sees real gaps."""
    brief: dict = {
        "business_vertical": getattr(ctx, "business_vertical", "other"),
        "analysis_days": getattr(ctx, "analysis_days", 30),
    }

    # POS-derived analyses (already computed by the rule engine) — pass the
    # headline numbers, not the raw rows.
    if isinstance(revenue, dict) and revenue:
        brief["revenue"] = {
            k: revenue.get(k)
            for k in ("total_revenue", "avg_daily_revenue", "trend", "trend_pct",
                      "growth_rate", "best_day", "worst_day")
            if revenue.get(k) is not None
        }
    if isinstance(products, dict) and products:
        brief["products"] = {
            k: products.get(k)
            for k in ("top_products", "underperformers", "dead_stock", "margin_leaders")
            if products.get(k) is not None
        }
    if isinstance(patterns, dict) and patterns:
        brief["timing"] = {
            k: patterns.get(k)
            for k in ("peak_hours", "slow_hours", "peak_days", "slow_days")
            if patterns.get(k) is not None
        }
    if isinstance(money_left, dict) and money_left:
        brief["money_left_on_table"] = {
            k: money_left.get(k)
            for k in ("total_score", "score", "top_opportunities", "biggest_gap")
            if money_left.get(k) is not None
        }

    # Multi-source signals (the whole point of the upgrade).
    phone = _summarize_phone(getattr(ctx, "phone_calls", []), getattr(ctx, "phone_orders", []))
    if phone:
        brief["phone"] = phone
    vision = _summarize_vision(getattr(ctx, "vision_traffic", []))
    if vision:
        brief["camera_footfall"] = vision
    health = _summarize_health(getattr(ctx, "merchant_health", []))
    if health:
        brief["merchant_health"] = health
    email = _summarize_email(getattr(ctx, "email_engagement", []))
    if email:
        brief["email_engagement"] = email
    feedback = _summarize_feedback(getattr(ctx, "action_feedback", []))
    if feedback:
        brief["recent_action_feedback"] = feedback

    # Give the model the rule engine's candidate titles as priors it may keep,
    # merge, or override — but it must still ground them in the brief.
    if candidate_insights:
        brief["rule_engine_candidates"] = [
            {"type": i.get("type"), "title": i.get("title"),
             "impact_cents": i.get("estimated_monthly_impact_cents")}
            for i in candidate_insights[:12]
        ]

    return brief


def _to_insight(ctx, action: dict) -> dict | None:
    """Map one model action to the persisted insight shape the actions route
    reads. Drops actions with no evidence (cite-or-drop)."""
    evidence = action.get("evidence") or []
    if not evidence:
        return None
    title = (action.get("title") or "").strip()
    summary = (action.get("summary") or "").strip()
    if not title or not summary:
        return None
    raw_type = (action.get("type") or "grounded_action").strip().lower().replace(" ", "_")[:48]
    impact = action.get("estimated_monthly_impact_cents")
    impact = int(impact) if isinstance(impact, (int, float)) else 0
    conf = action.get("confidence_score")
    conf = float(conf) if isinstance(conf, (int, float)) else 0.6
    conf = max(0.0, min(1.0, conf))
    return {
        "id": str(uuid4()),
        "org_id": ctx.org_id,
        "location_id": getattr(ctx, "location_id", None),
        "type": f"grounded_{raw_type}" if not raw_type.startswith("grounded") else raw_type,
        "title": title,
        "summary": summary,
        "details": {
            "action_item": (action.get("action_item") or "").strip(),
            "evidence": evidence,
            "source": "grounded_engine",
        },
        "estimated_monthly_impact_cents": impact,
        "confidence_score": conf,
        "related_products": [],
        "related_categories": [],
        "action_status": "pending",
        "valid_until": (datetime.now(timezone.utc) + timedelta(days=14)).isoformat(),
        "model_version": GROUNDED_MODEL_VERSION,
        "metadata": {"engine": "grounded", "grounded": True, "evidence_count": len(evidence)},
    }


async def generate_grounded_actions(
    ctx,
    revenue: dict,
    products: dict,
    patterns: dict,
    money_left: dict,
    candidate_insights: list[dict],
    top_n: int = 5,
) -> list[dict]:
    """Run the grounded reasoner. Returns insight dicts (persist-ready) or []."""
    import json

    try:
        brief = build_evidence_brief(ctx, revenue, products, patterns, money_left, candidate_insights)

        # Need at least one real signal beyond the trivial header to bother.
        signal_keys = set(brief) - {"business_vertical", "analysis_days", "rule_engine_candidates"}
        if not signal_keys:
            logger.info("grounded_actions: no usable signals for %s — skipping", ctx.org_id)
            return []

        user_content = (
            f"Produce up to {top_n} grounded actions. "
            "EVIDENCE BRIEF (this merchant's own data):\n" + json.dumps(brief, default=str)
        )
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

        from .llm_layer import _call_llm
        out = await _call_llm(messages, _RESPONSE_FORMAT, org_id=ctx.org_id, agent_name="grounded_actions")
        if not out or not isinstance(out, dict):
            logger.info("grounded_actions: empty LLM result for %s", ctx.org_id)
            return []

        actions = out.get("actions") or []
        insights = []
        for a in actions[:top_n]:
            ins = _to_insight(ctx, a)
            if ins:
                insights.append(ins)
        logger.info("grounded_actions: %s grounded actions for %s (from %s signals)",
                    len(insights), ctx.org_id, len(signal_keys))
        return insights
    except Exception as e:  # noqa: BLE001
        logger.error("grounded_actions failed for %s: %s", getattr(ctx, "org_id", "?"), e, exc_info=True)
        return []
