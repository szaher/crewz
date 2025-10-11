"""Flow API endpoints."""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...db.postgres import get_db
from ...schemas.flows import (
    FlowCreate,
    FlowUpdate,
    FlowResponse,
    FlowListResponse,
)
from ...schemas.executions import ExecutionCreate, ExecutionResponse
from ...services.flow_service import FlowService
from ...services.execution_service import ExecutionService
from ...api.middleware.auth import require_auth

router = APIRouter()


@router.get("", response_model=FlowListResponse)
async def list_flows(
    page: int = 1,
    page_size: int = 10,
    status: Optional[str] = None,
    tags: Optional[List[str]] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    List flows with pagination and filtering.

    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 10, max: 100)
    - **status**: Filter by status (draft, active, archived)
    - **tags**: Filter by tags (comma-separated)
    """
    if page_size > 100:
        page_size = 100

    flow_service = FlowService(db)
    return await flow_service.list_flows(
        page=page,
        page_size=page_size,
        status=status,
        tags=tags,
    )


@router.post("", response_model=FlowResponse, status_code=status.HTTP_201_CREATED)
async def create_flow(
    request: FlowCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Create a new flow.

    - **name**: Flow name (required)
    - **description**: Flow description
    - **nodes**: List of flow nodes
    - **edges**: List of flow edges
    - **tags**: Optional tags for categorization
    """
    flow_service = FlowService(db)
    flow = await flow_service.create_flow(request)
    return FlowResponse.from_orm(flow)


@router.get("/{flow_id}", response_model=FlowResponse)
async def get_flow(
    flow_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Get flow details by ID."""
    flow_service = FlowService(db)
    flow = await flow_service.get_flow(flow_id)
    return FlowResponse.from_orm(flow)


@router.put("/{flow_id}", response_model=FlowResponse)
async def update_flow(
    flow_id: int,
    request: FlowUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Update an existing flow.

    Only provided fields will be updated.
    """
    flow_service = FlowService(db)
    flow = await flow_service.update_flow(flow_id, request)
    return FlowResponse.from_orm(flow)


@router.delete("/{flow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_flow(
    flow_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Delete (archive) a flow.

    Flow is soft-deleted by setting status to 'archived'.
    """
    flow_service = FlowService(db)
    await flow_service.delete_flow(flow_id)


@router.post("/{flow_id}/execute", response_model=ExecutionResponse, status_code=status.HTTP_201_CREATED)
async def execute_flow(
    flow_id: int,
    input_data: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Execute a flow with provided input data.

    Returns execution record. Monitor progress via GET /executions/{execution_id}/stream
    """
    # Initialize services with proper dependencies
    flow_service = FlowService(db)

    from ...crewai.flow_executor import FlowExecutor
    from ...crewai.crew_factory import CrewFactory
    from ...crewai.agent_factory import AgentFactory
    from ...services.execution_events import ExecutionEventPublisher
    from ...services.llm_service import LLMService
    from ...services.docker_service import DockerService
    from ...crewai.tool_adapter import ToolAdapter

    # Initialize factories with dependencies
    llm_service = LLMService(db)
    docker_service = DockerService()
    tool_adapter = ToolAdapter(docker_service)
    agent_factory = AgentFactory(llm_service, tool_adapter)
    crew_factory = CrewFactory(agent_factory)
    event_publisher = ExecutionEventPublisher()
    flow_executor = FlowExecutor(crew_factory, agent_factory, event_publisher)

    execution_service = ExecutionService(db, flow_service, flow_executor)

    execution_request = ExecutionCreate(
        execution_type="flow",
        flow_id=flow_id,
        input_data=input_data,
    )

    # Use async creation that accepts ExecutionCreate and schedules execution
    execution = await execution_service.create_execution_async(
        execution_request,
        user_id=current_user["id"],
    )

    return ExecutionResponse.from_orm(execution)
