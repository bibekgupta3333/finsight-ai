"""
Circuit Breaker Pattern.

Prevents cascading failures by breaking the circuit when error threshold is exceeded.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "CLOSED"  # Normal operation
    OPEN = "OPEN"  # Circuit broken, fail fast
    HALF_OPEN = "HALF_OPEN"  # Testing if service recovered


class CircuitBreakerConfig(BaseModel):
    """Circuit breaker configuration."""

    failure_threshold: int = 5  # Failures before opening circuit
    success_threshold: int = 2  # Successes to close from half-open
    timeout: int = 60  # Seconds before attempting recovery
    half_open_max_calls: int = 3  # Max calls in half-open state


class CircuitBreaker:
    """
    Circuit breaker for external service calls.

    Implements the circuit breaker pattern to prevent cascading failures.
    """

    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
    ):
        """
        Initialize circuit breaker.

        Args:
            name: Circuit name (for logging)
            config: Circuit configuration
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.half_open_calls = 0

        logger.info(f"Circuit breaker initialized: {name}, threshold={self.config.failure_threshold}")

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Async function to call
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            Exception: If circuit is OPEN or function fails
        """
        # Check circuit state
        if self.state == CircuitState.OPEN:
            # Check if timeout expired
            if self._should_attempt_reset():
                logger.info(f"Circuit {self.name}: Transitioning to HALF_OPEN")
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
            else:
                raise Exception(f"Circuit breaker OPEN for {self.name}")

        # Limit calls in HALF_OPEN state
        if self.state == CircuitState.HALF_OPEN:
            if self.half_open_calls >= self.config.half_open_max_calls:
                raise Exception(f"Circuit breaker HALF_OPEN, max calls reached for {self.name}")
            self.half_open_calls += 1

        # Execute function
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result

        except Exception as e:
            self._on_failure()
            raise e

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if not self.last_failure_time:
            return False

        elapsed = datetime.utcnow() - self.last_failure_time
        return elapsed >= timedelta(seconds=self.config.timeout)

    def _on_success(self):
        """Handle successful call."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            logger.debug(
                f"Circuit {self.name}: Success in HALF_OPEN "
                f"({self.success_count}/{self.config.success_threshold})"
            )

            if self.success_count >= self.config.success_threshold:
                logger.info(f"Circuit {self.name}: Transitioning to CLOSED")
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
        else:
            # Reset failure count on success in CLOSED state
            self.failure_count = 0

    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()

        logger.warning(
            f"Circuit {self.name}: Failure "
            f"({self.failure_count}/{self.config.failure_threshold})"
        )

        if self.state == CircuitState.HALF_OPEN:
            # Immediate transition to OPEN on failure in HALF_OPEN
            logger.warning(f"Circuit {self.name}: Transitioning to OPEN (failed in HALF_OPEN)")
            self.state = CircuitState.OPEN
            self.success_count = 0

        elif self.failure_count >= self.config.failure_threshold:
            # Transition to OPEN when threshold exceeded
            logger.error(f"Circuit {self.name}: Transitioning to OPEN (threshold exceeded)")
            self.state = CircuitState.OPEN

    def get_state(self) -> CircuitState:
        """Get current circuit state."""
        return self.state

    def reset(self):
        """Manually reset circuit breaker."""
        logger.info(f"Circuit {self.name}: Manual reset to CLOSED")
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None

    def get_stats(self) -> dict:
        """Get circuit breaker statistics."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "config": self.config.model_dump(),
        }


# Global circuit breakers
_circuit_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(
    name: str,
    config: Optional[CircuitBreakerConfig] = None,
) -> CircuitBreaker:
    """
    Get or create circuit breaker.

    Args:
        name: Circuit name
        config: Circuit configuration

    Returns:
        CircuitBreaker instance
    """
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(name, config)

    return _circuit_breakers[name]
