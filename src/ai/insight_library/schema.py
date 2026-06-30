"""
Insight Library — core schema + lifecycle gate.

This module defines the data shapes for Meridian's prebuilt insight library and,
critically, the LIFECYCLE that guarantees a half-finished insight can never reach
a customer portal.

Lifecycle (one-way, gated):

    TEMPLATE  ──fill variables──▶ CANDIDATE ──prove──▶ PROVEN ──serve guard──▶ PUBLISHED
       │                              │                   │
       └── never customer-facing ─────┴── never ──────────┘   (only PUBLISHED is shown)

A TEMPLATE carries `{x}` placeholders (every fill-in value is generically "x" per
the design rule — no two templates differ only by a variable). It is library data,
NOT an insight about any merchant. It is *structurally* barred from the portal:

  * `is_portal_safe()` returns True ONLY for PROVEN/PUBLISHED rows, AND
  * it independently re-scans the rendered text for ANY remaining placeholder
    token and rejects it ("proven again" at the serving boundary).

So even a coding mistake that marks a row PROVEN while text still contains `{x}`
is caught at serve time. Defense in depth.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any

# Placeholder sentinel. Templates use `{x}` for EVERY fill-in value (counts,
# names, %s, day/hour, dollar amounts). A distinct brace token (not a bare "x")
# makes "still unfilled" unambiguously detectable by the guard below.
PLACEHOLDER = "{x}"
_PLACEHOLDER_RE = re.compile(r"\{x\b[^}]*\}|\{[a-z_]+\}")


class InsightStatus(str, Enum):
    TEMPLATE = "template"      # library row, has {x} placeholders — NEVER customer-facing
    CANDIDATE = "candidate"    # variables filled from real data — NOT yet proven, NEVER shown
    PROVEN = "proven"          # passed post-fill validation — eligible to publish
    PUBLISHED = "published"    # passed the serve-time guard — customer-facing
    REJECTED = "rejected"      # failed a proof step — quarantined, never shown


class SwarmCapability(str, Enum):
    FULL = "full"        # existing swarm agents already produce every required signal
    PARTIAL = "partial"  # some signals exist; a fusion/upgrade agent is needed
    MISSING = "missing"  # no agent produces these signals yet — upgrade required


@dataclass
class ReasoningChain:
    """The 'why' that ships with every preset insight. Placeholders allowed only
    while status == TEMPLATE / CANDIDATE."""
    observation: str       # what the data shows
    reasoning: str         # why it matters (the causal/economic link)
    conclusion: str        # the recommended action
    expected_effect: str   # the quantified upside/risk (in $ or % terms)

    def texts(self) -> list[str]:
        return [self.observation, self.reasoning, self.conclusion, self.expected_effect]


@dataclass
class InsightTemplate:
    """One prebuilt, situation-specific insight ROADMAP. Distinct by
    (domain, archetype, vertical, situation) — never by a numeric variable."""
    id: str
    domain: str            # e.g. "labor", "inventory", "footfall"
    archetype: str         # the reasoning pattern, e.g. "peak_coverage_gap"
    vertical: str          # e.g. "cafe", "salon", "dispensary"
    situation: str         # the trigger/state this fires under, e.g. "understaffed_peak"
    title: str             # short headline (with {x} placeholders)
    reasoning: ReasoningChain
    required_signals: list[str] = field(default_factory=list)   # data fields needed to fill it
    required_agents: list[str] = field(default_factory=list)    # swarm agents that produce them
    swarm_capability: SwarmCapability = SwarmCapability.FULL
    swarm_upgrade: str = ""        # spec for the new/fusion agent when not FULL
    recommend_when: dict = field(default_factory=dict)  # matcher: vertical/signals/state
    tags: list[str] = field(default_factory=list)
    status: InsightStatus = InsightStatus.TEMPLATE

    def to_row(self) -> dict[str, Any]:
        d = asdict(self)
        d["reasoning"] = asdict(self.reasoning)
        d["swarm_capability"] = self.swarm_capability.value
        d["status"] = self.status.value
        return d


def has_unfilled_placeholders(*texts: str) -> bool:
    """True if ANY provided text still contains a placeholder token. Used to bar
    a half-finished insight from the portal regardless of its status flag."""
    return any(bool(_PLACEHOLDER_RE.search(t or "")) for t in texts)


def is_portal_safe(row: dict) -> bool:
    """The single gate every customer-portal serving path MUST call.

    Returns True ONLY when:
      1. status is PROVEN or PUBLISHED, AND
      2. NO text field (title or any reasoning leg) still contains a placeholder
         — re-checked here at the boundary ("proven again"), independent of the
         status flag, so a mislabeled row can't leak.
    """
    status = row.get("status")
    if status not in (InsightStatus.PROVEN.value, InsightStatus.PUBLISHED.value):
        return False
    reasoning = row.get("reasoning") or {}
    texts = [
        row.get("title", ""),
        reasoning.get("observation", ""),
        reasoning.get("reasoning", ""),
        reasoning.get("conclusion", ""),
        reasoning.get("expected_effect", ""),
    ]
    if has_unfilled_placeholders(*texts):
        return False
    return True
