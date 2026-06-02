"""ML-model upgrade evals.

Each Wave-1..3 model swap from MERIDIAN_ML_MODEL_UPGRADES_PROMPT.md has a
test_*.py in this package that benchmarks the new model against the incumbent
on synthetic-or-real data and asserts equivalence (or improvement) on a
quality metric. These are pytest tests, but they're treated as "evals" — they
are allowed to be slower than unit tests and may skip when an optional ML
dependency is unavailable.
"""
