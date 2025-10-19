"""Execution service wrapper for worker architecture.

Wraps existing execution_service, adds queue_execution, cancel_execution, reexecute_with_version.
Delegates to old service when ENABLE_WORKER_ARCHITECTURE=False.
"""
from typing import Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from src.config.settings import Settings
from src.models.execution import Execution, ExecutionStatus
from src.services.queue_service import QueueService
from src.services.worker_service import WorkerService
from src.services.artifact_service import ArtifactService


class ExecutionServiceWorker:
    """
    Wrapper service for executions with worker architecture support.

    Delegates to legacy execution path when feature flag is disabled.
    """

    def __init__(
        self,
        db_session: Session,
        queue_service: QueueService = None,
        worker_service: WorkerService = None,
        artifact_service: ArtifactService = None,
        settings: Settings = None
    ):
        """
        Initialize execution service worker.

        Args:
            db_session: SQLAlchemy database session
            queue_service: Queue service instance
            worker_service: Worker service instance
            artifact_service: Artifact service instance
            settings: Settings instance
        """
        self.db = db_session
        self.settings = settings or Settings()
        self.enabled = self.settings.ENABLE_WORKER_ARCHITECTURE

        # Initialize services
        self.queue_service = queue_service or QueueService(settings=self.settings)
        self.worker_service = worker_service or WorkerService(db_session)
        self.artifact_service = artifact_service or ArtifactService(db_session)

    def queue_execution(
        self,
        execution_type: str,
        entity_id: UUID,
        input_params: Dict[str, Any],
        user_id: UUID,
        tenant_id: UUID = None,
        priority: int = 5,
        timeout_seconds: int = 600
    ) -> Execution:
        """
        Queue new execution (uses worker if enabled, else falls back to old flow).

        Args:
            execution_type: Type of execution (crew, flow, task)
            entity_id: Entity UUID (crew_id, flow_id, etc.)
            input_params: Input parameters
            user_id: User UUID
            tenant_id: Tenant UUID (optional)
            priority: Queue priority (0-10, lower is higher priority)
            timeout_seconds: Execution timeout

        Returns:
            Execution object
        """
        # Create execution record
        execution = Execution(
            execution_type=execution_type,
            user_id=user_id,
            input_data=input_params,
            priority=priority,
            timeout_seconds=timeout_seconds
        )

        # Set entity reference based on type
        if execution_type == "flow":
            execution.flow_id = entity_id
        elif execution_type == "crew":
            execution.crew_id = entity_id
        elif execution_type == "task":
            execution.task_id = entity_id
        elif execution_type == "agent":
            execution.agent_id = entity_id

        if self.enabled:
            # Worker architecture enabled - queue execution
            execution.status = ExecutionStatus.QUEUED

            self.db.add(execution)
            self.db.commit()
            self.db.refresh(execution)

            # Add to Redis queue
            position, estimated_wait = self.queue_service.add_to_queue(
                execution.id,
                priority=priority
            )

            execution.queue_position = position
            self.db.commit()

            # Dispatch to Celery worker
            self._dispatch_to_celery(execution, entity_id, input_params)

            return execution
        else:
            # Fall back to old execution path (synchronous)
            execution.status = ExecutionStatus.PENDING

            self.db.add(execution)
            self.db.commit()
            self.db.refresh(execution)

            # TODO: Trigger old synchronous execution flow
            # For now, just return the pending execution
            return execution

    def cancel_execution(
        self,
        execution_id: UUID,
        user_id: UUID
    ) -> Dict[str, bool]:
        """
        Cancel execution (sets cancellation_requested flag, sends Celery revoke if worker execution).

        Args:
            execution_id: Execution UUID
            user_id: User UUID requesting cancellation

        Returns:
            Dict with cancelled and final_state_logged flags
        """
        execution = self.db.query(Execution).filter(
            Execution.id == execution_id
        ).first()

        if not execution:
            return {"cancelled": False, "final_state_logged": False, "error": "not_found"}

        # Check if user owns the execution
        if execution.user_id != user_id:
            return {"cancelled": False, "final_state_logged": False, "error": "forbidden"}

        if execution.status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED]:
            # Already finished
            return {"cancelled": False, "final_state_logged": True}

        # Set cancellation flag
        execution.cancellation_requested = True
        execution.status = ExecutionStatus.CANCELLED

        if self.enabled and execution.worker_id:
            # Revoke Celery task if running on worker
            try:
                from src.workers.celery_app import celery_app
                celery_app.control.revoke(str(execution_id), terminate=True)
            except Exception:
                pass  # Continue even if revoke fails

        self.db.commit()

        return {"cancelled": True, "final_state_logged": True}

    def reexecute_with_version(
        self,
        execution_id: UUID,
        user_id: UUID
    ) -> Optional[Execution]:
        """
        Re-execute with same inputs (clones execution with parent_execution_id, increments artifact_version).

        Args:
            execution_id: Original execution UUID
            user_id: User UUID

        Returns:
            New Execution object or None if original not found
        """
        original_execution = self.db.query(Execution).filter(
            Execution.id == execution_id
        ).first()

        if not original_execution:
            return None

        # Clone execution with incremented version
        new_execution = Execution(
            execution_type=original_execution.execution_type,
            flow_id=original_execution.flow_id,
            crew_id=original_execution.crew_id,
            agent_id=original_execution.agent_id,
            tool_id=original_execution.tool_id,
            task_id=original_execution.task_id,
            user_id=user_id,
            input_data=original_execution.input_data,
            priority=original_execution.priority or 5,
            timeout_seconds=original_execution.timeout_seconds,
            parent_execution_id=execution_id,
            artifact_version=(original_execution.artifact_version or 1) + 1
        )

        if self.enabled:
            # Queue the new execution
            new_execution.status = ExecutionStatus.QUEUED

            self.db.add(new_execution)
            self.db.commit()
            self.db.refresh(new_execution)

            # Add to queue
            position, estimated_wait = self.queue_service.add_to_queue(
                new_execution.id,
                priority=new_execution.priority
            )

            new_execution.queue_position = position
            self.db.commit()

            # Dispatch to Celery worker
            entity_id = (
                original_execution.flow_id or
                original_execution.crew_id or
                original_execution.agent_id or
                original_execution.task_id
            )
            if entity_id:
                self._dispatch_to_celery(new_execution, entity_id, original_execution.input_data)

            return new_execution
        else:
            # Fall back to old execution path
            new_execution.status = ExecutionStatus.PENDING

            self.db.add(new_execution)
            self.db.commit()
            self.db.refresh(new_execution)

            return new_execution

    def handle_worker_crash_retry(self, execution_id: UUID) -> bool:
        """
        Handle worker crash and retry execution.

        Args:
            execution_id: Execution UUID that was running on crashed worker

        Returns:
            True if requeued, False otherwise
        """
        execution = self.db.query(Execution).filter(
            Execution.id == execution_id
        ).first()

        if not execution:
            return False

        if execution.retry_count >= (execution.max_retries or 3):
            # Max retries exceeded
            execution.status = ExecutionStatus.FAILED
            execution.error = "Worker crashed, max retries exceeded"
            self.db.commit()
            return False

        # Increment retry count and requeue
        execution.retry_count = (execution.retry_count or 0) + 1
        execution.status = ExecutionStatus.QUEUED
        execution.worker_id = None

        self.db.commit()

        if self.enabled:
            # Re-add to queue
            position, estimated_wait = self.queue_service.add_to_queue(
                execution.id,
                priority=execution.priority or 5
            )

            execution.queue_position = position
            self.db.commit()

        return True

    def get_execution_status(self, execution_id: UUID) -> Optional[Dict]:
        """
        Get execution status with queue info.

        Args:
            execution_id: Execution UUID

        Returns:
            Status dict or None if not found
        """
        execution = self.db.query(Execution).filter(
            Execution.id == execution_id
        ).first()

        if not execution:
            return None

        status = {
            "job_id": str(execution.id),
            "status": execution.status.value,
            "queue_position": execution.queue_position,
            "worker_id": str(execution.worker_id) if execution.worker_id else None,
            "started_at": execution.created_at.isoformat() if execution.created_at else None,
            "progress_percent": None  # TODO: Implement progress tracking
        }

        return status

    def _dispatch_to_celery(
        self,
        execution: Execution,
        entity_id: UUID,
        input_params: Dict[str, Any]
    ):
        """
        Dispatch execution to appropriate Celery task.

        Args:
            execution: Execution record
            entity_id: Entity UUID (flow_id, crew_id, etc.)
            input_params: Input parameters for execution
        """
        from src.workers.celery_app import celery_app

        # Map execution types to full task names (matching worker registration)
        task_name_map = {
            "flow": "backend.src.workers.tasks.execute_flow",
            "crew": "backend.src.workers.tasks.execute_crew",
            "agent": "backend.src.workers.tasks.execute_agent",
            "task": "backend.src.workers.tasks.execute_task",
            "tool": "backend.src.workers.tasks.execute_tool"
        }

        # Convert enum to string value for lookup
        execution_type_str = execution.execution_type.value if hasattr(execution.execution_type, 'value') else str(execution.execution_type)
        task_name = task_name_map.get(execution_type_str)
        if not task_name:
            raise ValueError(f"Unknown execution type: {execution.execution_type}")

        # Dispatch to Celery with send_task (uses task name string)
        payload = {
            "input_data": input_params,
            "timeout_seconds": execution.timeout_seconds
        }

        celery_app.send_task(
            task_name,
            args=[str(execution.id), str(entity_id), payload],
            task_id=str(execution.id),
            priority=execution.priority or 5,
            queue="normal_priority",  # Route to normal_priority queue where workers listen
            soft_time_limit=execution.timeout_seconds,
            time_limit=execution.timeout_seconds + 10  # Hard limit slightly higher
        )
