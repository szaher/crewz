"""Execution service for managing flow and crew runs."""

from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import asyncio

from ..models import Execution, Flow
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

    async def create_execution(
        self, data: ExecutionCreate, user_id: int
    ) -> Execution:
        """
        Create a new execution.

        Args:
            data: Execution creation data
            user_id: User initiating the execution

        Returns:
            Created Execution model
        """
        # Validate flow can be executed
        if data.flow_id:
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

        # Start execution asynchronously
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

        if execution.status not in ["pending", "running"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel execution with status: {execution.status}",
            )

        execution.status = "cancelled"
        self.db.commit()
        self.db.refresh(execution)

        # TODO: Send cancellation signal to running task

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

            elif execution.execution_type == "crew":
                # Execute crew
                # TODO: Implement crew execution
                execution.output_data = {"result": "crew execution not yet implemented"}
                execution.status = "completed"

            else:
                raise ValueError(f"Unknown execution type: {execution.execution_type}")

        except Exception as e:
            # Execution failed
            execution.status = "failed"
            execution.error = str(e)

        finally:
            self.db.commit()
