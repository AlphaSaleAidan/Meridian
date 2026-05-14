"""
Admin auth dependency + rate limiter for Meridian API.

Admin auth: checks X-Admin-Key header against MERIDIAN_ADMIN_KEY env var.
Rate limiter: in-memory sliding window, keyed by client IP.
"""
import os
import time
from collections import defaultdict
from threading import Lock

from fastapi import Depends, HTTPException, Request
from fastapi.security import APIKeyHeader

_admin_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)


async def require_admin(key: str = Depends(_admin_key_header)):
    expected = os.environ.get("MERIDIAN_ADMIN_KEY", "")
    if not expected:
        raise HTTPException(503, "Admin access not configured")
    if not key or key != expected:
        raise HTTPException(403, "Invalid admin key")


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
