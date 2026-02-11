"""
Rate Limiter
Equivalent to Pi Mono's packages/ai/src/utils/rate-limiter.ts

Advanced rate limiting with token bucket and sliding window.
"""
import time
import asyncio
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum
from collections import deque
import threading


class RateLimitStrategy(Enum):
    """Rate limiting strategies"""
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"


@dataclass
class RateLimitConfig:
    """Rate limit configuration"""
    requests_per_minute: int = 60
    tokens_per_minute: int = 100000
    burst_size: int = 10
    strategy: RateLimitStrategy = RateLimitStrategy.TOKEN_BUCKET


class RateLimiter:
    """
    Advanced rate limiter for API calls.
    
    Supports multiple strategies:
    - Token bucket: Allows bursts up to bucket size
    - Sliding window: Smooth rate over time window
    - Fixed window: Resets at window boundaries
    
    Example:
        >>> limiter = RateLimiter(requests_per_minute=60)
        >>> await limiter.acquire()
        >>> # Make API call
        >>> limiter.release()
    """
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        """
        Initialize rate limiter.
        
        Args:
            config: Rate limit configuration
        """
        self.config = config or RateLimitConfig()
        self._strategy = self.config.strategy
        
        # Token bucket state
        self._tokens = self.config.burst_size
        self._last_update = time.time()
        self._token_lock = threading.Lock()
        
        # Sliding window state
        self._request_times: deque = deque()
        self._window_lock = threading.Lock()
        
        # Fixed window state
        self._window_start = time.time()
        self._window_count = 0
        self._fixed_lock = threading.Lock()
        
        # Async lock for async operations
        self._async_lock = asyncio.Lock()
    
    async def acquire(self, tokens: int = 1) -> bool:
        """
        Acquire permission to make a request.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            True if acquired, False if would block
        """
        if self._strategy == RateLimitStrategy.TOKEN_BUCKET:
            return await self._acquire_token_bucket(tokens)
        elif self._strategy == RateLimitStrategy.SLIDING_WINDOW:
            return await self._acquire_sliding_window(tokens)
        else:
            return await self._acquire_fixed_window(tokens)
    
    async def acquire_wait(self, tokens: int = 1, timeout: Optional[float] = None) -> bool:
        """
        Acquire permission, waiting if necessary.
        
        Args:
            tokens: Number of tokens to consume
            timeout: Maximum wait time in seconds
            
        Returns:
            True if acquired, False on timeout
        """
        start = time.time()
        
        while True:
            if await self.acquire(tokens):
                return True
            
            if timeout and (time.time() - start) > timeout:
                return False
            
            await asyncio.sleep(0.1)
    
    def release(self, tokens: int = 1):
        """
        Release tokens back to the bucket.
        
        Args:
            tokens: Number of tokens to release
        """
        if self._strategy == RateLimitStrategy.TOKEN_BUCKET:
            with self._token_lock:
                self._tokens = min(
                    self.config.burst_size,
                    self._tokens + tokens
                )
    
    async def _acquire_token_bucket(self, tokens: int) -> bool:
        """Token bucket strategy"""
        with self._token_lock:
            now = time.time()
            elapsed = now - self._last_update
            
            # Add tokens based on time elapsed
            rate_per_second = self.config.requests_per_minute / 60
            self._tokens = min(
                self.config.burst_size,
                self._tokens + elapsed * rate_per_second
            )
            self._last_update = now
            
            # Try to consume tokens
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            
            return False
    
    async def _acquire_sliding_window(self, tokens: int) -> bool:
        """Sliding window strategy"""
        with self._window_lock:
            now = time.time()
            window_seconds = 60
            
            # Remove old requests outside window
            while self._request_times and self._request_times[0] < now - window_seconds:
                self._request_times.popleft()
            
            # Check if under limit
            if len(self._request_times) < self.config.requests_per_minute:
                self._request_times.append(now)
                return True
            
            return False
    
    async def _acquire_fixed_window(self, tokens: int) -> bool:
        """Fixed window strategy"""
        with self._fixed_lock:
            now = time.time()
            window_seconds = 60
            
            # Reset if new window
            if now - self._window_start >= window_seconds:
                self._window_start = now
                self._window_count = 0
            
            # Check if under limit
            if self._window_count < self.config.requests_per_minute:
                self._window_count += 1
                return True
            
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current rate limiter status.
        
        Returns:
            Status dict
        """
        status = {
            "strategy": self._strategy.value,
            "config": {
                "requests_per_minute": self.config.requests_per_minute,
                "burst_size": self.config.burst_size,
            }
        }
        
        if self._strategy == RateLimitStrategy.TOKEN_BUCKET:
            with self._token_lock:
                status["available_tokens"] = self._tokens
                status["utilization"] = 1 - (self._tokens / self.config.burst_size)
        
        elif self._strategy == RateLimitStrategy.SLIDING_WINDOW:
            with self._window_lock:
                now = time.time()
                # Clean old entries for accurate count
                while self._request_times and self._request_times[0] < now - 60:
                    self._request_times.popleft()
                status["requests_in_window"] = len(self._request_times)
                status["utilization"] = len(self._request_times) / self.config.requests_per_minute
        
        return status
    
    def time_until_available(self) -> float:
        """
        Estimate time until next request can be made.
        
        Returns:
            Seconds until available (0 if available now)
        """
        if self._strategy == RateLimitStrategy.TOKEN_BUCKET:
            with self._token_lock:
                if self._tokens >= 1:
                    return 0
                rate_per_second = self.config.requests_per_minute / 60
                tokens_needed = 1 - self._tokens
                return tokens_needed / rate_per_second
        
        elif self._strategy == RateLimitStrategy.SLIDING_WINDOW:
            with self._window_lock:
                if len(self._request_times) < self.config.requests_per_minute:
                    return 0
                # Time until oldest request falls out of window
                now = time.time()
                return max(0, self._request_times[0] + 60 - now)
        
        return 0


class MultiKeyRateLimiter:
    """
    Rate limiter with multiple keys (e.g., per API key).
    
    Example:
        >>> limiter = MultiKeyRateLimiter()
        >>> await limiter.acquire("api-key-1")
        >>> await limiter.acquire("api-key-2")  # Independent limit
    """
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self._limiters: Dict[str, RateLimiter] = {}
        self._lock = threading.Lock()
    
    async def acquire(self, key: str, tokens: int = 1) -> bool:
        """Acquire for specific key"""
        limiter = self._get_limiter(key)
        return await limiter.acquire(tokens)
    
    async def acquire_wait(self, key: str, tokens: int = 1, timeout: Optional[float] = None) -> bool:
        """Acquire with wait for specific key"""
        limiter = self._get_limiter(key)
        return await limiter.acquire_wait(tokens, timeout)
    
    def _get_limiter(self, key: str) -> RateLimiter:
        """Get or create limiter for key"""
        with self._lock:
            if key not in self._limiters:
                self._limiters[key] = RateLimiter(self.config)
            return self._limiters[key]
    
    def get_status(self, key: Optional[str] = None) -> Dict[str, Any]:
        """Get status for all or specific key"""
        if key:
            limiter = self._limiters.get(key)
            if limiter:
                return {key: limiter.get_status()}
            return {}
        
        return {k: v.get_status() for k, v in self._limiters.items()}


# Decorator for rate limiting
def rate_limited(
    requests_per_minute: int = 60,
    key_func: Optional[Callable] = None
):
    """
    Decorator to rate limit a function.
    
    Args:
        requests_per_minute: Rate limit
        key_func: Function to extract key from args for multi-key limiting
        
    Example:
        >>> @rate_limited(requests_per_minute=30)
        ... async def api_call():
        ...     pass
    """
    limiter = RateLimiter(RateLimitConfig(requests_per_minute=requests_per_minute))
    
    def decorator(func):
        async def wrapper(*args, **kwargs):
            key = key_func(*args, **kwargs) if key_func else "default"
            await limiter.acquire_wait()
            return await func(*args, **kwargs)
        return wrapper
    return decorator


__all__ = [
    "RateLimiter",
    "RateLimitConfig",
    "RateLimitStrategy",
    "MultiKeyRateLimiter",
    "rate_limited",
]
