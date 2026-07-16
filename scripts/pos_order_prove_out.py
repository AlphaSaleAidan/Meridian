#!/usr/bin/env python3
"""
POS order prove-out runbook — fire a REAL clearly-marked test order end-to-end
for one merchant and watch every delivery leg + the kitchen confirmation.

    # sandbox / demo-safe merchant (the normal case):
    python scripts/pos_order_prove_out.py --merchant-id <id>

    # LIVE merchant (creates a real ticket in their POS — they must delete it):
    python scripts/pos_order_prove_out.py --merchant-id <id> --i-know-this-is-live

Safety: refuses to run against a merchant unless demo_safe is set on their
phone_agent_config row OR you pass --i-know-this-is-live. Requires
SUPABASE_URL + SUPABASE_SERVICE_KEY in the environment (same env the API runs
with) plus the merchant's POS creds on their config row (or the SQUARE_* env
fallback).

This drives the SAME code path as POST /api/phone/test-order/{merchant_id}:
delivery_channels.build_test_order → pay_on_phone.dispatch_order →
pos_fulfillment.verify_fulfillment.
"""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_PHONE_AGENT_DIR = str(_ROOT / "services" / "phone_agent")
for p in (str(_ROOT), _PHONE_AGENT_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)


def _fmt(d: dict) -> str:
    return json.dumps(d, indent=2, default=str)


async def main() -> int:
    ap = argparse.ArgumentParser(description="Fire a real test order end-to-end")
    ap.add_argument("--merchant-id", required=True)
    ap.add_argument(
        "--i-know-this-is-live", action="store_true",
        help="Required for merchants WITHOUT demo_safe — a real POS ticket will be created.",
    )
    ap.add_argument("--skip-verify", action="store_true",
                    help="Skip the ~30s Square fulfillment poll")
    args = ap.parse_args()

    if not os.getenv("SUPABASE_URL"):
        print("ERROR: SUPABASE_URL not set — run with the API's environment.")
        return 2

    import dataclasses

    from delivery_channels import build_test_order  # type: ignore[import]
    from merchant_config import get_merchant_config  # type: ignore[import]
    from pay_on_phone import dispatch_order  # type: ignore[import]

    config = await get_merchant_config(args.merchant_id)
    if config is None:
        print(f"ERROR: no phone_agent_config row for merchant {args.merchant_id}")
        return 2

    demo_safe = bool(getattr(config, "demo_safe", False))
    print(f"Merchant: {config.business_name!r} ({config.merchant_id})")
    print(f"POS: {config.pos_system or '(none)'}  demo_safe={demo_safe}  "
          f"transfer_number={'set' if (config.transfer_number or '').strip() else 'NOT SET'}")

    # ── Guard: never touch a live POS without an explicit flag ──
    if not demo_safe and not args.i_know_this_is_live:
        print("\nREFUSING: this merchant is NOT demo_safe — a test order would create a")
        print("REAL ticket in their POS. Re-run with --i-know-this-is-live if that is")
        print("exactly what you want (then tell the merchant to delete the test ticket).")
        return 1

    test_config = dataclasses.replace(
        config, payment_mode="pay_at_pickup", sms_checkout_enabled=False,
    )
    order = build_test_order(test_config)
    print(f"\nTest order: 1x {order['items'][0]['name']} @ {order['total']} "
          f"{order['currency'].upper()} — customer {order['customer_name']!r}")

    routed = await dispatch_order(order, test_config, {"phone": ""})
    delivery = routed.get("delivery") or {}
    pos_result = routed.get("pos_result") or {}

    print("\n── Per-channel results ──")
    for leg in ("pos", "customer_sms", "merchant_sms"):
        print(f"  {leg:14s} {_fmt(delivery.get(leg) or {})}")
    print(f"  phone_orders row id: {routed.get('phone_order_id')}")

    pos_order_id = pos_result.get("pos_order_id", "")
    if args.skip_verify or not pos_order_id:
        if not pos_order_id:
            print("\nNo POS order id (guarded/failed/deferred) — nothing to verify.")
        return 0 if (delivery.get("pos") or {}).get("status") in ("sent", "demo_safe") else 1

    # ── Kitchen prove-out: poll the POS until the order is make-able ──
    print(f"\nVerifying fulfillment of {pos_order_id} (~30s poll)…")
    from src.services.pos_fulfillment import verify_and_record

    token = getattr(config, "pos_access_token", "") or ""
    location = getattr(config, "pos_location_id", "") or ""
    if (config.pos_system or "") == "square" and not token:
        token = os.getenv("SQUARE_ACCESS_TOKEN", "")
        location = location or os.getenv("SQUARE_LOCATION_ID", "")

    result = await verify_and_record(
        config.pos_system, pos_order_id, token,
        routed.get("phone_order_id") or "", location,
    )
    print(f"Fulfillment: {_fmt(result)}")
    if result.get("confirmed"):
        print("\n✅ Order confirmed make-able on the POS — check it printed in the "
              "kitchen, then DELETE the test ticket.")
        return 0
    if not result.get("supported"):
        print("\nℹ️  No verifier for this POS yet — check the kitchen printer manually.")
        return 0
    print("\n❌ Order NOT confirmed — investigate before onboarding this merchant.")
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
