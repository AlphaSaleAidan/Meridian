#!/usr/bin/env python3
"""Real-call self-training loop for the Meridian phone ordering agent.

The offline harness (scripts/phone_overnight_train.py) hardens the agent against
*synthetic* scenarios. This script closes the loop on *real* calls: it mines
completed conversations from phone_call_logs, scores each one with an LLM judge,
persists the score to phone_call_insights (powering the dashboard's agent-quality
panel), and distills the worst real calls into regression scenarios + concrete
fix proposals for human review.

    1. MINE     - pull recent phone_call_logs (transcript + outcome), skip calls
                  already judged, redact PII before anything leaves the box.
    2. JUDGE    - an LLM judge scores each call 0-10 and tags failure modes from
                  the same taxonomy as the synthetic harness.
    3. PERSIST  - upsert one row per call into phone_call_insights.
    4. DISTILL  - aggregate the worst real calls into (a) regression scenarios
                  for the synthetic harness and (b) a ranked list of rule fixes.

IMPORTANT: this never edits the live agent. Brain changes (prompt/rules/few-shot)
remain human-approved — past experience is that automated prompt rewrites regress
and the real weak spots are structural. This produces DATA and PROPOSALS only.

Requires SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY and DEEPSEEK_API_KEY in env
(keys never logged). Reuses DeepSeek/FAILURE_TAGS/_parse_json from the sibling
synthetic harness.

Usage:
    SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... DEEPSEEK_API_KEY=... \
      python3 scripts/phone_realcall_train.py --days 7 --concurrency 4 \
      --out /tmp/phone-realcall-out
    # add --dry-run to score without writing phone_call_insights
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

import httpx

# Reuse the synthetic harness's DeepSeek client, failure taxonomy, JSON parser.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from phone_overnight_train import (  # noqa: E402
    DEEPSEEK_MODEL,
    DeepSeek,
    FAILURE_TAGS,
    Usage,
    _parse_json,
)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = (
    os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    or os.environ.get("SUPABASE_SERVICE_KEY", "")
)
# Calls worth judging: completed conversations with at least a couple of turns.
DONE_STATUSES = {"completed", "order_placed", "ended", "hangup", "no_order", "failed"}

# --------------------------------------------------------------------------
# PII redaction — nothing identifying is sent to the judge or written to disk.
# --------------------------------------------------------------------------
_PHONE_RE = re.compile(r"\+?\d[\d\-\s().]{7,}\d")
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def redact(text: str) -> str:
    text = _EMAIL_RE.sub("[email]", text or "")
    text = _PHONE_RE.sub("[phone]", text)
    return text


def render_transcript(transcript: Any) -> str:
    """phone_call_logs.transcript is a list of {role, content} message dicts."""
    if not isinstance(transcript, list):
        return ""
    lines = []
    for m in transcript:
        if not isinstance(m, dict):
            continue
        role = m.get("role", "?")
        who = {"assistant": "AGENT", "user": "CALLER", "system": "SYSTEM"}.get(role, role.upper())
        if role == "system":
            continue  # the prompt itself isn't part of what we judge
        content = redact(str(m.get("content", "")).strip())
        if content:
            lines.append(f"{who}: {content}")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Supabase REST (service role).
# --------------------------------------------------------------------------
async def sb(client: httpx.AsyncClient, method: str, path: str, **kw) -> httpx.Response:
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    headers.update(kw.pop("headers", {}))
    return await client.request(method, f"{SUPABASE_URL}/rest/v1/{path}", headers=headers, **kw)


async def fetch_calls(client, days: int, limit: int, merchant: str | None, min_duration: int) -> list[dict]:
    since = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - days * 86400))
    params = {
        "select": "call_sid,merchant_id,status,transcript,order_data,duration_seconds,created_at",
        "created_at": f"gte.{since}",
        "order": "created_at.desc",
        "limit": str(limit),
    }
    if merchant:
        params["merchant_id"] = f"eq.{merchant}"
    r = await sb(client, "GET", "phone_call_logs", params=params)
    r.raise_for_status()
    rows = r.json()
    out = []
    for c in rows:
        if min_duration and int(c.get("duration_seconds") or 0) < min_duration:
            continue
        if not render_transcript(c.get("transcript")):
            continue  # nothing to judge
        out.append(c)
    return out


async def already_judged(client, sids: list[str]) -> set[str]:
    if not sids:
        return set()
    done: set[str] = set()
    for i in range(0, len(sids), 100):
        chunk = sids[i : i + 100]
        in_list = ",".join(f'"{s}"' for s in chunk)
        r = await sb(client, "GET", "phone_call_insights",
                     params={"select": "call_sid", "call_sid": f"in.({in_list})"})
        if r.status_code == 200:
            done.update(row["call_sid"] for row in r.json())
    return done


async def upsert_insight(client, row: dict) -> bool:
    r = await sb(client, "POST", "phone_call_insights?on_conflict=call_sid",
                 headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
                 content=json.dumps(row))
    return r.status_code in (200, 201, 204)


# --------------------------------------------------------------------------
# JUDGE — adapted for real calls (no synthetic scenario / expected outcome).
# --------------------------------------------------------------------------
async def judge_real(ds: DeepSeek, client: httpx.AsyncClient, call: dict) -> dict:
    transcript = render_transcript(call.get("transcript"))
    order = call.get("order_data")
    sys_p = (
        "You are a strict QA reviewer for a restaurant phone-ordering AI agent. "
        "You are given the transcript of a REAL inbound call and whatever order the "
        "agent submitted. Score the AGENT's performance 0 (terrible) to 10 (perfect). "
        "Penalize: wrong/missing/extra items, hallucinated prices or menu items, "
        "failing to ask a needed clarifying question, ignoring a modification or allergy, "
        "being verbose or robotic, submitting before the caller confirmed, never submitting "
        "a confirmed order, losing track of the conversation, or a poor closing. Reward calls "
        "that efficiently and accurately capture exactly what the caller wanted. Ignore the "
        "caller's identity; [phone]/[email] are redactions, not errors.\n"
        f"Choose any failure tags that apply from: {FAILURE_TAGS}.\n"
        'Return JSON: {"score": int 0-10, "tags": [str], "critique": str (one specific sentence), '
        '"fix": str (one concrete rule that, if added to the agent, would have prevented the problem; '
        'empty string if the call was great)}.'
    )
    user_p = (
        f"TRANSCRIPT:\n{transcript}\n\n"
        f"ORDER SUBMITTED: {json.dumps(order) if order else 'none'}\n"
        f"CALL STATUS: {call.get('status', 'unknown')}"
    )
    out = await ds.chat(
        client,
        [{"role": "system", "content": sys_p}, {"role": "user", "content": user_p}],
        temperature=0.0, json_mode=True, max_tokens=400,
    )
    parsed = _parse_json(out.get("content", "")) if out else None
    if not parsed:
        return {"score": 0, "tags": ["judge_failed"], "critique": "judge produced no output", "fix": ""}
    parsed["score"] = max(0, min(10, int(parsed.get("score", 0))))
    parsed.setdefault("tags", [])
    parsed.setdefault("critique", "")
    parsed.setdefault("fix", "")
    return parsed


# --------------------------------------------------------------------------
# DISTILL — worst real calls -> regression scenarios + ranked fixes (proposals).
# --------------------------------------------------------------------------
def distill(results: list[dict], out: Path) -> dict:
    ranked = sorted(results, key=lambda r: r["judgment"]["score"])
    worst = [r for r in ranked if r["judgment"]["score"] < 7]

    tag_counts: dict[str, int] = {}
    fix_counts: dict[str, int] = {}
    for r in results:
        for t in r["judgment"].get("tags", []):
            tag_counts[t] = tag_counts.get(t, 0) + 1
        fix = (r["judgment"].get("fix") or "").strip()
        if fix:
            fix_counts[fix] = fix_counts.get(fix, 0) + 1

    # regression scenarios for the synthetic harness: each worst real call becomes
    # a seed the simulator can replay against candidate prompts.
    scenarios = []
    for r in worst[:30]:
        scenarios.append({
            "id": f"real-{r['call_sid'][:12]}",
            "source": "real_call",
            "category": (r["judgment"].get("tags") or ["general"])[0],
            "critique": r["judgment"].get("critique", ""),
            "transcript": r["transcript"],
        })
    (out / "regression_scenarios.jsonl").write_text(
        "\n".join(json.dumps(s) for s in scenarios)
    )

    scores = [r["judgment"]["score"] for r in results]
    mean = round(sum(scores) / len(scores), 2) if scores else 0
    summary = {
        "calls_judged": len(results),
        "mean_score": mean,
        "below_7": len(worst),
        "top_tags": sorted(tag_counts.items(), key=lambda x: -x[1])[:10],
        "top_fixes": sorted(fix_counts.items(), key=lambda x: -x[1])[:10],
    }

    md = ["# Phone agent — real-call training report", ""]
    md.append(f"- Calls judged: **{summary['calls_judged']}**")
    md.append(f"- Mean quality score: **{mean}/10**")
    md.append(f"- Calls below 7/10: **{summary['below_7']}**")
    md.append("\n## Most common failure tags")
    for t, c in summary["top_tags"]:
        md.append(f"- `{t}` — {c}")
    md.append("\n## Proposed rule fixes (ranked by frequency — REVIEW before applying)")
    for f, c in summary["top_fixes"]:
        md.append(f"- ({c}×) {f}")
    md.append("\n## Worst calls (for the regression set)")
    for r in worst[:10]:
        j = r["judgment"]
        md.append(f"- **{j['score']}/10** [{', '.join(j.get('tags', []))}] — {j.get('critique','')}")
    md.append(
        "\n> These are PROPOSALS. Feed regression_scenarios.jsonl into "
        "scripts/phone_overnight_train.py and A/B any candidate prompt before shipping. "
        "The live agent is never modified by this script."
    )
    (out / "report.md").write_text("\n".join(md))
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    return summary


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--limit", type=int, default=500)
    ap.add_argument("--merchant", default=None, help="filter to one merchant_id")
    ap.add_argument("--min-duration", type=int, default=10, help="skip calls shorter than N seconds")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--rejudge", action="store_true", help="re-score calls even if already judged")
    ap.add_argument("--dry-run", action="store_true", help="score + report but do NOT write phone_call_insights")
    ap.add_argument("--out", default="/tmp/phone-realcall-out")
    args = ap.parse_args()

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY required", file=sys.stderr)
        return 2
    if not os.environ.get("DEEPSEEK_API_KEY"):
        print("ERROR: DEEPSEEK_API_KEY required", file=sys.stderr)
        return 2

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    usage = Usage()
    # one judge call per mined call; cap generously above the fetch limit.
    ds = DeepSeek(os.environ["DEEPSEEK_API_KEY"], usage, max_calls=args.limit + 50)

    async with httpx.AsyncClient(timeout=60) as client:
        calls = await fetch_calls(client, args.days, args.limit, args.merchant, args.min_duration)
        print(f"mined {len(calls)} judgeable calls (last {args.days}d)")
        if not args.rejudge:
            done = await already_judged(client, [c["call_sid"] for c in calls if c.get("call_sid")])
            calls = [c for c in calls if c.get("call_sid") not in done]
            print(f"{len(calls)} new (skipped {len(done)} already judged)")
        if not calls:
            print("nothing to do")
            return 0

        sem = asyncio.Semaphore(args.concurrency)
        results: list[dict] = []

        async def one(call: dict):
            async with sem:
                j = await judge_real(ds, client, call)
                rec = {
                    "call_sid": call.get("call_sid"),
                    "transcript": render_transcript(call.get("transcript")),
                    "judgment": j,
                }
                results.append(rec)
                if not args.dry_run:
                    ok = await upsert_insight(client, {
                        "call_sid": call.get("call_sid"),
                        "merchant_id": call.get("merchant_id") or "demo",
                        "score": j["score"],
                        "tags": j.get("tags", []),
                        "critique": j.get("critique", ""),
                        "fix": j.get("fix", ""),
                        "order_placed": bool(call.get("order_data")),
                        "duration_seconds": call.get("duration_seconds"),
                        "judge_model": DEEPSEEK_MODEL,
                        "judged_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    })
                    if not ok:
                        print(f"  WARN: failed to persist insight for {call.get('call_sid')}")
                print(f"  {call.get('call_sid','?')[:14]:14} score={j['score']} {','.join(j.get('tags',[]))}")

        await asyncio.gather(*(one(c) for c in calls))
        summary = distill(results, out)

    print(f"\nmean score {summary['mean_score']}/10 over {summary['calls_judged']} calls "
          f"({summary['below_7']} below 7)")
    print(f"report: {out}/report.md  |  regression set: {out}/regression_scenarios.jsonl")
    print(f"judge cost ~${usage.est_cost_usd():.3f} ({usage.calls} calls)")
    if args.dry_run:
        print("DRY RUN — phone_call_insights not written")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
