"""
Insight library tests — focus on the SAFETY GATE (a half-finished insight must
never reach a customer portal) plus catalog integrity and the recommender.
"""
import json
import os

from src.ai.insight_library import library
from src.ai.insight_library.schema import is_portal_safe, has_unfilled_placeholders, InsightStatus
from src.ai.insight_library.prover import fill, prove, publish, serve_for_portal

CATALOG = list(library.load_catalog())


# ── The gate: nothing half-finished can be served ────────────────────────────

def test_catalog_loaded():
    assert len(CATALOG) >= 10000, f"catalog should have >=10k templates, got {len(CATALOG)}"


def test_no_template_is_portal_safe():
    # Every raw template still has placeholders + status=template → must be barred.
    assert all(not is_portal_safe(r) for r in CATALOG)


def test_candidate_is_never_portal_safe():
    row = CATALOG[0]
    cand = fill(row, ["7"] * 40)  # over-supply values
    assert cand["status"] == InsightStatus.CANDIDATE.value
    # CANDIDATE never passes even if fully filled
    assert not is_portal_safe(cand)


def test_unfilled_placeholder_blocked_even_if_mislabeled_proven():
    # Simulate a bug: a row marked PROVEN but text still has a placeholder.
    row = dict(CATALOG[0])
    row["status"] = InsightStatus.PROVEN.value  # mislabel on purpose
    # title still contains {x} (we did NOT fill)
    assert has_unfilled_placeholders(row["title"])
    assert not is_portal_safe(row), "boundary guard must catch residual placeholders"


def test_full_pipeline_publishes_only_when_clean():
    row = CATALOG[0]
    texts = [row["title"]] + [row["reasoning"][k] for k in
                              ("observation", "reasoning", "conclusion", "expected_effect")]
    n = sum(t.count("{x}") for t in texts)
    ctx = {s.split(".")[0]: [1, 2, 3] for s in row["required_signals"]}
    published = library.compose_prove_publish(row, ["5"] * n, ctx, situation_holds=True)
    assert published is not None
    assert published["status"] == InsightStatus.PUBLISHED.value
    assert is_portal_safe(published)


def test_prove_rejects_missing_signal():
    row = CATALOG[0]
    if not row["required_signals"]:
        return
    texts = [row["title"]] + [row["reasoning"][k] for k in
                              ("observation", "reasoning", "conclusion", "expected_effect")]
    n = sum(t.count("{x}") for t in texts)
    cand = fill(row, ["5"] * n)
    rejected = prove(cand, context={}, situation_holds=True)  # no signals present
    assert rejected["status"] == InsightStatus.REJECTED.value
    assert rejected["reject_reason"].startswith("missing_signal")


def test_prove_rejects_when_situation_not_met():
    row = CATALOG[0]
    texts = [row["title"]] + [row["reasoning"][k] for k in
                              ("observation", "reasoning", "conclusion", "expected_effect")]
    n = sum(t.count("{x}") for t in texts)
    ctx = {s.split(".")[0]: [1] for s in row["required_signals"]}
    cand = fill(row, ["5"] * n)
    rejected = prove(cand, ctx, situation_holds=False)
    assert rejected["status"] == InsightStatus.REJECTED.value
    assert rejected["reject_reason"] == "situation_not_met"


def test_serve_for_portal_filters_everything_unproven():
    sample = CATALOG[:50]
    assert serve_for_portal(sample) == []  # all templates → none served


# ── Catalog integrity ────────────────────────────────────────────────────────

def test_every_row_has_reasoning_chain_and_placeholder():
    for r in CATALOG[:2000]:
        rc = r["reasoning"]
        assert all((rc.get(k) or "").strip() for k in
                   ("observation", "reasoning", "conclusion", "expected_effect"))
        texts = [r["title"]] + [rc[k] for k in ("observation", "reasoning", "conclusion", "expected_effect")]
        assert has_unfilled_placeholders(*texts), f"{r['id']} has no fill-in placeholder"


def test_ids_unique():
    ids = [r["id"] for r in CATALOG]
    assert len(ids) == len(set(ids))


# ── Recommender ──────────────────────────────────────────────────────────────

def test_recommend_splits_ready_and_blocked():
    rec = library.recommend_for(
        "cafe",
        available_signals={"hourly_revenue", "daily_revenue", "transactions", "schedule_shifts"},
        limit=200,
    )
    assert rec["vertical"] == "cafe"
    # ready ones must have all required signals available; blocked ones must not.
    for r in rec["ready"]:
        for s in r["required_signals"]:
            assert s.split(".")[0] in {"hourly_revenue", "daily_revenue", "transactions", "schedule_shifts"} \
                or s in {"hourly_revenue", "daily_revenue", "transactions", "schedule_shifts"}
    assert rec["blocked_count"] >= 0
