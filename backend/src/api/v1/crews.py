"""Crew management API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ...db.postgres import get_db
from ...api.middleware.auth import require_auth
from ...services.crew_service import CrewService
from ...schemas.crew import CrewCreate, CrewUpdate, CrewListResponse, CrewOut

router = APIRouter()


@router.get("", response_model=CrewListResponse)
async def list_crews(
    page: int = 1,
    page_size: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth)
):
    """List all crews for the current tenant."""
    service = CrewService(db)
    result = await service.list_crews(page=page, page_size=page_size)
    # Map ORM models to schema with agent_ids
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
    service = CrewService(db)
    # Normalize compatibility fields
    norm_process = crew_data.process or crew_data.process_type or None
    norm_agents = crew_data.agent_ids or crew_data.agents or []

    crew = await service.create_crew(
        name=crew_data.name,
        description=crew_data.description,
        process=norm_process,
        agent_ids=norm_agents,
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
    service = CrewService(db)
    norm_process = crew_data.process or crew_data.process_type if crew_data.process_type is not None else crew_data.process
    norm_agents = crew_data.agent_ids if crew_data.agent_ids is not None else crew_data.agents

    crew = await service.update_crew(
        crew_id=crew_id,
        name=crew_data.name,
        description=crew_data.description,
        process=norm_process,
        agent_ids=norm_agents,
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
