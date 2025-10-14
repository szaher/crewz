"""
Base abstract class for message queue backends.
Allows pluggable queue implementations (Redis, RabbitMQ, AWS SQS, etc.)
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from uuid import UUID


class MessageQueueBackend(ABC):
    """
    Abstract base class for message queue backends.

    Implementations must provide methods for task submission,
    status checking, and cancellation.
    """

    @abstractmethod
    def submit_task(
        self,
        task_name: str,
        args: tuple = (),
        kwargs: Dict[str, Any] = None,
        priority: str = "normal",
        task_id: Optional[str] = None,
        **options
    ) -> str:
        """
        Submit a task to the queue.

        Args:
            task_name: Name of the task to execute
            args: Positional arguments for the task
            kwargs: Keyword arguments for the task
            priority: Task priority (low, normal, high)
            task_id: Optional custom task ID
            **options: Additional queue-specific options

        Returns:
            Task ID (UUID string)
        """
        pass

    @abstractmethod
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a task.

        Args:
            task_id: Task ID to query

        Returns:
            Dict with status info or None if not found
            {
                "state": "PENDING"|"STARTED"|"SUCCESS"|"FAILURE"|"RETRY"|"REVOKED",
                "result": Any,
                "traceback": str (if failed),
                "info": Dict (additional metadata)
            }
        """
        pass

    @abstractmethod
    def cancel_task(self, task_id: str, terminate: bool = False) -> bool:
        """
        Cancel a task.

        Args:
            task_id: Task ID to cancel
            terminate: If True, forcefully terminate running task

        Returns:
            True if cancellation succeeded, False otherwise
        """
        pass

    def get_queue_depth(self, queue_name: str = "celery") -> int:
        """
        Get the number of tasks in the queue.

        Args:
            queue_name: Name of the queue to check

        Returns:
            Number of pending tasks
        """
        return 0  # Default implementation

    def purge_queue(self, queue_name: str = "celery") -> int:
        """
        Remove all tasks from the queue.

        Args:
            queue_name: Name of the queue to purge

        Returns:
            Number of tasks purged
        """
        return 0  # Default implementation
