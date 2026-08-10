"""The A2P 10DLC consent script is a legal attestation: the Telnyx campaign
files this wording verbatim, and carriers verified the agent speaks it. If any
required element disappears from the prompt, the filing becomes false and the
campaign can be revoked. This test freezes the required elements — changing
the wording is allowed ONLY together with a campaign messageFlow update
(see _sms_consent_step docstring).
"""
from types import SimpleNamespace

from src.api.routes.vapi_webhook import _sms_consent_step


def _step(business_name="Tony's Pizza"):
    return _sms_consent_step(SimpleNamespace(business_name=business_name))


def test_consent_script_contains_every_tcr_required_element():
    step = _step()
    # brand name
    assert "Meridian" in step
    # message types (confirmation + payment link)
    assert "confirmation" in step and "payment link" in step
    # frequency disclosure
    assert "1 to 3 texts per order" in step
    # rates disclosure
    assert "Message and data rates may apply" in step
    # STOP and HELP
    assert "STOP" in step and "HELP" in step
    # no-share language
    assert "never share your mobile information" in step
    # consent is asked, not assumed
    assert "Sound good?" in step


def test_decline_path_never_texts():
    step = _step()
    assert "pay_at_pickup" in step
    assert "no text is sent" in step


def test_merchant_name_is_spoken():
    assert "Maple Tandoor" in _step("Maple Tandoor")
    # missing name falls back gracefully rather than saying 'None'
    assert "None" not in _step(None) if _step(None) else True
