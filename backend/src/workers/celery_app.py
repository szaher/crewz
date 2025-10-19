"""
Celery application configuration for async task execution.

Configuration based on research.md recommendations:
- Broker: Redis Streams
- Result backend: Redis
- Retry: 3 attempts with exponential backoff
- Timeout: Configurable per tenant (default 10 minutes soft)
- Acknowledgment: Late ack for reliability
- Worker pool: Gevent for I/O-bound tasks (LLM API calls)
"""

from celery import Celery
from kombu import Exchange, Queue

# Import centralized settings
try:
    from ..config import settings
except ImportError:
    # Fallback for direct worker execution
    import os
    class Settings:
        REDIS_URL = os.getenv("CELERY_BROKER_URL", os.getenv("REDIS_URL", "redis://crewai-redis:6379/0"))
    settings = Settings()

# Create Celery app
celery_app = Celery(
    "crewai_platform",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

# Celery configuration
celery_app.conf.update(
    # Task execution settings
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,

    # Reliability settings
    task_acks_late=True,  # Acknowledge after task completes (prevents loss on worker crash)
    worker_prefetch_multiplier=1,  # Fetch one task at a time (fair distribution)
    task_reject_on_worker_lost=True,  # Requeue task if worker crashes

    # Retry configuration (exponential backoff)
    task_autoretry_for=(Exception,),  # Auto-retry on any exception
    task_max_retries=3,  # Maximum 3 retry attempts
    task_default_retry_delay=2,  # Start with 2 seconds
    task_retry_backoff=True,  # Enable exponential backoff (2s, 4s, 8s)
    task_retry_backoff_max=30,  # Maximum 30 seconds between retries
    task_retry_jitter=True,  # Add random jitter to prevent thundering herd

    # Timeout configuration (default 10 minutes, configurable per execution)
    task_soft_time_limit=600,  # 10 minutes soft limit (raises SoftTimeLimitExceeded, sends SIGTERM)
    task_time_limit=660,  # 11 minutes hard limit (kills task with SIGKILL)

    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    result_persistent=True,  # Persist results to Redis
    result_compression='gzip',  # Compress large results

    # Worker pool settings (gevent for I/O-bound tasks like LLM API calls)
    worker_pool="gevent",  # Use gevent pool for concurrent I/O-bound tasks
    worker_concurrency=4,  # 4 concurrent tasks per worker (2 CPU cores × 2 greenlets/core)

    # Worker settings
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks (prevent memory leaks)
    worker_disable_rate_limits=False,  # Enable rate limiting
    worker_send_task_events=True,  # Send task events for monitoring (Flower)
    worker_enable_remote_control=True,  # Enable remote control commands

    # Queue routing (priority queues)
    task_routes={
        "backend.src.workers.tasks.execute_flow": {"queue": "normal_priority"},
        "backend.src.workers.tasks.execute_crew": {"queue": "normal_priority"},
        "backend.src.workers.tasks.execute_agent": {"queue": "normal_priority"},
        "backend.src.workers.tasks.execute_task": {"queue": "normal_priority"},
        "backend.src.workers.tasks.execute_tool": {"queue": "normal_priority"},
        "backend.src.workers.tasks.process_queued_executions": {"queue": "normal_priority"},
        "backend.src.workers.tasks.cleanup_old_metrics": {"queue": "normal_priority"},
    },

    # Define queues with priorities
    task_queues=(
        # High priority queue (priority 1-3)
        Queue(
            "high_priority",
            Exchange("tasks", type="direct"),
            routing_key="high_priority",
            queue_arguments={"x-max-priority": 10},
        ),
        # Normal priority queue (priority 4-6)
        Queue(
            "normal_priority",
            Exchange("tasks", type="direct"),
            routing_key="normal_priority",
            queue_arguments={"x-max-priority": 10},
        ),
        # Low priority queue (priority 7-10)
        Queue(
            "low_priority",
            Exchange("tasks", type="direct"),
            routing_key="low_priority",
            queue_arguments={"x-max-priority": 10},
        ),
        # Legacy execution queue (for backward compatibility)
        Queue("executions", Exchange("executions"), routing_key="execution.#",
              priority=5, max_priority=10),
    ),

    # Task execution tracking
    task_track_started=True,  # Track when task starts
    task_send_sent_event=True,  # Send task-sent events

    # Error handling
    task_ignore_result=False,  # Store results even for failed tasks
    task_store_errors_even_if_ignored=True,  # Store errors for debugging
)

# Task discovery (auto-discover tasks in tasks.py)
celery_app.autodiscover_tasks(["src.workers"], related_name="tasks")

# Optional: Celery Beat configuration for periodic tasks
celery_app.conf.beat_schedule = {
    # Process queued executions every minute
    "process-queued-executions": {
        "task": "backend.src.workers.tasks.process_queued_executions",
        "schedule": 60.0,  # Run every minute
        "options": {"queue": "normal_priority"},  # Route to normal_priority queue
    },
    # Cleanup old metrics every hour
    "cleanup-old-metrics": {
        "task": "backend.src.workers.tasks.cleanup_old_metrics",
        "schedule": 3600.0,  # Run every hour
        "options": {"queue": "normal_priority"},  # Route to normal_priority queue
    },
}


def get_queue_for_priority(priority: int) -> str:
    """
    Map priority integer to queue name.

    Args:
        priority: Priority level (1-10, where 1 is highest)

    Returns:
        Queue name (high_priority, normal_priority, low_priority)
    """
    if priority <= 3:
        return "high_priority"
    elif priority <= 6:
        return "normal_priority"
    elif priority <= 10:
        return "low_priority"
    else:
        return "normal_priority"  # Default to normal


def get_celery_app() -> Celery:
    """Get the configured Celery app instance."""
    return celery_app


@celery_app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery configuration"""
    print(f"Request: {self.request!r}")
    return {"status": "ok", "message": "Celery is working!"}


if __name__ == "__main__":
    # Run Celery worker: celery -A src.workers.celery_app worker --loglevel=info --pool=gevent --concurrency=4
    celery_app.start()
