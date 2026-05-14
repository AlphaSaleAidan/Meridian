"""
Rate limiting for Meridian FastAPI endpoints.

Uses slowapi backed by Redis. Limits calibrated to real usage:
- Auth endpoints: strict (block brute force)
- POS operations: moderate (connects are rare)
- Data endpoints: lenient (merchants read often)
"""
import os

from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request

REDIS_URL = os.environ.get("REDIS_URL", "memory://")

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=REDIS_URL,
    default_limits=["200/minute"],
    headers_enabled=True,
)


def get_user_key(request: Request) -> str:
    ip = request.client.host if request.client else "unknown"
    user_id = getattr(request.state, "user_id", None)
    return f"{ip}:{user_id}" if user_id else ip
