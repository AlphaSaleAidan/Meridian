"""
Token Bucket Rate Limiter — Controls Square API request rate.

Square limits:
  - Standard endpoints: ~10 req/sec per app
  - Batch endpoints: ~5 req/sec
  - SearchOrders: ~5 req/sec

We stay under by default: 8 req/sec standard, 4 req/sec batch.
"""
import asyncio
import time
from dataclasses import dataclass, field


@dataclass
class TokenBucketRateLimiter:
    """
    Async token bucket rate limiter.
    
    Tokens refill at `rate` per second up to `capacity`.
    Each API call consumes 1 token. If bucket is empty, wait.
    """
    rate: float = 8.0          # tokens per second
    capacity: float = 10.0     # max burst capacity
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

                # Calculate wait time for tokens to become available
                deficit = tokens - self._tokens
                wait_time = deficit / self.rate

            # Wait outside the lock so other coroutines can proceed
            await asyncio.sleep(wait_time)
            total_wait += wait_time
            # Re-acquire lock and re-check (avoids going negative)

    @property
    def available_tokens(self) -> float:
        """Current available tokens (approximate, not thread-safe)."""
        self._refill()
        return self._tokens


# Pre-configured limiters
standard_limiter = TokenBucketRateLimiter(rate=8.0, capacity=10.0)
batch_limiter = TokenBucketRateLimiter(rate=4.0, capacity=5.0)
