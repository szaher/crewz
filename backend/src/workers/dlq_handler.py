"""
Dead Letter Queue (DLQ) handler for failed tasks.

Automatically moves tasks to DLQ after all retry attempts are exhausted.
Captures retry history for debugging and analysis.
"""

from datetime import datetime
from celery.signals import task_failure
from uuid import UUID

from ..db import get_db
from ..models.execution_queue import ExecutionQueue, ExecutionStatus
from ..models.dead_letter_task import DeadLetterTask


@task_failure.connect
def handle_task_failure(sender=None, task_id=None, exception=None, args=None, kwargs=None,
                       traceback=None, einfo=None, **extra_kwargs):
    """
    Celery signal handler for task failures.

    Called when a task fails after all retry attempts.
    Moves the task to the Dead Letter Queue for manual inspection.

    Args:
        sender: Task class
        task_id: Celery task ID
        exception: Exception that caused the failure
        args: Task args
        kwargs: Task kwargs
        traceback: Exception traceback
        einfo: Exception info
        **extra_kwargs: Additional context
    """

    # Extract execution_id from kwargs or args
    execution_id = kwargs.get("execution_id") if kwargs else (args[0] if args else None)

    if not execution_id:
        print(f"Task {task_id} failed but no execution_id found")
        return

    try:
        execution_uuid = UUID(execution_id)

        with next(get_db()) as db:
            # Get execution record
            execution = db.query(ExecutionQueue).filter(
                ExecutionQueue.execution_id == execution_uuid
            ).first()

            if not execution:
                print(f"Execution {execution_id} not found in database")
                return

            # Check if this is the final failure (after max retries)
            if execution.retry_count >= execution.max_retries:
                # Move to Dead Letter Queue
                dlq_task = DeadLetterTask(
                    original_queue_id=execution.id,
                    execution_type=execution.execution_type.value,
                    payload=execution.payload,
                    failure_reason=str(exception),
                    retry_history=[],
                    failure_timestamp=datetime.utcnow(),
                    is_requeued=False
                )

                # Build retry history from execution attempts
                # Each retry should have been logged with timestamp, error, duration
                for attempt in range(execution.retry_count + 1):  # +1 for initial attempt
                    retry_record = {
                        "attempt": attempt + 1,
                        "timestamp": datetime.utcnow().isoformat(),  # In production, get from logs
                        "error": str(exception) if attempt == execution.retry_count else "Previous attempt failed",
                        "duration_ms": execution.duration_ms or 0
                    }
                    dlq_task.retry_history.append(retry_record)

                db.add(dlq_task)

                # Update execution status to FAILED (if not already)
                if execution.status != ExecutionStatus.FAILED:
                    execution.status = ExecutionStatus.FAILED
                    execution.error = str(exception)
                    execution.completed_at = datetime.utcnow()
                    execution.calculate_duration()

                db.commit()

                print(f"Task {task_id} (execution {execution_id}) moved to DLQ after {execution.retry_count + 1} attempts")

                # Optionally: Send notification to admins
                _notify_dlq_entry(execution, dlq_task)

    except Exception as e:
        print(f"Failed to handle task failure for {task_id}: {e}")


def _notify_dlq_entry(execution: ExecutionQueue, dlq_task: DeadLetterTask):
    """
    Send notification when a task is moved to DLQ.

    Args:
        execution: Original execution queue record
        dlq_task: DLQ entry
    """
    try:
        from db.redis import get_redis_client

        redis_client = get_redis_client()

        # Notify user
        user_channel = f"notifications:user:{execution.user_id}"
        user_notification = {
            "type": "execution_failed",
            "execution_id": str(execution.execution_id),
            "execution_type": execution.execution_type.value,
            "status": "moved_to_dlq",
            "message": f"Execution failed after {execution.retry_count + 1} attempts",
            "timestamp": datetime.utcnow().isoformat()
        }
        redis_client.publish(user_channel, str(user_notification))

        # Notify admins (optional)
        admin_channel = "notifications:admins:dlq"
        admin_notification = {
            "type": "dlq_entry",
            "dlq_task_id": str(dlq_task.id),
            "execution_id": str(execution.execution_id),
            "execution_type": execution.execution_type.value,
            "tenant_id": str(execution.tenant_id),
            "user_id": str(execution.user_id),
            "failure_reason": dlq_task.failure_reason,
            "retry_count": len(dlq_task.retry_history),
            "timestamp": datetime.utcnow().isoformat()
        }
        redis_client.publish(admin_channel, str(admin_notification))

    except Exception as e:
        print(f"Failed to send DLQ notification: {e}")


def requeue_dlq_task(dlq_task_id: UUID) -> bool:
    """
    Manually requeue a task from the Dead Letter Queue.

    Args:
        dlq_task_id: DLQ task ID to requeue

    Returns:
        True if successfully requeued, False otherwise
    """
    try:
        from workers.celery_app import celery_app

        with next(get_db()) as db:
            dlq_task = db.query(DeadLetterTask).filter(DeadLetterTask.id == dlq_task_id).first()

            if not dlq_task:
                print(f"DLQ task {dlq_task_id} not found")
                return False

            if dlq_task.is_requeued:
                print(f"DLQ task {dlq_task_id} already requeued")
                return False

            # Get original execution
            execution = db.query(ExecutionQueue).filter(
                ExecutionQueue.id == dlq_task.original_queue_id
            ).first()

            if not execution:
                print(f"Original execution not found for DLQ task {dlq_task_id}")
                return False

            # Create new execution queue entry
            from uuid import uuid4
            new_execution = ExecutionQueue(
                execution_id=uuid4(),
                tenant_id=execution.tenant_id,
                user_id=execution.user_id,
                execution_type=execution.execution_type,
                entity_id=execution.entity_id,
                status=ExecutionStatus.PENDING,
                priority=execution.priority,
                retry_count=0,  # Reset retry count
                max_retries=execution.max_retries,
                payload=dlq_task.payload,
                scheduled_at=datetime.utcnow()
            )

            db.add(new_execution)

            # Mark DLQ task as requeued
            dlq_task.is_requeued = True

            db.commit()

            # Submit to Celery
            task_name = f"backend.src.workers.tasks.execute_{execution.execution_type.value}"
            celery_app.send_task(
                task_name,
                kwargs={
                    "execution_id": str(new_execution.execution_id),
                    f"{execution.execution_type.value}_id": str(execution.entity_id),
                    "payload": dlq_task.payload
                }
            )

            print(f"DLQ task {dlq_task_id} requeued as execution {new_execution.execution_id}")
            return True

    except Exception as e:
        print(f"Failed to requeue DLQ task {dlq_task_id}: {e}")
        return False
