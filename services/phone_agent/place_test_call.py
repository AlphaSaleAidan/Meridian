#!/usr/bin/env python3
"""
Place an OUTBOUND test call so a human can verify the real phone-audio leg
end-to-end (the bot greets, takes an order, posts to POS) without waiting for an
inbound call.

How it works: Telnyx places an outbound TeXML call from your DID to the target
number; when the callee answers, Telnyx fetches the TeXML `Url` — we point it at
`/twilio/voice?merchant_id=…`, the same handler inbound calls use, so the answered
callee talks to the live bot. Defaults to the demo merchant (always works).

Env (read, never printed):
  TELNYX_API_KEY                 — Telnyx API key
  TELNYX_VOICE_CONNECTION_ID     — the TeXML app id (e.g. 2975326560921322657)
  TELNYX_TEST_FROM               — the DID to call FROM (E.164), or pass --from

Usage:
  python3 place_test_call.py --to +15551234567                 # dial, demo merchant
  python3 place_test_call.py --to +1555… --merchant-id biz_…   # a specific merchant
  python3 place_test_call.py --to +1555… --dry-run             # validate, don't dial

The live dial is the only manual step (you answer + talk to the bot).
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


def build_call_params(to: str, frm: str, base_url: str, merchant_id: str,
                      status_path: str = "/twilio/status") -> dict:
    """Pure builder (unit-tested): the Twilio-compatible TeXML call params.

    On answer Telnyx GET/POSTs `Url`; we route to the inbound voice handler with a
    merchant_id override so an outbound call resolves a merchant despite having no
    inbound DID to key off.
    """
    base = base_url.rstrip("/")
    voice_url = f"{base}/twilio/voice?" + urllib.parse.urlencode({"merchant_id": merchant_id})
    return {
        "To": to,
        "From": frm,
        "Url": voice_url,
        "StatusCallback": f"{base}{status_path}",
        "StatusCallbackMethod": "POST",
    }


def place_call(connection_id: str, api_key: str, params: dict) -> dict:
    """POST the outbound TeXML call to Telnyx. Returns the parsed JSON response."""
    url = f"https://api.telnyx.com/v2/texml/calls/{connection_id}"
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Meridian phone test)",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return {"status": r.status, "body": json.loads(r.read().decode() or "{}")}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Place an outbound bot test call (Telnyx TeXML).")
    ap.add_argument("--to", required=True, help="number to call, E.164 (e.g. +15551234567)")
    ap.add_argument("--from", dest="frm", default=os.getenv("TELNYX_TEST_FROM", ""),
                    help="DID to call from (default $TELNYX_TEST_FROM)")
    ap.add_argument("--merchant-id", default=os.getenv("DEMO_MERCHANT_ID", "demo-merchant"))
    ap.add_argument("--base-url", default=os.getenv("PHONE_BASE_URL", "https://api.meridian.tips"))
    ap.add_argument("--dry-run", action="store_true", help="validate + print request, don't dial")
    args = ap.parse_args(argv)

    connection_id = os.getenv("TELNYX_VOICE_CONNECTION_ID", "")
    api_key = os.getenv("TELNYX_API_KEY", "")
    if not args.frm:
        print("ERROR: no --from and TELNYX_TEST_FROM unset", file=sys.stderr)
        return 2

    params = build_call_params(args.to, args.frm, args.base_url, args.merchant_id)

    if args.dry_run:
        print("DRY RUN — would place call:")
        print(f"  connection_id: {connection_id or '(MISSING TELNYX_VOICE_CONNECTION_ID)'}")
        print(f"  api_key:       {'set' if api_key else 'MISSING'}")
        print("  params:", json.dumps(params, indent=2))
        return 0

    if not connection_id or not api_key:
        print("ERROR: TELNYX_VOICE_CONNECTION_ID and TELNYX_API_KEY must be set", file=sys.stderr)
        return 2
    try:
        res = place_call(connection_id, api_key, params)
        sid = (res["body"].get("data") or {}).get("call_control_id") or res["body"].get("sid", "")
        print(f"Call placed (HTTP {res['status']}). id={sid or res['body']}")
        return 0
    except urllib.error.HTTPError as e:
        print(f"Telnyx error {e.code}: {e.read().decode()[:300]}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
