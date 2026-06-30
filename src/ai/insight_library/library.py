"""
Insight Library — backend integration surface.

Loads the prebuilt catalog from backend storage and exposes the ONLY safe path
from a template to a customer-facing insight:

    recommend(situation) → template rows (placeholders intact, never shown)
        → compose(row, values)         # fill {x} from real merchant data
        → prove(candidate, context)    # validate: filled, signals present, holds
        → publish(proven)              # final boundary guard ("prove again")
        → serve_for_portal(rows)       # the only filter a portal path may use

A template (or candidate, or rejected) can NEVER pass serve_for_portal(): the
gate requires PROVEN/PUBLISHED status AND zero residual placeholders, re-checked
at the boundary. See schema.is_portal_safe / prover.

Storage: the canonical store is the version-controlled JSONL shipped IN the
backend (data/insight_catalog.jsonl). load_catalog() reads it; a DB table is
optional (see supabase migration) for queryable storage at scale.
"""
from __future__ import annotations

import json
import os
from functools import lru_cache

from .prover import fill, prove, publish, serve_for_portal  # re-exported
from .recommender import Situation, recommend as _recommend
from .schema import is_portal_safe  # re-exported

_CATALOG_PATH = os.path.join(os.path.dirname(__file__), "data", "insight_catalog.jsonl")


@lru_cache(maxsize=1)
def load_catalog(path: str = _CATALOG_PATH) -> tuple[dict, ...]:
    """Load the prebuilt template catalog from backend storage (immutable tuple
    so callers can't mutate the shared cache)."""
    if not os.path.exists(path):
        return ()
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return tuple(rows)


def recommend_for(
    vertical: str,
    available_signals: set[str] | None = None,
    detected_states: set[str] | None = None,
    limit: int | None = None,
) -> dict:
    """Recommend templates for a specific business situation. Returns
    {'ready': [...], 'blocked': [...]} — still TEMPLATES, not customer text."""
    sit = Situation(
        vertical=vertical,
        available_signals=set(available_signals or ()),
        detected_states=set(detected_states or ()),
    )
    return _recommend(list(load_catalog()), sit, limit=limit)


def compose(template_row: dict, values: list[str]) -> dict:
    """Fill a template's {x} placeholders with real, computed values → CANDIDATE."""
    return fill(template_row, values)


def compose_prove_publish(template_row: dict, values: list[str], context: dict,
                          *, situation_holds: bool = True) -> dict | None:
    """Full pipeline: fill → prove → publish. Returns a PUBLISHED row ready for
    the portal, or None if any gate fails (it then stays internal/quarantined)."""
    candidate = fill(template_row, values)
    proven = prove(candidate, context, situation_holds=situation_holds)
    return publish(proven)  # None unless it passes the boundary guard


__all__ = [
    "load_catalog",
    "recommend_for",
    "compose",
    "compose_prove_publish",
    "fill",
    "prove",
    "publish",
    "serve_for_portal",
    "is_portal_safe",
    "Situation",
]
