"""Queue service for managing execution queue using Redis sorted sets.

Handles priority-based queueing (0-10), position tracking, and wait time estimation.
"""
import time
from typing import Optional, List, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from src.config.settings import Settings
from src.config.worker_config import WorkerConfig


class QueueService:
    """Service for managing execution queue with priority routing."""

    def __init__(self, redis_client=None, settings: Settings = None):
        """
        Initialize queue service.

        Args:
            redis_client: Redis client instance (injected for testing)
            settings: Settings instance (default loads from env)
        """
        self.settings = settings or Settings()
        self.enabled = self.settings.ENABLE_WORKER_ARCHITECTURE

        if redis_client:
            self.redis = redis_client
        else:
            import redis
            self.redis = redis.from_url(str(self.settings.REDIS_URL), decode_responses=True)

    def _get_queue_key(self, priority: int) -> str:
        """
        Get Redis key for priority queue.

        Queues: high_priority (0-3), normal_priority (4-6), low_priority (7-10)

        Args:
            priority: Priority level (0-10)

        Returns:
            Redis sorted set key
        """
        if priority <= 3:
            return "queue:high_priority"
        elif priority <= 6:
            return "queue:normal_priority"
        else:
            return "queue:low_priority"

    def add_to_queue(
        self,
        execution_id: UUID,
        priority: int = 5,
        timestamp: float = None
    ) -> Tuple[int, float]:
        """
        Add execution to queue.

        Args:
            execution_id: Execution UUID
            priority: Priority level (0-10, lower is higher priority)
            timestamp: Custom timestamp (default: current time)

        Returns:
            Tuple of (queue_position, estimated_wait_seconds)

        Raises:
            ValueError: If ENABLE_WORKER_ARCHITECTURE is False
        """
        if not self.enabled:
            raise ValueError("Worker architecture is disabled (ENABLE_WORKER_ARCHITECTURE=False)")

        if timestamp is None:
            timestamp = time.time()

        # Calculate score: priority * 1e10 + timestamp
        # This ensures priority sorting first, then FIFO within priority
        score = (priority * 1e10) + timestamp

        queue_key = self._get_queue_key(priority)
        self.redis.zadd(queue_key, {str(execution_id): score})

        # Get position and estimated wait time
        position = self.get_position(execution_id)
        estimated_wait = self.estimate_wait_time(execution_id)

        return position, estimated_wait

    def get_position(self, execution_id: UUID) -> int:
        """
        Get execution's position in queue.

        Args:
            execution_id: Execution UUID

        Returns:
            Position (0-indexed, 0 = next to execute)
        """
        execution_str = str(execution_id)

        # Check all queue keys
        for queue_key in ["queue:high_priority", "queue:normal_priority", "queue:low_priority"]:
            rank = self.redis.zrank(queue_key, execution_str)
            if rank is not None:
                # Add positions from higher priority queues
                if queue_key == "queue:normal_priority":
                    rank += self.redis.zcard("queue:high_priority")
                elif queue_key == "queue:low_priority":
                    rank += self.redis.zcard("queue:high_priority") + self.redis.zcard("queue:normal_priority")

                return rank

        return -1  # Not in queue

    def estimate_wait_time(self, execution_id: UUID) -> float:
        """
        Estimate wait time in seconds.

        Assumes average execution time from WorkerConfig.

        Args:
            execution_id: Execution UUID

        Returns:
            Estimated wait time in seconds
        """
        position = self.get_position(execution_id)
        if position < 0:
            return 0.0

        # Estimate based on position and average execution time
        # Assume we can process WORKER_CONCURRENCY tasks in parallel
        avg_execution_time = WorkerConfig.DEFAULT_EXECUTION_TIMEOUT_SECONDS / 2  # Conservative estimate
        concurrent_capacity = WorkerConfig.WORKER_CONCURRENCY

        batches_ahead = position // concurrent_capacity
        estimated_wait = batches_ahead * avg_execution_time

        return estimated_wait

    def remove_from_queue(self, execution_id: UUID) -> bool:
        """
        Remove execution from queue.

        Args:
            execution_id: Execution UUID

        Returns:
            True if removed, False if not found
        """
        execution_str = str(execution_id)
        removed = False

        for queue_key in ["queue:high_priority", "queue:normal_priority", "queue:low_priority"]:
            count = self.redis.zrem(queue_key, execution_str)
            if count > 0:
                removed = True

        return removed

    def get_next_execution(self) -> Optional[UUID]:
        """
        Get next execution from queue (highest priority first, FIFO within priority).

        Returns:
            Execution UUID or None if queue is empty
        """
        # Check queues in priority order
        for queue_key in ["queue:high_priority", "queue:normal_priority", "queue:low_priority"]:
            # Get lowest score (earliest timestamp) from queue
            result = self.redis.zpopmin(queue_key, count=1)
            if result:
                execution_str, score = result[0]
                return UUID(execution_str)

        return None

    def get_queue_stats(self) -> dict:
        """
        Get queue statistics.

        Returns:
            Dict with queue sizes per priority level
        """
        return {
            "high_priority_count": self.redis.zcard("queue:high_priority"),
            "normal_priority_count": self.redis.zcard("queue:normal_priority"),
            "low_priority_count": self.redis.zcard("queue:low_priority"),
            "total_queued": (
                self.redis.zcard("queue:high_priority") +
                self.redis.zcard("queue:normal_priority") +
                self.redis.zcard("queue:low_priority")
            )
        }

    def peek_queue(self, priority_level: str = "high_priority", limit: int = 10) -> List[Tuple[UUID, float]]:
        """
        Peek at queue without removing items.

        Args:
            priority_level: Queue to peek ("high_priority", "normal_priority", "low_priority")
            limit: Maximum items to return

        Returns:
            List of (execution_id, score) tuples
        """
        queue_key = f"queue:{priority_level}"
        items = self.redis.zrange(queue_key, 0, limit - 1, withscores=True)

        return [(UUID(item[0]), item[1]) for item in items]

    def clear_queue(self, priority_level: Optional[str] = None) -> int:
        """
        Clear queue(s).

        Args:
            priority_level: Specific queue to clear, or None for all queues

        Returns:
            Number of items removed
        """
        if priority_level:
            queue_key = f"queue:{priority_level}"
            return self.redis.delete(queue_key)
        else:
            # Clear all queues
            total = 0
            for level in ["high_priority", "normal_priority", "low_priority"]:
                total += self.redis.delete(f"queue:{level}")
            return total
