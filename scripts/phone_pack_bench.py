#!/usr/bin/env python3
"""Script-pack benchmark — packs vs the legacy generic prompt, on the sim harness.

Extends scripts/phone_overnight_train.py (imported, not modified): reuses its
DeepSeek client, caller-simulator and LLM judge, but drives the REAL production
prompt builder (src/api/routes/vapi_webhook._system_prompt) so what's measured
is exactly what a live Vapi call would receive — legacy control and each pack
differ ONLY by phone_agent_config.script_pack.

Suites (menu + fixed scenario set + packs, always including the legacy control):

    generic    American quick-food menu   → legacy, efficient_v1
    pizzeria   the demo pizza menu        → legacy, efficient_v1, pizzeria_v1
    cafe       espresso-bar menu          → legacy, efficient_v1, cafe_quickserve_v1
    indian     Indian restaurant menu     → legacy, indian_v1

Every suite carries the historical weak spots (group order, pay-now question)
plus a rambling-caller time-pressure scenario. Scenarios are FIXED (not
LLM-generated) so every pack faces the identical caller.

Metrics per run: mean judge score (0-10), mean caller turns (proxy for call
time under the 5-minute cap), completion rate (order submitted when the
scenario expects one). Verdict rule (docs/playbook 30-features/phone-orders/
script-packs.md): a pack is default-eligible only when its mean score is not
below baseline AND its mean turns are lower.

Requires DEEPSEEK_API_KEY (same contract as phone_overnight_train.py; the key
is never logged). Judge menu text == the exact MENU block in the prompts, so
the judge can never disagree with the agent about prices.

Usage:
    DEEPSEEK_API_KEY=... python3 scripts/phone_pack_bench.py \
        --concurrency 6 --out /tmp/phone-pack-bench
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import httpx

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import phone_overnight_train as pot  # noqa: E402 — the sim harness
from src.api.routes import vapi_webhook as vw  # noqa: E402 — real prompt builder

# ── suite menus (agent shape — exactly what MerchantPhoneConfig carries) ──

GENERIC_MENU = [
    {"name": "Cheeseburger", "price": 12.99, "sizes": ["regular", "double"]},
    {"name": "Chicken Sandwich", "price": 11.49},
    {"name": "Caesar Salad", "price": 9.99, "sizes": ["side", "full"]},
    {"name": "French Fries", "price": 4.99, "sizes": ["small", "medium", "large"]},
    {"name": "Onion Rings", "price": 5.99},
    {"name": "Coca-Cola", "price": 2.99, "sizes": ["small", "medium", "large"]},
    {"name": "Milkshake", "price": 6.99, "modifications": ["chocolate", "vanilla", "strawberry"]},
    {"name": "Apple Pie", "price": 4.49},
]

PIZZA_MENU = [
    {"name": "Cheese Pizza", "sizes": ["medium", "large"],
     "size_prices": {"medium": 14, "large": 18}, "topping_price": 2.0,
     "modifications": ["pepperoni", "mushroom", "onion", "sausage", "extra cheese", "peppers", "olives"]},
    {"name": "Pepperoni Pizza", "sizes": ["medium", "large"],
     "size_prices": {"medium": 16, "large": 20}, "topping_price": 2.0,
     "modifications": ["mushroom", "onion", "sausage", "extra cheese", "peppers", "olives"]},
    {"name": "Veggie Pizza", "sizes": ["medium", "large"],
     "size_prices": {"medium": 17, "large": 22}, "topping_price": 2.0,
     "modifications": ["mushroom", "onion", "extra cheese", "peppers", "olives"]},
    {"name": "Garlic Bread", "price": 6.0},
    {"name": "Wings", "price": 12.0, "modifications": ["mild", "medium", "hot", "bbq"]},
    {"name": "Caesar Salad", "price": 9.0},
    {"name": "Coke", "price": 3.0},
    {"name": "Sprite", "price": 3.0},
]

CAFE_MENU = [
    {"name": "Latte", "price": 5.25, "sizes": ["small", "medium", "large"],
     "modifications": ["oat milk", "almond milk", "extra shot", "vanilla syrup"]},
    {"name": "Cappuccino", "price": 4.95, "sizes": ["small", "medium", "large"],
     "modifications": ["oat milk", "almond milk", "extra shot"]},
    {"name": "Drip Coffee", "price": 3.25, "sizes": ["small", "medium", "large"]},
    {"name": "Iced Matcha", "price": 5.75, "sizes": ["medium", "large"],
     "modifications": ["oat milk", "almond milk"]},
    {"name": "Butter Croissant", "price": 4.25},
    {"name": "Blueberry Muffin", "price": 3.95},
    {"name": "Turkey Pesto Sandwich", "price": 9.5},
]

INDIAN_MENU = [
    {"name": "Butter Chicken", "price": 17.99, "modifications": ["mild", "medium", "hot"]},
    {"name": "Chana Masala", "price": 14.99, "modifications": ["mild", "medium", "hot"]},
    {"name": "Lamb Vindaloo", "price": 18.99, "modifications": ["mild", "medium", "hot"]},
    {"name": "Palak Paneer", "price": 15.99, "modifications": ["mild", "medium", "hot"]},
    {"name": "Chicken Biryani", "price": 16.99},
    {"name": "Garlic Naan", "price": 3.99},
    {"name": "Plain Naan", "price": 2.99},
    {"name": "Basmati Rice", "price": 3.99},
    {"name": "Samosas (2pc)", "price": 6.99},
    {"name": "Mango Lassi", "price": 4.99},
]


def _weak_spot_scenarios(food_a: str, food_b: str, drink: str) -> list[dict]:
    """The fixed scenario core every suite runs (weak spots + time pressure)."""
    return [
        {"id": "simple_pickup", "category": "clear single-item order, pickup",
         "persona": "A regular customer who knows what they want, friendly and quick.",
         "goal": f"Order one {food_a} and one {drink} for pickup.",
         "hidden_quirks": "Efficient, answers questions directly.",
         "expected_outcome": f"An order with one {food_a} and one {drink}, pickup, submitted.",
         "expect_order": True},
        {"id": "multi_delivery", "category": "multi-item order with sizes, delivery (needs address)",
         "persona": "A parent ordering dinner for the family, a little distracted.",
         "goal": f"Order two {food_a}, one {food_b}, and two {drink} for DELIVERY to 42 Birchwood Lane.",
         "hidden_quirks": "Mentions delivery late unless asked; has the address ready when asked.",
         "expected_outcome": "All items captured, delivery address collected, order submitted.",
         "expect_order": True},
        {"id": "group_order", "category": "large group order, many items and quantities",
         "persona": "An office admin ordering for four coworkers, reading from a list.",
         "goal": (f"Order for four people: Priya wants {food_a}; Marcus wants {food_b} and a {drink}; "
                  f"Jen wants {food_a} with a modification; Sam just wants two {drink}. Pickup."),
         "hidden_quirks": "Reads the list person by person; gets confused if items are re-asked.",
         "expected_outcome": "All four people's items captured correctly and submitted, grouped sensibly.",
         "expect_order": True},
        {"id": "pay_now", "category": "caller wants to pay now / asks about payment over the phone",
         "persona": "A cautious first-time caller who wants to pay immediately.",
         "goal": f"Order one {food_b} for pickup, but insists on paying over the phone with a card right now.",
         "hidden_quirks": "Asks twice about payment; satisfied by a clear one-sentence explanation of the text pay-link.",
         "expected_outcome": "Order submitted; agent explains the secure text payment link and NEVER takes card numbers.",
         "expect_order": True},
        {"id": "rambler", "category": "impatient or slightly rude caller in a hurry",
         "persona": "A chatty retiree who goes on tangents about the weather and their grandkids mid-order.",
         "goal": f"Eventually order one {food_a} and one {drink} for pickup — but takes the scenic route.",
         "hidden_quirks": "Rambles between items; responds well when the agent politely keeps things moving.",
         "expected_outcome": "Agent stays warm but keeps the call moving; correct 2-item order submitted before time runs out.",
         "expect_order": True},
        {"id": "changes_mind", "category": "caller changes their mind / removes an item mid-order",
         "persona": "An indecisive caller comparing options out loud.",
         "goal": f"Start with {food_b}, switch it to {food_a}, add a {drink}, then remove the {drink} before confirming. Pickup.",
         "hidden_quirks": "Thinks out loud; the FINAL order is just one {food}.".replace("{food}", food_a),
         "expected_outcome": f"Final submitted order contains exactly one {food_a} — no ghost items.",
         "expect_order": True},
    ]


SUITES: dict[str, dict] = {
    "generic": {
        "business": "Maple Street Grill",
        "menu": GENERIC_MENU,
        "packs": ["legacy", "efficient_v1"],
        "scenarios": _weak_spot_scenarios("Cheeseburger", "Chicken Sandwich", "Coca-Cola"),
    },
    "pizzeria": {
        "business": "Tony's Pizza",
        "menu": PIZZA_MENU,
        "packs": ["legacy", "efficient_v1", "pizzeria_v1"],
        "scenarios": _weak_spot_scenarios("Pepperoni Pizza", "Cheese Pizza", "Coke") + [
            {"id": "size_toppings", "category": "item needs a size or option the caller didn't state (agent must ask)",
             "persona": "A hungry caller who never states sizes unprompted.",
             "goal": "Order a cheese pizza with mushrooms and olives, and wings — never volunteers the size.",
             "hidden_quirks": "Says 'large' only when directly asked; wants hot wings.",
             "expected_outcome": "Large cheese pizza with 2 toppings (priced $18 + $2×2), hot wings, submitted.",
             "expect_order": True},
        ],
    },
    "cafe": {
        "business": "Fern & Foam Coffee",
        "menu": CAFE_MENU,
        "packs": ["legacy", "efficient_v1", "cafe_quickserve_v1"],
        "scenarios": _weak_spot_scenarios("Latte", "Turkey Pesto Sandwich", "Drip Coffee") + [
            {"id": "drink_mods", "category": "modifications: no onions, extra cheese, sauce on the side",
             "persona": "A commuter walking to the bus stop, in a hurry.",
             "goal": "A large oat-milk latte with an extra shot and a butter croissant, pickup, fast.",
             "hidden_quirks": "Short clipped answers; annoyed by repeated confirmations.",
             "expected_outcome": "Both items with the drink mods captured in few turns and submitted.",
             "expect_order": True},
        ],
    },
    "indian": {
        "business": "Maple Tandoor",
        "menu": INDIAN_MENU,
        "packs": ["legacy", "indian_v1"],
        "language": "multi",
        "scenarios": _weak_spot_scenarios("Butter Chicken", "Chana Masala", "Mango Lassi") + [
            {"id": "spice_pairing", "category": "item needs a size or option the caller didn't state (agent must ask)",
             "persona": "A family caller who never states spice level or sides unprompted.",
             "goal": "Order lamb vindaloo and palak paneer for pickup; wants naan but only mentions it if asked about sides.",
             "hidden_quirks": "Occasionally mixes in Hindi words ('thoda spicy', 'haan', 'bas'); expects the agent to follow naturally.",
             "expected_outcome": "Both dishes with spice levels captured, naan added, order submitted; agent never trips on the Hindi words.",
             "expect_order": True},
        ],
    },
}


def _suite_config(suite: dict, pack: str) -> SimpleNamespace:
    """A MerchantPhoneConfig stand-in — identical across packs except script_pack."""
    return SimpleNamespace(
        merchant_id=f"bench-{pack}",
        business_name=suite["business"],
        greeting=f"Thanks for calling {suite['business']}! What can I get for you?",
        menu_items=suite["menu"],
        order_types=["pickup", "delivery"],
        voice="af_bella",
        personality=None,
        language=suite.get("language", "en"),
        max_call_minutes=5,
        script_pack=None if pack == "legacy" else pack,
    )


async def run_suite(ds, client, name: str, suite: dict, max_turns: int,
                    concurrency: int) -> dict:
    results: dict[str, list[dict]] = {}
    for pack in suite["packs"]:
        cfg = _suite_config(suite, pack)
        prompt = vw._system_prompt(cfg)
        # Point the harness at THIS suite: judge menu == the exact MENU block
        # in the prompt (so judge and agent can never disagree on prices),
        # and the opening line == this suite's greeting.
        menu_block = vw._menu_block(cfg).replace("\n\nMENU:\n", "", 1)
        pot._menu_text = lambda _m=menu_block: _m
        pot.GREETING = cfg.greeting

        label = f"{name}/{pack}"
        results[pack] = await pot.run_batch(
            ds, client, suite["scenarios"], prompt, max_turns, concurrency, label)
    return results


def _row(convos: list[dict]) -> dict:
    n = max(1, len(convos))
    submitted_when_expected = sum(
        1 for c in convos if c["submitted"] == bool(c["scenario"].get("expect_order", True)))
    return {
        "score": sum(c["judgment"]["score"] for c in convos) / n,
        "turns": sum(c["turns"] for c in convos) / n,
        "completion": submitted_when_expected / n,
        "n": len(convos),
    }


def _verdict(base: dict, pack: dict) -> str:
    if pack["score"] < base["score"]:
        return "NOT READY (score below baseline)"
    if pack["turns"] < base["turns"]:
        return "BEATS BASELINE"
    return "TIED (score >= baseline, no turn savings)"


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--suites", default="generic,pizzeria,cafe,indian")
    ap.add_argument("--max-turns", type=int, default=12)
    ap.add_argument("--concurrency", type=int, default=6)
    ap.add_argument("--max-calls", type=int, default=3000, help="hard DeepSeek call budget")
    ap.add_argument("--out", default="/tmp/phone-pack-bench")
    args = ap.parse_args()

    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        print("ERROR: DEEPSEEK_API_KEY not set — results stay PENDING; see the "
              "usage block at the top of this file to run the bench.", file=sys.stderr)
        return 2

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    usage = pot.Usage()
    ds = pot.DeepSeek(api_key, usage, args.max_calls)
    t0 = time.time()

    selected = [s.strip() for s in args.suites.split(",") if s.strip() in SUITES]
    report = ["# Script-pack benchmark — packs vs legacy control",
              f"\nGenerated: {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}",
              "\nMetrics: judge score 0-10 (order accuracy/behavior), mean caller "
              "turns (proxy for call time under the 5-min cap), completion "
              "(submitted when the scenario expects an order)."]
    table_all: dict[str, dict] = {}

    async with httpx.AsyncClient(timeout=60.0) as client:
        for name in selected:
            suite = SUITES[name]
            print(f"\n=== suite: {name} ({len(suite['scenarios'])} scenarios × {len(suite['packs'])} packs) ===")
            per_pack = await run_suite(ds, client, name, suite, args.max_turns, args.concurrency)
            rows = {pack: _row(convos) for pack, convos in per_pack.items()}
            table_all[name] = rows

            report.append(f"\n## {name} — {suite['business']}")
            report.append("\n| pack | score | turns | completion | verdict |")
            report.append("|------|------:|------:|-----------:|---------|")
            base = rows["legacy"]
            for pack, r in rows.items():
                verdict = "control" if pack == "legacy" else _verdict(base, r)
                report.append(f"| {pack} | {r['score']:.2f} | {r['turns']:.1f} | "
                              f"{r['completion']*100:.0f}% | {verdict} |")

            (out / f"transcripts_{name}.jsonl").open("w").write(
                "\n".join(json.dumps({"pack": pk, **c}) for pk, cs in per_pack.items() for c in cs))

    report.append(f"\n---\nDeepSeek calls: {usage.calls} | est. cost: ${usage.est_cost_usd():.2f} "
                  f"| duration: {(time.time()-t0)/60:.1f} min")
    (out / "report.md").write_text("\n".join(report))
    (out / "summary.json").write_text(json.dumps(table_all, indent=2))
    print("\n" + "\n".join(report[3:]))
    print(f"\nDone. Report: {out/'report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
