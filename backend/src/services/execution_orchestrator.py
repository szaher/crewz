"""Execution Orchestrator Service - Central hub for all execution operations.

Provides unified interface for executing flows, crews, agents, tools, and tasks.
Standardizes response formats, validation, authorization, and error handling.
"""
from typing import Dict, Any, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from ..config.settings import Settings
from ..models.execution import Execution
from ..schemas.executions import ExecutionResponse
from .execution_service_worker import ExecutionServiceWorker


class ExecutionOrchestrator:
    """
    Central orchestrator for all execution operations.

    Provides type-safe execute methods for each entity type with:
    - Unified validation
    - Consistent authorization checks
    - Standardized response formats
    - Configurable priority and timeouts
    """

    # Default execution configurations per entity type
    DEFAULT_CONFIGS = {
        "flow": {"priority": 5, "timeout_seconds": 600},
        "crew": {"priority": 5, "timeout_seconds": 600},
        "agent": {"priority": 5, "timeout_seconds": 300},
        "tool": {"priority": 5, "timeout_seconds": 300},
        "task": {"priority": 5, "timeout_seconds": 300},
    }

    def __init__(
        self,
        db: Session,
        settings: Optional[Settings] = None,
        current_user: Optional[dict] = None
    ):
        """
        Initialize ExecutionOrchestrator.

        Args:
            db: Database session
            settings: Settings instance (creates new if None)
            current_user: Current authenticated user dict
        """
        self.db = db
        self.settings = settings or Settings()
        self.current_user = current_user
        self.execution_service = ExecutionServiceWorker(
            db_session=db,
            settings=self.settings
        )

    def _get_user_id(self) -> UUID:
        """Extract user ID from current_user."""
        if not self.current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )

        user_id = self.current_user.get("id")
        if isinstance(user_id, UUID):
            return user_id
        return UUID(user_id)

    def _get_tenant_id(self) -> Optional[UUID]:
        """Extract tenant ID from current_user."""
        if not self.current_user:
            return None

        tenant_id = self.current_user.get("tenant_id")
        if not tenant_id:
            return None
        if isinstance(tenant_id, UUID):
            return tenant_id
        return UUID(tenant_id)

    def _validate_entity_exists(
        self,
        entity_type: str,
        entity_id: UUID
    ) -> Any:
        """
        Validate that entity exists before execution.

        Args:
            entity_type: Type of entity (flow, crew, agent, tool, task)
            entity_id: Entity UUID

        Returns:
            Entity object

        Raises:
            HTTPException: If entity not found
        """
        from ..models import Flow, Crew, Agent, Tool, Task as TaskModel

        model_map = {
            "flow": Flow,
            "crew": Crew,
            "agent": Agent,
            "tool": Tool,
            "task": TaskModel,
        }

        model = model_map.get(entity_type)
        if not model:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown entity type: {entity_type}"
            )

        entity = self.db.query(model).filter(model.id == entity_id).first()
        if not entity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{entity_type.capitalize()} not found: {entity_id}"
            )

        return entity

    def _queue_execution(
        self,
        execution_type: str,
        entity_id: UUID,
        input_data: Dict[str, Any],
        priority: Optional[int] = None,
        timeout_seconds: Optional[int] = None
    ) -> Execution:
        """
        Queue execution with configured defaults.

        Args:
            execution_type: Type of execution (flow, crew, agent, tool, task)
            entity_id: Entity UUID
            input_data: Input parameters
            priority: Optional priority override
            timeout_seconds: Optional timeout override

        Returns:
            Execution object
        """
        config = self.DEFAULT_CONFIGS.get(execution_type, {})

        if priority is None:
            priority = config.get("priority", 5)
        if timeout_seconds is None:
            timeout_seconds = config.get("timeout_seconds", 600)

        user_id = self._get_user_id()
        tenant_id = self._get_tenant_id()

        return self.execution_service.queue_execution(
            execution_type=execution_type,
            entity_id=entity_id,
            input_params=input_data,
            user_id=user_id,
            tenant_id=tenant_id,
            priority=priority,
            timeout_seconds=timeout_seconds
        )

    async def execute_flow(
        self,
        flow_id: UUID,
        input_data: Dict[str, Any],
        priority: Optional[int] = None,
        timeout_seconds: Optional[int] = None
    ) -> Execution:
        """
        Execute a flow with provided input data.

        Args:
            flow_id: Flow UUID
            input_data: Flow input variables
            priority: Optional priority (0-10, lower is higher)
            timeout_seconds: Optional timeout override

        Returns:
            Execution object

        Raises:
            HTTPException: If flow not found or validation fails
        """
        # Validate flow exists
        self._validate_entity_exists("flow", flow_id)

        # Queue execution
        return self._queue_execution(
            execution_type="flow",
            entity_id=flow_id,
            input_data=input_data,
            priority=priority,
            timeout_seconds=timeout_seconds
        )

    async def execute_crew(
        self,
        crew_id: UUID,
        input_data: Dict[str, Any],
        priority: Optional[int] = None,
        timeout_seconds: Optional[int] = None
    ) -> Execution:
        """
        Execute a crew with provided input data.

        Args:
            crew_id: Crew UUID
            input_data: Crew input parameters
            priority: Optional priority (0-10, lower is higher)
            timeout_seconds: Optional timeout override

        Returns:
            Execution object

        Raises:
            HTTPException: If crew not found or validation fails
        """
        # Validate crew exists
        self._validate_entity_exists("crew", crew_id)

        # Queue execution
        return self._queue_execution(
            execution_type="crew",
            entity_id=crew_id,
            input_data=input_data,
            priority=priority,
            timeout_seconds=timeout_seconds
        )

    async def execute_agent(
        self,
        agent_id: UUID,
        input_data: Dict[str, Any],
        priority: Optional[int] = None,
        timeout_seconds: Optional[int] = None
    ) -> Execution:
        """
        Execute an agent with a task.

        Args:
            agent_id: Agent UUID
            input_data: Task description and parameters
            priority: Optional priority (0-10, lower is higher)
            timeout_seconds: Optional timeout override

        Returns:
            Execution object

        Raises:
            HTTPException: If agent not found or validation fails
        """
        # Validate agent exists
        self._validate_entity_exists("agent", agent_id)

        # Queue execution
        return self._queue_execution(
            execution_type="agent",
            entity_id=agent_id,
            input_data=input_data,
            priority=priority,
            timeout_seconds=timeout_seconds
        )

    async def execute_tool(
        self,
        tool_id: UUID,
        input_data: Dict[str, Any],
        priority: Optional[int] = None,
        timeout_seconds: Optional[int] = None
    ) -> Execution:
        """
        Execute a tool with provided input.

        Args:
            tool_id: Tool UUID
            input_data: Tool input parameters
            priority: Optional priority (0-10, lower is higher)
            timeout_seconds: Optional timeout override

        Returns:
            Execution object

        Raises:
            HTTPException: If tool not found or validation fails
        """
        # Validate tool exists
        self._validate_entity_exists("tool", tool_id)

        # Queue execution
        return self._queue_execution(
            execution_type="tool",
            entity_id=tool_id,
            input_data=input_data,
            priority=priority,
            timeout_seconds=timeout_seconds
        )

    async def execute_task(
        self,
        task_id: UUID,
        input_data: Dict[str, Any],
        priority: Optional[int] = None,
        timeout_seconds: Optional[int] = None
    ) -> Execution:
        """
        Execute a task with provided input.

        Args:
            task_id: Task UUID
            input_data: Task input parameters
            priority: Optional priority (0-10, lower is higher)
            timeout_seconds: Optional timeout override

        Returns:
            Execution object

        Raises:
            HTTPException: If task not found or validation fails
        """
        # Validate task exists
        self._validate_entity_exists("task", task_id)

        # Queue execution
        return self._queue_execution(
            execution_type="task",
            entity_id=task_id,
            input_data=input_data,
            priority=priority,
            timeout_seconds=timeout_seconds
        )

    async def re_execute(
        self,
        execution_id: UUID
    ) -> Execution:
        """
        Re-execute an existing execution with same inputs.

        Args:
            execution_id: Original execution UUID

        Returns:
            New execution object

        Raises:
            HTTPException: If execution not found or not authorized
        """
        # Get original execution
        original = self.db.query(Execution).filter(
            Execution.id == execution_id
        ).first()

        if not original:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Execution not found: {execution_id}"
            )

        # Check authorization
        user_id = self._get_user_id()
        is_super_admin = self.current_user.get("is_super_admin", False)

        if original.user_id != user_id and not is_super_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to re-execute this execution"
            )

        # Determine entity_id based on execution type
        entity_id = None
        if original.flow_id:
            entity_id = original.flow_id
        elif original.crew_id:
            entity_id = original.crew_id
        elif original.agent_id:
            entity_id = original.agent_id
        elif original.tool_id:
            entity_id = original.tool_id
        elif original.task_id:
            entity_id = original.task_id

        if not entity_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Original execution has no entity reference"
            )

        # Queue new execution with same inputs
        return self._queue_execution(
            execution_type=original.execution_type,
            entity_id=entity_id,
            input_data=original.input_data or {},
            priority=original.priority,
            timeout_seconds=original.timeout_seconds
        )

    async def cancel_execution(
        self,
        execution_id: UUID
    ) -> Dict[str, Any]:
        """
        Cancel a running or queued execution.

        Args:
            execution_id: Execution UUID

        Returns:
            Dict with cancellation status

        Raises:
            HTTPException: If execution not found or not authorized
        """
        user_id = self._get_user_id()
        result = self.execution_service.cancel_execution(
            execution_id=execution_id,
            user_id=user_id
        )

        if not result.get("cancelled"):
            error = result.get("error", "unknown")
            if error == "not_found":
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Execution not found"
                )
            elif error == "unauthorized":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to cancel this execution"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot cancel execution: {error}"
                )

        return result
