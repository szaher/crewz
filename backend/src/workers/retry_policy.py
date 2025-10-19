"""Retry policy with exponential backoff and jitter for failed executions.

Implements calculation logic for retry backoff: 2^n * random(0.5-1.5)
"""
import random
from typing import Tuple
from src.config.worker_config import WorkerConfig


def calculate_backoff(retry_count: int, base: float = 2.0, jitter_range: Tuple[float, float] = (0.5, 1.5)) -> float:
    """
    Calculate exponential backoff with jitter for retry attempts.

    Formula: 2^n * random(0.5-1.5)

    Args:
        retry_count: Current retry attempt number (0-indexed)
        base: Base for exponential calculation (default 2.0)
        jitter_range: Min/max multiplier for jitter (default 0.5-1.5)

    Returns:
        Backoff time in seconds

    Examples:
        >>> backoff = calculate_backoff(0)  # First retry
        >>> assert 1.0 <= backoff <= 3.0  # 2^0 * (0.5 to 1.5)

        >>> backoff = calculate_backoff(3)  # Fourth retry
        >>> assert 4.0 <= backoff <= 12.0  # 2^3 * (0.5 to 1.5)
    """
    jitter = random.uniform(*jitter_range)
    backoff_seconds = (base ** retry_count) * jitter
    return backoff_seconds


def should_retry(retry_count: int, max_retries: int = None) -> bool:
    """
    Determine if execution should be retried based on retry count.

    Args:
        retry_count: Current retry count
        max_retries: Maximum retries allowed (default from WorkerConfig)

    Returns:
        True if should retry, False otherwise

    Examples:
        >>> should_retry(0, max_retries=3)
        True
        >>> should_retry(3, max_retries=3)
        False
    """
    if max_retries is None:
        max_retries = WorkerConfig.MAX_RETRIES

    return retry_count < max_retries


def get_next_retry_time(retry_count: int) -> float:
    """
    Get the timestamp for the next retry attempt.

    Args:
        retry_count: Current retry count

    Returns:
        Unix timestamp for next retry

    Examples:
        >>> import time
        >>> next_retry = get_next_retry_time(2)
        >>> assert next_retry > time.time()  # Should be in the future
    """
    import time

    backoff_seconds = calculate_backoff(retry_count)
    next_retry_timestamp = time.time() + backoff_seconds

    return next_retry_timestamp


class RetryPolicy:
    """Retry policy manager for worker executions."""

    def __init__(self, max_retries: int = None, base: float = 2.0):
        """
        Initialize retry policy.

        Args:
            max_retries: Maximum retry attempts (default from WorkerConfig)
            base: Base for exponential backoff (default 2.0)
        """
        self.max_retries = max_retries or WorkerConfig.MAX_RETRIES
        self.base = base

    def should_retry_execution(self, retry_count: int) -> bool:
        """Check if execution should be retried."""
        return should_retry(retry_count, self.max_retries)

    def calculate_backoff_time(self, retry_count: int) -> float:
        """Calculate backoff time for retry."""
        return calculate_backoff(retry_count, base=self.base)

    def get_retry_delay(self, retry_count: int) -> float:
        """
        Get delay in seconds before next retry.

        Args:
            retry_count: Current retry count

        Returns:
            Delay in seconds
        """
        return self.calculate_backoff_time(retry_count)


# Unit tests inline per task requirements
if __name__ == "__main__":
    import doctest
    doctest.testmod()

    # Additional inline tests
    print("Running inline unit tests...")

    # Test calculate_backoff bounds
    for i in range(5):
        backoff = calculate_backoff(i)
        expected_min = (2 ** i) * 0.5
        expected_max = (2 ** i) * 1.5
        assert expected_min <= backoff <= expected_max, f"Retry {i} backoff {backoff} out of range"
        print(f"  Retry {i}: {backoff:.2f}s (expected {expected_min:.2f}-{expected_max:.2f}s) ✓")

    # Test should_retry
    assert should_retry(0, max_retries=3) is True
    assert should_retry(2, max_retries=3) is True
    assert should_retry(3, max_retries=3) is False
    assert should_retry(5, max_retries=3) is False
    print("  should_retry logic ✓")

    # Test RetryPolicy class
    policy = RetryPolicy(max_retries=5)
    assert policy.should_retry_execution(0) is True
    assert policy.should_retry_execution(5) is False
    delay = policy.get_retry_delay(2)
    assert 2.0 <= delay <= 6.0  # 2^2 * (0.5-1.5)
    print("  RetryPolicy class ✓")

    print("All inline tests passed! ✓")
