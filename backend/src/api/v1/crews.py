"""Crew management API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ...db.postgres import get_db
from ...api.middleware.auth import require_auth
from ...services.crew_service import CrewService
from ...schemas.crew import CrewCreate, CrewUpdate, CrewListResponse, CrewOut
from ...schemas.executions import ExecutionCreate, ExecutionResponse

router = APIRouter()


@router.get("", response_model=CrewListResponse)
async def list_crews(
    page: int = 1,
    page_size: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth)
):
    """List all crews for the current tenant."""
    from ...models.task import Task
    service = CrewService(db)
    result = await service.list_crews(page=page, page_size=page_size)
    # Map ORM models to schema with agent_ids and task_count
    crews_out = [
        CrewOut(
            id=c.id,
            name=c.name,
            description=c.description,
            process=c.process,
            verbose=c.verbose,
            memory=c.memory,
            manager_llm_provider_id=c.manager_llm_provider_id,
            agent_ids=[a.id for a in (c.agents or [])],
            task_count=db.query(Task).filter(Task.crew_id == c.id).count(),
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in result["crews"]
    ]
    return CrewListResponse(crews=crews_out, total=result["total"])


@router.post("", response_model=CrewOut, status_code=status.HTTP_201_CREATED)
async def create_crew(
    crew_data: CrewCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth)
):
    """Create a new crew."""
    from ...models.task import Task
    service = CrewService(db)
    # Normalize compatibility fields
    norm_process = crew_data.process or crew_data.process_type or None
    norm_agents = crew_data.agent_ids or crew_data.agents or []

    crew = await service.create_crew(
        name=crew_data.name,
        description=crew_data.description,
        process=norm_process,
        agent_ids=norm_agents,
        task_ids=crew_data.task_ids,
        verbose=crew_data.verbose,
        memory=crew_data.memory,
        manager_llm_provider_id=crew_data.manager_llm_provider_id
    )
    crew_out = CrewOut(
        id=crew.id,
        name=crew.name,
        description=crew.description,
        process=crew.process,
        verbose=crew.verbose,
        memory=crew.memory,
        manager_llm_provider_id=crew.manager_llm_provider_id,
        agent_ids=[a.id for a in (crew.agents or [])],
        task_count=db.query(Task).filter(Task.crew_id == crew.id).count(),
        created_at=crew.created_at,
        updated_at=crew.updated_at,
    )
    return crew_out


@router.get("/{crew_id}", response_model=CrewOut)
async def get_crew(
    crew_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth)
):
    """Get a specific crew by ID."""
    from ...models.task import Task
    service = CrewService(db)
    crew = await service.get_crew(crew_id)
    crew_out = CrewOut(
        id=crew.id,
        name=crew.name,
        description=crew.description,
        process=crew.process,
        verbose=crew.verbose,
        memory=crew.memory,
        manager_llm_provider_id=crew.manager_llm_provider_id,
        agent_ids=[a.id for a in (crew.agents or [])],
        task_count=db.query(Task).filter(Task.crew_id == crew.id).count(),
        created_at=crew.created_at,
        updated_at=crew.updated_at,
    )
    return crew_out


@router.put("/{crew_id}", response_model=CrewOut)
async def update_crew(
    crew_id: int,
    crew_data: CrewUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth)
):
    """Update a crew."""
    from ...models.task import Task
    service = CrewService(db)
    norm_process = crew_data.process or crew_data.process_type if crew_data.process_type is not None else crew_data.process
    norm_agents = crew_data.agent_ids if crew_data.agent_ids is not None else crew_data.agents

    crew = await service.update_crew(
        crew_id=crew_id,
        name=crew_data.name,
        description=crew_data.description,
        process=norm_process,
        agent_ids=norm_agents,
        task_ids=crew_data.task_ids,
        verbose=crew_data.verbose,
        memory=crew_data.memory
    )
    crew_out = CrewOut(
        id=crew.id,
        name=crew.name,
        description=crew.description,
        process=crew.process,
        verbose=crew.verbose,
        memory=crew.memory,
        manager_llm_provider_id=crew.manager_llm_provider_id,
        agent_ids=[a.id for a in (crew.agents or [])],
        task_count=db.query(Task).filter(Task.crew_id == crew.id).count(),
        created_at=crew.created_at,
        updated_at=crew.updated_at,
    )
    return crew_out


@router.delete("/{crew_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_crew(
    crew_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth)
):
    """Delete a crew."""
    service = CrewService(db)
    await service.delete_crew(crew_id)
    return None


@router.get("/{crew_id}/variables")
async def get_crew_variables(
    crew_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Get variables required by the first task of a crew.

    Returns a list of unique variable names found in the first task's description and expected_output.
    These variables need to be provided as input before executing the crew.
    """
    from ...services.task_service import TaskService

    task_service = TaskService(db)
    tasks = await task_service.get_crew_tasks(crew_id)

    # Get variables from the first task only
    if tasks and len(tasks) > 0:
        first_task = tasks[0]
        if first_task.variables:
            return {
                "variables": sorted(list(first_task.variables)),
                "task_name": first_task.name,
                "task_description": first_task.description
            }

    return {"variables": [], "task_name": None, "task_description": None}


@router.post("/{crew_id}/execute", response_model=ExecutionResponse, status_code=status.HTTP_201_CREATED)
async def execute_crew(
    crew_id: int,
    input_data: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Queue a crew execution and return an execution record.

    Execution runs asynchronously. Track status via /api/v1/executions.
    """
    from ...services.execution_service import ExecutionService

    # Create execution record and schedule async run
    execution_service = ExecutionService(db, None, None)
    execution = await execution_service.create_execution_async(
        ExecutionCreate(execution_type="crew", crew_id=crew_id, input_data=input_data),
        user_id=current_user["id"],
    )

    return ExecutionResponse.from_orm(execution)
