#!/usr/bin/env python3
"""Overnight self-improvement harness for the Meridian phone ordering agent.

The phone agent's "brain" is its system prompt + few-shot exemplars driving a
hosted, non-fine-tunable LLM (DeepSeek primary). This script hardens that brain
by running a closed feedback loop entirely offline (no telephony, no Supabase):

    1. GENERATE  - synthesize diverse caller scenarios across failure-prone
                   categories (ambiguous orders, modifications, allergies,
                   off-menu, ASR noise, indecisive/rude callers, ...).
    2. SIMULATE  - a caller-LLM persona talks turn-by-turn to the REAL agent
                   contract (same TOOLS, menu, prompt, DeepSeek payload shape
                   as src/api/routes/phone.py) until submit_order / end_call.
    3. JUDGE     - an LLM judge scores each conversation 0-10 and tags failure
                   modes from a fixed taxonomy.
    4. DISTILL   - aggregate the worst conversations into concrete RULES edits
                   and a few-shot exemplar library -> a NEW candidate prompt.
    5. A/B       - re-run the hardest scenarios against old vs new prompt; keep
                   the new prompt only if mean score improves.

Outputs (written to --out, default /tmp/phone-training-out, gitignored):
    transcripts.jsonl   every simulated conversation
    scores.json         per-scenario score + failure tags + critique
    report.md           human-readable summary + A/B result
    improved_prompt.txt candidate system prompt (for human review)
    few_shot.json       exemplar library

Requires DEEPSEEK_API_KEY in the environment. The key is never logged.

Usage:
    DEEPSEEK_API_KEY=... python3 scripts/phone_overnight_train.py \
        --scenarios 40 --concurrency 4 --out /tmp/phone-training-out
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

import httpx

# --------------------------------------------------------------------------
# Agent contract — kept in lockstep with src/api/routes/phone.py.
# --------------------------------------------------------------------------
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

DEMO_MENU = [
    {"name": "Cheeseburger", "price": 12.99, "sizes": ["regular", "double"]},
    {"name": "Chicken Sandwich", "price": 11.49},
    {"name": "Fish Tacos", "price": 13.99, "sizes": ["2-piece", "3-piece"]},
    {"name": "Caesar Salad", "price": 9.99, "sizes": ["side", "full"]},
    {"name": "French Fries", "price": 4.99, "sizes": ["small", "medium", "large"]},
    {"name": "Onion Rings", "price": 5.99},
    {"name": "Coca-Cola", "price": 2.99, "sizes": ["small", "medium", "large"]},
    {"name": "Lemonade", "price": 3.49, "sizes": ["small", "medium", "large"]},
    {"name": "Milkshake", "price": 6.99, "options": ["chocolate", "vanilla", "strawberry"]},
    {"name": "Apple Pie", "price": 4.49},
]

TOOLS = [
    {
        "name": "submit_order",
        "description": "Call ONLY after customer confirms their complete order.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_name": {"type": "string"},
                "order_type": {"type": "string", "enum": ["pickup", "delivery", "dine_in"]},
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "quantity": {"type": "integer"},
                            "size": {"type": "string"},
                            "modifications": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["name", "quantity"],
                    },
                },
                "special_requests": {"type": "string"},
            },
            "required": ["customer_name", "order_type", "items"],
        },
    },
    {
        "name": "end_call",
        "description": "Call when conversation is done (no order, or after order placed).",
        "input_schema": {
            "type": "object",
            "properties": {
                "reason": {"type": "string", "enum": ["order_placed", "no_order", "wrong_number", "question_only"]},
                "farewell": {"type": "string"},
            },
            "required": ["reason", "farewell"],
        },
    },
]

OPENAI_TOOLS = [
    {"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["input_schema"]}}
    for t in TOOLS
]


def _menu_text() -> str:
    lines = []
    for item in DEMO_MENU:
        line = f" - {item['name']}: ${item['price']:.2f}"
        if item.get("sizes"):
            line += f" (sizes: {', '.join(item['sizes'])})"
        if item.get("options"):
            line += f" (options: {', '.join(item['options'])})"
        lines.append(line)
    return "\n".join(lines)


BUSINESS_NAME = "Meridian Demo Restaurant"
GREETING = f"Thanks for calling {BUSINESS_NAME}! What can I get started for you?"

# Baseline prompt — exact copy of phone.py SYSTEM_PROMPT.
BASELINE_PROMPT = f"""You are a friendly AI phone ordering assistant for {BUSINESS_NAME}.
Keep responses SHORT - 1-2 sentences. Sound warm and natural, not robotic. This is a phone call.

MENU:
{_menu_text()}

RULES:
- Help the customer build their order item by item.
- Suggest sizes or options when relevant.
- When done, read back the order with total price, ask for their name and pickup/delivery/dine-in.
- If delivery, ask for their address.
- Once confirmed, call submit_order.
- For items not on menu, let them know politely.
- Keep it brief - phone conversations should be quick."""

# --------------------------------------------------------------------------
# Scenario taxonomy.
# --------------------------------------------------------------------------
SCENARIO_CATEGORIES = [
    "clear single-item order, pickup",
    "multi-item order with sizes, delivery (needs address)",
    "caller is vague and indecisive, needs the agent to guide them",
    "item needs a size or option the caller didn't state (agent must ask)",
    "modifications: no onions, extra cheese, sauce on the side",
    "dietary/allergy concern (e.g. nut allergy, vegetarian) - agent must be careful, not invent claims",
    "off-menu request (item we don't sell) - agent must decline politely and offer alternatives",
    "price or menu question only, no order placed",
    "hours / location question only (info not in prompt) - agent must not hallucinate",
    "caller changes their mind / removes an item mid-order",
    "dine-in order",
    "impatient or slightly rude caller in a hurry",
    "wrong number / caller didn't mean to call",
    "large group order, many items and quantities",
    "ASR noise: caller utterances contain mistranscribed/garbled words (simulate bad speech-to-text)",
    "caller mumbles a name that is hard to spell; agent confirms it",
    "caller asks for a recommendation / what's popular",
    "caller tries to combine items into a 'combo' or 'meal deal' we don't have",
    "caller wants to pay now / asks about payment over the phone",
    "caller orders, then adds one more item right before confirming",
]

FAILURE_TAGS = [
    "wrong_item", "missing_item", "extra_item", "price_hallucination",
    "menu_hallucination", "info_hallucination", "no_clarify", "too_verbose",
    "premature_submit", "never_submit", "bad_closing", "ignored_modification",
    "ignored_allergy", "robotic_tone", "lost_context",
]


# --------------------------------------------------------------------------
# DeepSeek client with usage accounting (key never logged).
# --------------------------------------------------------------------------
@dataclass
class Usage:
    calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0

    def add(self, data: dict) -> None:
        u = data.get("usage") or {}
        self.calls += 1
        self.prompt_tokens += int(u.get("prompt_tokens", 0))
        self.completion_tokens += int(u.get("completion_tokens", 0))

    def est_cost_usd(self) -> float:
        # deepseek-chat (cache-miss) ~ $0.27 / 1M input, $1.10 / 1M output.
        return self.prompt_tokens / 1e6 * 0.27 + self.completion_tokens / 1e6 * 1.10


class DeepSeek:
    def __init__(self, api_key: str, usage: Usage, max_calls: int):
        self._key = api_key
        self.usage = usage
        self.max_calls = max_calls

    async def chat(
        self,
        client: httpx.AsyncClient,
        messages: list[dict],
        *,
        tools: bool = False,
        temperature: float = 0.4,
        json_mode: bool = False,
        max_tokens: int = 400,
        retries: int = 3,
    ) -> dict | None:
        if self.usage.calls >= self.max_calls:
            raise RuntimeError(f"max-calls budget ({self.max_calls}) exhausted")
        payload: dict[str, Any] = {
            "model": DEEPSEEK_MODEL,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if tools:
            payload["tools"] = OPENAI_TOOLS
            payload["tool_choice"] = "auto"
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        last_err = None
        for attempt in range(retries):
            try:
                resp = await client.post(
                    f"{DEEPSEEK_BASE_URL}/chat/completions",
                    headers={"Authorization": f"Bearer {self._key}", "Content-Type": "application/json"},
                    json=payload,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    self.usage.add(data)
                    return data["choices"][0]["message"]
                last_err = f"HTTP {resp.status_code}: {resp.text[:160]}"
            except Exception as exc:  # noqa: BLE001
                last_err = repr(exc)
            await asyncio.sleep(1.5 * (attempt + 1))
        print(f"  ! deepseek call failed after {retries} tries: {last_err}", file=sys.stderr)
        return None


def _parse_json(text: str) -> dict | None:
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if 0 <= start < end:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                return None
    return None


# --------------------------------------------------------------------------
# 1. Scenario generation.
# --------------------------------------------------------------------------
async def gen_scenarios(ds: DeepSeek, client: httpx.AsyncClient, n: int) -> list[dict]:
    scenarios: list[dict] = []
    cats = [SCENARIO_CATEGORIES[i % len(SCENARIO_CATEGORIES)] for i in range(n)]
    random.shuffle(cats)
    for i, cat in enumerate(cats):
        sys_p = (
            "You design test cases for a restaurant phone-ordering AI. "
            "Given a category, invent ONE realistic caller scenario. "
            f"The menu is:\n{_menu_text()}\n"
            "Return JSON: {\"persona\": str (1 sentence: who is calling, mood, speaking style), "
            "\"goal\": str (what they want to accomplish), "
            "\"hidden_quirks\": str (how they behave: vague? in a hurry? heavy accent? changes mind?), "
            "\"expected_outcome\": str (what a GOOD agent should end with: an order with which items, or a polite decline, or info given)}."
        )
        msg = [
            {"role": "system", "content": sys_p},
            {"role": "user", "content": f"Category: {cat}"},
        ]
        out = await ds.chat(client, msg, temperature=0.9, json_mode=True, max_tokens=350)
        parsed = _parse_json(out.get("content", "")) if out else None
        if not parsed:
            continue
        parsed["category"] = cat
        parsed["id"] = f"s{i:03d}"
        scenarios.append(parsed)
    return scenarios


# --------------------------------------------------------------------------
# 2. Conversation simulation (caller-LLM vs real agent contract).
# --------------------------------------------------------------------------
def _caller_system(sc: dict) -> str:
    base = (
        "You are role-playing a CUSTOMER calling a restaurant to order food over the phone. "
        f"Persona: {sc.get('persona', '')}. Goal: {sc.get('goal', '')}. "
        f"Behavior quirks: {sc.get('hidden_quirks', '')}. "
        "Speak naturally and briefly like a real phone caller — one short turn at a time. "
        "Do NOT narrate or use stage directions. Only say what the customer says out loud. "
        "Stay in character. When your goal is met (order placed, question answered, or you've hung up), "
        "say a brief goodbye and then on the next line output exactly [[END]]."
    )
    if "ASR noise" in sc.get("category", ""):
        base += (
            " IMPORTANT: simulate imperfect speech-to-text — occasionally garble a word or two "
            "(e.g. 'cheeseburger' -> 'cheese booger', 'Coca-Cola' -> 'cocoa cola') so we can test "
            "how the agent recovers. Don't garble everything, just enough to be realistic."
        )
    return base


def _agent_message(text: str, tool: dict | None) -> dict:
    content: list[dict] = []
    if text:
        content.append({"type": "text", "text": text})
    if tool:
        content.append({"type": "tool_use", **tool})
    return {"content": content}


async def simulate(
    ds: DeepSeek, client: httpx.AsyncClient, sc: dict, agent_prompt: str, max_turns: int,
) -> dict:
    """Run one conversation. Returns transcript + final order + meta."""
    transcript: list[dict] = [{"speaker": "agent", "text": GREETING}]
    order: dict | None = None
    end_reason: str | None = None
    submitted = False

    for _turn in range(max_turns):
        # --- caller turn (sees agent lines as 'user') ---
        caller_msgs = [{"role": "system", "content": _caller_system(sc)}]
        for line in transcript:
            role = "user" if line["speaker"] == "agent" else "assistant"
            caller_msgs.append({"role": role, "content": line["text"]})
        caller_out = await ds.chat(client, caller_msgs, temperature=0.8, max_tokens=120)
        caller_text = (caller_out.get("content") or "").strip() if caller_out else ""
        ended_by_caller = "[[END]]" in caller_text
        caller_text = caller_text.replace("[[END]]", "").strip()
        if caller_text:
            transcript.append({"speaker": "caller", "text": caller_text})
        if ended_by_caller and not caller_text:
            break

        # --- agent turn (real contract: system prompt + tools) ---
        agent_msgs = [{"role": "system", "content": agent_prompt}]
        for line in transcript:
            role = "assistant" if line["speaker"] == "agent" else "user"
            agent_msgs.append({"role": role, "content": line["text"]})
        agent_out = await ds.chat(client, agent_msgs, tools=True, temperature=0.3, max_tokens=300)
        if not agent_out:
            transcript.append({"speaker": "agent", "text": "(no response)"})
            break
        text = (agent_out.get("content") or "").strip()
        tool = None
        for tc in agent_out.get("tool_calls") or []:
            args = _parse_json(tc["function"].get("arguments", "")) or {}
            tool = {"name": tc["function"]["name"], "input": args}
            break
        if text:
            transcript.append({"speaker": "agent", "text": text})
        if tool:
            transcript.append({"speaker": "agent_tool", "text": json.dumps(tool)})
            if tool["name"] == "submit_order":
                order = tool["input"]
                submitted = True
                end_reason = "order_placed"
                break
            if tool["name"] == "end_call":
                end_reason = tool["input"].get("reason", "ended")
                break
        if ended_by_caller:
            break

    return {
        "scenario": sc,
        "transcript": transcript,
        "order": order,
        "submitted": submitted,
        "end_reason": end_reason,
        "turns": sum(1 for t in transcript if t["speaker"] == "caller"),
    }


# --------------------------------------------------------------------------
# 3. Judge.
# --------------------------------------------------------------------------
def _render_transcript(convo: dict) -> str:
    lines = []
    for t in convo["transcript"]:
        if t["speaker"] == "agent_tool":
            lines.append(f"AGENT [tool]: {t['text']}")
        else:
            who = "AGENT" if t["speaker"] == "agent" else "CALLER"
            lines.append(f"{who}: {t['text']}")
    return "\n".join(lines)


async def judge(ds: DeepSeek, client: httpx.AsyncClient, convo: dict) -> dict:
    sc = convo["scenario"]
    sys_p = (
        "You are a strict QA reviewer for a restaurant phone-ordering AI. "
        f"The menu is:\n{_menu_text()}\n\n"
        "Score the AGENT's performance on this call from 0 (terrible) to 10 (perfect). "
        "Penalize: wrong/missing/extra items, hallucinated prices, items or facts not on the menu, "
        "failing to ask a needed clarifying question, ignoring a modification or allergy, being verbose "
        "or robotic, submitting before the caller confirmed, never submitting a confirmed order, or a bad closing.\n"
        f"Choose any failure tags that apply from: {FAILURE_TAGS}.\n"
        "Return JSON: {\"score\": int 0-10, \"tags\": [str], \"critique\": str (one sentence, specific), "
        "\"fix\": str (one concrete instruction that, if added to the agent's rules, would have prevented the problem; "
        "empty string if the call was great)}."
    )
    user_p = (
        f"SCENARIO: {sc.get('persona','')} | goal: {sc.get('goal','')} | "
        f"expected: {sc.get('expected_outcome','')}\n\n"
        f"TRANSCRIPT:\n{_render_transcript(convo)}\n\n"
        f"ORDER SUBMITTED: {json.dumps(convo['order']) if convo['order'] else 'none'}"
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
# 4. Distill -> improved prompt + few-shot library.
# --------------------------------------------------------------------------
async def distill(
    ds: DeepSeek, client: httpx.AsyncClient, results: list[dict],
) -> tuple[str, list[dict]]:
    ranked = sorted(results, key=lambda r: r["judgment"]["score"])
    worst = [r for r in ranked if r["judgment"]["score"] < 8][:12]
    fixes = [r["judgment"]["fix"] for r in worst if r["judgment"].get("fix")]
    tag_counts: dict[str, int] = {}
    for r in results:
        for tag in r["judgment"].get("tags", []):
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

    sys_p = (
        "You improve the SYSTEM PROMPT for a restaurant phone-ordering AI. "
        "You are given the current RULES, the most common failure tags, and specific fixes that reviewers "
        "said would have prevented failures. Produce an improved, de-duplicated RULES list: keep what works, "
        "add the fixes, stay concise (phone calls must be quick), and NEVER invent menu items, prices, hours, "
        "or facts not provided. Also produce 3-6 few-shot exemplars showing ideal handling of the hardest cases.\n"
        "Return JSON: {\"rules\": [str] (the full replacement RULES bullet list, no leading dash), "
        "\"few_shot\": [{\"situation\": str, \"caller\": str, \"ideal_agent\": str}]}."
    )
    user_p = (
        f"CURRENT RULES:\n{BASELINE_PROMPT.split('RULES:')[1].strip()}\n\n"
        f"FAILURE TAG COUNTS: {json.dumps(tag_counts)}\n\n"
        f"REVIEWER FIXES (most impactful first):\n" + "\n".join(f"- {f}" for f in fixes)
    )
    out = await ds.chat(
        client,
        [{"role": "system", "content": sys_p}, {"role": "user", "content": user_p}],
        temperature=0.4, json_mode=True, max_tokens=1200,
    )
    parsed = _parse_json(out.get("content", "")) if out else None
    if not parsed or not parsed.get("rules"):
        return BASELINE_PROMPT, []

    rules = "\n".join(f"- {r.lstrip('- ').strip()}" for r in parsed["rules"])
    few_shot = parsed.get("few_shot", []) or []
    fewshot_block = ""
    if few_shot:
        ex = "\n".join(
            f"  [{e.get('situation','')}] Caller: \"{e.get('caller','')}\" -> You: \"{e.get('ideal_agent','')}\""
            for e in few_shot
        )
        fewshot_block = f"\n\nEXAMPLES OF GREAT HANDLING:\n{ex}"
    improved = (
        f"You are a friendly AI phone ordering assistant for {BUSINESS_NAME}.\n"
        "Keep responses SHORT - 1-2 sentences. Sound warm and natural, not robotic. This is a phone call.\n\n"
        f"MENU:\n{_menu_text()}\n\n"
        f"RULES:\n{rules}{fewshot_block}"
    )
    return improved, few_shot


# --------------------------------------------------------------------------
# Orchestration.
# --------------------------------------------------------------------------
async def run_batch(ds, client, scenarios, prompt, max_turns, concurrency, label):
    sem = asyncio.Semaphore(concurrency)
    results: list[dict] = []

    async def one(sc):
        async with sem:
            convo = await simulate(ds, client, sc, prompt, max_turns)
            convo["judgment"] = await judge(ds, client, convo)
            score = convo["judgment"]["score"]
            print(f"  [{label}] {sc['id']} {sc['category'][:32]:32} score={score}")
            results.append(convo)

    await asyncio.gather(*(one(sc) for sc in scenarios))
    return results


def mean_score(results: list[dict]) -> float:
    return sum(r["judgment"]["score"] for r in results) / max(1, len(results))


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenarios", type=int, default=40)
    ap.add_argument("--max-turns", type=int, default=8)
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--max-calls", type=int, default=6000, help="hard cap on DeepSeek calls (cost guard)")
    ap.add_argument("--ab-count", type=int, default=12, help="hardest scenarios to A/B re-test")
    ap.add_argument("--candidate-prompt", default="", help="path to a candidate prompt; skips auto-distill")
    ap.add_argument("--ab-only", action="store_true",
                    help="with --candidate-prompt: run baseline vs candidate on a fresh scenario set, no distill")
    ap.add_argument("--out", default="/tmp/phone-training-out")
    args = ap.parse_args()

    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        print("ERROR: DEEPSEEK_API_KEY not set in environment", file=sys.stderr)
        return 2

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    usage = Usage()
    ds = DeepSeek(api_key, usage, args.max_calls)
    t0 = time.time()

    async with httpx.AsyncClient(timeout=60.0) as client:
        if args.ab_only:
            if not args.candidate_prompt:
                print("ERROR: --ab-only requires --candidate-prompt", file=sys.stderr)
                return 2
            candidate = Path(args.candidate_prompt).read_text()
            print(f"[A/B] generating {args.scenarios} fresh scenarios ...")
            scenarios = await gen_scenarios(ds, client, args.scenarios)
            print(f"      got {len(scenarios)} scenarios")
            base = await run_batch(ds, client, scenarios, BASELINE_PROMPT, args.max_turns, args.concurrency, "base")
            cand = await run_batch(ds, client, scenarios, candidate, args.max_turns, args.concurrency, "cand")
            bm, cm = mean_score(base), mean_score(cand)
            by_id = {r["scenario"]["id"]: r for r in cand}
            rows = []
            for r in sorted(base, key=lambda r: r["scenario"]["id"]):
                sid = r["scenario"]["id"]
                o, n = r["judgment"]["score"], by_id[sid]["judgment"]["score"]
                rows.append(f"- {sid} {r['scenario']['category'][:34]:34} old={o:2d} new={n:2d} ({'+' if n>=o else ''}{n-o})")
            report = [
                "# A/B: baseline vs candidate prompt",
                f"\nScenarios: {len(scenarios)} | DeepSeek calls: {usage.calls} | est. cost: ${usage.est_cost_usd():.2f}",
                f"\n**baseline mean = {bm:.2f}  |  candidate mean = {cm:.2f}  |  delta = {'+' if cm>=bm else ''}{cm-bm:.2f}**",
                f"\nVerdict: {'ADOPT candidate' if cm > bm else 'KEEP baseline'}",
                "\n## Per-scenario", *rows,
            ]
            (out / "ab_report.md").write_text("\n".join(report))
            print(f"\n[A/B] baseline={bm:.2f}  candidate={cm:.2f}  delta={cm-bm:+.2f} -> "
                  f"{'ADOPT' if cm>bm else 'KEEP BASELINE'}")
            print(f"Done. {usage.calls} calls, ~${usage.est_cost_usd():.2f}. Report: {out/'ab_report.md'}")
            return 0

        print(f"[1/5] generating {args.scenarios} scenarios ...")
        scenarios = await gen_scenarios(ds, client, args.scenarios)
        print(f"      got {len(scenarios)} scenarios")
        (out / "scenarios.json").write_text(json.dumps(scenarios, indent=2))

        print("[2/5] simulating + judging baseline brain ...")
        baseline = await run_batch(ds, client, scenarios, BASELINE_PROMPT, args.max_turns, args.concurrency, "base")
        base_mean = mean_score(baseline)
        print(f"      baseline mean score = {base_mean:.2f}")

        with (out / "transcripts.jsonl").open("w") as fh:
            for r in baseline:
                fh.write(json.dumps(r) + "\n")
        (out / "scores.json").write_text(json.dumps(
            [{"id": r["scenario"]["id"], "category": r["scenario"]["category"], **r["judgment"]} for r in baseline],
            indent=2,
        ))

        print("[3/5] distilling improved prompt + few-shot ...")
        improved_prompt, few_shot = await distill(ds, client, baseline)
        (out / "improved_prompt.txt").write_text(improved_prompt)
        (out / "few_shot.json").write_text(json.dumps(few_shot, indent=2))

        print(f"[4/5] A/B re-testing hardest {args.ab_count} scenarios ...")
        hardest = [r["scenario"] for r in sorted(baseline, key=lambda r: r["judgment"]["score"])[:args.ab_count]]
        ab_old = await run_batch(ds, client, hardest, BASELINE_PROMPT, args.max_turns, args.concurrency, "A/old")
        ab_new = await run_batch(ds, client, hardest, improved_prompt, args.max_turns, args.concurrency, "B/new")
        old_mean, new_mean = mean_score(ab_old), mean_score(ab_new)
        improved = new_mean > old_mean
        print(f"      A/B on hardest: old={old_mean:.2f}  new={new_mean:.2f}  -> {'KEEP NEW' if improved else 'KEEP OLD'}")

        print("[5/5] writing report ...")
        tag_counts: dict[str, int] = {}
        for r in baseline:
            for tag in r["judgment"].get("tags", []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        top_tags = sorted(tag_counts.items(), key=lambda kv: -kv[1])
        worst = sorted(baseline, key=lambda r: r["judgment"]["score"])[:8]

        report = [
            "# Phone Agent Overnight Training Report",
            f"\nGenerated: {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}",
            f"\nDuration: {(time.time()-t0)/60:.1f} min | DeepSeek calls: {usage.calls} "
            f"| est. cost: ${usage.est_cost_usd():.2f}",
            "\n## Scores",
            f"- Baseline mean (all {len(baseline)} scenarios): **{base_mean:.2f}/10**",
            f"- A/B on hardest {len(hardest)}: old **{old_mean:.2f}** vs new **{new_mean:.2f}** "
            f"({'+' if new_mean>=old_mean else ''}{new_mean-old_mean:.2f}) -> "
            f"**{'adopt improved prompt' if improved else 'keep baseline'}**",
            "\n## Most common failure modes",
        ]
        report += [f"- `{tag}` x{cnt}" for tag, cnt in top_tags] or ["- none recorded"]
        report.append("\n## Worst calls (for review)")
        for r in worst:
            j = r["judgment"]
            report.append(f"\n### {r['scenario']['id']} — {r['scenario']['category']} (score {j['score']})")
            report.append(f"- Critique: {j.get('critique','')}")
            report.append(f"- Suggested fix: {j.get('fix','')}")
        report.append("\n## Next step")
        report.append(
            "Review `improved_prompt.txt`. If adopting, update `SYSTEM_PROMPT` (and the merchant prompt "
            "template `_build_merchant_prompt`) in `src/api/routes/phone.py`. Few-shot exemplars are in "
            "`few_shot.json`."
        )
        (out / "report.md").write_text("\n".join(report))

    print(f"\nDone in {(time.time()-t0)/60:.1f} min. "
          f"{usage.calls} calls, ~${usage.est_cost_usd():.2f}. Output in {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
