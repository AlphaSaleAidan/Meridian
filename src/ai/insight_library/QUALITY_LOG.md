# Insight Library — Quality Improvement Loop

Self-improving loop: grade A–F → prune/fix the failing tier → learn from why they
failed and from the A's → refill with upgraded insights + grow the catalog.
Target: 5 iterations. Grader is deterministic (`grader.py`), so each run is
comparable. Catalog floor: 10,000.

## Rubric (what separates A from F)
A-grade insights: the **why** leg explains a causal/economic MECHANISM (not a
restatement of the observation); the **conclusion** names a concrete imperative
lever (add/cut/shift/reprice/bundle…); the **expected_effect** is quantified
($/%/per-unit); the observation is data-anchored (`{x}`); ≥1 required signal.

---

## Iteration 0 — baseline (2026-06-30)
- Catalog: 10,794 templates / 489 archetypes / 19 domains.
- Grade (calibrated rubric): A 62.6% · B 31.0% · C 5.9% · D 0.5% · F 0%.
- Top demerits: why_no_causal_mechanism (2,343), conclusion_not_concrete (2,249).
- 26 archetypes graded avg <66 (the fix/prune tier) — all failing on the same
  two axes: weak/absent causal "why" + soft conclusion verbs.
- Lesson banked: emulate labor.* / revenue.* (avg 100) — every leg earns its place.

## Iteration 1 — fix failing tier + grow (2026-06-30)
- Action: rewrote the 26 weakest archetypes to the A-pattern (causal mechanism in
  the **why** leg + concrete imperative lever in the **conclusion** + quantified
  **effect**), studying labor.*/revenue.* (avg 100) as exemplars; added 43 new
  upgraded archetypes across 13 domains.
- Catalog: 10,794 → **11,639** templates (489 → 532 archetypes).
- Grade: A **70.4%** (+7.8) · B 28.3% · C **1.2%** (−4.7) · D **0%** (−0.5) · F 0%.
- All 26 fixed archetypes now average 100; all new archetypes graded A on first pass.
- Lesson: the ONLY thing separating the failing tier from the A's was diction —
  the reasoning was sound but restated the observation and used soft verbs.
  Causal connectives + concrete levers + quantified effect is the repeatable lift.
- Remaining: 142 C's + ~1,790 why/conclusion demerits in borderline-B archetypes
  → iteration 2 targets these + continues growth.
