#!/usr/bin/env python3
"""Wrong-order detector for the Meridian phone ordering agent.

Today the only guard against the agent mis-hearing an order is the read-back it
performs mid-call: if the caller doesn't catch the mistake, nobody does. This
script is the systematic check that runs after the fact. For every recent call
that has BOTH a transcript and a submitted order, an LLM judge is shown what was
said and what was captured, and asked one narrow question: does the captured
order match what the caller actually asked for?

    1. MINE    - pull recent phone_call_logs that have a transcript + order_data,
                 skip calls already checked, redact PII before anything leaves
                 the box (caller phone/email/name never reach the judge).
    2. JUDGE   - one focused DeepSeek call per order; returns a structured
                 verdict with itemised discrepancies.
    3. PERSIST - upsert one row per call into phone_order_accuracy.

Severity is computed here, not by the judge, so it stays predictable:
    high   - missing / extra / wrong item, or an ignored allergy
    medium - wrong quantity or wrong size
    low    - wrong modifier, anything unrecognised, or a low-confidence verdict
    none   - order matches

IMPORTANT: this is detection and review only. It never edits an order, never
blocks a submission, and never touches the live agent — same contract as
scripts/phone_realcall_train.py. Every failure mode is quiet: a judge error, a
malformed verdict or a write failure is counted and skipped, never raised.

Requires SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY and DEEPSEEK_API_KEY in env
(keys never logged). Reuses the DeepSeek client and JSON parser from
scripts/phone_overnight_train.py rather than standing up a second LLM client.

Usage:
    SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... DEEPSEEK_API_KEY=... \
      python3 scripts/phone_order_accuracy.py --days 3 --concurrency 3 \
      --out /tmp/phone-order-accuracy
    # add --dry-run to judge without writing phone_order_accuracy
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
# DeepSeek client, usage accounting and JSON parser come from the synthetic
# harness — the LLM client is never rebuilt.
from phone_overnight_train import (  # noqa: E402
    DEEPSEEK_MODEL,
    DeepSeek,
    Usage,
    _parse_json,
)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = (
    os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    or os.environ.get("SUPABASE_SERVICE_KEY", "")
)

# --------------------------------------------------------------------------
# PII redaction — nothing identifying is sent to the judge or written to disk.
# Same contract and patterns as the real-call training harness.
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
        who = {"assistant": "AGENT", "user": "CALLER", "system": "SYSTEM"}.get(
            role, str(role).upper()
        )
        if role == "system":
            continue  # the agent's own prompt isn't part of what the caller asked for
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
    return await client.request(
        method, f"{SUPABASE_URL}/rest/v1/{path}", headers=headers, **kw
    )

# Discrepancy taxonomy -> severity. A mis-captured order is worse the further it
# is from what the caller said: a missing or invented item means the wrong food
# leaves the kitchen; a wrong size is a smaller (but still chargeable) error.
DISCREPANCY_SEVERITY = {
    "ignored_allergy": "high",
    "missing_item": "high",
    "extra_item": "high",
    "wrong_item": "high",
    "wrong_quantity": "medium",
    "wrong_size": "medium",
    "wrong_modifier": "low",
}
DISCREPANCY_TYPES = list(DISCREPANCY_SEVERITY)
_SEVERITY_RANK = {"none": 0, "low": 1, "medium": 2, "high": 3}

# Order fields that identify the caller — stripped before the order is serialised
# for the judge. The judge only needs the line items.
#
# Deliberately NOT including a bare "name": that is the line item's own name
# ("Latte"), which is the single most important thing the judge has to compare.
# A nested {"customer": {"name": ...}} is handled by dropping "customer" whole.
_PII_ORDER_KEYS = {
    "customer_name", "caller_name", "customer_phone", "caller_phone",
    "phone", "phone_number", "customer_email", "email", "address",
    "delivery_address", "customer",
}


def scrub_order(order: Any) -> Any:
    """Strip caller-identifying fields from a captured order, recursively, then
    redact any phone/email that survives inside a free-text field."""
    if isinstance(order, dict):
        return {
            k: scrub_order(v)
            for k, v in order.items()
            if k.lower() not in _PII_ORDER_KEYS
        }
    if isinstance(order, list):
        return [scrub_order(v) for v in order]
    if isinstance(order, str):
        return redact(order)
    return order


def severity_for(
    matches: bool,
    discrepancies: list[dict],
    confidence: float,
    min_confidence: float,
) -> str:
    """Worst discrepancy wins. A verdict the judge isn't sure about is capped at
    'low' so the review queue stays sorted by things that are probably real.

    A flagged call with no itemised discrepancy is unactionable but still real,
    so it lands at 'low' rather than disappearing into 'none'.
    """
    if matches:
        return "none"
    worst = "low"
    for d in discrepancies:
        sev = DISCREPANCY_SEVERITY.get(str(d.get("type", "")).strip().lower(), "low")
        if _SEVERITY_RANK[sev] > _SEVERITY_RANK[worst]:
            worst = sev
    if confidence < min_confidence:
        return "low"
    return worst


# --------------------------------------------------------------------------
# MINE
# --------------------------------------------------------------------------
async def fetch_orders(
    client: httpx.AsyncClient,
    days: int,
    limit: int,
    merchant: str | None,
) -> list[dict]:
    """Recent calls that actually have an order to check."""
    since = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - days * 86400))
    params = {
        "select": "call_sid,merchant_id,status,transcript,order_data,duration_seconds,created_at",
        "created_at": f"gte.{since}",
        "order_data": "not.is.null",
        "order": "created_at.desc",
        "limit": str(limit),
    }
    if merchant:
        params["merchant_id"] = f"eq.{merchant}"
    r = await sb(client, "GET", "phone_call_logs", params=params)
    r.raise_for_status()

    out = []
    for c in r.json():
        if not c.get("call_sid"):
            continue  # no natural key -> can't dedupe or reference it later
        if not c.get("order_data"):
            continue
        if not render_transcript(c.get("transcript")):
            continue  # nothing was said, or nothing survived rendering
        out.append(c)
    return out


async def already_checked(client: httpx.AsyncClient, sids: list[str]) -> set[str]:
    if not sids:
        return set()
    done: set[str] = set()
    for i in range(0, len(sids), 100):
        in_list = ",".join(f'"{s}"' for s in sids[i : i + 100])
        r = await sb(client, "GET", "phone_order_accuracy",
                     params={"select": "call_sid", "call_sid": f"in.({in_list})"})
        if r.status_code == 200:
            done.update(row["call_sid"] for row in r.json())
    return done


async def upsert_finding(client: httpx.AsyncClient, row: dict) -> bool:
    r = await sb(client, "POST", "phone_order_accuracy?on_conflict=call_sid",
                 headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
                 content=json.dumps(row))
    return r.status_code in (200, 201, 204)


# --------------------------------------------------------------------------
# JUDGE
# --------------------------------------------------------------------------
async def judge_order(ds: DeepSeek, client: httpx.AsyncClient, call: dict) -> dict | None:
    """One narrow question: does the captured order match the call?

    Returns a verdict dict, or None if the judge failed / returned nonsense —
    the caller skips those rather than inventing a verdict.
    """
    transcript = render_transcript(call.get("transcript"))
    order = scrub_order(call.get("order_data"))

    sys_p = (
        "You audit a restaurant phone-ordering AI for ORDER ACCURACY only. You are "
        "given the transcript of a real call and the order the system captured from "
        "it. Decide one thing: does the captured order match what the caller "
        "actually asked for by the end of the call?\n"
        "Judge only the final state of the order. Callers change their mind — if "
        "someone orders two coffees and then says 'actually make it one', one coffee "
        "is CORRECT. Items the agent offered and the caller declined are correctly "
        "absent. Prices, totals and tax are not your concern. [phone] and [email] "
        "are redactions, not errors, and a missing customer name is expected.\n"
        f"Each discrepancy must use one of these types: {DISCREPANCY_TYPES}.\n"
        "Set confidence to how sure you are: 1.0 when the transcript states the "
        "order plainly, lower when the audio was clearly garbled or the caller was "
        "ambiguous.\n"
        'Return JSON: {"order_matches": bool, "confidence": float 0-1, '
        '"discrepancies": [{"type": str, "item": str, "expected": str, '
        '"captured": str, "detail": str}], "summary": str (one sentence; empty if '
        'the order matches)}. If the order matches, discrepancies MUST be empty.'
    )
    user_p = (
        f"TRANSCRIPT:\n{transcript}\n\n"
        f"ORDER CAPTURED BY THE SYSTEM:\n{json.dumps(order, indent=2)}"
    )

    try:
        out = await ds.chat(
            client,
            [{"role": "system", "content": sys_p}, {"role": "user", "content": user_p}],
            temperature=0.0, json_mode=True, max_tokens=700,
        )
    except Exception as exc:  # noqa: BLE001 — a judge failure must not end the sweep
        print(f"  ! judge error on {call.get('call_sid','?')}: {exc!r}", file=sys.stderr)
        return None

    parsed = _parse_json(out.get("content", "")) if out else None
    if not isinstance(parsed, dict) or "order_matches" not in parsed:
        return None
    return normalize_verdict(parsed)


def normalize_verdict(parsed: dict) -> dict:
    """Coerce whatever the judge returned into the shape we persist."""
    try:
        confidence = float(parsed.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))

    discrepancies = []
    for d in parsed.get("discrepancies") or []:
        if not isinstance(d, dict):
            continue
        dtype = str(d.get("type", "")).strip().lower()
        discrepancies.append({
            "type": dtype if dtype in DISCREPANCY_SEVERITY else "wrong_item",
            "item": str(d.get("item", "")),
            "expected": str(d.get("expected", "")),
            "captured": str(d.get("captured", "")),
            "detail": str(d.get("detail", "")),
        })

    # The two halves of the verdict can disagree. An order only counts as
    # matching when the judge says so AND lists nothing wrong — a listed
    # discrepancy always flags, and a bare "mismatch" is trusted even when the
    # judge failed to itemise it.
    matches = bool(parsed.get("order_matches")) and not discrepancies

    return {
        "order_matches": matches,
        "confidence": confidence,
        "discrepancies": discrepancies,
        "summary": str(parsed.get("summary", "") or ""),
    }


# --------------------------------------------------------------------------
# SWEEP
# --------------------------------------------------------------------------
async def check_call(
    ds: DeepSeek,
    client: httpx.AsyncClient,
    call: dict,
    *,
    min_confidence: float,
    dry_run: bool,
) -> dict | None:
    """Judge one call and persist the finding. Returns the finding, or None if
    the call was skipped for any reason."""
    verdict = await judge_order(ds, client, call)
    if verdict is None:
        return None

    severity = severity_for(
        verdict["order_matches"], verdict["discrepancies"],
        verdict["confidence"], min_confidence,
    )
    order = call.get("order_data") or {}
    total = order.get("total") if isinstance(order, dict) else None

    finding = {
        "call_sid": call.get("call_sid"),
        "merchant_id": call.get("merchant_id") or "demo",
        "order_matches": verdict["order_matches"],
        "confidence": round(verdict["confidence"], 3),
        "severity": severity,
        "discrepancies": verdict["discrepancies"],
        "summary": verdict["summary"],
        "order_total": total,
        "duration_seconds": call.get("duration_seconds"),
        "judge_model": DEEPSEEK_MODEL,
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    if not dry_run:
        try:
            if not await upsert_finding(client, finding):
                print(f"  WARN: failed to persist finding for {finding['call_sid']}",
                      file=sys.stderr)
        except Exception as exc:  # noqa: BLE001 — a write failure loses one row, not the sweep
            print(f"  WARN: persist error for {finding['call_sid']}: {exc!r}",
                  file=sys.stderr)

    return finding


def write_report(findings: list[dict], skipped: int, out: Path) -> dict:
    flagged = [f for f in findings if not f["order_matches"]]
    by_severity: dict[str, int] = {}
    by_type: dict[str, int] = {}
    for f in flagged:
        by_severity[f["severity"]] = by_severity.get(f["severity"], 0) + 1
        for d in f["discrepancies"]:
            by_type[d["type"]] = by_type.get(d["type"], 0) + 1

    summary = {
        "orders_checked": len(findings),
        "skipped": skipped,
        "flagged": len(flagged),
        "flag_rate_pct": round(len(flagged) / len(findings) * 100, 1) if findings else 0,
        "by_severity": by_severity,
        "by_discrepancy_type": sorted(by_type.items(), key=lambda x: -x[1]),
    }

    md = ["# Phone agent — order accuracy sweep", ""]
    md.append(f"- Orders checked: **{summary['orders_checked']}**")
    md.append(f"- Flagged as mis-captured: **{summary['flagged']}** "
              f"({summary['flag_rate_pct']}%)")
    md.append(f"- Skipped (no transcript / no order / judge error): **{skipped}**")
    if by_severity:
        md.append("\n## By severity")
        for sev in ("high", "medium", "low"):
            if sev in by_severity:
                md.append(f"- {sev}: {by_severity[sev]}")
    if summary["by_discrepancy_type"]:
        md.append("\n## By discrepancy type")
        for t, c in summary["by_discrepancy_type"]:
            md.append(f"- `{t}` — {c}")
    if flagged:
        md.append("\n## Flagged orders (review these)")
        ranked = sorted(
            flagged,
            key=lambda f: (-_SEVERITY_RANK[f["severity"]], -f["confidence"]),
        )
        for f in ranked[:25]:
            md.append(
                f"- **{f['severity']}** `{f['call_sid']}` "
                f"(confidence {f['confidence']}) — {f['summary']}"
            )
            for d in f["discrepancies"]:
                md.append(
                    f"    - `{d['type']}` {d['item']}: "
                    f"caller asked for \"{d['expected']}\", captured \"{d['captured']}\""
                )
    md.append(
        "\n> Detection only. No order was modified and the live agent was not "
        "touched. Review a flagged call against its recording before acting on it."
    )

    out.mkdir(parents=True, exist_ok=True)
    (out / "report.md").write_text("\n".join(md))
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    (out / "flagged.jsonl").write_text("\n".join(json.dumps(f) for f in flagged))
    return summary


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=3)
    ap.add_argument("--limit", type=int, default=500)
    ap.add_argument("--merchant", default=None, help="filter to one merchant_id")
    ap.add_argument("--concurrency", type=int, default=3)
    ap.add_argument("--min-confidence", type=float, default=0.5,
                    help="verdicts below this confidence are capped at 'low' severity")
    ap.add_argument("--recheck", action="store_true",
                    help="re-judge calls that already have a finding")
    ap.add_argument("--dry-run", action="store_true",
                    help="judge + report but do NOT write phone_order_accuracy")
    ap.add_argument("--out", default="/tmp/phone-order-accuracy")
    args = ap.parse_args()

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY required", file=sys.stderr)
        return 2
    if not os.environ.get("DEEPSEEK_API_KEY"):
        print("ERROR: DEEPSEEK_API_KEY required", file=sys.stderr)
        return 2

    out = Path(args.out)
    usage = Usage()
    ds = DeepSeek(os.environ["DEEPSEEK_API_KEY"], usage, max_calls=args.limit + 50)

    async with httpx.AsyncClient(timeout=60) as client:
        calls = await fetch_orders(client, args.days, args.limit, args.merchant)
        print(f"mined {len(calls)} checkable orders (last {args.days}d)")

        if not args.recheck:
            done = await already_checked(client, [c["call_sid"] for c in calls])
            calls = [c for c in calls if c["call_sid"] not in done]
            print(f"{len(calls)} new (skipped {len(done)} already checked)")
        if not calls:
            print("nothing to do")
            return 0

        sem = asyncio.Semaphore(args.concurrency)
        findings: list[dict] = []
        skipped = 0

        async def one(call: dict):
            nonlocal skipped
            async with sem:
                try:
                    finding = await check_call(
                        ds, client, call,
                        min_confidence=args.min_confidence,
                        dry_run=args.dry_run,
                    )
                except Exception as exc:  # noqa: BLE001 — one bad call never ends the sweep
                    print(f"  ! error on {call.get('call_sid','?')}: {exc!r}", file=sys.stderr)
                    finding = None
                if finding is None:
                    skipped += 1
                    return
                findings.append(finding)
                mark = "OK  " if finding["order_matches"] else "FLAG"
                print(f"  {mark} {finding['call_sid'][:14]:14} "
                      f"{finding['severity']:6} {finding['summary'][:70]}")

        await asyncio.gather(*(one(c) for c in calls))
        summary = write_report(findings, skipped, out)

    print(f"\n{summary['flagged']} of {summary['orders_checked']} orders flagged "
          f"({summary['flag_rate_pct']}%), {skipped} skipped")
    print(f"report: {out}/report.md  |  flagged: {out}/flagged.jsonl")
    print(f"judge cost ~${usage.est_cost_usd():.3f} ({usage.calls} calls)")
    if args.dry_run:
        print("DRY RUN — phone_order_accuracy not written")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
