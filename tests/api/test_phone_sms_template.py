"""
Text-to-Pay SMS template rendering — merchant-customized checkout SMS.

Merchants can store a custom SMS body (phone_agent_config.sms_pay_template,
edited from Phone Orders → Settings) with {name} {business} {total} {link}
placeholders. services/phone_agent/sms_checkout._format_checkout_sms renders
it with SAFE single-pass substitution (never str.format), falling back to the
original default copy when no template is set.

Covers:
  1. No template / blank template → byte-identical default copy (regression
     guard for every existing merchant).
  2. Placeholder substitution for {name} {business} {total} {link},
     including CAD currency symbol in {total}.
  3. Safety: stray braces in the template or customer-supplied values never
     raise (would KeyError under .format) and substituted values are not
     re-scanned for placeholders.
  4. A template that omits {link} still delivers the payment link.

Run:  python -m pytest tests/api/test_phone_sms_template.py -v
"""
from __future__ import annotations

import os
import sys

# sms_checkout lives in the flat services/phone_agent package (bare imports).
sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "services", "phone_agent")
    ),
)

from sms_checkout import _format_checkout_sms  # noqa: E402


def _order(**overrides) -> dict:
    base = {
        "customer_name": "Jamie Lee",
        "currency": "CAD",
        "total": 24.5,
        "order_type": "pickup",
        "items": [
            {"name": "Cheese Pizza", "quantity": 1, "price": 18.0},
            {"name": "Coke", "quantity": 2, "price": 3.25},
        ],
        "caller_phone": "+14165550123",
    }
    base.update(overrides)
    return base


LINK = "https://pay.meridian.tips/p/abc123"
BIZ = "Tony's Pizza"


# ── 1. Default copy (no template) ──────────────────────────────────────────

def test_default_copy_without_template():
    body = _format_checkout_sms(_order(), LINK, BIZ)
    assert "Hi Jamie!" in body  # first name only
    assert f"Your pickup order from {BIZ} is confirmed." in body
    assert "3 items — CA$24.50" in body
    assert f"Pay here: {LINK}" in body
    assert f"Thank you! — {BIZ}" in body


def test_blank_and_whitespace_template_fall_back_to_default():
    default = _format_checkout_sms(_order(), LINK, BIZ)
    assert _format_checkout_sms(_order(), LINK, BIZ, "") == default
    assert _format_checkout_sms(_order(), LINK, BIZ, "   \n ") == default


def test_default_copy_usd_and_no_customer_name():
    body = _format_checkout_sms(
        _order(customer_name="", currency="USD"), LINK, BIZ
    )
    assert body.splitlines()[0] == f"Your pickup order from {BIZ} is confirmed."
    assert "$24.50" in body and "CA$" not in body


# ── 2. Placeholder substitution ─────────────────────────────────────────────

def test_template_substitutes_all_placeholders():
    template = "Hey {name}! {business} says thanks — {total} due. Pay: {link}"
    body = _format_checkout_sms(_order(), LINK, BIZ, template)
    assert body == f"Hey Jamie! {BIZ} says thanks — CA$24.50 due. Pay: {LINK}"


def test_template_total_uses_usd_symbol_for_non_cad():
    body = _format_checkout_sms(
        _order(currency="USD"), LINK, BIZ, "Total {total}. {link}"
    )
    assert body == f"Total $24.50. {LINK}"


def test_template_repeated_placeholder():
    body = _format_checkout_sms(
        _order(), LINK, BIZ, "{name} {name} pay {link}"
    )
    assert body == f"Jamie Jamie pay {LINK}"


# ── 3. Safety: braces never raise, values never re-scanned ─────────────────

def test_stray_braces_in_template_do_not_raise():
    template = "Order {status} for {name} — cost {total} {link}"
    body = _format_checkout_sms(_order(), LINK, BIZ, template)
    # Unknown {status} placeholder passes through literally, no KeyError.
    assert "{status}" in body
    assert "Jamie" in body and LINK in body


def test_placeholder_shaped_customer_name_is_not_reinterpreted():
    # A caller who gives their name as "{link}" must stay literal — the value
    # must NOT be replaced by the payment link (single-pass substitution).
    body = _format_checkout_sms(
        _order(customer_name="{link}"), LINK, BIZ, "Hi {name}! Pay {link}"
    )
    assert body == f"Hi {{link}}! Pay {LINK}"


# ── 4. Link is always delivered ─────────────────────────────────────────────

def test_template_without_link_gets_link_appended():
    body = _format_checkout_sms(
        _order(), LINK, BIZ, "Thanks {name}, your {business} order is confirmed."
    )
    assert body.startswith(f"Thanks Jamie, your {BIZ} order is confirmed.")
    assert f"Pay here: {LINK}" in body
