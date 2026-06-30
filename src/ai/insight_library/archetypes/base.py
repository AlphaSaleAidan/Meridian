"""
Archetype base contract.

An Archetype is ONE distinct reasoning pattern. The generator instantiates it
across the verticals where it genuinely applies (resolved by structural flags /
families / explicit keys) and across the business SITUATIONS where the action
differs. Distinctness comes from (archetype × vertical × situation); never from a
numeric variable — those are `{x}` placeholders filled later by the prover.

A `build(vertical, situation) -> Built` function is where per-vertical, per-
situation specialization lives: it must use the vertical's staff_role / sale_unit
/ core_kpis / channels so the reasoning is genuinely different, not a label swap.
Every text field uses the `{x}` placeholder for any value that will come from
real data.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from ..schema import InsightTemplate, ReasoningChain, SwarmCapability, InsightStatus, PLACEHOLDER
from ..verticals import (
    Vertical,
    VERTICALS,
    verticals_with_flags,
    verticals_in_families,
    VERTICALS_BY_KEY,
)

X = PLACEHOLDER  # convenient alias for archetype authors


@dataclass
class Built:
    """The specialized content an archetype emits for one (vertical, situation)."""
    title: str
    observation: str
    reasoning: str
    conclusion: str
    expected_effect: str
    recommend_when: dict = field(default_factory=dict)
    tags: tuple[str, ...] = ()


@dataclass
class Archetype:
    key: str                       # unique within its domain
    domain: str
    name: str
    build: Callable[[Vertical, str], Built]
    situations: tuple[str, ...] = ("baseline",)
    required_signals: tuple[str, ...] = ()
    required_agents: tuple[str, ...] = ()
    swarm_capability: SwarmCapability = SwarmCapability.FULL
    swarm_upgrade: str = ""
    # Vertical targeting (any matching mechanism; intersected with excludes):
    applies_flags: tuple[str, ...] = ()        # vertical must carry ALL these flags
    applies_families: tuple[str, ...] = ()     # OR be in one of these families
    applies_keys: tuple[str, ...] = ()         # OR be one of these explicit keys
    exclude_keys: tuple[str, ...] = ()

    def verticals(self) -> list[Vertical]:
        chosen: dict[str, Vertical] = {}
        if self.applies_flags:
            for v in verticals_with_flags(*self.applies_flags):
                chosen[v.key] = v
        if self.applies_families:
            for v in verticals_in_families(*self.applies_families):
                chosen[v.key] = v
        if self.applies_keys:
            for k in self.applies_keys:
                if k in VERTICALS_BY_KEY:
                    chosen[k] = VERTICALS_BY_KEY[k]
        if not (self.applies_flags or self.applies_families or self.applies_keys):
            chosen = {v.key: v for v in VERTICALS}  # universal archetype
        for k in self.exclude_keys:
            chosen.pop(k, None)
        return list(chosen.values())


# Registry — every domain module appends its archetypes here via register().
REGISTRY: list[Archetype] = []


def register(*archetypes: Archetype) -> None:
    REGISTRY.extend(archetypes)


# ── Situation vocabulary ─────────────────────────────────────────────────
# Each situation is a distinct business STATE that changes the recommended
# action (not just a number). Archetypes opt into the subset that fits.
SITUATIONS = {
    "baseline": "the steady-state pattern",
    "emerging": "a new favorable pattern is forming — capitalize before competitors",
    "declining": "a previously strong pattern is eroding — defend it",
    "volatile": "high variance/unpredictability — stabilize it",
    "concentrated": "value is dangerously concentrated in one slice — de-risk it",
    "leaking": "measurable value is being lost — plug the leak",
    "untapped": "a latent opportunity has never been worked — start",
    "seasonal_peak": "a seasonal high is approaching — prepare capacity",
    "seasonal_trough": "a seasonal low is approaching — protect cash/margin",
    "anomaly": "a sudden break from the norm — investigate now",
}
