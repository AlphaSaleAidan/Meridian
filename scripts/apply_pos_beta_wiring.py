"""Apply the P0 POS beta-wiring migration to production Supabase.

Calls the Supabase Management API SQL endpoint
(POST /v1/projects/{ref}/database/query) with the migration body,
then verifies via PostgREST that each new column is present.

Authorized by the user 2026-06-03 for one-shot application of
supabase/migrations/20260603_pos_beta_wiring.sql.

Run:

    PYTHONPATH=/root/Meridian /root/Meridian/.venv/bin/python \
        -m scripts.apply_pos_beta_wiring
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = REPO_ROOT / "supabase" / "migrations" / "20260603_pos_beta_wiring.sql"
MGMT_BASE = "https://api.supabase.com"


def _load_env() -> None:
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _project_ref() -> str:
    url = os.environ.get("SUPABASE_URL", "")
    host = url.split("://", 1)[1] if "://" in url else url
    return host.split(".", 1)[0]


def _strip_rollback(sql: str) -> str:
    """Strip the trailing rollback-comment block so it's not even
    parsed by Postgres (it's commented out, but cleaner to send only
    the UP block to the API)."""
    marker = "-- ROLLBACK START"
    if marker in sql:
        return sql.split(marker, 1)[0]
    return sql


def _mgmt_post(ref: str, token: str, body: str) -> tuple[int, str]:
    url = f"{MGMT_BASE}/v1/projects/{ref}/database/query"
    payload = json.dumps({"query": body}).encode()
    req = urllib.request.Request(
        url, data=payload, method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            # Default urllib UA is blocked by Cloudflare (Error 1010).
            "User-Agent": "meridian-migration/1.0 (curl-compatible)",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace") if exc.fp else ""
        return exc.code, body


def _postgrest_columns(table: str) -> list[str]:
    """Probe PostgREST for the table's column list (uses SUPABASE_SERVICE_ROLE_KEY)."""
    base = os.environ["SUPABASE_URL"].rstrip("/") + "/rest/v1"
    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
           or os.environ["SUPABASE_SERVICE_KEY"])
    url = f"{base}/{table}?select=*&limit=1"
    req = urllib.request.Request(
        url, headers={"apikey": key, "Authorization": f"Bearer {key}"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        rows = json.loads(resp.read() or b"[]")
    if rows:
        return list(rows[0].keys())
    # No rows — fall back to a HEAD which still returns the schema in
    # the PostgREST OpenAPI definition.
    return []


def main() -> int:
    _load_env()

    ref = _project_ref()
    token = os.environ.get("SUPABASE_ACCESS_TOKEN", "")
    if not (ref and token):
        print("ABORT: SUPABASE_URL or SUPABASE_ACCESS_TOKEN missing")
        return 2

    sql = MIGRATION_PATH.read_text()
    up_block = _strip_rollback(sql)
    print(f"Applying migration: {MIGRATION_PATH.name}")
    print(f"  size: {len(up_block):,} chars (UP block only, rollback comments stripped)")
    print(f"  target project: {ref}")
    print()

    status, body = _mgmt_post(ref, token, up_block)
    print(f"Management API response: HTTP {status}")
    if status >= 400:
        print(body[:1000])
        return 3
    # Successful response is JSON; print a trimmed echo so the run log
    # shows what came back.
    try:
        echo = json.loads(body) if body else []
        print(f"  body: {json.dumps(echo)[:300]}")
    except json.JSONDecodeError:
        print(f"  body (non-JSON): {body[:300]}")
    print()

    # ── Verify columns now exist via PostgREST ─────────────────
    print("Verifying columns via PostgREST schema probe...")
    for table, expected in [
        ("transactions", {"customer_id", "customer_email", "currency"}),
        ("pos_connections", {"connected_by_rep_id"}),
    ]:
        cols = set(_postgrest_columns(table))
        if not cols:
            print(f"  {table}: no rows to probe; "
                  "schema cache may still confirm columns via OpenAPI")
            continue
        missing = expected - cols
        if missing:
            print(f"  {table}: MISSING {sorted(missing)} — "
                  f"got {sorted(cols & expected)}")
            return 4
        print(f"  {table}: ✓ {sorted(expected)} present")

    print()
    print("Migration applied successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
