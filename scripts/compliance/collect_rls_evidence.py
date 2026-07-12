#!/usr/bin/env python3
"""
CC6.1 live evidence collector — READ-ONLY.

Queries prod pg_policies + role_table_grants through the Supabase management
API and writes a timestamped JSON evidence artifact. Exits non-zero when the
live posture violates the control:

  V1  a policy with qual USING(true) targets anon/public/authenticated on a
      table outside the public allowlist (the PR #198 incident shape)
  V2  anon holds INSERT/UPDATE/DELETE on any sensitive table
  V3  a sensitive table has RLS disabled entirely

Environment (read-only credentials, never printed):
  SUPABASE_MGMT_TOKEN            management API token
  SUPABASE_PROJECT_REF_MERIDIAN  project ref
  COMPLIANCE_EVIDENCE_DIR        output dir (default: compliance-evidence/)

Usage: python scripts/compliance/collect_rls_evidence.py
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# Tables whose rows are published content by design (no tenant/PII data).
# spaces/space_zones are deliberately NOT here: their USING(true) policies
# were the first live catch of this collector (2026-07-12) — any logged-in
# user can read every merchant's camera-space metadata. Fix, don't allowlist.
PUBLIC_POLICY_ALLOWLIST = {"compliance_documents", "training_lessons"}

SENSITIVE_TABLES = {
    "phone_agent_config", "phone_orders", "phone_call_logs",
    "leads", "us_leads", "business_users", "checkout_sessions",
    "sales_rep_commissions", "email_send_log", "payouts", "sales_reps",
    "voice_ledger", "rep_client_assignments",
}

QUERY = """
select json_build_object(
  'policies', (select coalesce(json_agg(json_build_object(
      'table', tablename, 'policy', policyname, 'roles', roles::text,
      'cmd', cmd, 'qual', qual)), '[]'::json)
    from pg_policies where schemaname = 'public'),
  'rls_disabled', (select coalesce(json_agg(c.relname), '[]'::json)
    from pg_class c join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'public' and c.relkind = 'r' and not c.relrowsecurity),
  'anon_writes', (select coalesce(json_agg(json_build_object(
      'table', table_name, 'privilege', privilege_type)), '[]'::json)
    from information_schema.role_table_grants
    where grantee = 'anon' and table_schema = 'public'
      and privilege_type in ('INSERT','UPDATE','DELETE'))
) as posture
"""


def main() -> int:
    token = os.environ.get("SUPABASE_MGMT_TOKEN", "")
    ref = os.environ.get("SUPABASE_PROJECT_REF_MERIDIAN", "")
    if not token or not ref:
        print("SKIP: SUPABASE_MGMT_TOKEN / SUPABASE_PROJECT_REF_MERIDIAN not set "
              "(live evidence collection needs read-only credentials)")
        return 0

    req = urllib.request.Request(
        f"https://api.supabase.com/v1/projects/{ref}/database/query",
        data=json.dumps({"query": QUERY}).encode(),
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json",
                 "User-Agent": "meridian-compliance-collector/1.0"},
    )
    posture = json.loads(urllib.request.urlopen(req, timeout=30).read())[0]["posture"]

    violations = []
    for pol in posture["policies"]:
        roles = pol["roles"].strip("{}").split(",")
        broad = {r.strip() for r in roles} & {"anon", "public", "authenticated"}
        if broad and (pol["qual"] or "").strip().lower() == "true" \
                and pol["table"] not in PUBLIC_POLICY_ALLOWLIST:
            violations.append({"code": "V1", "detail": f"{pol['table']}.{pol['policy']} "
                               f"USING(true) TO {sorted(broad)}"})
    for grant in posture["anon_writes"]:
        if grant["table"] in SENSITIVE_TABLES:
            violations.append({"code": "V2", "detail": f"anon {grant['privilege']} "
                               f"on {grant['table']}"})
    for table in posture["rls_disabled"]:
        if table in SENSITIVE_TABLES:
            violations.append({"code": "V3", "detail": f"RLS disabled on {table}"})

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path(os.environ.get("COMPLIANCE_EVIDENCE_DIR", "compliance-evidence"))
    out_dir.mkdir(parents=True, exist_ok=True)
    artifact = out_dir / f"rls_posture_{stamp}.json"
    artifact.write_text(json.dumps({
        "control": "CC6.1",
        "collected_at": stamp,
        "method": "read-only pg_policies/role_table_grants via management API",
        "policy_count": len(posture["policies"]),
        "rls_disabled_tables": posture["rls_disabled"],
        "violations": violations,
    }, indent=2))

    print(f"CC6.1 evidence: {artifact} ({len(posture['policies'])} policies)")
    if violations:
        for v in violations:
            print(f"  VIOLATION {v['code']}: {v['detail']}")
        return 1
    print("  no violations")
    return 0


if __name__ == "__main__":
    sys.exit(main())
