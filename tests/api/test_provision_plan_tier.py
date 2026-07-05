"""Regression tests for provision-customer plan_tier 23514 500s.

POST /api/onboarding/provision-customer wrote req.plan (sales-portal pricing ids:
weekly/standard/premium/command — see frontend/src/lib/proposal-plans.ts) straight
into businesses.plan_tier, which is check-constrained to trial/starter/growth/
enterprise (migration 20260429_001, businesses_plan_tier_check). Every rep
provision 500'd with a 23514 check violation.

Fix: _plan_tier() maps the sales-plan id to a valid tier before the upsert.

Run:  python -m pytest tests/api/test_provision_plan_tier.py -v
"""
from __future__ import annotations

import inspect
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.api.routes import onboarding as onboarding_mod  # noqa: E402


# ── Mapping: every sales-portal plan id lands on a constraint-valid tier ─────

@pytest.mark.parametrize(
    "plan,expected",
    [
        ("weekly", "starter"),
        ("standard", "growth"),
        ("premium", "growth"),
        ("command", "enterprise"),
    ],
)
def test_sales_plan_ids_map_to_valid_tiers(plan, expected):
    assert onboarding_mod._plan_tier(plan) == expected


@pytest.mark.parametrize("tier", ["trial", "starter", "growth", "enterprise"])
def test_valid_tiers_pass_through(tier):
    assert onboarding_mod._plan_tier(tier) == tier


@pytest.mark.parametrize("plan", [None, "", "  ", "PREMIUM", " Weekly ", "bogus-plan"])
def test_unknown_case_and_whitespace_never_escape_the_constraint(plan):
    assert onboarding_mod._plan_tier(plan) in onboarding_mod._VALID_PLAN_TIERS


def test_every_mapped_value_is_constraint_valid():
    assert set(onboarding_mod._PLAN_TIER_MAP.values()) <= onboarding_mod._VALID_PLAN_TIERS


# ── Wiring: the provision upsert uses the mapper, not the raw request value ──

def test_provision_customer_writes_mapped_plan_tier():
    src = inspect.getsource(onboarding_mod.provision_customer)
    assert '"plan_tier": _plan_tier(req.plan)' in src
    assert '"plan_tier": req.plan' not in src


def test_provision_token_status_is_constraint_valid():
    # businesses_token_status_check allows pending/redeemed/expired only;
    # "active" was the second hidden 23514 behind the plan_tier one.
    src = inspect.getsource(onboarding_mod.provision_customer)
    assert '"token_status": "pending"' in src
    assert '"token_status": "active"' not in src


def test_provision_org_id_must_be_uuid():
    # slug org ids 22P02 every uuid-typed org_id column downstream (live hit)
    with pytest.raises(Exception):
        onboarding_mod.ProvisionCustomerRequest(
            org_id="biz_slug", email="a@b.co", owner_name="A", business_name="B")
    req = onboarding_mod.ProvisionCustomerRequest(
        org_id="d9155461-07d0-4b7a-a8ee-e32a9e11e316", email="a@b.co",
        owner_name="A", business_name="B")
    assert req.org_id


def test_onboarding_notifications_use_valid_enum_status():
    import inspect as _i
    src = _i.getsource(onboarding_mod)
    # notifications.status enum: pending/sent/delivered/failed/acknowledged
    assert '"status": "active",\n            "created_at"' not in src.replace('    ', ' ')
