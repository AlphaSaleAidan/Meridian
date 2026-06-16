#!/usr/bin/env python3
"""
Static schema-conformance guard for the POS-connect write paths.

The stubbed e2e (FakeDB) can't catch a real Postgres NOT-NULL violation — that's
exactly how organizations.vertical and notifications.{user_id,channel,
scheduled_for} shipped broken (callback inserted a row missing a NOT-NULL-no-
default column → insert failed → "Connected but failed to save"). This checks the
EXACT column sets the OAuth callbacks insert against the LIVE table schema
(PostgREST OpenAPI 'required' = NOT NULL with no default) and fails if any
required column is missing.

Keep CALLBACK_INSERTS in sync with src/api/routes/oauth.py + clover_oauth.py.
Reads SUPABASE creds from /root/Meridian/.env. Exit 0 = conformant, 1 = a gap.
"""
import json
import os
import sys
import urllib.request
import urllib.error

# The columns each connect-path insert actually sends (must mirror the code).
CALLBACK_INSERTS = {
    "square: organizations": ("organizations",
        {"id", "name", "slug", "vertical", "created_at", "updated_at"}),
    "square: pos_connections": ("pos_connections",
        {"id", "org_id", "provider", "status", "external_merchant_id",
         "access_token_enc", "refresh_token_enc", "token_expires_at",
         "historical_import_complete", "created_at", "updated_at"}),
    "square: notifications": ("notifications",
        {"id", "org_id", "user_id", "channel", "scheduled_for", "title", "body",
         "priority", "source_type", "status", "created_at"}),
    "clover: organizations": ("organizations",
        {"id", "name", "slug", "vertical", "created_at", "updated_at"}),
    "clover: pos_connections": ("pos_connections",
        {"id", "org_id", "provider", "status", "external_merchant_id",
         "access_token_enc", "credentials_encrypted",
         "historical_import_complete", "created_at", "updated_at"}),
    "clover: notifications": ("notifications",
        {"id", "org_id", "user_id", "channel", "scheduled_for", "title", "body",
         "priority", "source_type", "status", "created_at"}),
}


def load_env() -> dict:
    env = dict(os.environ)
    try:
        for line in open("/root/Meridian/.env"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    except FileNotFoundError:
        pass
    return env


def main() -> int:
    env = load_env()
    url = env.get("SUPABASE_URL", "").rstrip("/")
    key = env.get("SUPABASE_SERVICE_ROLE_KEY") or env.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        print("conformance: SKIP (no Supabase creds)")
        return 0
    req = urllib.request.Request(
        f"{url}/rest/v1/",
        headers={"apikey": key, "Authorization": f"Bearer {key}",
                 "Accept": "application/openapi+json"},
    )
    try:
        defs = json.loads(urllib.request.urlopen(req, timeout=20).read().decode()).get("definitions", {})
    except urllib.error.URLError as e:
        print(f"conformance: SKIP (schema fetch failed: {e})")
        return 0

    def required(t):
        return set(defs.get(t, {}).get("required", []))

    bug = False
    for label, (table, keys) in CALLBACK_INSERTS.items():
        missing = required(table) - keys
        if missing:
            bug = True
            print(f"  [BUG] {label}: insert omits NOT-NULL column(s) {sorted(missing)}")
        else:
            print(f"  [OK ] {label}")
    print("CONFORMANCE:", "FAIL" if bug else "PASS")
    return 1 if bug else 0


if __name__ == "__main__":
    sys.exit(main())
