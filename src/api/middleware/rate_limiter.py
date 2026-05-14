"""
Rate limiting middleware for Meridian FastAPI endpoints.

Implements rate limiting as middleware (not per-route decorators)
because FastAPI auto-converts dict returns → Response objects,
which breaks slowapi's decorator approach.

Limits by IP address, with tighter limits on sensitive paths.
"""
import os
import time
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

RATE_LIMITS: dict[str, tuple[int, int]] = {
    "/api/admin/": (10, 3600),
    "/api/pos/connect": (10, 3600),
    "/api/pos/test-connection": (20, 3600),
    "/api/garry/chat": (30, 60),
}

DEFAULT_LIMIT = (200, 60)

_buckets: dict[str, list[float]] = defaultdict(list)


def _get_limit(path: str) -> tuple[int, int]:
    for prefix, limit in RATE_LIMITS.items():
        if path.startswith(prefix):
            return limit
    return DEFAULT_LIMIT


class RateLimitMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):
        ip = request.client.host if request.client else "unknown"
        path = request.url.path
        max_requests, window_seconds = _get_limit(path)

        key = f"{ip}:{path}"
        now = time.monotonic()
        cutoff = now - window_seconds

        hits = _buckets[key]
        hits[:] = [t for t in hits if t > cutoff]

        if len(hits) >= max_requests:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."},
                headers={
                    "Retry-After": str(window_seconds),
                    "X-RateLimit-Limit": str(max_requests),
                    "X-RateLimit-Remaining": "0",
                },
            )

        hits.append(now)

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Remaining"] = str(max(0, max_requests - len(hits)))
        return response
