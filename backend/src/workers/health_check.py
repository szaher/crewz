"""Worker health check periodic task.

Celery beat task runs every 30s, marks workers crashed if heartbeat > 90s,
requeues jobs with retry policy.
"""
from celery import Task
from src.workers.celery_app import celery_app
from src.config.worker_config import WorkerConfig
from src.models.execution import Execution, ExecutionStatus


class HealthCheckTask(Task):
    """Custom health check task."""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Log health check failure."""
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Health check task failed: {exc}")


@celery_app.task(
    bind=True,
    base=HealthCheckTask,
    name='workers.check_worker_health'
)
def check_worker_health(self):
    """
    Periodic health check task (runs every 30s).

    Checks all workers for stale heartbeats (>90s), marks as crashed,
    and requeues their jobs with retry policy.
    """
    from src.db import get_db
    from src.services.worker_service import WorkerService
    from src.services.execution_service_worker import ExecutionServiceWorker
    import logging

    logger = logging.getLogger(__name__)
    db = next(get_db())

    try:
        worker_service = WorkerService(db)
        execution_service = ExecutionServiceWorker(db)

        # Check for crashed workers
        crashed_workers = worker_service.check_and_mark_crashed_workers()

        if crashed_workers:
            logger.warning(f"Found {len(crashed_workers)} crashed workers")

            for worker in crashed_workers:
                logger.warning(
                    f"Worker {worker.worker_hostname} crashed "
                    f"(last heartbeat: {worker.last_heartbeat_at})"
                )

                # Find executions running on crashed worker
                crashed_executions = db.query(Execution).filter(
                    Execution.worker_id == worker.worker_hostname,
                    Execution.status == ExecutionStatus.RUNNING
                ).all()

                for execution in crashed_executions:
                    logger.warning(
                        f"Requeuing execution {execution.id} from crashed worker {worker.worker_hostname}"
                    )

                    # Handle crash retry
                    requeued = execution_service.handle_worker_crash_retry(execution.id)

                    if requeued:
                        logger.info(f"Execution {execution.id} requeued (retry #{execution.retry_count})")
                    else:
                        logger.error(f"Execution {execution.id} failed - max retries exceeded")

        # Get pool metrics for monitoring
        metrics = worker_service.get_pool_metrics()
        logger.info(
            f"Worker pool: {metrics['healthy_workers']}/{metrics['total_workers']} healthy, "
            f"{metrics['idle_workers']} idle, {metrics['busy_workers']} busy, "
            f"{metrics['crashed_workers']} crashed"
        )

        return {
            "crashed_workers": len(crashed_workers),
            "pool_metrics": metrics
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise

    finally:
        db.close()


@celery_app.task(
    name='workers.cleanup_expired_artifacts'
)
def cleanup_expired_artifacts():
    """
    Periodic task to cleanup expired artifacts (runs daily).

    Deletes artifacts past their retention period.
    """
    from src.db import get_db
    from src.services.artifact_service import ArtifactService
    import logging

    logger = logging.getLogger(__name__)
    db = next(get_db())

    try:
        artifact_service = ArtifactService(db)

        deleted_count = artifact_service.cleanup_expired_artifacts()

        logger.info(f"Cleaned up {deleted_count} expired artifacts")

        return {"deleted_count": deleted_count}

    except Exception as e:
        logger.error(f"Artifact cleanup failed: {e}")
        raise

    finally:
        db.close()


@celery_app.task(
    name='workers.send_heartbeat'
)
def send_heartbeat():
    """
    Worker heartbeat task (runs every 30s on each worker).

    Updates worker's last_heartbeat_at and resource usage.
    """
    from src.db import get_db
    from src.services.worker_service import WorkerService
    import logging
    import psutil
    import socket

    logger = logging.getLogger(__name__)
    db = next(get_db())

    try:
        worker_service = WorkerService(db)

        # Get worker hostname
        worker_hostname = socket.gethostname()

        # Get resource usage
        cpu_percent = psutil.cpu_percent(interval=1)
        memory_info = psutil.virtual_memory()
        memory_mb = int(memory_info.used / (1024 * 1024))

        # Update heartbeat
        updated = worker_service.update_heartbeat(
            worker_hostname=worker_hostname,
            cpu_percent=cpu_percent,
            memory_mb=memory_mb
        )

        if not updated:
            # Register worker if not found
            worker_service.register_worker(
                worker_hostname=worker_hostname,
                cpu_percent=cpu_percent,
                memory_mb=memory_mb
            )

        logger.debug(
            f"Heartbeat sent: {worker_hostname} - CPU: {cpu_percent}%, Memory: {memory_mb}MB"
        )

        return {
            "worker_hostname": worker_hostname,
            "cpu_percent": cpu_percent,
            "memory_mb": memory_mb
        }

    except Exception as e:
        logger.error(f"Heartbeat failed: {e}")
        raise

    finally:
        db.close()


# Configure Celery Beat schedule
celery_app.conf.beat_schedule = {
    'check-worker-health': {
        'task': 'workers.check_worker_health',
        'schedule': 30.0,  # Every 30 seconds
    },
    'cleanup-expired-artifacts': {
        'task': 'workers.cleanup_expired_artifacts',
        'schedule': 86400.0,  # Every 24 hours
    },
    'send-heartbeat': {
        'task': 'workers.send_heartbeat',
        'schedule': 30.0,  # Every 30 seconds
    },
}
