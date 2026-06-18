#!/usr/bin/env python3
"""
Verify a POS connection actually ingested data — run right after a merchant connects.

Usage:
    python scripts/verify_pos_connection.py <org_id> [provider]

Checks (read-only) the live Supabase:
  1. pos_connections row    — status, provider, historical_import_complete, last_sync_at, last_error
  2. transactions count     — how many rows landed for the org
  3. transaction_items count
  4. a sample transaction   — confirms the canonical columns (transaction_at, type, total_cents) are populated

Reads SUPABASE_URL + service key from the environment (falls back to /root/Meridian/.env).
Exit 0 = connected AND transactions present; 1 = a problem to look at.
"""
import sys
import os
import json
import urllib.request
import urllib.error


def load_env() -> dict:
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


def get(url: str, key: str, want_count: bool = False):
    headers = {"apikey": key, "Authorization": f"Bearer {key}"}
    if want_count:
        headers["Prefer"] = "count=exact"
        headers["Range"] = "0-0"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read().decode() or "[]")
            total = None
            cr = resp.headers.get("Content-Range", "")
            if "/" in cr:
                total = cr.rsplit("/", 1)[-1]
            return body, total
    except urllib.error.HTTPError as e:
        return {"_error": f"{e.code} {e.read().decode()[:200]}"}, None


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python scripts/verify_pos_connection.py <org_id> [provider]")
        return 2
    org_id = sys.argv[1]
    provider = sys.argv[2] if len(sys.argv) > 2 else None

    env = load_env()
    url = env.get("SUPABASE_URL", "").rstrip("/")
    key = env.get("SUPABASE_SERVICE_ROLE_KEY") or env.get("SUPABASE_SERVICE_KEY") or ""
    if not url or not key:
        print("✗ SUPABASE_URL / service key not found in env or .env")
        return 2

    rest = f"{url}/rest/v1"
    print("=" * 70)
    print(f"  POS CONNECTION VERIFICATION — org {org_id}" + (f" / {provider}" if provider else ""))
    print("=" * 70)

    ok = True

    # 1. connection
    pfilter = f"&provider=eq.{provider}" if provider else ""
    conns, _ = get(f"{rest}/pos_connections?org_id=eq.{org_id}{pfilter}&select=provider,status,historical_import_complete,last_sync_at,last_error,external_merchant_id", key)
    if isinstance(conns, dict) and conns.get("_error"):
        print(f"\n✗ pos_connections query failed: {conns['_error']}")
        return 1
    if not conns:
        print("\n❌ No pos_connections row — the OAuth callback never stored a token (connect didn't complete).")
        return 1
    for c in conns:
        flag = "✅" if c.get("status") == "connected" else "⚠️"
        print(f"\n{flag} connection: provider={c.get('provider')} status={c.get('status')} "
              f"merchant={c.get('external_merchant_id')}")
        print(f"   historical_import_complete={c.get('historical_import_complete')}  last_sync_at={c.get('last_sync_at')}")
        if c.get("last_error"):
            print(f"   ⚠️ last_error: {c['last_error']}")
            ok = False
        if c.get("status") != "connected":
            ok = False

    # 2. transactions
    txns, txn_total = get(f"{rest}/transactions?org_id=eq.{org_id}&select=external_id,type,total_cents,transaction_at,payment_method&order=transaction_at.desc", key, want_count=True)
    if isinstance(txns, dict) and txns.get("_error"):
        print(f"\n✗ transactions query failed: {txns['_error']}")
        return 1
    print(f"\n📊 transactions: {txn_total or len(txns)} row(s)")
    if not txns:
        print("   ❌ Zero transactions — connected but nothing ingested yet (backfill running? or failed — check last_error + worker logs).")
        ok = False
    else:
        s = txns[0]
        missing = [f for f in ("transaction_at", "type", "total_cents") if s.get(f) in (None, "")]
        mark = "❌ missing " + ",".join(missing) if missing else "✅ canonical columns populated"
        print(f"   latest: {s.get('external_id')} {s.get('total_cents')}¢ {s.get('type')} "
              f"{s.get('payment_method')} @ {s.get('transaction_at')}  [{mark}]")
        if missing:
            ok = False

    # 3. line items
    _, items_total = get(f"{rest}/transaction_items?org_id=eq.{org_id}&select=id", key, want_count=True)
    print(f"🧾 transaction_items: {items_total or 0} row(s)")

    print("\n" + "=" * 70)
    print(f"  RESULT: {'✅ INGESTING — connection live, data flowing' if ok else '❌ NEEDS A LOOK — see above'}")
    print("=" * 70)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
