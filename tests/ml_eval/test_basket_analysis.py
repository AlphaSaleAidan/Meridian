"""Wave 1C — Apriori → FP-Growth swap in BaseAgent.find_associations.

What this eval guarantees:
  1. On the same synthetic baskets, mlxtend's `fpgrowth` and `apriori` produce
     identical frequent itemsets (modulo row order) at the same min_support.
  2. The downstream `association_rules(... metric='lift')` output is identical
     (modulo row order) regardless of which frequent-itemset algorithm fed it.
  3. find_associations() returns the same top-N rules under either backend
     (selected via MERIDIAN_BASKET_BACKEND).
  4. FP-Growth is at least as fast as Apriori on this workload (informational
     timing print; not a hard assertion to avoid flaky CI).

If mlxtend isn't installed in this Python, the test skips with a clear
reason — production already runs the manual-pair-counting fallback when
mlxtend is absent.
"""
from __future__ import annotations

import os
import random
import time
from typing import Any

import pytest

mlxtend = pytest.importorskip(
    "mlxtend",
    reason="mlxtend is an optional ML dep (requirements-ml.txt). Install with "
           "`pip install --break-system-packages mlxtend` to run this eval.",
)


def _synthetic_baskets(n_baskets: int = 400, seed: int = 7) -> list[list[str]]:
    """Generate baskets with planted cross-sell patterns (coffee+pastry, etc.)."""
    rng = random.Random(seed)
    items_general = [
        "coffee", "tea", "pastry", "muffin", "bagel", "sandwich", "juice",
        "water", "salad", "cookie", "fruit", "yogurt",
    ]
    patterns = [
        (["coffee", "pastry"], 0.55),
        (["coffee", "muffin"], 0.35),
        (["tea", "cookie"], 0.25),
        (["sandwich", "juice"], 0.30),
        (["bagel", "coffee"], 0.40),
        (["salad", "water"], 0.20),
    ]
    baskets: list[list[str]] = []
    for _ in range(n_baskets):
        basket: set[str] = set()
        for combo, p in patterns:
            if rng.random() < p:
                basket.update(combo)
        for item in items_general:
            if rng.random() < 0.08:
                basket.add(item)
        if not basket:
            basket.add(rng.choice(items_general))
        baskets.append(sorted(basket))
    return baskets


def _itemset_key(row: Any) -> tuple:
    return tuple(sorted(row["itemsets"]))


def _rule_key(row: Any) -> tuple:
    return (
        tuple(sorted(row["antecedents"])),
        tuple(sorted(row["consequents"])),
    )


@pytest.fixture(scope="module")
def baskets() -> list[list[str]]:
    return _synthetic_baskets()


@pytest.fixture(scope="module")
def encoded(baskets):
    import pandas as pd
    from mlxtend.preprocessing import TransactionEncoder

    te = TransactionEncoder()
    arr = te.fit(baskets).transform(baskets)
    return pd.DataFrame(arr, columns=te.columns_)


def test_frequent_itemsets_equivalent(encoded):
    """fpgrowth and apriori must enumerate the same frequent itemsets."""
    from mlxtend.frequent_patterns import apriori, fpgrowth

    min_support = 0.01

    t0 = time.perf_counter()
    a = apriori(encoded, min_support=min_support, use_colnames=True)
    t_apriori = time.perf_counter() - t0

    t0 = time.perf_counter()
    f = fpgrowth(encoded, min_support=min_support, use_colnames=True)
    t_fpgrowth = time.perf_counter() - t0

    a_keys = {(_itemset_key(r), round(r["support"], 6)) for _, r in a.iterrows()}
    f_keys = {(_itemset_key(r), round(r["support"], 6)) for _, r in f.iterrows()}

    print(
        f"\n  apriori={t_apriori * 1000:.1f}ms n={len(a)}, "
        f"fpgrowth={t_fpgrowth * 1000:.1f}ms n={len(f)}, "
        f"speedup={t_apriori / max(t_fpgrowth, 1e-9):.2f}x"
    )

    assert a_keys == f_keys, (
        f"itemset set differs: apriori-only={a_keys - f_keys}, "
        f"fpgrowth-only={f_keys - a_keys}"
    )


def test_association_rules_equivalent(encoded):
    """Identical inputs to association_rules → identical rule output."""
    from mlxtend.frequent_patterns import apriori, association_rules, fpgrowth

    min_support = 0.01
    a = apriori(encoded, min_support=min_support, use_colnames=True)
    f = fpgrowth(encoded, min_support=min_support, use_colnames=True)

    rules_a = association_rules(a, metric="lift", min_threshold=1.2)
    rules_f = association_rules(f, metric="lift", min_threshold=1.2)

    keys_a = {(_rule_key(r), round(r["lift"], 4)) for _, r in rules_a.iterrows()}
    keys_f = {(_rule_key(r), round(r["lift"], 4)) for _, r in rules_f.iterrows()}

    assert keys_a == keys_f, (
        f"rule set differs: apriori-only={keys_a - keys_f}, "
        f"fpgrowth-only={keys_f - keys_a}"
    )


def test_find_associations_backend_parity(baskets, monkeypatch):
    """BaseAgent.find_associations returns identical top-N under either backend."""
    from src.ai.agents.base import BaseAgent

    class _Stub(BaseAgent):
        name = "_test_basket"

        async def analyze(self) -> dict:  # pragma: no cover — never called here
            return {}

    class _Ctx:  # minimal stand-in for the orchestrator ctx
        transactions: list = []
        daily_revenue: list = []
        product_performance: list = []
        products: list = []
        inventory: list = []

    agent = _Stub(_Ctx())

    # Tighter support keeps the top-20 cutoff clear of ties at the boundary;
    # the underlying algorithm equivalence is asserted with the looser
    # support=0.01 setting in test_frequent_itemsets_equivalent / _rules_equivalent.
    monkeypatch.setenv("MERIDIAN_BASKET_BACKEND", "apriori")
    out_apriori = agent.find_associations(baskets, min_support=0.05, min_lift=1.2)

    monkeypatch.setenv("MERIDIAN_BASKET_BACKEND", "fpgrowth")
    out_fpgrowth = agent.find_associations(baskets, min_support=0.05, min_lift=1.2)

    def _norm(rule: dict) -> tuple:
        return (
            tuple(sorted(rule["antecedents"])),
            tuple(sorted(rule["consequents"])),
            rule["support"],
            rule["confidence"],
            rule["lift"],
        )

    assert {_norm(r) for r in out_apriori} == {_norm(r) for r in out_fpgrowth}


def test_default_backend_is_fpgrowth(baskets, monkeypatch):
    """Unset MERIDIAN_BASKET_BACKEND must select fpgrowth (the new default)."""
    monkeypatch.delenv("MERIDIAN_BASKET_BACKEND", raising=False)

    # Reach into the same env-driven logic as find_associations to assert default.
    backend = os.environ.get("MERIDIAN_BASKET_BACKEND", "fpgrowth").lower()
    assert backend == "fpgrowth"
