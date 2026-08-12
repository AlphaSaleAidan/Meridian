#!/usr/bin/env python3
"""Provision a region rep login (20260812 sales regions).

Creates (or updates) a Supabase auth user + sales_reps row for an isolated
region. First use: Enoch Cheung's Odyssey Region — one login that works on
BOTH portals (portal_context='all'), rooted as the region lead
(role='regional_manager', no manager), fenced by region='odyssey'.

Requires the 20260812_sales_regions.sql migration to be applied first, and
SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY in the environment (source them from
/root/.secrets — never paste keys).

Usage:
  python scripts/provision_region_rep.py \
    --email enoch@example.com --name "Enoch Cheung" \
    --region odyssey --role regional_manager
  # add --password to set one explicitly; omitted = generated and printed once
"""
from __future__ import annotations

import argparse
import os
import secrets
import string
import sys

import httpx

VALID_ROLES = {
    "admin", "vp_sales", "regional_manager", "district_manager",
    "office_manager", "assistant_manager", "sales_rep",
}


def _gen_password() -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(14))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--email", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--region", required=True, help="region slug, e.g. odyssey")
    ap.add_argument("--role", default="regional_manager", choices=sorted(VALID_ROLES))
    ap.add_argument("--portal", default="all", choices=["us", "canada", "all"])
    ap.add_argument("--password", default=None, help="omit to generate one")
    args = ap.parse_args()

    supabase_url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    service_key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        or os.environ.get("SUPABASE_SERVICE_KEY", "")
    )
    if not supabase_url or not service_key:
        print("ERROR: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set", file=sys.stderr)
        return 1

    email = args.email.strip().lower()
    password = args.password or _gen_password()
    generated = args.password is None
    headers = {
        "Authorization": f"Bearer {service_key}",
        "apikey": service_key,
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=20.0) as client:
        # 1. Auth user (idempotent: 422 already-registered → set password/meta).
        resp = client.post(
            f"{supabase_url}/auth/v1/admin/users",
            headers=headers,
            json={
                "email": email,
                "password": password,
                "email_confirm": True,
                "user_metadata": {
                    "full_name": args.name,
                    "role": "sales_rep",
                    "portal": args.portal,
                    "region": args.region,
                },
            },
        )
        if resp.status_code in (200, 201):
            print(f"auth user created: {email}")
        elif resp.status_code == 422 and "already been registered" in resp.text.lower():
            print(f"auth user already exists: {email} (password unchanged)")
            generated = False
        else:
            print(f"ERROR: auth create failed {resp.status_code}: {resp.text[:300]}", file=sys.stderr)
            return 1

        # 2. sales_reps row (upsert on email).
        resp = client.post(
            f"{supabase_url}/rest/v1/sales_reps?on_conflict=email",
            headers={**headers, "Prefer": "return=representation,resolution=merge-duplicates"},
            json={
                "name": args.name,
                "email": email,
                "commission_rate": 0.70,
                "is_active": True,
                "portal_context": args.portal,
                "role": args.role,
                "region": args.region,
            },
        )
        if resp.status_code not in (200, 201):
            print(f"ERROR: sales_reps upsert failed {resp.status_code}: {resp.text[:300]}", file=sys.stderr)
            return 1
        row = resp.json()
        row = row[0] if isinstance(row, list) else row
        print(f"sales_reps row: id={row.get('id')} region={row.get('region')} "
              f"role={row.get('role')} portal={row.get('portal_context')}")

    if generated:
        print(f"TEMP PASSWORD (share once, then have them change it): {password}")
    print("Login works on BOTH portals: /us/portal/login and /canada/portal/login")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
