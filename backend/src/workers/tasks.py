"""
Celery tasks for async execution of crews, flows, agents, and tasks.

Each task:
1. Updates execution_queue status: pending → running
2. Calls CrewAI SDK or execution logic
3. Saves result to execution_queue
4. Updates status: running → completed/failed/timeout
5. Publishes notification via Redis pub/sub
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID
from celery import Task
from celery.exceptions import SoftTimeLimitExceeded

from .celery_app import celery_app
from ..db import get_db
from ..models.execution_queue import ExecutionQueue, ExecutionStatus
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
        """Update execution queue record"""
        try:
            with next(get_db()) as db:
                execution = db.query(ExecutionQueue).filter(
                    ExecutionQueue.execution_id == execution_id
                ).first()

                if execution:
                    execution.status = status

                    if status == ExecutionStatus.RUNNING:
                        execution.started_at = datetime.utcnow()
                    elif status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.TIMEOUT]:
                        execution.completed_at = datetime.utcnow()
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

    def _publish_notification(self, execution: ExecutionQueue):
        """Publish execution status update to Redis pub/sub"""
        try:
            redis_client = get_redis_client()
            channel = f"notifications:user:{execution.user_id}"

            notification_data = {
                "type": "execution_update",
                "execution_id": str(execution.execution_id),
                "status": execution.status.value,
                "timestamp": datetime.utcnow().isoformat()
            }

            redis_client.publish(channel, str(notification_data))
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

    try:
        # Import crew execution logic
        from services.crew_service import CrewService

        with next(get_db()) as db:
            crew_service = CrewService(db)
            result = crew_service.execute_crew(crew_uuid, payload)

        return {
            "status": "success",
            "result": result,
            "execution_id": execution_id
        }

    except SoftTimeLimitExceeded:
        # Soft timeout - gracefully handle
        self._update_execution_status(execution_uuid, ExecutionStatus.TIMEOUT,
                                     error="Execution exceeded time limit")
        raise

    except Exception as e:
        # Task will be retried automatically
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
        # Import flow execution logic
        from services.flow_service import FlowService

        with next(get_db()) as db:
            flow_service = FlowService(db)
            result = flow_service.execute_flow(flow_uuid, payload)

        return {
            "status": "success",
            "result": result,
            "execution_id": execution_id
        }

    except SoftTimeLimitExceeded:
        self._update_execution_status(execution_uuid, ExecutionStatus.TIMEOUT,
                                     error="Flow execution exceeded time limit")
        raise

    except Exception as e:
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

        with next(get_db()) as db:
            agent_service = AgentService(db)
            result = agent_service.execute_agent(agent_uuid, payload)

        return {
            "status": "success",
            "result": result,
            "execution_id": execution_id
        }

    except SoftTimeLimitExceeded:
        self._update_execution_status(execution_uuid, ExecutionStatus.TIMEOUT,
                                     error="Agent execution exceeded time limit")
        raise

    except Exception as e:
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

        with next(get_db()) as db:
            task_service = TaskService(db)
            result = task_service.execute_task(task_uuid, payload)

        return {
            "status": "success",
            "result": result,
            "execution_id": execution_id
        }

    except SoftTimeLimitExceeded:
        self._update_execution_status(execution_uuid, ExecutionStatus.TIMEOUT,
                                     error="Task execution exceeded time limit")
        raise

    except Exception as e:
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

        with next(get_db()) as db:
            tool_service = ToolService(db)
            result = tool_service.execute_tool(tool_uuid, payload)

        return {
            "status": "success",
            "result": result,
            "execution_id": execution_id
        }

    except SoftTimeLimitExceeded:
        self._update_execution_status(execution_uuid, ExecutionStatus.TIMEOUT,
                                     error="Tool execution exceeded time limit")
        raise

    except Exception as e:
        raise


@celery_app.task(name="backend.src.workers.tasks.cleanup_old_metrics")
def cleanup_old_metrics(retention_days: int = 90):
    """
    Periodic task to clean up old execution metrics.

    Args:
        retention_days: Number of days to retain metrics (default: 90)
    """
    try:
        from models.execution_metrics import ExecutionMetrics
        from datetime import timedelta

        with next(get_db()) as db:
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

            deleted_count = db.query(ExecutionMetrics).filter(
                ExecutionMetrics.timestamp < cutoff_date
            ).delete()

            db.commit()

            print(f"Cleaned up {deleted_count} old metric records")
            return {"deleted_count": deleted_count}

    except Exception as e:
        print(f"Failed to cleanup old metrics: {e}")
        return {"error": str(e)}
