"""Regression tests for industry-template selection.

Guards the vertical vocabulary bridge: the 16 templates must actually register,
and the many vertical vocabularies (deck slugs, POS labels, DB values) must fold
onto the right template key — while anything unrecognized still degrades to the
generic analyzer rather than raising.
"""
from src.ai.industry_templates import get_industry_analyzer, normalize_vertical, REGISTRY
from src.ai.industry_templates.base import GenericAnalyzer


def test_all_templates_register():
    # Touch the package so lazy loading fires, then assert the full set.
    get_industry_analyzer("restaurant", "org")
    assert len(REGISTRY) == 16
    expected = {
        "auto_repair", "bakery", "bar", "brewery", "cannabis", "coffee_shop",
        "convenience", "fitness", "food_truck", "grocery", "pizza", "restaurant",
        "retail", "salon", "smoke_shop", "spa",
    }
    assert set(REGISTRY) == expected


def test_exact_keys_pass_through():
    for key in REGISTRY:
        assert normalize_vertical(key) == key


def test_deck_slugs_and_aliases_resolve():
    cases = {
        "ca-restaurant": "restaurant", "us-restaurant": "restaurant",
        "ca-coffee": "coffee_shop", "cafe": "coffee_shop",
        "us-qsr": "restaurant", "fast_food": "restaurant",
        "ca-smokeshop": "smoke_shop", "auto_shop": "auto_repair",
        "ca-gym": "fitness", "ca-dispensary": "cannabis",
        "ca-foodtruck": "food_truck", "ca-bar": "bar",
        "Coffee Shop": "coffee_shop",  # spaces + case
    }
    for raw, expected in cases.items():
        assert normalize_vertical(raw) == expected, raw


def test_unknown_and_empty_degrade_to_generic():
    assert normalize_vertical("") == "other"
    assert normalize_vertical(None) == "other"
    # An unrecognized token stays a non-registered string → GenericAnalyzer.
    assert isinstance(get_industry_analyzer("wormhole_repair", "org"), GenericAnalyzer)
    assert isinstance(get_industry_analyzer("other", "org"), GenericAnalyzer)
    assert isinstance(get_industry_analyzer(None, "org"), GenericAnalyzer)


def test_selects_specific_analyzer():
    a = get_industry_analyzer("ca-coffee", "org")
    assert a.vertical == "coffee_shop"
    assert not isinstance(a, GenericAnalyzer)


def test_templates_fabricate_on_current_data_contract_so_stay_gated():
    """WHY INDUSTRY_TEMPLATES_ENABLED defaults off (engine Phase 2b): the
    templates read a FLAT metrics dict, but the analyzers emit NESTED dicts
    (avg_ticket_cents lives under revenue["kpis"]), so a subset of guards read a
    missing value as 0 and fabricate "$0.00 below benchmark" claims — even when a
    real ticket exists. If someone fixes the data contract AND makes the guards
    presence-require, update this test and flip the flag on."""
    nested_real = {"kpis": {"avg_ticket_cents": 9800}}  # a real $98 ticket, nested
    spa = get_industry_analyzer("spa", "org")
    fabricated = spa.analyze_revenue(nested_real)["adjustments"]
    assert any("$0.00" in a["detail"] for a in fabricated), "hazard should still exist"
    # The default generic analyzer never fabricates — this is what prod runs.
    assert GenericAnalyzer("org").analyze_revenue(nested_real)["adjustments"] == []
