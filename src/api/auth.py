"""
Auth dependencies for Meridian API.

- require_admin: X-Admin-Key header check (admin-only ops)
- require_service_auth: Authorization Bearer token OR X-Admin-Key (service/internal endpoints)
- require_org_access: validates org_id access (placeholder for JWT — currently checks org exists)
"""
import os
import time
from collections import defaultdict
from ipaddress import ip_address, ip_network
from threading import Lock

from fastapi import Depends, HTTPException, Request
from fastapi.security import APIKeyHeader

_admin_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)
_auth_header = APIKeyHeader(name="Authorization", auto_error=False)


async def require_admin(key: str = Depends(_admin_key_header)):
    expected = os.environ.get("MERIDIAN_ADMIN_KEY", "")
    if not expected:
        raise HTTPException(503, "Admin access not configured")
    if not key or key != expected:
        raise HTTPException(403, "Invalid admin key")


async def require_service_auth(
    admin_key: str = Depends(_admin_key_header),
    auth_header: str = Depends(_auth_header),
):
    """Require either X-Admin-Key or Authorization Bearer token.
    Used for internal/service endpoints that shouldn't be fully public."""
    admin_expected = os.environ.get("MERIDIAN_ADMIN_KEY", "")
    service_token = os.environ.get("MERIDIAN_SERVICE_TOKEN", "")

    if admin_key and admin_expected and admin_key == admin_expected:
        return
    if auth_header and service_token:
        token = auth_header.removeprefix("Bearer ").strip()
        if token == service_token:
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
