#!/usr/bin/env python3
"""
Ground-truth reconcile: Clover's own numbers vs what Meridian propagated & stored.

This is the Clover analog of the Square "$1 check" — the only test that proves the
whole pipeline (OAuth/token → list_orders/list_refunds → mappers → upsert → DB) is
faithful end to end. It pulls totals straight from the Clover REST API and the same
window from Meridian's `transactions`, then asserts they match.

Usage:
    # sandbox merchant (token from the test Merchant Dashboard → API tokens)
    python scripts/reconcile_clover.py <org_id> \
        --token <CLOVER_API_TOKEN> --merchant <MERCHANT_ID> --sandbox --days 30

    # production merchant
    python scripts/reconcile_clover.py <org_id> \
        --token <TOKEN> --merchant <MID> --region na --days 30

Clover creds: --token/--merchant (or env CLOVER_ACCESS_TOKEN / CLOVER_MERCHANT_ID).
Meridian DB: SUPABASE_URL + service key from env (falls back to /root/Meridian/.env).

Both sides apply the SAME sale/void classification the mapper uses (state in
cancelled/refunded → not counted as sale), so a match proves every order made it
across with the right total. Exit 0 = reconciled (all metrics match within
tolerance); 1 = a mismatch worth investigating.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Orders whose Clover state is one of these are NOT revenue — the mapper records
# them as type='void', so the reconcile must exclude them from "sale" totals too.
_NON_SALE_STATES = {"cancelled", "refunded"}


def _load_env() -> dict:
    env = dict(os.environ)
    if not (env.get("SUPABASE_URL") and (env.get("SUPABASE_SERVICE_ROLE_KEY") or env.get("SUPABASE_SERVICE_KEY"))):
        for path in ("/root/Meridian/.env", os.path.join(os.path.dirname(__file__), "..", ".env")):
            try:
                with open(path) as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        k, v = line.split("=", 1)
                        env.setdefault(k.strip(), v.strip().strip('"').strip("'"))
                break
            except FileNotFoundError:
                continue
    return env


def _rest_get(url: str, key: str):
    req = urllib.request.Request(url, headers={"apikey": key, "Authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode() or "[]"), None
    except urllib.error.HTTPError as e:
        return None, f"{e.code} {e.read().decode()[:200]}"


async def _clover_totals(token: str, merchant: str, start: datetime, end: datetime) -> dict:
    """Pull Clover's own numbers for the window via the REST API (read-only)."""
    from src.clover.client import CloverClient  # imported after env is set for env/region

    client = CloverClient(access_token=token, merchant_id=merchant)
    try:
        orders = await client.list_orders(start_time=start, end_time=end)
        refunds = await client.list_refunds(start_time=start, end_time=end)
    finally:
        await client.close()

    sale_gross = 0
    sale_count = 0
    for o in orders:
        state = (o.get("state") or "").lower()
        if state in _NON_SALE_STATES:
            continue
        sale_gross += o.get("total", 0) or 0
        sale_count += 1

    refund_total = sum(r.get("amount", 0) or 0 for r in refunds if r.get("id"))
    return {
        "sale_gross_cents": sale_gross,
        "sale_count": sale_count,
        "refund_total_cents": refund_total,
        "refund_count": sum(1 for r in refunds if r.get("id")),
    }


def _meridian_totals(rest: str, key: str, org_id: str, start: datetime, end: datetime) -> dict | None:
    """Pull the same window from Meridian's stored `transactions`."""
    lo, hi = start.isoformat(), end.isoformat()
    q = (f"{rest}/transactions?org_id=eq.{org_id}"
         f"&transaction_at=gte.{lo}&transaction_at=lte.{hi}"
         f"&select=type,total_cents")
    rows, err = _rest_get(q, key)
    if err:
        print(f"✗ Meridian transactions query failed: {err}")
        return None
    sale_gross = sum(r.get("total_cents", 0) or 0 for r in rows if r.get("type") == "sale")
    sale_count = sum(1 for r in rows if r.get("type") == "sale")
    refund_total = sum(r.get("total_cents", 0) or 0 for r in rows if r.get("type") == "refund")
    refund_count = sum(1 for r in rows if r.get("type") == "refund")
    return {
        "sale_gross_cents": sale_gross,
        "sale_count": sale_count,
        "refund_total_cents": refund_total,
        "refund_count": refund_count,
    }


def _cmp(label: str, clover, meridian, tol: int = 0) -> bool:
    ok = abs(clover - meridian) <= tol
    mark = "✅" if ok else "❌"
    print(f"  {mark} {label:<22} clover={clover:<12} meridian={meridian:<12} diff={clover - meridian}")
    return ok


async def _main() -> int:
    ap = argparse.ArgumentParser(description="Reconcile Clover vs Meridian for an org window.")
    ap.add_argument("org_id")
    ap.add_argument("--token", default=os.getenv("CLOVER_ACCESS_TOKEN", ""))
    ap.add_argument("--merchant", default=os.getenv("CLOVER_MERCHANT_ID", ""))
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--sandbox", action="store_true", help="point the Clover client at the sandbox host")
    ap.add_argument("--region", default=os.getenv("CLOVER_REGION", "na"), help="production region: na/eu/la")
    args = ap.parse_args()

    if not args.token or not args.merchant:
        print("✗ need a Clover token + merchant id (--token/--merchant or CLOVER_ACCESS_TOKEN/CLOVER_MERCHANT_ID)")
        return 2

    # Point src.config at the right Clover host BEFORE importing the client.
    os.environ["CLOVER_ENVIRONMENT"] = "sandbox" if args.sandbox else "production"
    os.environ["CLOVER_REGION"] = args.region

    env = _load_env()
    url = env.get("SUPABASE_URL", "").rstrip("/")
    key = env.get("SUPABASE_SERVICE_ROLE_KEY") or env.get("SUPABASE_SERVICE_KEY") or ""
    if not url or not key:
        print("✗ SUPABASE_URL / service key not found in env or .env")
        return 2
    rest = f"{url}/rest/v1"

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=args.days)

    print("=" * 74)
    print(f"  CLOVER ↔ MERIDIAN RECONCILE — org {args.org_id} — last {args.days} days")
    print(f"  host={'sandbox' if args.sandbox else 'production/' + args.region}  merchant={args.merchant}")
    print("=" * 74)

    clover = await _clover_totals(args.token, args.merchant, start, end)
    meridian = _meridian_totals(rest, key, args.org_id, start, end)
    if meridian is None:
        return 1

    print("\nGround truth (Clover API) vs propagated (Meridian DB):\n")
    ok = True
    ok &= _cmp("sale gross (cents)", clover["sale_gross_cents"], meridian["sale_gross_cents"])
    ok &= _cmp("sale count", clover["sale_count"], meridian["sale_count"])
    ok &= _cmp("refund total (cents)", clover["refund_total_cents"], meridian["refund_total_cents"])
    ok &= _cmp("refund count", clover["refund_count"], meridian["refund_count"])

    print("\n" + "=" * 74)
    print(f"  RESULT: {'✅ RECONCILED — propagation is faithful' if ok else '❌ MISMATCH — investigate above'}")
    print("=" * 74)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
