"""
Provision a Twilio number for the Meridian phone agent.

Once you've purchased a number in Twilio Console (Canadian local DID
for the demo, per the Session 2 plan), run this script to:

  1. Set voice URL    → https://api.meridian.tips/twilio/voice (POST)
  2. Set voice status → https://api.meridian.tips/twilio/status (POST)
  3. Set SMS URL      → https://api.meridian.tips/sms/inbound (POST)
  4. Set SMS status   → https://api.meridian.tips/sms/status (POST)
  5. Optionally update phone_agent_config.phone_number for a merchant
     so the inbound webhook can resolve the merchant by Twilio number.

Idempotent — safe to re-run. The Twilio API does PATCH-style updates.

Run via railway env (so TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN and
SUPABASE_URL / SUPABASE_ANON_KEY are injected from prod):

    railway run -p 55479e81-06ed-4953-b651-db7402dcb06f \\
        -e production -s Meridian -- \\
        python3 scripts/provision_meridian_twilio_number.py PN... [--merchant demo-merchant] [--dry-run]

Accepts either a Twilio number SID (PNxxxxxxxx) or an E.164 string
(+16475550123). E.164 inputs are resolved to the SID via the
IncomingPhoneNumbers list endpoint.
"""
from __future__ import annotations

import argparse
import os
import sys

import httpx

API_BASE_URL = os.getenv("MERIDIAN_API_BASE_URL", "https://api.meridian.tips")
VOICE_URL = f"{API_BASE_URL}/twilio/voice"
VOICE_STATUS_URL = f"{API_BASE_URL}/twilio/status"
SMS_URL = f"{API_BASE_URL}/sms/inbound"
SMS_STATUS_URL = f"{API_BASE_URL}/sms/status"

TWILIO_API_BASE = "https://api.twilio.com/2010-04-01"


def _twilio_auth() -> tuple[str, str]:
    sid = os.environ.get("TWILIO_ACCOUNT_SID", "")
    token = os.environ.get("TWILIO_AUTH_TOKEN", "")
    if not sid or not token:
        sys.exit("FAIL: TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN not set in env")
    return sid, token


def _resolve_to_sid(number_or_sid: str, account_sid: str, auth_token: str) -> str:
    """Accept either a PN-prefixed SID or an E.164 number and return the SID."""
    if number_or_sid.startswith("PN") and len(number_or_sid) >= 32:
        return number_or_sid
    if not number_or_sid.startswith("+"):
        sys.exit(f"FAIL: '{number_or_sid}' is neither a SID (PN...) nor E.164 (+...)")
    # Look up by phone number
    resp = httpx.get(
        f"{TWILIO_API_BASE}/Accounts/{account_sid}/IncomingPhoneNumbers.json",
        params={"PhoneNumber": number_or_sid},
        auth=(account_sid, auth_token),
        timeout=15.0,
    )
    if resp.status_code != 200:
        sys.exit(f"FAIL: Twilio lookup HTTP {resp.status_code}: {resp.text[:300]}")
    data = resp.json()
    matches = data.get("incoming_phone_numbers", [])
    if not matches:
        sys.exit(f"FAIL: no Twilio number found matching {number_or_sid}")
    return matches[0]["sid"]


def _current_config(sid: str, account_sid: str, auth_token: str) -> dict:
    resp = httpx.get(
        f"{TWILIO_API_BASE}/Accounts/{account_sid}/IncomingPhoneNumbers/{sid}.json",
        auth=(account_sid, auth_token),
        timeout=15.0,
    )
    if resp.status_code != 200:
        sys.exit(f"FAIL: Twilio fetch HTTP {resp.status_code}: {resp.text[:300]}")
    return resp.json()


def _apply_webhooks(
    sid: str,
    account_sid: str,
    auth_token: str,
    *,
    dry_run: bool,
) -> dict:
    payload = {
        "VoiceUrl": VOICE_URL,
        "VoiceMethod": "POST",
        "StatusCallback": VOICE_STATUS_URL,
        "StatusCallbackMethod": "POST",
        "SmsUrl": SMS_URL,
        "SmsMethod": "POST",
        "SmsFallbackUrl": "",
        "SmsFallbackMethod": "POST",
    }
    if dry_run:
        print("DRY RUN — would PATCH the following onto", sid)
        for k, v in payload.items():
            print(f"  {k:25s} {v}")
        return {}

    resp = httpx.post(
        f"{TWILIO_API_BASE}/Accounts/{account_sid}/IncomingPhoneNumbers/{sid}.json",
        data=payload,
        auth=(account_sid, auth_token),
        timeout=15.0,
    )
    if resp.status_code != 200:
        sys.exit(f"FAIL: Twilio update HTTP {resp.status_code}: {resp.text[:300]}")
    return resp.json()


def _persist_phone_to_merchant(merchant_id: str, e164: str, *, dry_run: bool) -> None:
    """Write phone_number into phone_agent_config so inbound webhooks
    can resolve merchant_id by the Twilio number that was dialled."""
    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("SUPABASE_SERVICE_KEY")
        or os.environ.get("SUPABASE_ANON_KEY", "")
    )
    if not supabase_url or not supabase_key:
        print(
            "WARN: SUPABASE_URL / key not set — skipping phone_agent_config update. "
            "You'll need to set phone_number manually."
        )
        return

    if dry_run:
        print(f"DRY RUN — would PATCH phone_agent_config.phone_number={e164} for {merchant_id}")
        return

    resp = httpx.patch(
        f"{supabase_url}/rest/v1/phone_agent_config",
        params={"merchant_id": f"eq.{merchant_id}"},
        headers={
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        },
        json={"phone_number": e164},
        timeout=10.0,
    )
    if resp.status_code not in (200, 204):
        print(
            f"WARN: phone_agent_config update HTTP {resp.status_code}: {resp.text[:300]}",
            file=sys.stderr,
        )
        return
    print(f"OK: phone_agent_config.phone_number set to {e164} for {merchant_id}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "number",
        help="Twilio number SID (PN...) or E.164 (+16475550123)",
    )
    parser.add_argument(
        "--merchant",
        default=None,
        help="Optional merchant_id — if set, also writes the number into phone_agent_config",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without writing anything",
    )
    args = parser.parse_args()

    account_sid, auth_token = _twilio_auth()

    print(f"Resolving {args.number} ...")
    sid = _resolve_to_sid(args.number, account_sid, auth_token)
    current = _current_config(sid, account_sid, auth_token)
    e164 = current.get("phone_number", "")
    friendly = current.get("friendly_name", "")
    print(f"  sid:           {sid}")
    print(f"  phone_number:  {e164}")
    print(f"  friendly_name: {friendly}")
    print(f"  voice_url (current): {current.get('voice_url', '')}")
    print(f"  sms_url   (current): {current.get('sms_url', '')}")
    print()

    print(f"Applying Meridian webhooks (api_base={API_BASE_URL}) ...")
    updated = _apply_webhooks(sid, account_sid, auth_token, dry_run=args.dry_run)
    if not args.dry_run:
        print("OK: Twilio webhooks updated.")
        print(f"  voice_url -> {updated.get('voice_url', '')}")
        print(f"  sms_url   -> {updated.get('sms_url', '')}")

    if args.merchant:
        print()
        _persist_phone_to_merchant(args.merchant, e164, dry_run=args.dry_run)

    return 0


if __name__ == "__main__":
    sys.exit(main())
