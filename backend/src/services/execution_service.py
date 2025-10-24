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
from ..integrations.langfuse import CrewAILangfuseHandler


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
        # Initialize event publisher (best-effort)
        try:
            from ..services.execution_events import ExecutionEventPublisher
            event_publisher = ExecutionEventPublisher()
        except Exception:
            event_publisher = None

        if execution.status not in ["pending", "running"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel execution with status: {execution.status}",
            )

        execution.status = "cancelled"
        self.db.commit()
        self.db.refresh(execution)

        # Publish cancellation event via Redis (best-effort)
        if event_publisher:
            try:
                await event_publisher.publish_cancellation(execution_id)
            except Exception:
                pass

        return execution

    async def _execute_async(self, execution_id: int) -> None:
        """
        Execute a flow/crew asynchronously using a fresh DB session.

        Args:
            execution_id: Execution ID to run
        """
        from ..db.postgres import SessionLocal
        from ..models.execution import Execution as ExecutionModel

        db = SessionLocal()
        try:
            execution = db.query(ExecutionModel).filter(ExecutionModel.id == execution_id).first()
            if not execution:
                return

            # Prepare event publisher (do not fail execution if Redis is unavailable)
            try:
                from ..services.execution_events import ExecutionEventPublisher
                event_publisher = ExecutionEventPublisher()
            except Exception:
                event_publisher = None

            # Mark running
            execution.status = "running"
            db.commit()

            if event_publisher:
                try:
                    await event_publisher.publish_execution_started(execution_id, execution.input_data or {})
                except Exception:
                    pass

            if execution.execution_type == "flow":
                import time
                from uuid import UUID
                from ..models.user import User

                start_time = time.time()

                # Get tenant_id for Langfuse handler
                user = db.query(User).filter(User.id == execution.user_id).first()
                tenant_id = UUID(str(user.tenant_id)) if user and user.tenant_id else None

                # Initialize Langfuse handler for tracing (graceful degradation if disabled)
                langfuse_handler = None
                if tenant_id:
                    try:
                        langfuse_handler = CrewAILangfuseHandler(
                            execution_id=UUID(str(execution.id)),
                            tenant_id=tenant_id,
                            enable_async=True
                        )
                    except Exception as e:
                        print(f"Warning: Failed to initialize Langfuse handler: {e}")

                # Build services tied to this DB session
                from ..services.flow_service import FlowService
                from ..services.llm_service import LLMService
                from ..services.docker_service import DockerService
                from ..crewai.tool_adapter import ToolAdapter
                from ..crewai.agent_factory import AgentFactory
                from ..crewai.crew_factory import CrewFactory
                from ..crewai.flow_executor import FlowExecutor
                flow_service = FlowService(db)
                llm_service = LLMService(db)
                docker_service = DockerService()
                tool_adapter = ToolAdapter(docker_service)
                agent_factory = AgentFactory(llm_service, tool_adapter)
                crew_factory = CrewFactory(agent_factory)
                flow_executor = FlowExecutor(crew_factory, agent_factory, event_publisher)

                flow = await flow_service.get_flow(execution.flow_id)
                output = await flow_executor.execute_flow(
                    flow=flow,
                    execution=execution,
                    input_data=execution.input_data,
                    langfuse_handler=langfuse_handler,
                )

                execution.output_data = output
                execution.execution_time_ms = int((time.time() - start_time) * 1000)
                execution.status = "completed"
                db.commit()

                # Flush Langfuse traces and verify overhead requirement (FR-021: <2%)
                if langfuse_handler:
                    try:
                        await langfuse_handler.flush()
                        overhead_pct = langfuse_handler.get_overhead_percentage(execution.execution_time_ms)
                        if overhead_pct >= 2.0:
                            print(f"Warning: Langfuse overhead {overhead_pct:.2f}% exceeds 2% requirement (FR-021)")
                    except Exception as e:
                        print(f"Warning: Failed to flush Langfuse traces: {e}")

                if event_publisher:
                    try:
                        await event_publisher.publish_execution_completed(execution_id, output or {})
                    except Exception:
                        pass
                # Notification (best-effort)
                try:
                    from .notification_service import NotificationService
                    from .notification_events import NotificationPublisher
                    from ..schemas.notifications import NotificationCreate
                    ns = NotificationService(db)
                    title = f"Flow #{execution.flow_id} completed"
                    # Get tenant_id from user
                    from ..models.user import User
                    user = db.query(User).filter(User.id == execution.user_id).first()
                    tenant_id_val = user.tenant_id if user else None
                    _ = await ns.create_notification(
                        user_id=execution.user_id,
                        tenant_id=tenant_id_val,
                        data=NotificationCreate(
                            type="success",
                            title=title,
                            message="The flow execution finished successfully.",
                            data={"execution_id": str(execution.id), "type": "flow"},
                        ),
                    )
                    NotificationPublisher().publish(execution.user_id, {
                        "type": "success",
                        "title": title,
                        "message": "The flow execution finished successfully.",
                        "data": {"execution_id": str(execution.id), "type": "flow"},
                    })
                except Exception:
                    pass

            elif execution.execution_type == "crew":
                import time, json
                from uuid import UUID
                from ..services.llm_service import LLMService
                from ..services.docker_service import DockerService
                from ..services.task_service import TaskService
                from ..services.crew_service import CrewService
                from ..crewai.tool_adapter import ToolAdapter
                from ..crewai.agent_factory import AgentFactory
                from ..crewai.crew_factory import CrewFactory
                from ..models.agent import Agent
                from ..models.user import User

                start_time = time.time()
                crew_service = CrewService(db)
                crew_model = await crew_service.get_crew(execution.crew_id)

                # Get tenant_id for Langfuse handler
                user = db.query(User).filter(User.id == execution.user_id).first()
                tenant_id = UUID(str(user.tenant_id)) if user and user.tenant_id else None

                # Initialize Langfuse handler for tracing (graceful degradation if disabled)
                langfuse_handler = None
                if tenant_id:
                    try:
                        langfuse_handler = CrewAILangfuseHandler(
                            execution_id=UUID(str(execution.id)),
                            tenant_id=tenant_id,
                            enable_async=True
                        )
                    except Exception as e:
                        print(f"Warning: Failed to initialize Langfuse handler: {e}")

                llm_service = LLMService(db)
                docker_service = DockerService()
                tool_adapter = ToolAdapter(docker_service)
                agent_factory = AgentFactory(llm_service, tool_adapter)
                crew_factory = CrewFactory(agent_factory)
                crewai_crew = await crew_factory.from_db_model(crew_model, langfuse_handler=langfuse_handler)

                task_service = TaskService(db)
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
                tasks: list = []
                task_map: dict = {}
                if stored_tasks:
                    for db_task in stored_tasks:
                        agent_instance = None
                        if db_task.agent_id:
                            agent_model = db.query(Agent).filter(Agent.id == db_task.agent_id).first()
                            if agent_model:
                                agent_instance = await agent_factory.from_db_model(agent_model)
                        else:
                            agents = getattr(crewai_crew, 'agents', [])
                            agent_instance = agents[0] if agents else None

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
                result = await asyncio.to_thread(crewai_crew.kickoff)

                execution.output_data = {"output": str(result), "task_count": len(tasks)}
                execution.execution_time_ms = int((time.time() - start_time) * 1000)
                execution.status = "completed"
                db.commit()

                # Flush Langfuse traces and verify overhead requirement (FR-021: <2%)
                if langfuse_handler:
                    try:
                        await langfuse_handler.flush()
                        overhead_pct = langfuse_handler.get_overhead_percentage(execution.execution_time_ms)
                        if overhead_pct >= 2.0:
                            print(f"Warning: Langfuse overhead {overhead_pct:.2f}% exceeds 2% requirement (FR-021)")
                    except Exception as e:
                        print(f"Warning: Failed to flush Langfuse traces: {e}")

                if event_publisher:
                    try:
                        await event_publisher.publish_execution_completed(execution_id, execution.output_data or {})
                    except Exception:
                        pass
                try:
                    from .notification_service import NotificationService
                    from .notification_events import NotificationPublisher
                    from ..schemas.notifications import NotificationCreate
                    ns = NotificationService(db)
                    title = f"Crew #{execution.crew_id} completed"
                    # Get tenant_id from user
                    from ..models.user import User
                    user = db.query(User).filter(User.id == execution.user_id).first()
                    tenant_id_val = user.tenant_id if user else None
                    _ = await ns.create_notification(
                        user_id=execution.user_id,
                        tenant_id=tenant_id_val,
                        data=NotificationCreate(
                            type="success",
                            title=title,
                            message="The crew execution finished successfully.",
                            data={"execution_id": str(execution.id), "type": "crew"},
                        ),
                    )
                    NotificationPublisher().publish(execution.user_id, {
                        "type": "success",
                        "title": title,
                        "message": "The crew execution finished successfully.",
                        "data": {"execution_id": str(execution.id), "type": "crew"},
                    })
                except Exception:
                    pass

            else:
                raise ValueError(f"Unknown execution type: {execution.execution_type}")

        except Exception as e:
            # Update to failed and notify
            try:
                execution = db.query(ExecutionModel).filter(ExecutionModel.id == execution_id).first()
                if execution:
                    execution.status = "failed"
                    execution.error = str(e)
                    db.commit()
                    if 'event_publisher' in locals() and event_publisher:
                        try:
                            await event_publisher.publish_execution_failed(execution_id, execution.error)
                        except Exception:
                            pass
                    try:
                        from .notification_service import NotificationService
                        from .notification_events import NotificationPublisher
                        from ..schemas.notifications import NotificationCreate
                        ns = NotificationService(db)
                        title = f"{str(execution.execution_type).capitalize()} execution failed"
                        # Get tenant_id from user
                        from ..models.user import User
                        user = db.query(User).filter(User.id == execution.user_id).first()
                        tenant_id_val = user.tenant_id if user else None
                        _ = await ns.create_notification(
                            user_id=execution.user_id,
                            tenant_id=tenant_id_val,
                            data=NotificationCreate(
                                type="error",
                                title=title,
                                message=str(e),
                                data={"execution_id": str(execution.id), "type": execution.execution_type},
                            ),
                        )
                        NotificationPublisher().publish(execution.user_id, {
                            "type": "error",
                            "title": title,
                            "message": str(e),
                            "data": {"execution_id": str(execution.id), "type": execution.execution_type},
                        })
                    except Exception:
                        pass
            except Exception:
                pass
        finally:
            try:
                db.close()
            except Exception:
                pass

    def create_agent_execution(
        self,
        agent_id,  # UUID
        user_id,  # UUID
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

    async def execute_agent_async(
        self,
        agent_id,  # UUID
        user_id,  # UUID
        input_data: Dict[str, Any],
    ) -> Execution:
        """Create and execute agent asynchronously."""
        # Create execution record
        execution = self.create_agent_execution(agent_id, user_id, input_data)

        # Start execution in background
        asyncio.create_task(self._execute_agent_async(execution.id, agent_id, input_data))

        return execution

    async def _execute_agent_async(self, execution_id: int, agent_id, input_data: Dict[str, Any]) -> None:
        """Execute agent in background."""
        import time
        from uuid import UUID
        from ..services.llm_service import LLMService
        from ..services.docker_service import DockerService
        from ..services.agent_service import AgentService
        from ..crewai.tool_adapter import ToolAdapter
        from ..crewai.agent_factory import AgentFactory
        from crewai import Crew, Task
        from ..db.postgres import SessionLocal
        from ..models.user import User

        # Create a new database session for this background task
        db = SessionLocal()

        try:
            execution = db.query(Execution).filter(Execution.id == execution_id).first()
            if not execution:
                return

            start_time = time.time()

            # Update to running
            execution.status = ExecutionStatus.RUNNING.value
            db.commit()

            # Get agent
            agent_service = AgentService(db)
            agent = await agent_service.get_agent(agent_id)

            # Get tenant_id for Langfuse handler
            user = db.query(User).filter(User.id == execution.user_id).first()
            tenant_id = UUID(str(user.tenant_id)) if user and user.tenant_id else None

            # Initialize Langfuse handler for tracing (graceful degradation if disabled)
            langfuse_handler = None
            if tenant_id:
                try:
                    langfuse_handler = CrewAILangfuseHandler(
                        execution_id=UUID(str(execution.id)),
                        tenant_id=tenant_id,
                        enable_async=True
                    )
                except Exception as e:
                    print(f"Warning: Failed to initialize Langfuse handler: {e}")

            # Initialize dependencies
            llm_service = LLMService(db)
            docker_service = DockerService()
            tool_adapter = ToolAdapter(docker_service)
            agent_factory = AgentFactory(llm_service, tool_adapter)

            # Get provider override if specified
            provider_id_override = input_data.get('provider_id')

            # Create CrewAI agent with Langfuse handler
            crewai_agent = await agent_factory.from_db_model(
                agent,
                provider_id_override,
                langfuse_handler=langfuse_handler
            )

            # Helper function to substitute variables
            def substitute_variables(text: str, vars: dict) -> str:
                if not text or not vars:
                    return text
                result = text
                for key, value in vars.items():
                    result = result.replace(f'{{{key}}}', str(value))
                return result

            # Get variables
            variables = input_data.get('variables', {})

            # Get task description
            task_description = None
            expected_output = None

            if 'task_id' in input_data:
                from ..services.task_service import TaskService
                task_service = TaskService(db)
                db_task = await task_service.get_task(input_data['task_id'])
                task_description = substitute_variables(db_task.description, variables)
                expected_output = substitute_variables(db_task.expected_output, variables)
            else:
                task_description = substitute_variables(
                    input_data.get('task', 'Perform your assigned task'),
                    variables
                )
                expected_output = substitute_variables(
                    input_data.get('expected_output', 'A detailed response to the task'),
                    variables
                )

            # Create task and crew
            task = Task(
                description=task_description,
                agent=crewai_agent,
                expected_output=expected_output
            )

            crew = Crew(
                agents=[crewai_agent],
                tasks=[task],
                verbose=True
            )

            # Execute in a separate thread to avoid blocking the event loop
            result = await asyncio.to_thread(crew.kickoff)
            execution_time_ms = int((time.time() - start_time) * 1000)

            # Update to completed
            execution.status = ExecutionStatus.COMPLETED.value
            execution.output_data = {"output": str(result)}
            execution.execution_time_ms = execution_time_ms
            db.commit()

            # Flush Langfuse traces and verify overhead requirement (FR-021: <2%)
            if langfuse_handler:
                try:
                    await langfuse_handler.flush()
                    overhead_pct = langfuse_handler.get_overhead_percentage(execution_time_ms)
                    if overhead_pct >= 2.0:
                        print(f"Warning: Langfuse overhead {overhead_pct:.2f}% exceeds 2% requirement (FR-021)")
                except Exception as e:
                    print(f"Warning: Failed to flush Langfuse traces: {e}")

            # Send success notification
            try:
                from .notification_service import NotificationService
                from .notification_events import NotificationPublisher
                from ..schemas.notifications import NotificationCreate
                ns = NotificationService(db)
                title = f"Agent #{agent_id} completed"
                await ns.create_notification(
                    user_id=execution.user_id,
                    tenant_id=getattr(agent, 'tenant_id', 1),
                    data=NotificationCreate(
                        type="success",
                        title=title,
                        message="Agent run finished successfully.",
                        data={"execution_id": str(execution.id), "type": "agent"},
                    ),
                )
                NotificationPublisher().publish(execution.user_id, {
                    "type": "success",
                    "title": title,
                    "message": "Agent run finished successfully.",
                    "data": {"execution_id": str(execution.id), "type": "agent"},
                })
            except Exception:
                pass

        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            execution.status = ExecutionStatus.FAILED.value
            execution.error = str(e)
            execution.execution_time_ms = execution_time_ms
            db.commit()

            # Send failure notification
            try:
                from .notification_service import NotificationService
                from .notification_events import NotificationPublisher
                from ..schemas.notifications import NotificationCreate
                ns = NotificationService(db)
                title = f"Agent #{agent_id} failed"
                await ns.create_notification(
                    user_id=execution.user_id,
                    tenant_id=1,
                    data=NotificationCreate(
                        type="error",
                        title=title,
                        message=str(e),
                        data={"execution_id": str(execution.id), "type": "agent"},
                    ),
                )
                NotificationPublisher().publish(execution.user_id, {
                    "type": "error",
                    "title": title,
                    "message": str(e),
                    "data": {"execution_id": str(execution.id), "type": "agent"},
                })
            except Exception:
                pass
        finally:
            # Close the database session
            db.close()

    def create_tool_execution(
        self,
        tool_id,
        user_id,
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

    async def execute_tool_async(
        self,
        tool_id,
        user_id,
        input_data: Dict[str, Any],
    ) -> Execution:
        """Create and execute tool asynchronously."""
        # Create execution record
        execution = self.create_tool_execution(tool_id, user_id, input_data)

        # Start execution in background
        asyncio.create_task(self._execute_tool_async(execution.id, tool_id, input_data))

        return execution

    async def _execute_tool_async(self, execution_id: int, tool_id, input_data: Dict[str, Any]) -> None:
        """Execute tool in background."""
        import time
        from ..services.tool_service import ToolService
        from ..db.postgres import SessionLocal

        # Create a new database session for this background task
        db = SessionLocal()

        try:
            execution = db.query(Execution).filter(Execution.id == execution_id).first()
            if not execution:
                return

            start_time = time.time()

            try:
                # Update to running
                execution.status = ExecutionStatus.RUNNING.value
                db.commit()

                # Get tool
                tool_service = ToolService(db)
                tool = await tool_service.get_tool(tool_id)

                result = None

                if tool.tool_type == "custom":
                    # Execute custom Python tool
                    import sys
                    import site
                    user_site = site.getusersitepackages()
                    if user_site not in sys.path:
                        sys.path.insert(0, user_site)

                    namespace = {
                        '__builtins__': __builtins__,
                        '__name__': '__main__',
                        '__file__': '<tool>',
                    }

                    exec(tool.code, namespace)

                    # Find the function
                    func_name = None
                    for name, obj in namespace.items():
                        if callable(obj) and not name.startswith('_'):
                            func_name = name
                            break

                    if not func_name:
                        raise ValueError("No callable function found in tool code")

                    func = namespace[func_name]

                    # Execute with input_data in a separate thread to avoid blocking
                    if isinstance(input_data, dict):
                        result = await asyncio.to_thread(func, **input_data)
                    else:
                        result = await asyncio.to_thread(func, input_data)

                elif tool.tool_type == "docker":
                    # Execute Docker tool
                    from ..services.docker_service import DockerService
                    docker_service = DockerService()

                    import json
                    input_str = json.dumps(input_data) if isinstance(input_data, dict) else str(input_data)

                    result = await docker_service.execute_tool(
                        tool_id=str(tool_id),
                        input_data=input_str,
                        docker_image=tool.docker_image,
                        docker_command=tool.docker_command,
                        timeout=30
                    )
                else:
                    raise ValueError(f"Unsupported tool type: {tool.tool_type}")

                execution_time_ms = int((time.time() - start_time) * 1000)

                # Update to completed
                execution.status = ExecutionStatus.COMPLETED.value
                execution.output_data = {"output": str(result)}
                execution.execution_time_ms = execution_time_ms
                db.commit()

            except Exception as e:
                execution_time_ms = int((time.time() - start_time) * 1000)
                execution.status = ExecutionStatus.FAILED.value
                execution.error = str(e)
                execution.execution_time_ms = execution_time_ms
                db.commit()
        finally:
            # Close the database session
            db.close()

    def create_task_execution(
        self,
        task_id,
        user_id,
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
