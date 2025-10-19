"""
Celery tasks for async execution of crews, flows, agents, and tasks.

Each task:
1. Updates execution_queue status: pending → running
2. Calls CrewAI SDK or execution logic
3. Saves result to execution_queue
4. Updates status: running → completed/failed/timeout
5. Publishes notification via Redis pub/sub
"""

import json
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID
from celery import Task
from celery.exceptions import SoftTimeLimitExceeded

from .celery_app import celery_app
from ..db import get_db
from ..models.execution import Execution, ExecutionStatus
from ..db.redis import get_redis_client


class ExecutionTask(Task):
    """
    Base class for execution tasks with common functionality.
    Provides automatic status updates and error handling.
    """

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called when task fails"""
        execution_id = kwargs.get("execution_id") or (args[0] if args else None)
        if execution_id:
            self._update_execution_status(
                execution_id,
                ExecutionStatus.FAILED,
                error=str(exc)
            )

    def on_success(self, retval, task_id, args, kwargs):
        """Called when task succeeds"""
        execution_id = kwargs.get("execution_id") or (args[0] if args else None)
        if execution_id:
            self._update_execution_status(
                execution_id,
                ExecutionStatus.COMPLETED,
                result=retval
            )

    def _update_execution_status(
        self,
        execution_id: UUID,
        status: ExecutionStatus,
        result: Optional[Dict] = None,
        error: Optional[str] = None
    ):
        """Update execution record"""
        try:
            with next(get_db()) as db:
                execution = db.query(Execution).filter(
                    Execution.id == execution_id
                ).first()

                if execution:
                    execution.status = status

                    if status == ExecutionStatus.RUNNING:
                        execution.started_at = datetime.utcnow()
                    elif status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED]:
                        execution.completed_at = datetime.utcnow()
                        if hasattr(execution, 'calculate_duration'):
                            execution.calculate_duration()

                    if result:
                        execution.result = result
                    if error:
                        execution.error = error

                    db.commit()

                    # Publish notification
                    self._publish_notification(execution)

        except Exception as e:
            print(f"Failed to update execution status: {e}")

    def _publish_notification(self, execution: Execution):
        """Publish execution status update to Redis pub/sub"""
        try:
            redis_client = get_redis_client()
            channel = f"notifications:user:{execution.user_id}"

            notification_data = {
                "type": "execution_update",
                "execution_id": str(execution.id),
                "status": execution.status.value,
                "timestamp": datetime.utcnow().isoformat()
            }

            redis_client.publish(channel, json.dumps(notification_data))
        except Exception as e:
            print(f"Failed to publish notification: {e}")


@celery_app.task(base=ExecutionTask, bind=True, name="backend.src.workers.tasks.execute_crew")
def execute_crew(self, execution_id: str, crew_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a CrewAI crew.

    Args:
        execution_id: Execution queue record ID
        crew_id: Crew to execute
        payload: Execution parameters (inputs, config)

    Returns:
        Execution result
    """
    execution_uuid = UUID(execution_id)
    crew_uuid = UUID(crew_id)

    # Update status to running
    self._update_execution_status(execution_uuid, ExecutionStatus.RUNNING)

    # Initialize stream handler for live output
    from src.workers.stream_handler import StreamHandler
    stream_handler = StreamHandler(execution_id)

    try:
        # Import crew execution logic
        from src.services.crew_service import CrewService
        from fastapi import HTTPException

        with next(get_db()) as db:
            crew_service = CrewService(db)
            result = crew_service.execute_crew(
                crew_uuid,
                payload,
                execution_id=execution_uuid,
                stream_handler=stream_handler
            )

        return {
            "status": "success",
            "result": result,
            "execution_id": execution_id
        }

    except SoftTimeLimitExceeded:
        # Soft timeout - gracefully handle
        stream_handler.emit_error(
            error_type="TimeoutError",
            message="Execution exceeded time limit"
        )
        stream_handler.emit_completed(
            status="failed",
            result_summary="Execution exceeded time limit",
            artifacts=[]
        )
        self._update_execution_status(execution_uuid, ExecutionStatus.FAILED,
                                     error="Execution exceeded time limit (timeout)")
        raise

    except HTTPException as e:
        # Handle validation and business logic errors (don't retry)
        error_msg = e.detail if hasattr(e, 'detail') else str(e)
        stream_handler.emit_error(
            error_type="ValidationError" if e.status_code == 400 else "ExecutionError",
            message=error_msg
        )
        # Emit completion event so client knows execution is done
        stream_handler.emit_completed(
            status="failed",
            result_summary=f"Execution failed: {error_msg}",
            artifacts=[]
        )
        self._update_execution_status(execution_uuid, ExecutionStatus.FAILED,
                                     error=error_msg)
        # Return error response instead of raising (prevents retry)
        return {
            "status": "failed",
            "error": error_msg,
            "execution_id": execution_id
        }

    except Exception as e:
        # Emit error event
        stream_handler.emit_error(
            error_type=type(e).__name__,
            message=str(e)
        )
        # Emit completion event so client knows execution failed
        stream_handler.emit_completed(
            status="failed",
            result_summary=f"Execution failed: {str(e)}",
            artifacts=[]
        )
        # Update status and raise for retry
        self._update_execution_status(execution_uuid, ExecutionStatus.FAILED,
                                     error=str(e))
        raise


@celery_app.task(base=ExecutionTask, bind=True, name="backend.src.workers.tasks.execute_flow")
def execute_flow(self, execution_id: str, flow_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a workflow.

    Args:
        execution_id: Execution queue record ID
        flow_id: Flow to execute
        payload: Execution parameters (variables, config)

    Returns:
        Execution result
    """
    execution_uuid = UUID(execution_id)
    flow_uuid = UUID(flow_id)

    # Update status to running
    self._update_execution_status(execution_uuid, ExecutionStatus.RUNNING)

    try:
        # Import flow execution dependencies
        from src.services.flow_service import FlowService
        from src.crewai.flow_executor import FlowExecutor
        from src.crewai.crew_factory import CrewFactory
        from src.crewai.agent_factory import AgentFactory
        from src.services.execution_events import ExecutionEventPublisher
        from src.services.llm_service import LLMService
        from src.services.docker_service import DockerService
        from src.crewai.tool_adapter import ToolAdapter
        from fastapi import HTTPException

        with next(get_db()) as db:
            # Initialize execution dependencies
            llm_service = LLMService(db)
            docker_service = DockerService()
            tool_adapter = ToolAdapter(docker_service)
            agent_factory = AgentFactory(llm_service, tool_adapter)
            crew_factory = CrewFactory(agent_factory)
            event_publisher = ExecutionEventPublisher()
            flow_executor = FlowExecutor(crew_factory, agent_factory, event_publisher)

            # Get flow
            flow_service = FlowService(db)
            flow = flow_service.get_flow(str(flow_uuid))

            # Execute flow
            input_data = payload.get("input_data", {})
            result = flow_executor.execute(flow, input_data)

        return {
            "status": "success",
            "result": result,
            "execution_id": execution_id
        }

    except SoftTimeLimitExceeded:
        self._update_execution_status(execution_uuid, ExecutionStatus.FAILED,
                                     error="Flow execution exceeded time limit (timeout)")
        raise

    except HTTPException as e:
        # Handle validation and business logic errors (don't retry)
        error_msg = e.detail if hasattr(e, 'detail') else str(e)
        self._update_execution_status(execution_uuid, ExecutionStatus.FAILED,
                                     error=error_msg)
        return {
            "status": "failed",
            "error": error_msg,
            "execution_id": execution_id
        }

    except Exception as e:
        self._update_execution_status(execution_uuid, ExecutionStatus.FAILED,
                                     error=str(e))
        raise


@celery_app.task(base=ExecutionTask, bind=True, name="backend.src.workers.tasks.execute_agent")
def execute_agent(self, execution_id: str, agent_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a single agent.

    Args:
        execution_id: Execution queue record ID
        agent_id: Agent to execute
        payload: Execution parameters

    Returns:
        Execution result
    """
    execution_uuid = UUID(execution_id)
    agent_uuid = UUID(agent_id)

    # Update status to running
    self._update_execution_status(execution_uuid, ExecutionStatus.RUNNING)

    try:
        # Import agent execution logic
        from services.agent_service import AgentService
        from fastapi import HTTPException

        with next(get_db()) as db:
            agent_service = AgentService(db)
            result = agent_service.execute_agent(agent_uuid, payload)

        return {
            "status": "success",
            "result": result,
            "execution_id": execution_id
        }

    except SoftTimeLimitExceeded:
        self._update_execution_status(execution_uuid, ExecutionStatus.FAILED,
                                     error="Agent execution exceeded time limit (timeout)")
        raise

    except HTTPException as e:
        # Handle validation and business logic errors (don't retry)
        error_msg = e.detail if hasattr(e, 'detail') else str(e)
        self._update_execution_status(execution_uuid, ExecutionStatus.FAILED,
                                     error=error_msg)
        return {
            "status": "failed",
            "error": error_msg,
            "execution_id": execution_id
        }

    except Exception as e:
        self._update_execution_status(execution_uuid, ExecutionStatus.FAILED,
                                     error=str(e))
        raise


@celery_app.task(base=ExecutionTask, bind=True, name="backend.src.workers.tasks.execute_task")
def execute_task(self, execution_id: str, task_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a single task.

    Args:
        execution_id: Execution queue record ID
        task_id: Task to execute
        payload: Execution parameters

    Returns:
        Execution result
    """
    execution_uuid = UUID(execution_id)
    task_uuid = UUID(task_id)

    # Update status to running
    self._update_execution_status(execution_uuid, ExecutionStatus.RUNNING)

    try:
        # Import task execution logic
        from services.task_service import TaskService
        from fastapi import HTTPException

        with next(get_db()) as db:
            task_service = TaskService(db)
            result = task_service.execute_task(task_uuid, payload)

        return {
            "status": "success",
            "result": result,
            "execution_id": execution_id
        }

    except SoftTimeLimitExceeded:
        self._update_execution_status(execution_uuid, ExecutionStatus.FAILED,
                                     error="Task execution exceeded time limit (timeout)")
        raise

    except HTTPException as e:
        # Handle validation and business logic errors (don't retry)
        error_msg = e.detail if hasattr(e, 'detail') else str(e)
        self._update_execution_status(execution_uuid, ExecutionStatus.FAILED,
                                     error=error_msg)
        return {
            "status": "failed",
            "error": error_msg,
            "execution_id": execution_id
        }

    except Exception as e:
        self._update_execution_status(execution_uuid, ExecutionStatus.FAILED,
                                     error=str(e))
        raise


@celery_app.task(base=ExecutionTask, bind=True, name="backend.src.workers.tasks.execute_tool")
def execute_tool(self, execution_id: str, tool_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a single tool.

    Args:
        execution_id: Execution queue record ID
        tool_id: Tool to execute
        payload: Tool parameters

    Returns:
        Tool execution result
    """
    execution_uuid = UUID(execution_id)
    tool_uuid = UUID(tool_id)

    # Update status to running
    self._update_execution_status(execution_uuid, ExecutionStatus.RUNNING)

    try:
        # Import tool execution logic
        from services.tool_service import ToolService
        from fastapi import HTTPException

        with next(get_db()) as db:
            tool_service = ToolService(db)
            result = tool_service.execute_tool(tool_uuid, payload)

        return {
            "status": "success",
            "result": result,
            "execution_id": execution_id
        }

    except SoftTimeLimitExceeded:
        self._update_execution_status(execution_uuid, ExecutionStatus.FAILED,
                                     error="Tool execution exceeded time limit (timeout)")
        raise

    except HTTPException as e:
        # Handle validation and business logic errors (don't retry)
        error_msg = e.detail if hasattr(e, 'detail') else str(e)
        self._update_execution_status(execution_uuid, ExecutionStatus.FAILED,
                                     error=error_msg)
        return {
            "status": "failed",
            "error": error_msg,
            "execution_id": execution_id
        }

    except Exception as e:
        self._update_execution_status(execution_uuid, ExecutionStatus.FAILED,
                                     error=str(e))
        raise


@celery_app.task(name="backend.src.workers.tasks.process_queued_executions")
def process_queued_executions():
    """
    Periodic task to process stuck executions in QUEUED status.

    This task finds executions that are in QUEUED status but have not been
    dispatched to Celery (no active task), and re-dispatches them.
    """
    try:
        from src.models.execution import Execution, ExecutionStatus
        from src.db import get_db
        from datetime import timedelta
        from src.workers.celery_app import celery_app as app

        with next(get_db()) as db:
            # Find executions in QUEUED status older than 30 seconds
            cutoff_time = datetime.utcnow() - timedelta(seconds=30)

            queued_executions = db.query(Execution).filter(
                Execution.status == ExecutionStatus.QUEUED,
                Execution.created_at < cutoff_time
            ).all()

            dispatched_count = 0
            for execution in queued_executions:
                # Check if task is already in Celery
                task_id = str(execution.id)
                task_result = app.AsyncResult(task_id)

                # If task doesn't exist or is in a terminal state, re-dispatch
                if task_result.state in ['PENDING', 'FAILURE', 'REVOKED', 'REJECTED']:
                    try:
                        # Map execution types to task names
                        task_name_map = {
                            "flow": "backend.src.workers.tasks.execute_flow",
                            "crew": "backend.src.workers.tasks.execute_crew",
                            "agent": "backend.src.workers.tasks.execute_agent",
                            "task": "backend.src.workers.tasks.execute_task",
                            "tool": "backend.src.workers.tasks.execute_tool"
                        }

                        execution_type_str = execution.execution_type.value if hasattr(execution.execution_type, 'value') else str(execution.execution_type)
                        task_name = task_name_map.get(execution_type_str)

                        if not task_name:
                            continue

                        # Determine entity_id based on execution type
                        entity_id = None
                        if execution.flow_id:
                            entity_id = execution.flow_id
                        elif execution.crew_id:
                            entity_id = execution.crew_id
                        elif execution.agent_id:
                            entity_id = execution.agent_id
                        elif execution.task_id:
                            entity_id = execution.task_id
                        elif execution.tool_id:
                            entity_id = execution.tool_id

                        if not entity_id:
                            continue

                        payload = {
                            "input_data": execution.input_data or {},
                            "timeout_seconds": execution.timeout_seconds or 600
                        }

                        # Re-dispatch to Celery with queue routing
                        app.send_task(
                            task_name,
                            args=[str(execution.id), str(entity_id), payload],
                            task_id=str(execution.id),
                            priority=execution.priority or 5,
                            queue="normal_priority",  # Route to normal_priority queue
                            soft_time_limit=execution.timeout_seconds or 600,
                            time_limit=(execution.timeout_seconds or 600) + 10
                        )

                        dispatched_count += 1
                        print(f"Re-dispatched execution {execution.id} ({execution.execution_type})")

                    except Exception as e:
                        print(f"Failed to re-dispatch execution {execution.id}: {e}")

            if dispatched_count > 0:
                print(f"Processed {dispatched_count} queued executions")

    except Exception as e:
        print(f"Error processing queued executions: {e}")


@celery_app.task(name="backend.src.workers.tasks.cleanup_old_metrics")
def cleanup_old_metrics(retention_days: int = 90):
    """
    Periodic task to clean up old execution metrics.

    Args:
        retention_days: Number of days to retain metrics (default: 90)
    """
    try:
        from src.models.execution_metrics import ExecutionMetrics
        from datetime import timedelta
        from sqlalchemy.exc import ProgrammingError
        import psycopg2

        with next(get_db()) as db:
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

            deleted_count = db.query(ExecutionMetrics).filter(
                ExecutionMetrics.timestamp < cutoff_date
            ).delete()

            db.commit()

            print(f"Cleaned up {deleted_count} old metric records")
            return {"deleted_count": deleted_count}

    except (ProgrammingError, psycopg2.errors.UndefinedTable) as e:
        # Table doesn't exist yet - skip cleanup silently
        if "execution_metrics" in str(e) and "does not exist" in str(e):
            return {"deleted_count": 0, "skipped": "table_not_exists"}
        # Re-raise other programming errors
        print(f"Failed to cleanup old metrics: {e}")
        return {"error": str(e)}

    except Exception as e:
        print(f"Failed to cleanup old metrics: {e}")
        return {"error": str(e)}
