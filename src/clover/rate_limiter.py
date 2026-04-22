"""
Token Bucket Rate Limiter — Controls Clover API request rate.

Clover limits:
  - 16 requests per second per access token (across all apps)
  - No separate batch vs standard distinction
  - Cross-app limit: all apps sharing a token share the budget

We stay safely under: 12 req/sec standard.
"""
import asyncio
import time
from dataclasses import dataclass, field


@dataclass
class CloverRateLimiter:
    """
    Async token bucket rate limiter for Clover API.

    Tokens refill at `rate` per second up to `capacity`.
    Each API call consumes 1 token. If bucket is empty, wait.
    """
    rate: float = 12.0         # tokens per second
    capacity: float = 16.0     # max burst capacity
    _tokens: float = field(init=False)
    _last_refill: float = field(init=False)
    _lock: asyncio.Lock = field(init=False, default_factory=asyncio.Lock)

    def __post_init__(self):
        self._tokens = self.capacity
        self._last_refill = time.monotonic()

    def _refill(self):
        """Add tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
        self._last_refill = now

    async def acquire(self, tokens: float = 1.0):
        """
        Acquire tokens. Waits if not enough available.

        Returns the total wait time in seconds (0 if no wait needed).
        """
        total_wait = 0.0

        while True:
            async with self._lock:
                self._refill()

                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return total_wait

                deficit = tokens - self._tokens
                wait_time = deficit / self.rate

            await asyncio.sleep(wait_time)
            total_wait += wait_time

    @property
    def available_tokens(self) -> float:
        """Current available tokens (approximate)."""
        self._refill()
        return self._tokens


# Pre-configured limiter (Clover: 16/sec limit, we use 12/sec)
standard_limiter = CloverRateLimiter(rate=12.0, capacity=16.0)
