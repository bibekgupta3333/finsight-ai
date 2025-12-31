"""
Retry Logic with Exponential Backoff and Jitter.

Implements resilient retry patterns for distributed systems.
"""

import asyncio
import logging
import random
from typing import Any, Callable, Optional, Type

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class RetryConfig(BaseModel):
    """Retry configuration."""

    max_attempts: int = 3  # Maximum retry attempts
    base_delay: float = 1.0  # Base delay in seconds
    max_delay: float = 60.0  # Maximum delay in seconds
    exponential_base: float = 2.0  # Exponential backoff base
    jitter: bool = True  # Add random jitter
    retryable_exceptions: tuple = (Exception,)  # Exceptions to retry


class RetryExhausted(Exception):
    """Raised when all retry attempts are exhausted."""

    pass


async def retry_with_backoff(
    func: Callable,
    *args,
    config: Optional[RetryConfig] = None,
    **kwargs,
) -> Any:
    """
    Execute function with exponential backoff and jitter.

    Args:
        func: Async function to execute
        *args: Positional arguments
        config: Retry configuration
        **kwargs: Keyword arguments

    Returns:
        Function result

    Raises:
        RetryExhausted: If all attempts fail
    """
    config = config or RetryConfig()
    last_exception: Optional[Exception] = None

    for attempt in range(1, config.max_attempts + 1):
        try:
            result = await func(*args, **kwargs)
            if attempt > 1:
                logger.info(f"Retry succeeded on attempt {attempt}")
            return result

        except config.retryable_exceptions as e:
            last_exception = e
            
            if attempt == config.max_attempts:
                logger.error(
                    f"Retry exhausted after {config.max_attempts} attempts: {str(e)}"
                )
                break

            # Calculate delay with exponential backoff
            delay = min(
                config.base_delay * (config.exponential_base ** (attempt - 1)),
                config.max_delay,
            )

            # Add jitter
            if config.jitter:
                delay = delay * (0.5 + random.random())

            logger.warning(
                f"Attempt {attempt}/{config.max_attempts} failed: {str(e)}. "
                f"Retrying in {delay:.2f}s..."
            )

            await asyncio.sleep(delay)

    raise RetryExhausted(
        f"Failed after {config.max_attempts} attempts: {str(last_exception)}"
    )


class RetryableOperation:
    """
    Wrapper for retryable operations.

    Provides a clean interface for retry logic with configuration.
    """

    def __init__(
        self,
        name: str,
        config: Optional[RetryConfig] = None,
    ):
        """
        Initialize retryable operation.

        Args:
            name: Operation name (for logging)
            config: Retry configuration
        """
        self.name = name
        self.config = config or RetryConfig()
        self.attempt_count = 0
        self.success_count = 0
        self.failure_count = 0

    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with retry logic.

        Args:
            func: Async function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            RetryExhausted: If all attempts fail
        """
        try:
            result = await retry_with_backoff(
                func,
                *args,
                config=self.config,
                **kwargs,
            )
            self.success_count += 1
            return result

        except RetryExhausted as e:
            self.failure_count += 1
            logger.error(f"Operation {self.name} failed: {str(e)}")
            raise e

    def get_stats(self) -> dict:
        """Get operation statistics."""
        return {
            "name": self.name,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "config": self.config.model_dump(),
        }


def calculate_backoff_delay(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
) -> float:
    """
    Calculate backoff delay for an attempt.

    Args:
        attempt: Attempt number (1-indexed)
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Exponential base
        jitter: Add random jitter

    Returns:
        Delay in seconds
    """
    delay = min(
        base_delay * (exponential_base ** (attempt - 1)),
        max_delay,
    )

    if jitter:
        delay = delay * (0.5 + random.random())

    return delay
