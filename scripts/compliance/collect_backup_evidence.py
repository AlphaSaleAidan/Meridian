#!/usr/bin/env python3
"""
A1 live evidence collector — READ-ONLY.

Fetches Supabase database backup/PITR status through the management API and
writes a timestamped JSON evidence artifact. Exits non-zero when no backup
newer than MAX_BACKUP_AGE_HOURS (default 48) exists — that's the availability
control failing, not the collector.

Environment: SUPABASE_MGMT_TOKEN, SUPABASE_PROJECT_REF_MERIDIAN,
COMPLIANCE_EVIDENCE_DIR (default compliance-evidence/).
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

MAX_BACKUP_AGE_HOURS = int(os.environ.get("MAX_BACKUP_AGE_HOURS", "48"))


def main() -> int:
    token = os.environ.get("SUPABASE_MGMT_TOKEN", "")
    ref = os.environ.get("SUPABASE_PROJECT_REF_MERIDIAN", "")
    if not token or not ref:
        print("SKIP: management credentials not set")
        return 0

    req = urllib.request.Request(
        f"https://api.supabase.com/v1/projects/{ref}/database/backups",
        headers={"Authorization": f"Bearer {token}",
                 "User-Agent": "meridian-compliance-collector/1.0"},
    )
    data = json.loads(urllib.request.urlopen(req, timeout=30).read())

    backups = data.get("backups", []) if isinstance(data, dict) else data
    pitr = data.get("pitr_enabled") if isinstance(data, dict) else None
    newest = None
    for b in backups:
        ts = b.get("inserted_at") or b.get("created_at") or ""
        if ts and (newest is None or ts > newest):
            newest = ts

    fresh = False
    if newest:
        try:
            newest_dt = datetime.fromisoformat(newest.replace("Z", "+00:00"))
            fresh = datetime.now(timezone.utc) - newest_dt < timedelta(hours=MAX_BACKUP_AGE_HOURS)
        except ValueError:
            pass

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path(os.environ.get("COMPLIANCE_EVIDENCE_DIR", "compliance-evidence"))
    out_dir.mkdir(parents=True, exist_ok=True)
    artifact = out_dir / f"backup_status_{stamp}.json"
    artifact.write_text(json.dumps({
        "control": "A1.2",
        "collected_at": stamp,
        "method": "read-only management API /database/backups",
        "backup_count": len(backups),
        "newest_backup": newest,
        "pitr_enabled": pitr,
        f"fresh_within_{MAX_BACKUP_AGE_HOURS}h": fresh,
    }, indent=2))

    print(f"A1 evidence: {artifact} (backups={len(backups)}, newest={newest}, pitr={pitr})")
    if not backups and not pitr:
        print("  VIOLATION: no backups and PITR not enabled")
        return 1
    if backups and not fresh:
        print(f"  VIOLATION: newest backup older than {MAX_BACKUP_AGE_HOURS}h")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
