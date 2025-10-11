"""Execution service for managing flow and crew runs."""

from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import asyncio

from ..models import Execution, Flow
from ..models.execution import ExecutionType, ExecutionStatus
from ..schemas.executions import ExecutionCreate, ExecutionResponse
from ..services.flow_service import FlowService
from ..crewai.flow_executor import FlowExecutor


class ExecutionService:
    """Service for execution lifecycle management."""

    def __init__(
        self,
        db: Session,
        flow_service: FlowService,
        flow_executor: FlowExecutor,
    ):
        self.db = db
        self.flow_service = flow_service
        self.flow_executor = flow_executor

    def create_execution(
        self,
        execution_type: str,
        user_id: int,
        input_data: dict,
        flow_id: int = None,
        crew_id: int = None,
    ) -> Execution:
        """
        Create a new execution (synchronous version for direct calls).

        Args:
            execution_type: Type of execution
            user_id: User initiating the execution
            input_data: Input data
            flow_id: Optional flow ID
            crew_id: Optional crew ID

        Returns:
            Created Execution model
        """
        execution = Execution(
            execution_type=execution_type,
            status="pending",
            flow_id=flow_id,
            crew_id=crew_id,
            user_id=user_id,
            input_data=input_data,
        )

        self.db.add(execution)
        self.db.commit()
        self.db.refresh(execution)

        return execution

    async def create_execution_async(
        self, data: ExecutionCreate, user_id: int
    ) -> Execution:
        """
        Create a new execution (async version for flow executor).

        Args:
            data: Execution creation data
            user_id: User initiating the execution

        Returns:
            Created Execution model
        """
        # Validate flow can be executed
        if data.flow_id and self.flow_service:
            await self.flow_service.check_can_execute(data.flow_id)

        execution = Execution(
            execution_type=data.execution_type,
            status="pending",
            flow_id=data.flow_id,
            crew_id=data.crew_id,
            user_id=user_id,
            input_data=data.input_data,
        )

        self.db.add(execution)
        self.db.commit()
        self.db.refresh(execution)

        # Start execution asynchronously regardless of type
        asyncio.create_task(self._execute_async(execution.id))

        return execution

    async def get_execution(self, execution_id: int) -> Execution:
        """Get execution by ID."""
        execution = (
            self.db.query(Execution).filter(Execution.id == execution_id).first()
        )

        if not execution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Execution not found",
            )

        return execution

    async def list_executions(
        self,
        user_id: Optional[int] = None,
        flow_id: Optional[int] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> dict:
        """List executions with filtering and pagination."""
        query = self.db.query(Execution)

        if user_id:
            query = query.filter(Execution.user_id == user_id)
        if flow_id:
            query = query.filter(Execution.flow_id == flow_id)
        if status:
            query = query.filter(Execution.status == status)

        total = query.count()
        offset = (page - 1) * page_size
        executions = query.offset(offset).limit(page_size).all()

        return {
            "executions": [ExecutionResponse.from_orm(e) for e in executions],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def cancel_execution(self, execution_id: int) -> Execution:
        """Cancel a running execution."""
        execution = await self.get_execution(execution_id)
        # Event publisher for SSE
        from ..services.execution_events import ExecutionEventPublisher
        event_publisher = ExecutionEventPublisher()

        if execution.status not in ["pending", "running"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel execution with status: {execution.status}",
            )

        execution.status = "cancelled"
        self.db.commit()
        self.db.refresh(execution)

        # Send cancellation signal to running task
        # Publish cancellation event via Redis for background workers to pick up
        from ..services.execution_events import ExecutionEventPublisher
        event_publisher = ExecutionEventPublisher()
        await event_publisher.publish_cancellation(execution_id)

        return execution

    async def _execute_async(self, execution_id: int) -> None:
        """
        Execute a flow/crew asynchronously.

        Args:
            execution_id: Execution ID to run
        """
        execution = await self.get_execution(execution_id)

        try:
            # Update status to running
            execution.status = "running"
            self.db.commit()
            # Publish execution started event (best-effort)
            try:
                await event_publisher.publish_execution_started(execution_id, execution.input_data or {})
            except Exception:
                pass

            if execution.execution_type == "flow":
                # Execute flow
                flow = await self.flow_service.get_flow(execution.flow_id)
                output = await self.flow_executor.execute_flow(
                    flow=flow,
                    execution=execution,
                    input_data=execution.input_data,
                )

                # Update execution with output
                execution.output_data = output
                execution.status = "completed"
                # Publish completion event and notification
                try:
                    await event_publisher.publish_execution_completed(execution_id, output or {})
                except Exception:
                    pass
                try:
                    from .notification_service import NotificationService
                    from .notification_events import NotificationPublisher
                    from ..schemas.notifications import NotificationCreate
                    ns = NotificationService(self.db)
                    title = f"Flow #{execution.flow_id} completed"
                    n = await ns.create_notification(
                        user_id=execution.user_id,
                        tenant_id=getattr(getattr(flow, 'tenant', None), 'id', None) or getattr(flow, 'tenant_id', 1),
                        data=NotificationCreate(
                            type="success",
                            title=title,
                            message="The flow execution finished successfully.",
                            data={"execution_id": execution.id, "type": "flow"},
                        ),
                    )
                    NotificationPublisher().publish(execution.user_id, {
                        "type": "success",
                        "title": title,
                        "message": "The flow execution finished successfully.",
                        "data": {"execution_id": execution.id, "type": "flow"},
                    })
                except Exception:
                    pass
                try:
                    await event_publisher.publish_execution_completed(execution_id, execution.output_data or {})
                except Exception:
                    pass

            elif execution.execution_type == "crew":
                # Execute crew directly (without flow)
                import time
                from ..services.llm_service import LLMService
                from ..services.docker_service import DockerService
                from ..services.task_service import TaskService
                from ..services.crew_service import CrewService
                from ..crewai.tool_adapter import ToolAdapter
                from ..crewai.agent_factory import AgentFactory
                from ..crewai.crew_factory import CrewFactory
                from ..models.agent import Agent

                start_time = time.time()

                # Load crew model
                crew_service = CrewService(self.db)
                crew_model = await crew_service.get_crew(execution.crew_id)

                # Initialize dependencies
                llm_service = LLMService(self.db)
                docker_service = DockerService()
                tool_adapter = ToolAdapter(docker_service)
                agent_factory = AgentFactory(llm_service, tool_adapter)
                crew_factory = CrewFactory(agent_factory)

                # Create CrewAI crew
                crewai_crew = await crew_factory.from_db_model(crew_model)

                # Build tasks
                task_service = TaskService(self.db)
                stored_tasks = await task_service.get_crew_tasks(execution.crew_id)

                variables = {}
                try:
                    variables = execution.input_data.get('variables', {}) if isinstance(execution.input_data, dict) else {}
                except Exception:
                    variables = {}

                def substitute_variables(text: str, vars: dict) -> str:
                    if not text or not vars:
                        return text
                    result = text
                    for k, v in vars.items():
                        result = result.replace(f'{{{k}}}', str(v))
                    return result

                from crewai import Task as CrewTask
                import json

                tasks: list = []
                task_map: dict = {}

                if stored_tasks:
                    for db_task in stored_tasks:
                        # Resolve agent
                        agent_instance = None
                        if db_task.agent_id:
                            agent_model = self.db.query(Agent).filter(Agent.id == db_task.agent_id).first()
                            if agent_model:
                                agent_instance = await agent_factory.from_db_model(agent_model)
                        else:
                            agents = getattr(crewai_crew, 'agents', [])
                            agent_instance = agents[0] if agents else None

                        # Context refs
                        context_tasks = []
                        if db_task.context:
                            try:
                                context_data = json.loads(db_task.context) if isinstance(db_task.context, str) else db_task.context
                                if isinstance(context_data, dict) and 'task_ids' in context_data:
                                    for tid in context_data['task_ids']:
                                        if tid in task_map:
                                            context_tasks.append(task_map[tid])
                            except Exception:
                                pass

                        # Tools (basic: reuse agent tools if any)
                        task_tools = []
                        if db_task.tools_config and agent_instance and hasattr(agent_instance, 'tools'):
                            task_tools = agent_instance.tools

                        description = substitute_variables(db_task.description, variables)
                        expected_output = substitute_variables(db_task.expected_output, variables)

                        task_kwargs = {
                            'description': description,
                            'agent': agent_instance,
                            'expected_output': expected_output,
                            'async_execution': db_task.async_execution,
                        }
                        if context_tasks:
                            task_kwargs['context'] = context_tasks
                        if task_tools:
                            task_kwargs['tools'] = task_tools
                        if db_task.output_file:
                            task_kwargs['output_file'] = db_task.output_file

                        t = CrewTask(**task_kwargs)
                        tasks.append(t)
                        task_map[db_task.id] = t
                else:
                    # Dynamic tasks from input
                    tasks_input = []
                    try:
                        tasks_input = execution.input_data.get('tasks', []) if isinstance(execution.input_data, dict) else []
                    except Exception:
                        tasks_input = []
                    if not tasks_input:
                        tasks_input = ['Complete the assigned objectives as a team']

                    agents = getattr(crewai_crew, 'agents', [])
                    for i, task_desc in enumerate(tasks_input):
                        agent_instance = agents[i % len(agents)] if agents else None
                        t = CrewTask(
                            description=task_desc,
                            agent=agent_instance,
                            expected_output=f"Completion of: {task_desc}",
                        )
                        tasks.append(t)

                crewai_crew.tasks = tasks

                # Execute crew (synchronously)
                result = crewai_crew.kickoff()

                # Update execution
                execution.output_data = {"output": str(result), "task_count": len(tasks)}
                execution.execution_time_ms = int((time.time() - start_time) * 1000)
                execution.status = "completed"
                try:
                    await event_publisher.publish_execution_completed(execution_id, execution.output_data or {})
                except Exception:
                    pass
                try:
                    from .notification_service import NotificationService
                    from .notification_events import NotificationPublisher
                    from ..schemas.notifications import NotificationCreate
                    ns = NotificationService(self.db)
                    title = f"Crew #{execution.crew_id} completed"
                    n = await ns.create_notification(
                        user_id=execution.user_id,
                        tenant_id=getattr(getattr(crew_model, 'tenant', None), 'id', None) if 'crew_model' in locals() else 1,
                        data=NotificationCreate(
                            type="success",
                            title=title,
                            message="The crew execution finished successfully.",
                            data={"execution_id": execution.id, "type": "crew"},
                        ),
                    )
                    NotificationPublisher().publish(execution.user_id, {
                        "type": "success",
                        "title": title,
                        "message": "The crew execution finished successfully.",
                        "data": {"execution_id": execution.id, "type": "crew"},
                    })
                except Exception:
                    pass
                try:
                    await event_publisher.publish_execution_completed(execution_id, execution.output_data or {})
                except Exception:
                    pass

            else:
                raise ValueError(f"Unknown execution type: {execution.execution_type}")

        except Exception as e:
            # Execution failed
            execution.status = "failed"
            execution.error = str(e)
            try:
                await event_publisher.publish_execution_failed(execution_id, execution.error)
            except Exception:
                pass
            # Send failure notification
            try:
                from .notification_service import NotificationService
                from .notification_events import NotificationPublisher
                from ..schemas.notifications import NotificationCreate
                ns = NotificationService(self.db)
                what = execution.execution_type
                title = f"{what.capitalize()} execution failed"
                _ = await ns.create_notification(
                    user_id=execution.user_id,
                    tenant_id=1,
                    data=NotificationCreate(
                        type="error",
                        title=title,
                        message=execution.error,
                        data={"execution_id": execution.id, "type": execution.execution_type},
                    ),
                )
                NotificationPublisher().publish(execution.user_id, {
                    "type": "error",
                    "title": title,
                    "message": execution.error,
                    "data": {"execution_id": execution.id, "type": execution.execution_type},
                })
            except Exception:
                pass
            try:
                await event_publisher.publish_execution_failed(execution_id, execution.error)
            except Exception:
                pass

        finally:
            self.db.commit()

    def create_agent_execution(
        self,
        agent_id: int,
        user_id: int,
        input_data: Dict[str, Any],
    ) -> Execution:
        """Create execution record for agent execution."""
        execution = Execution(
            execution_type=ExecutionType.AGENT.value,
            status=ExecutionStatus.PENDING.value,
            agent_id=agent_id,
            user_id=user_id,
            input_data=input_data,
        )
        self.db.add(execution)
        self.db.commit()
        self.db.refresh(execution)
        return execution

    def create_tool_execution(
        self,
        tool_id: int,
        user_id: int,
        input_data: Dict[str, Any],
    ) -> Execution:
        """Create execution record for tool execution."""
        execution = Execution(
            execution_type=ExecutionType.TOOL.value,
            status=ExecutionStatus.PENDING.value,
            tool_id=tool_id,
            user_id=user_id,
            input_data=input_data,
        )
        self.db.add(execution)
        self.db.commit()
        self.db.refresh(execution)
        return execution

    def create_task_execution(
        self,
        task_id: int,
        user_id: int,
        input_data: Dict[str, Any],
    ) -> Execution:
        """Create execution record for task execution."""
        execution = Execution(
            execution_type=ExecutionType.TASK.value,
            status=ExecutionStatus.PENDING.value,
            task_id=task_id,
            user_id=user_id,
            input_data=input_data,
        )
        self.db.add(execution)
        self.db.commit()
        self.db.refresh(execution)
        return execution

    def update_execution_status(
        self,
        execution_id: int,
        status: ExecutionStatus,
        output_data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        execution_time_ms: Optional[int] = None,
    ) -> Execution:
        """Update execution status and results."""
        execution = self.db.query(Execution).filter(Execution.id == execution_id).first()
        if not execution:
            raise ValueError(f"Execution {execution_id} not found")

        execution.status = status.value if isinstance(status, ExecutionStatus) else status
        if output_data is not None:
            execution.output_data = output_data
        if error is not None:
            execution.error = error
        if execution_time_ms is not None:
            execution.execution_time_ms = execution_time_ms

        self.db.commit()
        self.db.refresh(execution)
        return execution
