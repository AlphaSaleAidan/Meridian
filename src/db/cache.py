import hashlib
import time
from typing import Any


TTL_FAST = 30
TTL_SLOW = 300


class TTLCache:
    """In-memory TTL cache for dashboard queries."""

    def __init__(self):
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if time.monotonic() > expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl_seconds: int):
        self._store[key] = (time.monotonic() + ttl_seconds, value)

    def invalidate(self, prefix: str = ""):
        if not prefix:
            self._store.clear()
            return
        keys = [k for k in self._store if k.startswith(prefix)]
        for k in keys:
            del self._store[k]

    def invalidate_org(self, org_id: str):
        keys = [k for k in self._store if f":{org_id}:" in k]
        for k in keys:
            del self._store[k]

    @staticmethod
    def make_key(endpoint: str, org_id: str, **params) -> str:
        parts = "&".join(f"{k}={v}" for k, v in sorted(params.items()) if v is not None)
        suffix = hashlib.md5(parts.encode()).hexdigest()[:8] if parts else "0"
        return f"{endpoint}:{org_id}:{suffix}"


dashboard_cache = TTLCache()
