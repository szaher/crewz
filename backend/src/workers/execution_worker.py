"""Main execution worker task for processing crew/flow/task executions.

Celery task with soft_time_limit, timeout via SIGTERM, artifact capture.
Only runs if ENABLE_WORKER_ARCHITECTURE=True.
"""
import sys
import os
import time
from io import StringIO
from celery import Task
from celery.exceptions import SoftTimeLimitExceeded
from src.workers.celery_app import celery_app
from src.config.settings import Settings
from src.config.worker_config import WorkerConfig
from src.models.execution import Execution, ExecutionStatus
from src.models.execution_artifact import ExecutionArtifact, ArtifactType
from src.services.artifact_service import ArtifactService
from src.services.worker_service import WorkerService
from src.workers.stream_handler import StreamHandler


class ExecutionTask(Task):
    """Custom Celery task class for executions."""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        from src.db import get_db

        execution_id = args[0] if args else None
        if not execution_id:
            return

        db = next(get_db())
        try:
            execution = db.query(Execution).filter(Execution.id == execution_id).first()
            if execution:
                execution.status = ExecutionStatus.FAILED
                execution.error = str(exc)
                db.commit()
        finally:
            db.close()


@celery_app.task(
    bind=True,
    base=ExecutionTask,
    soft_time_limit=WorkerConfig.SOFT_TIME_LIMIT_SECONDS,
    time_limit=WorkerConfig.HARD_TIME_LIMIT_SECONDS,
    name='workers.execute_crew_task'
)
def execute_crew_task(self, execution_id: str):
    """
    Execute crew/flow/task with timeout and artifact capture.

    Args:
        execution_id: Execution UUID string

    Only runs if ENABLE_WORKER_ARCHITECTURE=True.
    """
    from src.db import get_db
    from uuid import UUID

    settings = Settings()

    # Check if worker architecture is enabled
    if not settings.ENABLE_WORKER_ARCHITECTURE:
        raise Exception("Worker architecture is disabled (ENABLE_WORKER_ARCHITECTURE=False)")

    db = next(get_db())
    execution = None

    try:
        # Load execution from database
        execution = db.query(Execution).filter(Execution.id == UUID(execution_id)).first()
        if not execution:
            raise Exception(f"Execution {execution_id} not found")

        # Update status to running
        execution.status = ExecutionStatus.RUNNING
        execution.worker_id = self.request.hostname
        db.commit()

        # Initialize services
        artifact_service = ArtifactService(db)
        stream_handler = StreamHandler(execution_id)

        # Emit execution.started event
        stream_handler.emit_started(worker_id=self.request.hostname)

        # Capture stdout/stderr
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        output_buffer = StringIO()
        error_buffer = StringIO()

        try:
            sys.stdout = output_buffer
            sys.stderr = error_buffer

            # Execute based on type
            result = None
            if execution.execution_type.value == "crew":
                result = _execute_crew(execution, stream_handler, db)
            elif execution.execution_type.value == "flow":
                result = _execute_flow(execution, stream_handler, db)
            elif execution.execution_type.value == "task":
                result = _execute_task(execution, stream_handler, db)
            else:
                raise Exception(f"Unknown execution type: {execution.execution_type}")

            # Restore stdout/stderr
            sys.stdout = old_stdout
            sys.stderr = old_stderr

            # Capture output as artifact
            output_content = output_buffer.getvalue()
            error_content = error_buffer.getvalue()

            if output_content:
                _save_artifact(
                    execution, artifact_service, "output.log",
                    output_content.encode(), ArtifactType.OUTPUT_FILE
                )

            if error_content:
                _save_artifact(
                    execution, artifact_service, "error.log",
                    error_content.encode(), ArtifactType.ERROR_LOG
                )

            # Update execution with result
            execution.status = ExecutionStatus.COMPLETED
            execution.output_data = result
            db.commit()

            # Emit completion event
            stream_handler.emit_completed(status="completed", result_summary="Execution completed successfully")

        except SoftTimeLimitExceeded:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

            execution.status = ExecutionStatus.FAILED
            execution.error = f"Execution timed out after {WorkerConfig.SOFT_TIME_LIMIT_SECONDS}s"
            db.commit()

            stream_handler.emit_error(
                error_type="TimeoutError",
                message=f"Execution exceeded {WorkerConfig.SOFT_TIME_LIMIT_SECONDS}s timeout"
            )
            raise

        except Exception as e:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

            execution.status = ExecutionStatus.FAILED
            execution.error = str(e)
            db.commit()

            stream_handler.emit_error(
                error_type=type(e).__name__,
                message=str(e),
                traceback=None  # Could add traceback.format_exc() here
            )
            raise

    finally:
        if db:
            db.close()


def _execute_crew(execution: Execution, stream_handler: StreamHandler, db):
    """Execute crew run."""
    # TODO: Implement actual crew execution logic
    # For now, simulate execution
    stream_handler.emit_output("Starting crew execution...", stream_type="stdout")
    time.sleep(2)
    stream_handler.emit_progress(percent=50, current_step="Running tasks", total_steps=2)
    time.sleep(2)
    stream_handler.emit_output("Crew execution completed", stream_type="stdout")

    return {"status": "success", "message": "Crew executed successfully"}


def _execute_flow(execution: Execution, stream_handler: StreamHandler, db):
    """Execute flow run."""
    # TODO: Implement actual flow execution logic
    stream_handler.emit_output("Starting flow execution...", stream_type="stdout")
    time.sleep(2)
    stream_handler.emit_progress(percent=100, current_step="Flow completed", total_steps=1)

    return {"status": "success", "message": "Flow executed successfully"}


def _execute_task(execution: Execution, stream_handler: StreamHandler, db):
    """Execute single task."""
    # TODO: Implement actual task execution logic
    stream_handler.emit_output("Starting task execution...", stream_type="stdout")
    time.sleep(1)

    return {"status": "success", "message": "Task executed successfully"}


def _save_artifact(
    execution: Execution,
    artifact_service: ArtifactService,
    filename: str,
    content: bytes,
    artifact_type: ArtifactType
):
    """Save execution artifact."""
    # For now, save to temp file (in production, would upload to S3)
    import tempfile

    with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{filename}") as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    # Create artifact record
    artifact_service.create_artifact_record(
        execution_id=execution.id,
        tenant_id=execution.user.tenant_id if hasattr(execution.user, 'tenant_id') else None,
        file_name=filename,
        file_size=len(content),
        file_path=tmp_path,  # In production: upload to S3 first
        artifact_type=artifact_type,
        version_number=execution.artifact_version or 1
    )
