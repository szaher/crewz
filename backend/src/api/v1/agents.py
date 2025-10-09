"""Agent and Crew API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...db.postgres import get_db
from ...schemas.agents import (
    AgentCreate,
    AgentUpdate,
    AgentResponse,
    AgentListResponse,
)
from ...services.agent_service import AgentService
from ...services.versioning_service import VersioningService
from ...api.middleware.auth import require_auth

router = APIRouter()


# Agent endpoints
@router.get("", response_model=AgentListResponse)
async def list_agents(
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    List agents with pagination.

    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 10, max: 100)
    """
    if page_size > 100:
        page_size = 100

    agent_service = AgentService(db)
    return await agent_service.list_agents(page=page, page_size=page_size)


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    request: AgentCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Create a new agent.

    - **name**: Agent name
    - **role**: Agent role/specialty
    - **goal**: Agent's primary objective
    - **backstory**: Agent's background and expertise
    - **llm_provider_id**: LLM provider to use
    - **temperature**: Sampling temperature (0.0-2.0)
    - **tool_ids**: List of tool IDs the agent can use
    """
    agent_service = AgentService(db)
    agent = await agent_service.create_agent(request)
    return AgentResponse.from_orm(agent)


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Get agent details by ID."""
    agent_service = AgentService(db)
    agent = await agent_service.get_agent(agent_id)
    return AgentResponse.from_orm(agent)


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: int,
    request: AgentUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Update an existing agent."""
    agent_service = AgentService(db)
    agent = await agent_service.update_agent(agent_id, request)
    return AgentResponse.from_orm(agent)


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Delete an agent."""
    agent_service = AgentService(db)
    await agent_service.delete_agent(agent_id)


@router.get("/{agent_id}/versions", response_model=dict)
async def get_agent_versions(
    agent_id: int,
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Get version history for an agent.

    Returns:
    - versions: List of version entries with configuration snapshots and diffs
    - total: Total number of versions
    - page: Current page number
    - page_size: Number of items per page
    """
    if page_size > 50:
        page_size = 50

    versioning_service = VersioningService(db)
    offset = (page - 1) * page_size

    versions, total = versioning_service.get_agent_versions(
        agent_id=agent_id,
        limit=page_size,
        offset=offset
    )

    return {
        "versions": [
            {
                "id": v.id,
                "version_number": v.version_number,
                "action": v.action.value,
                "changed_by_user_id": v.changed_by_user_id,
                "configuration": v.configuration,
                "diff_from_previous": v.diff_from_previous,
                "change_description": v.change_description,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            for v in versions
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/{agent_id}/rollback/{version_number}", response_model=AgentResponse)
async def rollback_agent(
    agent_id: int,
    version_number: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Rollback an agent to a specific version.

    - **version_number**: Version number to rollback to
    """
    versioning_service = VersioningService(db)

    try:
        agent = versioning_service.rollback_agent(
            agent_id=agent_id,
            version_number=version_number,
            changed_by_user_id=current_user.get("user_id")
        )
        return AgentResponse.from_orm(agent)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/{agent_id}/execute")
async def execute_agent(
    agent_id: int,
    input_data: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Execute an agent with a task.

    Input should contain:
    - task: The task description for the agent to perform
    - context: Optional context or additional information
    """
    import time
    from ...services.llm_service import LLMService
    from ...services.docker_service import DockerService
    from ...crewai.tool_adapter import ToolAdapter
    from ...crewai.agent_factory import AgentFactory

    agent_service = AgentService(db)
    agent = await agent_service.get_agent(agent_id)

    start_time = time.time()

    try:
        # Initialize dependencies
        llm_service = LLMService(db)
        docker_service = DockerService()
        tool_adapter = ToolAdapter(docker_service)
        agent_factory = AgentFactory(llm_service, tool_adapter)

        # Create CrewAI agent
        crewai_agent = await agent_factory.from_db_model(agent)

        # Get task from input
        task_description = input_data.get('task', 'Perform your assigned task')
        context = input_data.get('context', '')

        # For single agent execution, we need to create a simple crew
        from crewai import Crew, Task

        # Create a task for the agent
        task = Task(
            description=task_description,
            agent=crewai_agent,
            expected_output=input_data.get('expected_output', 'A detailed response to the task')
        )

        # Create a crew with just this agent
        crew = Crew(
            agents=[crewai_agent],
            tasks=[task],
            verbose=True
        )

        # Execute the crew (which runs the single agent)
        result = crew.kickoff()

        execution_time_ms = int((time.time() - start_time) * 1000)

        return {
            "agent_id": agent_id,
            "agent_name": agent.name,
            "input_data": input_data,
            "status": "success",
            "output": str(result),
            "execution_time_ms": execution_time_ms
        }

    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        return {
            "agent_id": agent_id,
            "agent_name": agent.name,
            "input_data": input_data,
            "status": "failed",
            "error": str(e),
            "execution_time_ms": execution_time_ms
        }


# Note: Crew endpoints live in backend/src/api/v1/crews.py
