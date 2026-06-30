"""
Insight quality grader (A–F).

Deterministic, LLM-free rubric so it can run every loop iteration cheaply. Scores
each template on measurable quality dimensions, bands to A–F, and reports the
archetypes whose output grades worst (prune/fix targets) and best (patterns to
learn from). The loop uses this to remove F's, learn from A's, and refill with
upgraded insights.

Run:  python -m src.ai.insight_library.grader [--json] [--catalog PATH]
"""
from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter, defaultdict

_CATALOG = os.path.join(os.path.dirname(__file__), "data", "insight_catalog.jsonl")
_PLACEHOLDER_RE = re.compile(r"\{x\b[^}]*\}|\{[a-z_]+\}")
_WS = re.compile(r"\s+")

# Vague/low-information action verbs that signal a weak conclusion.
_VAGUE = re.compile(r"\b(improve|optimi[sz]e|review|consider|look into|focus on|"
                    r"enhance|leverage|address|evaluate|monitor|explore|assess)\b", re.I)
# Concrete imperative levers — a good conclusion tells you what to literally do.
_CONCRETE = re.compile(r"\b(add|cut|shift|move|rais\w*|lower|repric\w*|schedul\w*|stagger|"
                       r"trim|extend|open|clos\w*|bundl\w*|promot\w*|reorder|stock|set|"
                       r"requir\w*|enabl\w*|trigger|launch|test|cap|redistribut\w*|stag\w*|"
                       r"introduc\w*|swap|merchandis\w*|reserv\w*|collect|prep|rout\w*|"
                       r"flag|standardi[sz]\w*|pre-?set|pre-?book|reactivat\w*|offer|"
                       r"convert|batch|pause|drop|split|combin\w*|train|bill|deposit|"
                       r"upsell|cross-?sell|tier|surcharge|waive|book|fill|build|create|"
                       r"send|call|remind|tighten|rebalanc\w*|reallocat\w*|run|pilot)\b", re.I)
_QUANT = re.compile(r"[$%]|\bper\b|\bhour|\bweek|\bmonth|/mo|/wk|/yr|\bunits?\b|\bpoints?\b")
# Causal connectives — A-grade reasoning EXPLAINS a mechanism, not restates data.
_CAUSAL = re.compile(r"\b(because|so that|so |which|drives?|driving|means|since|"
                     r"leads? to|results? in|costs?|while|whereas|instead|rather than|"
                     r"without|every future|compounding|erodes?|leaks?|captures?|"
                     r"protects?|recovers?|signals?|implies)\b", re.I)


def _ph_count(text: str) -> int:
    return len(_PLACEHOLDER_RE.findall(text or ""))


def _words(text: str) -> int:
    return len(_WS.sub(" ", (text or "").strip()).split())


def grade_row(row: dict) -> tuple[str, int, list[str]]:
    """Return (grade, score 0-100, list of demerit reasons)."""
    rc = row.get("reasoning") or {}
    obs, why = rc.get("observation", ""), rc.get("reasoning", "")
    concl, eff = rc.get("conclusion", ""), rc.get("expected_effect", "")
    title = row.get("title", "")
    score = 100
    reasons: list[str] = []

    def demerit(pts: int, why_: str):
        nonlocal score
        score -= pts
        reasons.append(why_)

    # 1) Causal "why" must add information beyond the observation, not restate it.
    if _words(why) < 16:
        demerit(24, "why_leg_thin")
    if why and obs and _WS.sub(" ", why.lower())[:40] == _WS.sub(" ", obs.lower())[:40]:
        demerit(22, "why_restates_observation")
    if not _CAUSAL.search(why):
        demerit(20, "why_no_causal_mechanism")
    # 2) Conclusion must be a concrete action, not a vague platitude.
    if not _CONCRETE.search(concl):
        demerit(22, "conclusion_not_concrete")
    if _VAGUE.search(concl) and not _CONCRETE.search(concl):
        demerit(12, "conclusion_vague_verb")
    if _words(concl) < 9:
        demerit(12, "conclusion_thin")
    # 3) Expected effect should be quantified ($/%/per-unit).
    if not _QUANT.search(eff):
        demerit(18, "effect_not_quantified")
    if _words(eff) < 6:
        demerit(8, "effect_thin")
    # 4) Title hygiene: headlines need not carry a number, but soup is bad.
    tph = _ph_count(title)
    if tph >= 4 or (_words(title) and tph / max(_words(title), 1) > 0.4):
        demerit(14, "title_placeholder_soup")
    # 5) Substantive text present.
    blob = " ".join([obs, why, concl]).lower()
    if not re.search(r"[a-z]{4,}", blob):
        demerit(12, "no_substantive_text")
    # 6) Grounding: at least one required signal.
    if not row.get("required_signals"):
        demerit(10, "no_required_signal")
    # 7) Observation should be data-anchored (carry a metric placeholder).
    if _ph_count(obs) == 0:
        demerit(10, "observation_not_data_anchored")

    score = max(0, min(100, score))
    grade = ("A" if score >= 85 else "B" if score >= 70 else
             "C" if score >= 55 else "D" if score >= 40 else "F")
    return grade, score, reasons


def grade_catalog(path: str = _CATALOG) -> dict:
    rows = [json.loads(l) for l in open(path) if l.strip()]
    dist = Counter()
    demerits = Counter()
    arch_scores: dict[str, list[int]] = defaultdict(list)
    graded = []
    for r in rows:
        g, s, reasons = grade_row(r)
        dist[g] += 1
        for d in reasons:
            demerits[d] += 1
        arch_scores[f"{r['domain']}.{r['archetype']}"].append(s)
        graded.append((r, g, s))
    arch_avg = {k: round(sum(v) / len(v), 1) for k, v in arch_scores.items()}
    worst = sorted(arch_avg.items(), key=lambda kv: kv[1])[:25]
    best = sorted(arch_avg.items(), key=lambda kv: kv[1], reverse=True)[:25]
    total = len(rows)
    return {
        "total": total,
        "distribution": dict(dist),
        "pct": {k: round(100 * v / total, 1) for k, v in dist.items()},
        "top_demerits": dict(demerits.most_common(15)),
        "worst_archetypes": worst,
        "best_archetypes": best,
        "_graded": graded,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", default=_CATALOG)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    rep = grade_catalog(args.catalog)
    rep.pop("_graded", None)
    if args.json:
        print(json.dumps(rep, indent=2))
        return
    print(f"Graded {rep['total']} insights")
    print("Distribution:", rep["distribution"], rep["pct"])
    print("\nTop demerits:")
    for k, v in rep["top_demerits"].items():
        print(f"  {v:>5}  {k}")
    print("\nWorst archetypes (avg score):")
    for k, v in rep["worst_archetypes"][:15]:
        print(f"  {v:>5}  {k}")
    print("\nBest archetypes (avg score):")
    for k, v in rep["best_archetypes"][:10]:
        print(f"  {v:>5}  {k}")


if __name__ == "__main__":
    main()
