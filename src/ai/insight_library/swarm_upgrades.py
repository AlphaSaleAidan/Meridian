"""
Swarm capability map.

Aggregates, across every archetype, which data signals the insight library needs,
which existing swarm agents already provide them (FULL), and where the swarm must
be UPGRADED (PARTIAL/MISSING) — with the concrete fusion/ingest agent spec.

This is the "make the agent swarm able to collect the data, or spec the upgrade"
deliverable: run it to get the prioritized list of new agents to build, ranked by
how many prebuilt insights each one unlocks.

Run:  python -m src.ai.insight_library.swarm_upgrades [--json]
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict

from . import archetypes as _archetypes  # populates REGISTRY
from .archetypes.base import REGISTRY
from .schema import SwarmCapability

_AGENT_RE = re.compile(r"\b([A-Z][A-Za-z0-9]+Agent)\b")


def _named_agents(text: str) -> list[str]:
    return _AGENT_RE.findall(text or "")


def build_map() -> dict:
    cap = Counter()
    signals_needed = Counter()
    existing_agents = Counter()
    upgrade_agents: dict[str, dict] = defaultdict(lambda: {"archetypes": [], "domains": set(), "spec": ""})

    for a in REGISTRY:
        cap[a.swarm_capability.value] += 1
        for s in a.required_signals:
            signals_needed[s] += 1
        for ag in a.required_agents:
            existing_agents[ag] += 1
        if a.swarm_capability != SwarmCapability.FULL and a.swarm_upgrade:
            for ag in _named_agents(a.swarm_upgrade) or ["(unnamed upgrade)"]:
                rec = upgrade_agents[ag]
                rec["archetypes"].append(f"{a.domain}.{a.key}")
                rec["domains"].add(a.domain)
                if len(a.swarm_upgrade) > len(rec["spec"]):
                    rec["spec"] = a.swarm_upgrade

    upgrades = sorted(
        (
            {
                "agent": name,
                "unlocks_archetypes": len(rec["archetypes"]),
                "domains": sorted(rec["domains"]),
                "spec": rec["spec"],
                "example_archetypes": rec["archetypes"][:6],
            }
            for name, rec in upgrade_agents.items()
        ),
        key=lambda r: r["unlocks_archetypes"],
        reverse=True,
    )

    return {
        "capability_breakdown": dict(cap),
        "existing_agents_referenced": dict(existing_agents.most_common()),
        "top_signals_needed": dict(signals_needed.most_common(30)),
        "swarm_upgrades_needed": upgrades,
        "upgrade_agent_count": len(upgrades),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    m = build_map()
    if args.json:
        print(json.dumps(m, indent=2))
        return
    print(f"Capability across {sum(m['capability_breakdown'].values())} archetypes: {m['capability_breakdown']}")
    print(f"\nNew swarm agents to build ({m['upgrade_agent_count']}), ranked by insights unlocked:\n")
    for u in m["swarm_upgrades_needed"][:40]:
        print(f"  {u['unlocks_archetypes']:>4}  {u['agent']:<28} {','.join(u['domains'])}")
        print(f"        {u['spec'][:150]}")


if __name__ == "__main__":
    main()
