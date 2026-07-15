"""
Auth dependencies for Meridian API.

- require_admin: X-Admin-Key header check (admin-only ops)
- require_jwt: Supabase JWT verification (returns user dict)
- require_admin_jwt: JWT + admin email check
- require_service_auth: Authorization Bearer token OR X-Admin-Key (service/internal endpoints)
"""
import hmac
import json
import logging
import os
import time
from collections import defaultdict
from ipaddress import ip_address, ip_network
from threading import Lock

from fastapi import Depends, HTTPException, Request
from fastapi.security import APIKeyHeader

logger = logging.getLogger("meridian.auth")

_admin_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)
_auth_header = APIKeyHeader(name="Authorization", auto_error=False)

ADMIN_EMAILS = [
    "apierce@alphasale.co",
    "aidanpierce72@gmail.com",
    "aidanpierce@meridian.tips",
    "cheungenochmgmt@gmail.com",
    "aidanvietnguyen@gmail.com",
]


async def require_admin(key: str = Depends(_admin_key_header)):
    expected = os.environ.get("MERIDIAN_ADMIN_KEY", "")
    if not expected:
        raise HTTPException(503, "Admin access not configured")
    # Constant-time compare — a plain != leaks the correct prefix length via
    # timing, letting an attacker brute-force the key byte-by-byte.
    if not key or not hmac.compare_digest(key, expected):
        raise HTTPException(403, "Invalid admin key")


async def _verify_supabase_token(token: str) -> dict | None:
    """Verify a Supabase JWT by calling the auth API. Returns user dict or None."""
    import httpx
    supabase_url = os.environ.get("SUPABASE_URL", "")
    service_key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        or os.environ.get("SUPABASE_SERVICE_KEY", "")
    )
    if not supabase_url or not service_key:
        return None
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{supabase_url}/auth/v1/user",
                headers={"Authorization": f"Bearer {token}", "apikey": service_key},
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass
    return None


async def require_jwt(auth_header: str = Depends(_auth_header)) -> dict:
    """Verify Supabase JWT and return user dict. Use as Depends(require_jwt)."""
    if not auth_header:
        raise HTTPException(401, "Authorization header required")
    token = auth_header.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(401, "Bearer token required")
    user = await _verify_supabase_token(token)
    if not user:
        raise HTTPException(401, "Invalid or expired token")
    return user


async def require_admin_jwt(user: dict = Depends(require_jwt)) -> dict:
    """Verify JWT user is in the admin list. Use as Depends(require_admin_jwt)."""
    email = (user.get("email") or "").lower()
    if email not in [e.lower() for e in ADMIN_EMAILS]:
        logger.warning("Admin access denied for %s", email)
        raise HTTPException(403, "Admin access required")
    return user


async def _check_org_membership(user: dict, org_id: str) -> bool:
    """Return True if the JWT user is the owner of, or a member of, the given org.

    Membership rules:
      - businesses.owner_user_id == user.id
      - OR business_users row with business_id == org_id AND user_id == user.id AND is_active
      - OR user email is in the global ADMIN_EMAILS allowlist (for support access)
    """
    import httpx
    email = (user.get("email") or "").lower()
    if email and email in [e.lower() for e in ADMIN_EMAILS]:
        return True

    user_id = user.get("id") or user.get("sub") or ""
    if not user_id or not org_id:
        return False

    supabase_url = os.environ.get("SUPABASE_URL", "")
    service_key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        or os.environ.get("SUPABASE_SERVICE_KEY", "")
    )
    if not supabase_url or not service_key:
        # If Supabase isn't configured we can't verify — fail closed.
        return False

    headers = {"Authorization": f"Bearer {service_key}", "apikey": service_key}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            owner_resp = await client.get(
                f"{supabase_url}/rest/v1/businesses",
                params={"id": f"eq.{org_id}", "owner_user_id": f"eq.{user_id}", "select": "id"},
                headers=headers,
            )
            if owner_resp.status_code == 200 and owner_resp.json():
                return True

            member_resp = await client.get(
                f"{supabase_url}/rest/v1/business_users",
                params={
                    "business_id": f"eq.{org_id}",
                    "user_id": f"eq.{user_id}",
                    "is_active": "eq.true",
                    "select": "user_id",
                },
                headers=headers,
            )
            if member_resp.status_code == 200 and member_resp.json():
                return True
    except Exception as exc:
        logger.warning("org membership lookup failed for user=%s org=%s: %s", email, org_id, exc)

    return False


async def _org_id_from_body(request: Request) -> str | None:
    """Resolve org_id (or merchant_id) from the request BODY for endpoints that
    pass it there instead of query/path.

    Reads via Starlette's cached body/form (`request.body()` caches `_body`,
    `request.form()` caches `_form`) so the handler still receives the full
    payload — reading here does NOT consume the request stream.
    """
    if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
        return None
    ctype = request.headers.get("content-type", "")
    try:
        if "application/json" in ctype:
            raw = await request.body()  # cached on request._body for the handler
            if not raw:
                return None
            data = json.loads(raw)
            if isinstance(data, dict):
                val = data.get("org_id") or data.get("merchant_id")
                return val if isinstance(val, str) and val.strip() else None
        elif "multipart/form-data" in ctype or "x-www-form-urlencoded" in ctype:
            form = await request.form()  # cached on request._form for the handler
            val = form.get("org_id") or form.get("merchant_id")
            return val if isinstance(val, str) and val.strip() else None
    except Exception as exc:
        logger.warning("require_org_access: body org_id resolution failed: %s", exc)
    return None


async def require_org_access(
    request: Request,
    auth_header: str = Depends(_auth_header),
) -> dict | None:
    """Tenancy guard for org-scoped endpoints.

    Behavior:
      - If the request has no org_id (in query or path), this is a no-op and returns None.
        Other auth deps (e.g. require_admin on admin endpoints) handle their own checks.
      - If org_id is present, requires a valid JWT and verifies org membership.
      - On mismatch: raises 403 by default. If TENANCY_ENFORCEMENT_DISABLED is truthy,
        logs a warning and lets the call through (emergency rollback knob).

    Apply at the router level:
        router = APIRouter(prefix="...", dependencies=[Depends(require_org_access)])
    """
    org_id = request.query_params.get("org_id") or request.path_params.get("org_id")
    if not org_id:
        # SECURITY (CA-1/CA-2): also resolve org_id from the request BODY. POS
        # connect/disconnect/test, cline, predictive, spaces, vision and
        # upload-csv all pass org_id in the body — previously the guard saw no
        # query/path org_id, returned None (no-op), and allowed UNAUTHENTICATED
        # cross-tenant writes. Now a body org_id is enforced exactly like a
        # query/path one (valid JWT + verified membership below).
        org_id = await _org_id_from_body(request)
    if not org_id:
        # Genuinely no org param anywhere → no-op; routes with no org are guarded
        # by their own deps (require_admin / require_jwt / etc.).
        return None

    # An org was named (query, path, OR body) → require a valid principal AND
    # membership. Deny by default if either is missing.
    if not auth_header:
        raise HTTPException(401, "Authorization header required for org-scoped endpoint")
    token = auth_header.removeprefix("Bearer ").strip()
    user = await _verify_supabase_token(token)
    if not user:
        raise HTTPException(401, "Invalid or expired token")

    if await _check_org_membership(user, org_id):
        return user

    disabled = os.environ.get("TENANCY_ENFORCEMENT_DISABLED", "").lower() in ("true", "1", "yes")
    if disabled:
        logger.warning(
            "TENANCY_WARN (enforcement disabled) user=%s email=%s tried org=%s",
            user.get("id"), user.get("email"), org_id,
        )
        return user

    logger.warning(
        "TENANCY_DENY user=%s email=%s tried org=%s",
        user.get("id"), user.get("email"), org_id,
    )
    raise HTTPException(403, "Access denied: you are not a member of this organization")


async def require_org_member(user: dict, org_id: str) -> None:
    """Explicit org-membership check for endpoints that carry the org id in the
    request body or under a different param name (require_org_access only sees
    `org_id` in query/path params). Call inside the endpoint after require_jwt:

        user: dict = Depends(require_jwt)
        await require_org_member(user, req.merchant_id)

    Honors the same TENANCY_ENFORCEMENT_DISABLED rollback knob as require_org_access.
    """
    if await _check_org_membership(user, org_id):
        return

    disabled = os.environ.get("TENANCY_ENFORCEMENT_DISABLED", "").lower() in ("true", "1", "yes")
    if disabled:
        logger.warning(
            "TENANCY_WARN (enforcement disabled) user=%s email=%s tried org=%s",
            user.get("id"), user.get("email"), org_id,
        )
        return

    logger.warning(
        "TENANCY_DENY user=%s email=%s tried org=%s",
        user.get("id"), user.get("email"), org_id,
    )
    raise HTTPException(403, "Access denied: you are not a member of this organization")


async def require_service_auth(
    admin_key: str = Depends(_admin_key_header),
    auth_header: str = Depends(_auth_header),
) -> dict:
    """Accept X-Admin-Key, MERIDIAN_SERVICE_TOKEN, or a valid Supabase session token.

    Returns a principal describing who authenticated:
        {"kind": "admin"}                       — X-Admin-Key
        {"kind": "service"}                     — MERIDIAN_SERVICE_TOKEN
        {"kind": "user", "user": {...}}         — Supabase session

    NOTE (security): this dependency authenticates but does NOT authorize against a
    specific org. Endpoints that take a merchant_id/org_id and return tenant data
    MUST additionally call ``enforce_service_member(principal, org_id)`` to prevent
    a logged-in user from reading another tenant's data (BOLA). Routes that only
    expose global/admin data should use ``require_admin_auth`` instead.
    """
    admin_expected = os.environ.get("MERIDIAN_ADMIN_KEY", "")
    service_token = os.environ.get("MERIDIAN_SERVICE_TOKEN", "")

    if admin_key and admin_expected and hmac.compare_digest(admin_key, admin_expected):
        return {"kind": "admin"}
    if auth_header:
        token = auth_header.removeprefix("Bearer ").strip()
        if service_token and hmac.compare_digest(token, service_token):
            return {"kind": "service"}
        user = await _verify_supabase_token(token)
        if user:
            return {"kind": "user", "user": user}
    raise HTTPException(403, "Authentication required")


async def require_admin_auth(
    admin_key: str = Depends(_admin_key_header),
    auth_header: str = Depends(_auth_header),
) -> dict:
    """Strict machine-only auth: accept ONLY X-Admin-Key, MERIDIAN_SERVICE_TOKEN, or
    a user whose email is in ADMIN_EMAILS. Use for global/cross-tenant admin
    surfaces (e.g. the payout ledger) that must never be exposed to an ordinary
    logged-in merchant user."""
    admin_expected = os.environ.get("MERIDIAN_ADMIN_KEY", "")
    service_token = os.environ.get("MERIDIAN_SERVICE_TOKEN", "")

    if admin_key and admin_expected and hmac.compare_digest(admin_key, admin_expected):
        return {"kind": "admin"}
    if auth_header:
        token = auth_header.removeprefix("Bearer ").strip()
        if service_token and hmac.compare_digest(token, service_token):
            return {"kind": "service"}
        user = await _verify_supabase_token(token)
        if user:
            email = (user.get("email") or "").lower()
            if email and email in [e.lower() for e in ADMIN_EMAILS]:
                return {"kind": "user", "user": user}
    raise HTTPException(403, "Admin authentication required")


async def enforce_service_member(principal: dict, org_id: str) -> None:
    """Authorize a ``require_service_auth`` principal against a specific org.

    No-op for machine principals (admin/service) and ADMIN_EMAILS users; for an
    ordinary session user, requires verified org membership (same rules as
    require_org_member). Honors TENANCY_ENFORCEMENT_DISABLED for rollback."""
    if not principal or principal.get("kind") in ("admin", "service"):
        return
    user = principal.get("user") or {}
    await require_org_member(user, org_id)


PRIVATE_NETWORKS = [
    ip_network("10.0.0.0/8"),
    ip_network("172.16.0.0/12"),
    ip_network("192.168.0.0/16"),
    ip_network("127.0.0.0/8"),
    ip_network("169.254.0.0/16"),
    ip_network("::1/128"),
    ip_network("fc00::/7"),
    ip_network("fe80::/10"),
]


def is_private_url(url: str) -> bool:
    """Check if a URL targets a private/internal IP range."""
    from urllib.parse import urlparse
    import socket
    parsed = urlparse(url)
    hostname = parsed.hostname
    if not hostname:
        return True
    if hostname in ("localhost", "metadata.google.internal"):
        return True
    try:
        addr = ip_address(hostname)
        return any(addr in net for net in PRIVATE_NETWORKS)
    except ValueError:
        pass
    try:
        resolved = socket.getaddrinfo(hostname, None)
        for _, _, _, _, sockaddr in resolved:
            addr = ip_address(sockaddr[0])
            if any(addr in net for net in PRIVATE_NETWORKS):
                return True
    except (socket.gaierror, OSError):
        pass
    return False


class RateLimiter:
    def __init__(self, requests_per_minute: int = 30):
        self._rpm = requests_per_minute
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def check(self, client_ip: str) -> bool:
        now = time.monotonic()
        cutoff = now - 60.0
        with self._lock:
            hits = self._hits[client_ip]
            self._hits[client_ip] = [t for t in hits if t > cutoff]
            if len(self._hits[client_ip]) >= self._rpm:
                return False
            self._hits[client_ip].append(now)
            return True


_default_limiter = RateLimiter(requests_per_minute=30)
_scrape_limiter = RateLimiter(requests_per_minute=5)


class HourRateLimiter:
    """Sliding-window rate limiter measured in requests per hour."""
    def __init__(self, requests_per_hour: int):
        self._rph = requests_per_hour
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def check(self, client_ip: str) -> bool:
        now = time.monotonic()
        cutoff = now - 3600.0
        with self._lock:
            hits = self._hits[client_ip]
            self._hits[client_ip] = [t for t in hits if t > cutoff]
            if len(self._hits[client_ip]) >= self._rph:
                return False
            self._hits[client_ip].append(now)
            return True


_signup_limiter = HourRateLimiter(requests_per_hour=5)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # Last hop is appended by our own proxy; earlier hops are client-controlled.
        return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


async def rate_limit(request: Request):
    if not _default_limiter.check(_client_ip(request)):
        raise HTTPException(429, "Too many requests — try again in a minute")


async def rate_limit_scrape(request: Request):
    if not _scrape_limiter.check(_client_ip(request)):
        raise HTTPException(429, "Scrape rate limited — max 5 per minute")


async def rate_limit_signup(request: Request):
    """Hard cap on rep-signup attempts: 5 per hour per IP, to block account-spam bots."""
    if not _signup_limiter.check(_client_ip(request)):
        raise HTTPException(429, "Too many signup attempts — try again in an hour")
