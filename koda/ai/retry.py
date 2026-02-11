"""
Retry Logic
Equivalent to Pi Mono's packages/ai/src/utils/retry.ts

Advanced retry with exponential backoff, jitter, and circuit breaker.
"""
import asyncio
import random
import time
from typing import Callable, Optional, Type, List, Any, Dict
from dataclasses import dataclass
from enum import Enum
import functools


class RetryStrategy(Enum):
    """Retry strategies"""
    FIXED = "fixed"
    EXPONENTIAL = "exponential"
    LINEAR = "linear"


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered


@dataclass
class RetryConfig:
    """Retry configuration"""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    jitter: bool = True
    jitter_max: float = 0.1
    retryable_exceptions: List[Type[Exception]] = None
    on_retry: Optional[Callable[[Exception, int], None]] = None
    on_success: Optional[Callable[[], None]] = None
    on_failure: Optional[Callable[[Exception], None]] = None
    
    def __post_init__(self):
        if self.retryable_exceptions is None:
            self.retryable_exceptions = [Exception]


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration"""
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    half_open_max_calls: int = 3


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.
    
    Prevents cascading failures by stopping requests to failing service.
    
    Example:
        >>> breaker = CircuitBreaker()
        >>> @breaker.protect
        ... async def api_call():
        ...     return await make_request()
    """
    
    def __init__(self, config: Optional[CircuitBreakerConfig] = None, name: str = "default"):
        self.config = config or CircuitBreakerConfig()
        self.name = name
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0
    
    @property
    def state(self) -> CircuitState:
        """Current circuit state"""
        if self._state == CircuitState.OPEN:
            # Check if recovery timeout passed
            if self._last_failure_time:
                elapsed = time.time() - self._last_failure_time
                if elapsed >= self.config.recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
        
        return self._state
    
    def record_success(self):
        """Record a successful call"""
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.config.half_open_max_calls:
                # Recovery successful
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._success_count = 0
        else:
            self._failure_count = 0
    
    def record_failure(self):
        """Record a failed call"""
        self._failure_count += 1
        self._last_failure_time = time.time()
        
        if self._state == CircuitState.HALF_OPEN:
            # Recovery failed
            self._state = CircuitState.OPEN
        elif self._failure_count >= self.config.failure_threshold:
            # Threshold reached, open circuit
            self._state = CircuitState.OPEN
    
    def can_execute(self) -> bool:
        """Check if execution is allowed"""
        state = self.state  # Update state first
        
        if state == CircuitState.CLOSED:
            return True
        elif state == CircuitState.OPEN:
            return False
        elif state == CircuitState.HALF_OPEN:
            if self._half_open_calls < self.config.half_open_max_calls:
                self._half_open_calls += 1
                return True
            return False
        
        return False
    
    def protect(self, func: Callable) -> Callable:
        """Decorator to protect a function with circuit breaker"""
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if not self.can_execute():
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{self.name}' is OPEN"
                )
            
            try:
                result = await func(*args, **kwargs)
                self.record_success()
                return result
            except Exception as e:
                self.record_failure()
                raise
        
        return wrapper


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open"""
    pass


class RetryHandler:
    """
    Advanced retry handler with multiple strategies.
    
    Example:
        >>> handler = RetryHandler(RetryConfig(max_attempts=5))
        >>> result = await handler.execute(async_function)
    """
    
    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
    
    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with retry logic.
        
        Args:
            func: Async function to execute
            *args, **kwargs: Arguments to pass to function
            
        Returns:
            Function result
            
        Raises:
            Exception: If all retries exhausted
        """
        last_exception = None
        
        for attempt in range(1, self.config.max_attempts + 1):
            try:
                result = await func(*args, **kwargs)
                
                if self.config.on_success:
                    self.config.on_success()
                
                return result
                
            except tuple(self.config.retryable_exceptions) as e:
                last_exception = e
                
                if attempt == self.config.max_attempts:
                    break
                
                # Calculate delay
                delay = self._calculate_delay(attempt)
                
                # Notify retry
                if self.config.on_retry:
                    self.config.on_retry(e, attempt)
                
                # Wait before retry
                await asyncio.sleep(delay)
        
        # All retries exhausted
        if self.config.on_failure:
            self.config.on_failure(last_exception)
        
        raise last_exception
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt"""
        strategy = self.config.strategy
        base = self.config.base_delay
        
        if strategy == RetryStrategy.FIXED:
            delay = base
        elif strategy == RetryStrategy.LINEAR:
            delay = base * attempt
        else:  # EXPONENTIAL
            delay = base * (2 ** (attempt - 1))
        
        # Cap at max delay
        delay = min(delay, self.config.max_delay)
        
        # Add jitter
        if self.config.jitter:
            jitter_amount = delay * self.config.jitter_max
            delay += random.uniform(-jitter_amount, jitter_amount)
        
        return max(0, delay)


# Convenience decorator
def retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
    retryable_exceptions: List[Type[Exception]] = None
):
    """
    Decorator to add retry logic to a function.
    
    Example:
        >>> @retry(max_attempts=5, base_delay=2.0)
        ... async def fetch_data():
        ...     return await api_call()
    """
    config = RetryConfig(
        max_attempts=max_attempts,
        base_delay=base_delay,
        strategy=strategy,
        retryable_exceptions=retryable_exceptions
    )
    handler = RetryHandler(config)
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await handler.execute(func, *args, **kwargs)
        return wrapper
    
    return decorator


# Combined retry + circuit breaker
class ResilientClient:
    """
    Client with both retry and circuit breaker.
    
    Example:
        >>> client = ResilientClient()
        >>> result = await client.call(api_function)
    """
    
    def __init__(
        self,
        retry_config: Optional[RetryConfig] = None,
        circuit_config: Optional[CircuitBreakerConfig] = None,
        name: str = "default"
    ):
        self.retry_handler = RetryHandler(retry_config)
        self.circuit_breaker = CircuitBreaker(circuit_config, name)
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Call function with retry and circuit breaker protection.
        
        Args:
            func: Function to call
            *args, **kwargs: Function arguments
            
        Returns:
            Function result
        """
        # Check circuit breaker
        if not self.circuit_breaker.can_execute():
            raise CircuitBreakerOpenError(
                f"Circuit breaker '{self.circuit_breaker.name}' is OPEN"
            )
        
        try:
            # Execute with retry
            result = await self.retry_handler.execute(func, *args, **kwargs)
            self.circuit_breaker.record_success()
            return result
            
        except Exception as e:
            self.circuit_breaker.record_failure()
            raise
    
    def get_status(self) -> Dict[str, Any]:
        """Get client status"""
        return {
            "circuit_state": self.circuit_breaker.state.value,
            "circuit_failures": self.circuit_breaker._failure_count,
        }


__all__ = [
    "RetryHandler",
    "RetryConfig",
    "RetryStrategy",
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitState",
    "CircuitBreakerOpenError",
    "ResilientClient",
    "retry",
]
