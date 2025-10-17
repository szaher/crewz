"""
Celery application configuration for async task execution.

Configuration based on research.md recommendations:
- Broker: Redis Streams
- Result backend: Redis
- Retry: 3 attempts with exponential backoff
- Timeout: 30 minutes (soft), 31 minutes (hard)
- Acknowledgment: Late ack for reliability
"""

import os
from celery import Celery
from kombu import Exchange, Queue

# Get Redis connection from environment or use default
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
CELERY_BROKER_URL = f"{REDIS_URL}/0"  # Database 0 for broker
CELERY_RESULT_BACKEND = f"{REDIS_URL}/1"  # Database 1 for results

# Create Celery app
celery_app = Celery(
    "crewai_platform",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND
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

    # Timeout configuration
    task_soft_time_limit=1800,  # 30 minutes soft limit (raises SoftTimeLimitExceeded)
    task_time_limit=1860,  # 31 minutes hard limit (kills task)

    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    result_persistent=True,  # Persist results to Redis
    result_compression='gzip',  # Compress large results

    # Worker settings
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks (prevent memory leaks)
    worker_disable_rate_limits=False,  # Enable rate limiting

    # Queue routing (priority queues)
    task_routes={
        "backend.src.workers.tasks.execute_*": {
            "queue": "executions",
            "routing_key": "execution.default"
        },
    },

    # Define queues with priorities
    task_queues=(
        Queue("executions", Exchange("executions"), routing_key="execution.#",
              priority=5, max_priority=10),
        Queue("high_priority", Exchange("executions"), routing_key="execution.high",
              priority=9, max_priority=10),
        Queue("low_priority", Exchange("executions"), routing_key="execution.low",
              priority=1, max_priority=10),
    ),

    # Task execution tracking
    task_track_started=True,  # Track when task starts
    task_send_sent_event=True,  # Send task-sent events

    # Error handling
    task_ignore_result=False,  # Store results even for failed tasks
    task_store_errors_even_if_ignored=True,  # Store errors for debugging
)

# Task discovery (auto-discover tasks in tasks.py)
celery_app.autodiscover_tasks(["backend.src.workers"])

# Optional: Celery Beat configuration for periodic tasks
celery_app.conf.beat_schedule = {
    # Example: Cleanup old metrics every hour
    "cleanup-old-metrics": {
        "task": "backend.src.workers.tasks.cleanup_old_metrics",
        "schedule": 3600.0,  # Run every hour
    },
}


@celery_app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery configuration"""
    print(f"Request: {self.request!r}")
    return {"status": "ok", "message": "Celery is working!"}


if __name__ == "__main__":
    # Run Celery worker
    celery_app.start()
