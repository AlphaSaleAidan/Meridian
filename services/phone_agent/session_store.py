"""
SHARED SESSION STORE — optional Redis mirror for live phone/SMS/card state.

Live call state has always lived in per-process dicts (phone._sessions,
sms_order._sms_sessions, card_on_phone._captures). That is correct with one
uvicorn worker and silently fatal with several: a mid-call webhook lands on a
worker that never saw the session, so the order or card capture dies. This
module is the shared store that lifts that constraint.

FAIL-OPEN BY DESIGN. Without REDIS_URL — which is where Railway sits today —
`shared` is False, every method short-circuits to an in-process dict, and the
callers keep behaving exactly as they do now. If Redis is configured but throws
at call time, each operation degrades to the same in-process path rather than
raising into a live call. Nothing here can hang up on a caller.

Namespaces and their TTLs mirror the existing in-module expiry constants
(phone.SESSION_TTL 600s, sms_order.SESSION_TTL 1800s, card_on_phone
_CAPTURE_TTL 300s). Those in-module sweeps stay authoritative — session values
carry their own `ts`/`created` timestamp, so a value read back from Redis
expires on exactly the same clock it always did. The Redis TTL is a backstop
that stops abandoned keys from accumulating.

PCI: the "captures" namespace holds partial card digits. Its payload is
encrypted with the same AES-256-GCM primitive used for POS OAuth tokens
(src.security.encryption, ENCRYPTION_KEY) before it ever reaches Redis, and is
decrypted on read. With no ENCRYPTION_KEY set the namespace refuses Redis
entirely and stays in-process — card data never lands in Redis in the clear.
Nothing in this module logs a value.

Usage:
    from session_store import get_session_store, NS_SESSIONS

    store = get_session_store()
    if store.shared:
        await store.set(NS_SESSIONS, call_sid, session_dict)
        session_dict = await store.get(NS_SESSIONS, call_sid)
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("meridian.phone_agent.session_store")

# Project root on sys.path so this sidecar module can import src.* whether it
# runs standalone (python main.py) or mounted under the main API app.
_PROJECT_ROOT = str(Path(__file__).resolve().parents[2])
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


# ─── Namespaces ──────────────────────────────────────────────────────────────

NS_SESSIONS = "sessions"            # phone._sessions        — live voice calls
NS_SMS_SESSIONS = "sms_sessions"    # sms_order._sms_sessions — text ordering
NS_CAPTURES = "captures"            # card_on_phone._captures — keypad card data

# Defaults match the in-module constants they mirror. Env overrides are per
# namespace so an operator can lengthen SMS sessions without touching calls.
_TTL_DEFAULTS: dict[str, int] = {
    NS_SESSIONS: 600,
    NS_SMS_SESSIONS: 1800,
    NS_CAPTURES: 300,
}
_TTL_ENV: dict[str, str] = {
    NS_SESSIONS: "PHONE_SESSION_TTL",
    NS_SMS_SESSIONS: "SMS_SESSION_TTL",
    NS_CAPTURES: "PHONE_CARD_CAPTURE_TTL",
}

# Only this namespace is encrypted at rest — it is the only one that ever holds
# card data.
_ENCRYPTED_NAMESPACES = frozenset({NS_CAPTURES})


def ttl_for(namespace: str) -> int:
    """TTL in seconds for a namespace, env-overridable, never below 1."""
    raw = os.getenv(_TTL_ENV.get(namespace, ""), "")
    if raw:
        try:
            return max(1, int(raw))
        except ValueError:
            logger.warning("Bad TTL for %s namespace; using default", namespace)
    return _TTL_DEFAULTS.get(namespace, 600)


# ─── Store ───────────────────────────────────────────────────────────────────

class SessionStore:
    """Dict-like async store, Redis-backed when REDIS_URL is set.

    Every method is safe to call unconditionally: with no Redis configured (or
    Redis erroring) they operate on the in-process dicts and never raise.
    """

    def __init__(self, url: str | None = None, prefix: str = "meridian:phone",
                 client: Any = None) -> None:
        self._url = url if url is not None else os.getenv("REDIS_URL", "").strip()
        self._prefix = prefix
        self._client = client                  # injected client wins (tests)
        self._client_ready = client is not None
        self._local: dict[str, dict[str, tuple[float, Any]]] = {}
        self._degraded = False                 # Redis configured but unusable
        self._warned_no_key = False

    # ── configuration ───────────────────────────────────────────────────

    @property
    def shared(self) -> bool:
        """True when this store mirrors to Redis rather than a local dict."""
        return bool(self._client) or bool(self._url)

    def _namespace_shared(self, namespace: str) -> bool:
        """Per-namespace gate: captures also need an encryption key."""
        if not self.shared or self._degraded:
            return False
        if namespace in _ENCRYPTED_NAMESPACES and not _encryption_available():
            if not self._warned_no_key:
                self._warned_no_key = True
                logger.warning(
                    "REDIS_URL is set but ENCRYPTION_KEY is not — the %r namespace "
                    "holds card data and stays in-process rather than writing "
                    "unencrypted to Redis.", namespace,
                )
            return False
        return True

    def _key(self, namespace: str, key: str) -> str:
        return f"{self._prefix}:{namespace}:{key}"

    async def _redis(self) -> Any:
        """Lazily open the shared client. None when unavailable."""
        if self._client_ready:
            return self._client
        self._client_ready = True
        if not self._url:
            return None
        try:
            from redis.asyncio import Redis  # noqa: PLC0415 — optional at import time
            self._client = Redis.from_url(self._url, decode_responses=True)
        except Exception as e:
            self._degraded = True
            logger.warning("Redis unavailable (%s) — phone sessions stay in-process",
                           type(e).__name__)
            self._client = None
        return self._client

    async def ping(self) -> bool:
        """True when Redis is configured AND answering. Used by the startup
        multi-worker guard, so a misconfigured URL cannot unlock multi-worker."""
        if not self.shared:
            return False
        client = await self._redis()
        if client is None:
            return False
        try:
            return bool(await client.ping())
        except Exception as e:
            logger.warning("Redis ping failed: %s", type(e).__name__)
            return False

    # ── operations ──────────────────────────────────────────────────────

    async def get(self, namespace: str, key: str) -> Any | None:
        """Value for `key`, or None if missing, expired, or unreadable.

        A corrupt or undecryptable entry is treated as missing — a caller
        mid-payment gets the "let's start over" path, never a stack trace.
        """
        if not key:
            return None
        if not self._namespace_shared(namespace):
            return self._local_get(namespace, key)
        client = await self._redis()
        if client is None:
            return self._local_get(namespace, key)
        try:
            raw = await client.get(self._key(namespace, key))
        except Exception as e:
            logger.warning("Redis get failed for %s (%s) — using in-process state",
                           namespace, type(e).__name__)
            return self._local_get(namespace, key)
        if raw is None:
            # Either genuinely gone, or a write that had to stay in-process
            # because Redis was down at the time. delete() clears both, so
            # falling through here can't resurrect a deleted session.
            return self._local_get(namespace, key)
        try:
            return _decode(namespace, raw)
        except Exception:
            # Never log the payload: this namespace may hold card digits.
            logger.warning("Discarding unreadable %s entry", namespace)
            return None

    async def set(self, namespace: str, key: str, value: Any) -> bool:
        """Store `value`. Returns True when it reached Redis."""
        if not key:
            return False
        ttl = ttl_for(namespace)
        if not self._namespace_shared(namespace):
            self._local_set(namespace, key, value, ttl)
            return False
        try:
            raw = _encode(namespace, value)
        except Exception as e:
            # Value shape the JSON codec can't take. Keep the call alive on the
            # in-process path rather than failing the webhook.
            logger.warning("Cannot serialize %s entry (%s) — keeping it in-process",
                           namespace, type(e).__name__)
            self._local_set(namespace, key, value, ttl)
            return False
        client = await self._redis()
        if client is None:
            self._local_set(namespace, key, value, ttl)
            return False
        try:
            await client.set(self._key(namespace, key), raw, ex=ttl)
            return True
        except Exception as e:
            logger.warning("Redis set failed for %s (%s) — using in-process state",
                           namespace, type(e).__name__)
            self._local_set(namespace, key, value, ttl)
            return False

    async def delete(self, namespace: str, key: str) -> bool:
        """Drop `key`. Best-effort in both backends."""
        if not key:
            return False
        self._local.get(namespace, {}).pop(key, None)
        if not self._namespace_shared(namespace):
            return False
        client = await self._redis()
        if client is None:
            return False
        try:
            await client.delete(self._key(namespace, key))
            return True
        except Exception as e:
            logger.warning("Redis delete failed for %s (%s)", namespace, type(e).__name__)
            return False

    async def touch(self, namespace: str, key: str) -> bool:
        """Extend the TTL without rewriting the value."""
        if not key:
            return False
        ttl = ttl_for(namespace)
        local = self._local.get(namespace, {})
        if key in local:
            local[key] = (time.time() + ttl, local[key][1])
        if not self._namespace_shared(namespace):
            return False
        client = await self._redis()
        if client is None:
            return False
        try:
            return bool(await client.expire(self._key(namespace, key), ttl))
        except Exception as e:
            logger.warning("Redis touch failed for %s (%s)", namespace, type(e).__name__)
            return False

    async def close(self) -> None:
        client, self._client = self._client, None
        self._client_ready = False
        if client is None:
            return
        try:
            await client.aclose()
        except Exception:
            pass

    # ── in-process fallback ─────────────────────────────────────────────

    def _local_get(self, namespace: str, key: str) -> Any | None:
        bucket = self._local.get(namespace)
        if not bucket:
            return None
        entry = bucket.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if expires_at <= time.time():
            bucket.pop(key, None)
            return None
        return value

    def _local_set(self, namespace: str, key: str, value: Any, ttl: int) -> None:
        bucket = self._local.setdefault(namespace, {})
        now = time.time()
        # Opportunistic sweep so an abandoned call can't pin memory forever,
        # matching the _cleanup_sessions()/_gc() behaviour of the callers.
        for k in [k for k, (exp, _) in bucket.items() if exp <= now]:
            bucket.pop(k, None)
        bucket[key] = (now + ttl, value)


# ─── Codec ───────────────────────────────────────────────────────────────────

def _encryption_available() -> bool:
    return bool(os.getenv("ENCRYPTION_KEY", "").strip())


def _encode(namespace: str, value: Any) -> str:
    """JSON, then AES-256-GCM for namespaces that hold card data."""
    raw = json.dumps(value)
    if namespace in _ENCRYPTED_NAMESPACES:
        from src.security.encryption import encrypt_token  # noqa: PLC0415
        return encrypt_token(raw)
    return raw


def _decode(namespace: str, raw: str) -> Any:
    if namespace in _ENCRYPTED_NAMESPACES:
        from src.security.encryption import decrypt_token  # noqa: PLC0415
        raw = decrypt_token(raw)
    return json.loads(raw)


# ─── Module-level accessor ───────────────────────────────────────────────────

_STORE: SessionStore | None = None


def get_session_store() -> SessionStore:
    """The process-wide store. One lazily-opened Redis client is shared by all
    three namespaces."""
    global _STORE
    if _STORE is None:
        _STORE = SessionStore()
    return _STORE


def reset_session_store(store: SessionStore | None = None) -> None:
    """Swap the process-wide store. Test seam — production never calls this."""
    global _STORE
    _STORE = store
