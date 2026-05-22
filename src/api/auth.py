"""
Auth dependencies for Meridian API.

- require_admin: X-Admin-Key header check (admin-only ops)
- require_jwt: Supabase JWT verification (returns user dict)
- require_admin_jwt: JWT + admin email check
- require_service_auth: Authorization Bearer token OR X-Admin-Key (service/internal endpoints)
"""
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
    if not key or key != expected:
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


async def require_service_auth(
    admin_key: str = Depends(_admin_key_header),
    auth_header: str = Depends(_auth_header),
):
    """Accept X-Admin-Key, MERIDIAN_SERVICE_TOKEN, or a valid Supabase session token."""
    admin_expected = os.environ.get("MERIDIAN_ADMIN_KEY", "")
    service_token = os.environ.get("MERIDIAN_SERVICE_TOKEN", "")

    if admin_key and admin_expected and admin_key == admin_expected:
        return
    if auth_header:
        token = auth_header.removeprefix("Bearer ").strip()
        if service_token and token == service_token:
            return
        user = await _verify_supabase_token(token)
        if user:
            return
    raise HTTPException(403, "Authentication required")


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


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def rate_limit(request: Request):
    if not _default_limiter.check(_client_ip(request)):
        raise HTTPException(429, "Too many requests — try again in a minute")


async def rate_limit_scrape(request: Request):
    if not _scrape_limiter.check(_client_ip(request)):
        raise HTTPException(429, "Scrape rate limited — max 5 per minute")
