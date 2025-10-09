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


@router.post("/{crew_id}/execute")
async def execute_crew(
    crew_id: int,
    input_data: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Execute a crew with tasks.

    If the crew has stored tasks, those will be used.
    Otherwise, input should contain:
    - tasks: List of task descriptions for the crew to perform
    - context: Optional context or additional information
    """
    import time
    from ...services.llm_service import LLMService
    from ...services.docker_service import DockerService
    from ...services.task_service import TaskService
    from ...crewai.tool_adapter import ToolAdapter
    from ...crewai.agent_factory import AgentFactory
    from ...crewai.crew_factory import CrewFactory
    from ...models.agent import Agent

    service = CrewService(db)
    crew_model = await service.get_crew(crew_id)

    start_time = time.time()

    try:
        # Initialize dependencies
        llm_service = LLMService(db)
        docker_service = DockerService()
        tool_adapter = ToolAdapter(docker_service)
        agent_factory = AgentFactory(llm_service, tool_adapter)
        crew_factory = CrewFactory(agent_factory)

        # Create CrewAI crew
        crewai_crew = await crew_factory.from_db_model(crew_model)

        # Get stored tasks for this crew
        task_service = TaskService(db)
        stored_tasks = await task_service.get_crew_tasks(crew_id)

        # Create tasks for the crew
        from crewai import Task
        import json
        tasks = []
        task_map = {}  # Map to track tasks for context references

        if stored_tasks:
            # Use stored tasks - create them in order
            for db_task in stored_tasks:
                # Get the agent for this task
                agent = None
                if db_task.agent_id:
                    # Find the agent in the crew's agents
                    agent_model = db.query(Agent).filter(Agent.id == db_task.agent_id).first()
                    if agent_model:
                        agent = await agent_factory.from_db_model(agent_model)
                else:
                    # If no specific agent, use first agent in crew
                    agents = crewai_crew.agents
                    agent = agents[0] if agents else None

                # Parse context if it references other tasks
                context_tasks = []
                if db_task.context:
                    try:
                        context_data = json.loads(db_task.context) if isinstance(db_task.context, str) else db_task.context
                        if isinstance(context_data, dict) and 'task_ids' in context_data:
                            # Context references other task IDs
                            for task_id in context_data['task_ids']:
                                if task_id in task_map:
                                    context_tasks.append(task_map[task_id])
                    except (json.JSONDecodeError, TypeError):
                        # Context is just a text string, not JSON
                        pass

                # Get tools for this task
                task_tools = []
                if db_task.tools_config:
                    try:
                        tools_config = json.loads(db_task.tools_config) if isinstance(db_task.tools_config, str) else db_task.tools_config
                        if isinstance(tools_config, dict) and 'tool_ids' in tools_config:
                            # Get the agent's tools and filter by tool_ids
                            if agent and hasattr(agent, 'tools'):
                                task_tools = agent.tools
                    except (json.JSONDecodeError, TypeError):
                        pass

                # Create the CrewAI Task
                task_kwargs = {
                    'description': db_task.description,
                    'agent': agent,
                    'expected_output': db_task.expected_output,
                    'async_execution': db_task.async_execution,
                }

                # Add optional parameters
                if context_tasks:
                    task_kwargs['context'] = context_tasks
                if task_tools:
                    task_kwargs['tools'] = task_tools
                if db_task.output_file:
                    task_kwargs['output_file'] = db_task.output_file

                task = Task(**task_kwargs)
                tasks.append(task)
                task_map[db_task.id] = task
        else:
            # Fall back to dynamic tasks from input
            tasks_input = input_data.get('tasks', [])
            if not tasks_input:
                # Default task if none provided
                tasks_input = ['Complete the assigned objectives as a team']

            agents = crewai_crew.agents
            for i, task_desc in enumerate(tasks_input):
                # Assign tasks round-robin to agents
                agent = agents[i % len(agents)] if agents else None
                task = Task(
                    description=task_desc,
                    agent=agent,
                    expected_output=f"Completion of: {task_desc}"
                )
                tasks.append(task)

        # Update crew with tasks
        crewai_crew.tasks = tasks

        # Execute the crew
        result = crewai_crew.kickoff()

        execution_time_ms = int((time.time() - start_time) * 1000)

        return {
            "crew_id": crew_id,
            "crew_name": crew_model.name,
            "input_data": input_data,
            "tasks_used": "stored" if stored_tasks else "dynamic",
            "task_count": len(tasks),
            "status": "success",
            "output": str(result),
            "execution_time_ms": execution_time_ms
        }

    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        return {
            "crew_id": crew_id,
            "crew_name": crew_model.name,
            "input_data": input_data,
            "status": "failed",
            "error": str(e),
            "execution_time_ms": execution_time_ms
        }
