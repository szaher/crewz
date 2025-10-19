"""
Unit tests for retry policy with exponential backoff + jitter (T080).

Tests:
- Backoff calculation: 2^n * jitter
- Jitter range: [0.5, 1.5]
- Max retries enforcement
"""

import pytest
from src.workers.retry_policy import calculate_backoff, should_retry, get_retry_delay


class TestRetryPolicy:
    """Unit tests for retry policy calculations."""

    def test_backoff_exponential_growth(self):
        """Test that backoff grows exponentially with retry count."""
        # Test increasing backoff
        backoff_0 = calculate_backoff(0)
        backoff_1 = calculate_backoff(1)
        backoff_2 = calculate_backoff(2)
        backoff_3 = calculate_backoff(3)

        # Backoff should increase (with jitter variance)
        # 2^0 = 1, 2^1 = 2, 2^2 = 4, 2^3 = 8
        assert 0.5 <= backoff_0 <= 1.5  # 2^0 * [0.5, 1.5] = [0.5, 1.5]
        assert 1.0 <= backoff_1 <= 3.0  # 2^1 * [0.5, 1.5] = [1.0, 3.0]
        assert 2.0 <= backoff_2 <= 6.0  # 2^2 * [0.5, 1.5] = [2.0, 6.0]
        assert 4.0 <= backoff_3 <= 12.0  # 2^3 * [0.5, 1.5] = [4.0, 12.0]

    def test_backoff_formula_2_power_n(self):
        """Test that backoff follows 2^n formula (before jitter)."""
        # Run multiple times to get average (reduce jitter effect)
        samples = 100
        retry_count = 3

        backoffs = [calculate_backoff(retry_count) for _ in range(samples)]
        average_backoff = sum(backoffs) / len(backoffs)

        # Expected base: 2^3 = 8
        # With jitter [0.5, 1.5], average should be around 8 * 1.0 = 8
        # Allow some variance due to randomness
        assert 7.0 <= average_backoff <= 9.0

    def test_jitter_within_bounds(self):
        """Test that jitter is always within [0.5, 1.5] range."""
        retry_count = 2
        expected_base = 2 ** retry_count  # 4

        # Run many times to test jitter distribution
        for _ in range(100):
            backoff = calculate_backoff(retry_count)

            # Backoff should be base * jitter
            # Min: 4 * 0.5 = 2.0
            # Max: 4 * 1.5 = 6.0
            assert 2.0 <= backoff <= 6.0

    def test_max_retries_enforcement(self):
        """Test that max_retries limit is enforced."""
        max_retries = 3

        # Should retry for attempts 0, 1, 2
        assert should_retry(0, max_retries) is True
        assert should_retry(1, max_retries) is True
        assert should_retry(2, max_retries) is True

        # Should NOT retry for attempt 3 (reached max)
        assert should_retry(3, max_retries) is False
        assert should_retry(4, max_retries) is False

    def test_zero_retry_count(self):
        """Test backoff calculation for first retry (count=0)."""
        backoff = calculate_backoff(0)

        # 2^0 = 1, with jitter [0.5, 1.5]
        assert 0.5 <= backoff <= 1.5

    def test_high_retry_count(self):
        """Test that high retry counts don't cause overflow."""
        # Test with high retry count
        retry_count = 10

        backoff = calculate_backoff(retry_count)

        # 2^10 = 1024, with jitter: [512, 1536]
        assert 512 <= backoff <= 1536

        # Should not raise exception or return invalid value
        assert backoff > 0
        assert isinstance(backoff, (int, float))

    def test_get_retry_delay_with_max_delay(self):
        """Test that retry delay respects max_delay cap."""
        retry_count = 10  # Would normally give huge delay
        max_delay = 60  # Cap at 60 seconds

        delay = get_retry_delay(retry_count, max_delay=max_delay)

        # Delay should not exceed max
        assert delay <= max_delay

    def test_retry_policy_consistency(self):
        """Test that same retry count gives values in same range."""
        retry_count = 2
        delays = [calculate_backoff(retry_count) for _ in range(20)]

        # All delays should be in expected range
        for delay in delays:
            assert 2.0 <= delay <= 6.0  # 2^2 * [0.5, 1.5]

    def test_should_retry_with_zero_max(self):
        """Test that max_retries=0 means no retries allowed."""
        assert should_retry(0, max_retries=0) is False
        assert should_retry(1, max_retries=0) is False

    def test_should_retry_with_negative_count(self):
        """Test handling of negative retry count (should not happen but be safe)."""
        # Negative count should be treated as 0 or allowed
        result = should_retry(-1, max_retries=3)

        # Either allow it or treat as 0
        assert isinstance(result, bool)

    def test_backoff_randomness(self):
        """Test that jitter adds randomness to backoff."""
        retry_count = 2

        # Generate multiple backoffs
        backoffs = [calculate_backoff(retry_count) for _ in range(50)]

        # Should have variance (not all same value)
        unique_values = len(set(backoffs))

        # At least some variation (not all identical)
        assert unique_values > 1

    def test_get_retry_delay_default_params(self):
        """Test get_retry_delay with default parameters."""
        delay = get_retry_delay(1)

        # Should return valid delay
        assert delay > 0
        assert isinstance(delay, (int, float))

    def test_calculate_backoff_never_negative(self):
        """Test that backoff is never negative."""
        for retry_count in range(10):
            backoff = calculate_backoff(retry_count)
            assert backoff > 0

    def test_max_retries_boundary_conditions(self):
        """Test boundary conditions for max retries."""
        # At exactly max retries - 1, should still retry
        assert should_retry(2, max_retries=3) is True

        # At max retries, should not retry
        assert should_retry(3, max_retries=3) is False

    def test_jitter_distribution_roughly_uniform(self):
        """Test that jitter produces roughly uniform distribution."""
        retry_count = 2
        base = 2 ** retry_count  # 4

        backoffs = [calculate_backoff(retry_count) for _ in range(1000)]

        # Calculate average jitter
        average_jitter = sum(b / base for b in backoffs) / len(backoffs)

        # Average jitter should be around 1.0 (middle of [0.5, 1.5])
        # Allow some variance due to randomness
        assert 0.95 <= average_jitter <= 1.05
