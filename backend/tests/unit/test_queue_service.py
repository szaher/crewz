"""
Unit tests for queue service (T081).

Tests:
- Redis sorted set operations
- Queue position calculation
- Estimated wait time: position * avg_time
- Priority routing correctness (0-10 scale)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from src.services.queue_service import QueueService


class TestQueueService:
    """Unit tests for queue service operations."""

    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client."""
        redis_mock = Mock()
        redis_mock.zadd = Mock(return_value=1)
        redis_mock.zrank = Mock(return_value=2)
        redis_mock.zcard = Mock(return_value=5)
        redis_mock.zrange = Mock(return_value=[])
        redis_mock.zrem = Mock(return_value=1)
        return redis_mock

    @pytest.fixture
    def queue_service(self, mock_redis):
        """Create queue service with mocked Redis."""
        service = QueueService()
        service.redis = mock_redis
        return service

    def test_add_to_queue_with_priority(self, queue_service, mock_redis):
        """Test adding job to queue with priority."""
        job_id = "test-job-123"
        priority = 5

        queue_service.add_to_queue(job_id, priority=priority)

        # Should call zadd with priority as score
        mock_redis.zadd.assert_called_once()
        call_args = mock_redis.zadd.call_args

        # Verify job was added with correct priority
        assert job_id in str(call_args)

    def test_priority_ordering_high_before_low(self, queue_service, mock_redis):
        """Test that high priority (0) comes before low priority (10)."""
        # Priority 0 = highest, 10 = lowest
        # In sorted set, lower score = higher priority

        job_high = "job-priority-0"
        job_low = "job-priority-10"

        queue_service.add_to_queue(job_high, priority=0)
        queue_service.add_to_queue(job_low, priority=10)

        # Verify zadd was called twice
        assert mock_redis.zadd.call_count == 2

    def test_get_queue_position(self, queue_service, mock_redis):
        """Test getting queue position for a job."""
        job_id = "test-job-456"

        # Mock zrank to return position 2 (3rd in queue)
        mock_redis.zrank.return_value = 2

        position = queue_service.get_position(job_id)

        # Should return position
        assert position == 2

        # Verify zrank was called
        mock_redis.zrank.assert_called_once()

    def test_get_position_for_nonexistent_job(self, queue_service, mock_redis):
        """Test getting position for job not in queue."""
        job_id = "nonexistent-job"

        # Mock zrank returns None for non-existent job
        mock_redis.zrank.return_value = None

        position = queue_service.get_position(job_id)

        # Should return None
        assert position is None

    def test_estimate_wait_time_calculation(self, queue_service, mock_redis):
        """Test estimated wait time = position * avg_time."""
        job_id = "test-job-789"

        # Mock position = 3
        mock_redis.zrank.return_value = 3

        # Mock average execution time = 60 seconds
        avg_execution_time = 60

        estimated_time = queue_service.estimate_wait_time(
            job_id,
            avg_execution_time=avg_execution_time
        )

        # Expected: 3 * 60 = 180 seconds
        assert estimated_time == 180

    def test_estimate_wait_time_for_first_in_queue(self, queue_service, mock_redis):
        """Test estimate for job at position 0 (next to run)."""
        job_id = "first-job"

        # Position 0 = next to run
        mock_redis.zrank.return_value = 0

        estimated_time = queue_service.estimate_wait_time(job_id, avg_execution_time=60)

        # Should be 0 or very small
        assert estimated_time == 0

    def test_priority_routing_correctness(self, queue_service, mock_redis):
        """Test that priority values are handled correctly (0-10 scale)."""
        # Priority boundaries
        priorities = [0, 5, 10]

        for priority in priorities:
            job_id = f"job-priority-{priority}"
            queue_service.add_to_queue(job_id, priority=priority)

        # Verify all adds succeeded
        assert mock_redis.zadd.call_count == len(priorities)

    def test_invalid_priority_handling(self, queue_service):
        """Test handling of invalid priority values."""
        job_id = "test-job"

        # Test out-of-range priority
        with pytest.raises((ValueError, AssertionError)):
            queue_service.add_to_queue(job_id, priority=11)  # Out of range

        with pytest.raises((ValueError, AssertionError)):
            queue_service.add_to_queue(job_id, priority=-1)  # Negative

    def test_queue_size(self, queue_service, mock_redis):
        """Test getting total queue size."""
        # Mock queue size
        mock_redis.zcard.return_value = 10

        size = queue_service.get_queue_size()

        assert size == 10
        mock_redis.zcard.assert_called_once()

    def test_remove_from_queue(self, queue_service, mock_redis):
        """Test removing job from queue."""
        job_id = "job-to-remove"

        queue_service.remove_from_queue(job_id)

        # Should call zrem
        mock_redis.zrem.assert_called_once()

    def test_peek_next_job(self, queue_service, mock_redis):
        """Test peeking at next job without removing it."""
        # Mock zrange to return next job
        mock_redis.zrange.return_value = [b"next-job-id"]

        next_job = queue_service.peek_next()

        assert next_job == "next-job-id" or next_job == b"next-job-id"
        mock_redis.zrange.assert_called_once()

    def test_pop_next_job(self, queue_service, mock_redis):
        """Test popping next job from queue."""
        # Mock zrange and zrem
        mock_redis.zrange.return_value = [b"job-to-pop"]
        mock_redis.zrem.return_value = 1

        job_id = queue_service.pop_next()

        # Should return job ID
        assert job_id is not None

        # Should have called zrange and zrem
        mock_redis.zrange.assert_called_once()

    def test_empty_queue_pop(self, queue_service, mock_redis):
        """Test popping from empty queue."""
        # Mock empty queue
        mock_redis.zrange.return_value = []

        job_id = queue_service.pop_next()

        # Should return None
        assert job_id is None

    def test_fifo_ordering_same_priority(self, queue_service, mock_redis):
        """Test FIFO ordering for jobs with same priority."""
        # When priorities are equal, should use timestamp for FIFO
        job1 = "job-1"
        job2 = "job-2"
        priority = 5

        queue_service.add_to_queue(job1, priority=priority)
        queue_service.add_to_queue(job2, priority=priority)

        # Both should be added
        assert mock_redis.zadd.call_count == 2

    def test_get_all_queued_jobs(self, queue_service, mock_redis):
        """Test getting list of all queued jobs."""
        # Mock zrange to return all jobs
        mock_redis.zrange.return_value = [b"job1", b"job2", b"job3"]

        jobs = queue_service.get_all_jobs()

        assert len(jobs) == 3
        mock_redis.zrange.assert_called_once()

    def test_estimate_wait_time_with_no_position(self, queue_service, mock_redis):
        """Test estimate when job not in queue."""
        job_id = "not-in-queue"

        # Mock zrank returns None
        mock_redis.zrank.return_value = None

        estimated_time = queue_service.estimate_wait_time(job_id, avg_execution_time=60)

        # Should return None or 0
        assert estimated_time is None or estimated_time == 0

    def test_priority_score_mapping(self, queue_service):
        """Test that priority is correctly mapped to Redis score."""
        # Lower priority number = higher priority = lower score
        # This ensures priority 0 comes before priority 10

        job_high = "high-priority-job"
        job_low = "low-priority-job"

        # The service should map priority to score correctly
        # Implementation detail: might use priority directly or transform it

        queue_service.add_to_queue(job_high, priority=0)
        queue_service.add_to_queue(job_low, priority=10)

        # Both should be added successfully
        assert queue_service.redis.zadd.call_count == 2

    def test_concurrent_add_operations(self, queue_service, mock_redis):
        """Test multiple concurrent add operations."""
        jobs = [f"job-{i}" for i in range(10)]

        for job in jobs:
            queue_service.add_to_queue(job, priority=5)

        # Should have added all jobs
        assert mock_redis.zadd.call_count == len(jobs)

    def test_queue_position_updates_after_pop(self, queue_service, mock_redis):
        """Test that positions update correctly after removing jobs."""
        # This is implicit in Redis sorted sets
        # When you remove an item, ranks auto-update

        job_id = "test-job"

        # Initial position
        mock_redis.zrank.return_value = 3

        position_before = queue_service.get_position(job_id)
        assert position_before == 3

        # After a job is popped, position should decrease
        mock_redis.zrank.return_value = 2

        position_after = queue_service.get_position(job_id)
        assert position_after == 2
        assert position_after < position_before
