"""
Redis Streams backend for Celery message queue.
Implements MessageQueueBackend interface using Celery with Redis Streams broker.
"""

from typing import Optional, Dict, Any
from celery import Celery
from celery.result import AsyncResult
import os

from .base import MessageQueueBackend


class RedisBackend(MessageQueueBackend):
    """
    Redis Streams backend for message queue.

    Uses Celery with Redis Streams as broker for persistent, log-structured queuing.
    Supports priority queues, task cancellation, and queue monitoring.
    """

    def __init__(self, celery_app: Optional[Celery] = None):
        """
        Initialize Redis backend.

        Args:
            celery_app: Celery application instance. If None, uses default from celery_app module.
        """
        if celery_app is None:
            # Import here to avoid circular dependency
            from ..celery_app import celery_app as default_app
            self.celery_app = default_app
        else:
            self.celery_app = celery_app

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
        Submit a task to Redis Streams queue via Celery.

        Args:
            task_name: Fully qualified task name (e.g., 'workers.tasks.execute_crew')
            args: Positional arguments for the task
            kwargs: Keyword arguments for the task
            priority: Task priority ('low'=0, 'normal'=5, 'high'=9)
            task_id: Optional custom task ID (UUID)
            **options: Additional Celery options (countdown, eta, expires, etc.)

        Returns:
            Task ID (UUID string)
        """
        kwargs = kwargs or {}

        # Map priority to Celery priority (0-9 scale)
        priority_map = {
            "low": 0,
            "normal": 5,
            "high": 9
        }
        celery_priority = priority_map.get(priority, 5)

        # Submit task to Celery
        result = self.celery_app.send_task(
            task_name,
            args=args,
            kwargs=kwargs,
            task_id=task_id,
            priority=celery_priority,
            **options
        )

        return result.id

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a Celery task.

        Args:
            task_id: Celery task ID

        Returns:
            Dict with status information or None if not found
            {
                "state": "PENDING"|"STARTED"|"SUCCESS"|"FAILURE"|"RETRY"|"REVOKED",
                "result": Any (task return value or exception),
                "traceback": str (if failed),
                "info": Dict (additional metadata)
            }
        """
        result = AsyncResult(task_id, app=self.celery_app)

        # Check if task exists (PENDING state can mean task doesn't exist yet)
        if result.state == "PENDING" and not result.backend.get(result.backend.get_key_for_task(task_id)):
            return None

        status = {
            "state": result.state,
            "result": None,
            "traceback": None,
            "info": {}
        }

        if result.state == "SUCCESS":
            status["result"] = result.result
        elif result.state == "FAILURE":
            status["result"] = str(result.result)
            status["traceback"] = result.traceback
        elif result.state in ["STARTED", "RETRY"]:
            status["info"] = result.info or {}

        return status

    def cancel_task(self, task_id: str, terminate: bool = False) -> bool:
        """
        Cancel a Celery task.

        Args:
            task_id: Celery task ID
            terminate: If True, send SIGTERM to worker. If False, send SIGKILL (revoke).

        Returns:
            True if cancellation command was sent successfully
        """
        try:
            result = AsyncResult(task_id, app=self.celery_app)
            result.revoke(terminate=terminate, signal='SIGTERM' if terminate else 'SIGKILL')
            return True
        except Exception as e:
            print(f"Error cancelling task {task_id}: {e}")
            return False

    def get_queue_depth(self, queue_name: str = "celery") -> int:
        """
        Get the number of tasks in the Redis queue.

        Args:
            queue_name: Name of the Celery queue

        Returns:
            Number of pending tasks in the queue
        """
        try:
            # Get queue length from Redis
            # Celery uses Redis lists for queues
            redis_client = self.celery_app.broker_connection().channel().client
            queue_key = f"{queue_name}"
            return redis_client.llen(queue_key)
        except Exception as e:
            print(f"Error getting queue depth: {e}")
            return 0

    def purge_queue(self, queue_name: str = "celery") -> int:
        """
        Remove all tasks from the Redis queue.

        Args:
            queue_name: Name of the Celery queue to purge

        Returns:
            Number of tasks purged
        """
        try:
            # Purge using Celery's control API
            from celery import current_app
            purged = current_app.control.purge()
            return purged
        except Exception as e:
            print(f"Error purging queue: {e}")
            return 0
