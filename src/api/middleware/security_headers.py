"""
Security headers middleware — adds defensive HTTP headers to every response,
including unhandled 500 errors.
"""
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger("meridian.middleware.security_headers")

_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "connect-src 'self' https://*.supabase.co wss://*.supabase.co; "
        "frame-ancestors 'none';"
    ),
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": (
        "camera=(self), microphone=(self), geolocation=(), "
        "payment=(), usb=(), bluetooth=()"
    ),
}


def _apply_headers(response: Response) -> Response:
    for key, value in _SECURITY_HEADERS.items():
        response.headers[key] = value
    if "Server" in response.headers:
        del response.headers["Server"]
    if "X-Powered-By" in response.headers:
        del response.headers["X-Powered-By"]
    return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next) -> Response:
        try:
            response = await call_next(request)
        except Exception:
            # Log with traceback BEFORE swallowing — a silent 500 here made a
            # real webhook failure undebuggable (no trace anywhere). The client
            # still gets a generic message; operators get the cause.
            logger.exception("Unhandled exception in %s %s",
                             request.method, request.url.path)
            response = JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"},
            )
        return _apply_headers(response)
