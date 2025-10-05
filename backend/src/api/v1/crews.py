"""Crew management API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ...db.postgres import get_db
from ...api.middleware.auth import require_auth
from ...services.crew_service import CrewService
from ...schemas.crew import CrewCreate, CrewUpdate, CrewResponse, CrewListResponse

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
    return CrewListResponse(crews=result["crews"], total=result["total"])


@router.post("", response_model=CrewResponse, status_code=status.HTTP_201_CREATED)
async def create_crew(
    crew_data: CrewCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth)
):
    """Create a new crew."""
    service = CrewService(db)
    crew = await service.create_crew(
        name=crew_data.name,
        description=crew_data.description,
        process=crew_data.process,
        agent_ids=crew_data.agent_ids,
        verbose=crew_data.verbose,
        memory=crew_data.memory,
        manager_llm_provider_id=crew_data.manager_llm_provider_id
    )
    return CrewResponse(crew=crew)


@router.get("/{crew_id}", response_model=CrewResponse)
async def get_crew(
    crew_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth)
):
    """Get a specific crew by ID."""
    service = CrewService(db)
    crew = await service.get_crew(crew_id)
    return CrewResponse(crew=crew)


@router.put("/{crew_id}", response_model=CrewResponse)
async def update_crew(
    crew_id: int,
    crew_data: CrewUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth)
):
    """Update a crew."""
    service = CrewService(db)
    crew = await service.update_crew(
        crew_id=crew_id,
        name=crew_data.name,
        description=crew_data.description,
        process=crew_data.process,
        agent_ids=crew_data.agent_ids,
        verbose=crew_data.verbose,
        memory=crew_data.memory
    )
    return CrewResponse(crew=crew)


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
