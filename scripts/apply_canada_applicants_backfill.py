"""Apply the Canada applicants backfill migration to production Supabase.

Calls the Supabase Management API SQL endpoint
(POST /v1/projects/{ref}/database/query) with the migration body, then
verifies via a follow-up query that the pending applicant rows exist.

Authorized by the user (Aidan) 2026-07-29 ("go ahead and run the backfill")
for one-shot application of
supabase/migrations/20260729_backfill_canada_applicants.sql — idempotent,
insert-only-if-absent, plus e2e-careers-test-* cleanup.

Run:

    python3 scripts/apply_canada_applicants_backfill.py
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = REPO_ROOT / "supabase" / "migrations" / "20260729_backfill_canada_applicants.sql"
MGMT_BASE = "https://api.supabase.com"
SECRETS_ENV = Path("/root/.secrets/supabase.env")


def _load_env() -> None:
    for env_path in (REPO_ROOT / ".env", SECRETS_ENV):
        if not env_path.exists():
            continue
        for raw in env_path.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _query(ref: str, token: str, sql: str):
    req = urllib.request.Request(
        f"{MGMT_BASE}/v1/projects/{ref}/database/query",
        data=json.dumps({"query": sql}).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            # api.supabase.com sits behind Cloudflare, which 403s (code 1010)
            # requests with the default urllib signature.
            "User-Agent": "meridian-migrations/1.0 (+https://meridian.tips)",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read() or b"[]")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:800]


def main() -> int:
    _load_env()
    ref = os.environ.get("SUPABASE_PROJECT_REF_MERIDIAN", "")
    token = os.environ.get("SUPABASE_MGMT_TOKEN", "")
    if not ref or not token:
        print("SUPABASE_PROJECT_REF_MERIDIAN / SUPABASE_MGMT_TOKEN not set")
        return 1

    sql = MIGRATION_PATH.read_text()
    status, out = _query(ref, token, sql)
    print(f"migration apply: HTTP {status}")
    if status != 200 and status != 201:
        print(out)
        return 1

    status, out = _query(
        ref, token,
        "SELECT name, email, is_active, created_at::date AS applied "
        "FROM sales_reps WHERE portal_context='canada' AND is_active=false "
        "ORDER BY created_at DESC LIMIT 20",
    )
    print(f"\npending Canada applicants after backfill (HTTP {status}):")
    print(json.dumps(out, indent=1, default=str))

    status, out = _query(
        ref, token,
        "SELECT count(*) AS leftover_test_rows FROM career_applications "
        "WHERE lower(email) LIKE 'e2e-careers-test-%@meridian.tips'",
    )
    print(f"\ntest-row cleanup check (HTTP {status}): {json.dumps(out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
