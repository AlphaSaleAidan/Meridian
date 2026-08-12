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
