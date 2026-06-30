"""Shared Supabase auth-admin helpers for rep/user cleanup.

Both the US and Canada rep-management routes need to fully remove a test/rep
account — not just the `sales_reps` row, but the underlying Supabase
`auth.users` login. Without deleting the auth user, a "removed" rep can simply
sign in again (the frontend auto-creates a sales_reps row on login) and the
account reappears — which is exactly the "can't delete some test users"
complaint. These helpers centralise that logic so both portals behave
identically.

All functions are best-effort and NEVER raise on Supabase errors — the caller
decides how to react. The only hard dependency is a service-role key (the admin
API rejects anon/user tokens).
"""
import logging

logger = logging.getLogger("meridian.api.supabase_admin")


async def find_auth_user_by_email(client, supabase_url: str, service_key: str, email: str) -> dict | None:
    """Page through the Supabase admin user list to find a user by email.

    The GoTrue admin API has no server-side email filter, so we page (200 per
    page, up to 4000 users — same bound the create-customer reset path uses).
    Returns the user dict or None.
    """
    target = (email or "").strip().lower()
    if not target:
        return None
    for page in range(1, 21):  # 20 * 200 = 4000 users
        resp = await client.get(
            f"{supabase_url}/auth/v1/admin/users",
            headers={"Authorization": f"Bearer {service_key}", "apikey": service_key},
            params={"page": page, "per_page": 200},
        )
        if resp.status_code != 200:
            logger.error("admin user list failed p%s: %s %s", page, resp.status_code, resp.text[:200])
            break
        users = resp.json().get("users", [])
        for u in users:
            if (u.get("email") or "").strip().lower() == target:
                return u
        if len(users) < 200:
            break
    return None


async def delete_auth_user_by_email(
    client,
    supabase_url: str,
    service_key: str,
    email: str,
    protected_emails: list[str] | None = None,
) -> tuple[bool, str]:
    """Best-effort delete of the Supabase auth.users record for `email`.

    Returns (deleted, detail). Detail is one of:
      - "deleted"                 → auth user removed
      - "protected"               → email is on the protected allowlist; skipped
      - "no_auth_user"            → no matching auth user found (already gone)
      - "delete_failed:<status>"  → Supabase refused the delete (e.g. the user
                                     still owns a business via a NO ACTION FK —
                                     a real merchant, not a disposable test rep)

    Never raises — rep-row removal must still report success even if the login
    can't be torn down.
    """
    target = (email or "").strip().lower()
    if not target:
        return False, "no_auth_user"
    if protected_emails and target in [e.strip().lower() for e in protected_emails]:
        logger.warning("auth-user delete BLOCKED for protected email %s", target)
        return False, "protected"
    try:
        user = await find_auth_user_by_email(client, supabase_url, service_key, target)
        if not user:
            return False, "no_auth_user"
        uid = user["id"]
        resp = await client.delete(
            f"{supabase_url}/auth/v1/admin/users/{uid}",
            headers={"Authorization": f"Bearer {service_key}", "apikey": service_key},
        )
        if resp.status_code in (200, 204):
            logger.info("auth user deleted: %s (%s)", uid, target)
            return True, "deleted"
        logger.error("auth user delete failed for %s: %s %s", target, resp.status_code, resp.text[:200])
        return False, f"delete_failed:{resp.status_code}"
    except Exception as exc:  # noqa: BLE001 — best-effort, never propagate
        logger.error("auth user delete errored for %s: %s", target, exc)
        return False, "delete_failed:exception"
