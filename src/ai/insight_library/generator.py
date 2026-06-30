"""
Catalog generator.

Crosses every archetype with the verticals it applies to and the situations where
its action differs, emitting one InsightTemplate per genuinely-distinct combo. A
content-signature dedupe ENFORCES the "no variable-only duplicates" rule: because
every fill-in value is the identical `{x}` token, two insights that differ only by
a number collapse to one signature and one is dropped; only entries whose reasoning
text genuinely differs survive.

Run:  python -m src.ai.insight_library.generator  [--out PATH] [--stats]
Output: JSONL, one InsightTemplate row per line (status=template).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from collections import Counter

from .schema import InsightTemplate, ReasoningChain, InsightStatus
from . import archetypes as _archetypes  # populates REGISTRY
from .archetypes.base import REGISTRY

_DEFAULT_OUT = os.path.join(os.path.dirname(__file__), "data", "insight_catalog.jsonl")
_WS = re.compile(r"\s+")


def _sig(built_texts: list[str]) -> str:
    norm = _WS.sub(" ", " ".join(built_texts)).strip().lower()
    return hashlib.sha1(norm.encode()).hexdigest()


def build_catalog() -> list[InsightTemplate]:
    seen: set[str] = set()
    out: list[InsightTemplate] = []
    for arch in REGISTRY:
        for v in arch.verticals():
            for situation in arch.situations:
                try:
                    b = arch.build(v, situation)
                except Exception:
                    continue
                texts = [b.title, b.observation, b.reasoning, b.conclusion, b.expected_effect]
                sig = _sig(texts)
                if sig in seen:
                    continue  # variable-only / accidental duplicate → drop
                seen.add(sig)
                rid = f"{arch.domain}.{arch.key}.{v.key}.{situation}"
                out.append(InsightTemplate(
                    id=rid,
                    domain=arch.domain,
                    archetype=arch.key,
                    vertical=v.key,
                    situation=situation,
                    title=b.title,
                    reasoning=ReasoningChain(b.observation, b.reasoning, b.conclusion, b.expected_effect),
                    required_signals=list(arch.required_signals),
                    required_agents=list(arch.required_agents),
                    swarm_capability=arch.swarm_capability,
                    swarm_upgrade=arch.swarm_upgrade,
                    recommend_when={**b.recommend_when, "vertical": v.key, "situation": situation},
                    tags=list(b.tags),
                    status=InsightStatus.TEMPLATE,
                ))
    return out


def write_catalog(rows: list[InsightTemplate], out_path: str) -> None:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        for r in rows:
            f.write(json.dumps(r.to_row()) + "\n")


def stats(rows: list[InsightTemplate]) -> dict:
    return {
        "total": len(rows),
        "archetypes": len(REGISTRY),
        "by_domain": dict(Counter(r.domain for r in rows).most_common()),
        "by_vertical": dict(Counter(r.vertical for r in rows).most_common()),
        "by_situation": dict(Counter(r.situation for r in rows).most_common()),
        "swarm_capability": dict(Counter(r.swarm_capability.value for r in rows).most_common()),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=_DEFAULT_OUT)
    ap.add_argument("--stats", action="store_true")
    args = ap.parse_args()
    rows = build_catalog()
    write_catalog(rows, args.out)
    s = stats(rows)
    print(f"Wrote {s['total']} distinct templates from {s['archetypes']} archetypes -> {args.out}")
    if args.stats:
        print(json.dumps(s, indent=2))


if __name__ == "__main__":
    main()
