"""Task API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any

from ...db.postgres import get_db
from ...schemas.task import (
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    TaskListResponse,
)
from ...services.task_service import TaskService
from ...services.task_templates import TaskTemplates
from ...api.middleware.auth import require_auth

router = APIRouter()


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    page: int = 1,
    page_size: int = 10,
    crew_id: Optional[int] = None,
    agent_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    List tasks with pagination and optional filtering.

    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 10, max: 100)
    - **crew_id**: Optional crew ID to filter by
    - **agent_id**: Optional agent ID to filter by
    """
    if page_size > 100:
        page_size = 100

    task_service = TaskService(db)
    result = await task_service.list_tasks(
        page=page,
        page_size=page_size,
        crew_id=crew_id,
        agent_id=agent_id,
    )

    return TaskListResponse(**result)


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    request: TaskCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Create a new task.

    - **name**: Task name
    - **description**: Detailed task description
    - **expected_output**: Expected output description
    - **agent_id**: Optional agent to assign task to
    - **crew_id**: Optional crew to associate task with
    - **order**: Task order within crew (default: 0)
    - **async_execution**: Execute asynchronously (default: false)
    - **output_format**: Output format (TEXT, JSON, PYDANTIC)
    - **output_file**: Optional output file path
    - **context**: Optional additional context
    - **tools_config**: Optional JSON string of tool configurations
    """
    task_service = TaskService(db)
    task = await task_service.create_task(request)
    return TaskResponse.from_orm(task)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Get task details by ID."""
    task_service = TaskService(db)
    task = await task_service.get_task(task_id)
    return TaskResponse.from_orm(task)


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    request: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Update an existing task."""
    task_service = TaskService(db)
    task = await task_service.update_task(task_id, request)
    return TaskResponse.from_orm(task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Delete a task."""
    task_service = TaskService(db)
    await task_service.delete_task(task_id)


@router.put("/{task_id}/unassign", response_model=TaskResponse)
async def unassign_task_from_crew(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Unassign a task from its crew.

    This removes the task from the crew (sets crew_id to NULL) but preserves the task,
    allowing it to be reused or reassigned to a different crew later.
    """
    task_service = TaskService(db)
    task = await task_service.unassign_from_crew(task_id)
    return TaskResponse.from_orm(task)


@router.get("/crew/{crew_id}/tasks", response_model=list[TaskResponse])
async def get_crew_tasks(
    crew_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """Get all tasks for a specific crew, ordered by task order."""
    task_service = TaskService(db)
    tasks = await task_service.get_crew_tasks(crew_id)
    return [TaskResponse.from_orm(task) for task in tasks]


@router.post("/crew/{crew_id}/reorder", response_model=list[TaskResponse])
async def reorder_crew_tasks(
    crew_id: int,
    task_orders: dict[int, int],
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Reorder tasks within a crew.

    Request body should be a dictionary mapping task_id to new order value.
    Example: {"1": 0, "2": 1, "3": 2}
    """
    task_service = TaskService(db)
    tasks = await task_service.reorder_crew_tasks(crew_id, task_orders)
    return [TaskResponse.from_orm(task) for task in tasks]


@router.get("/templates", response_model=List[Dict[str, Any]])
async def get_task_templates(
    current_user: dict = Depends(require_auth),
):
    """
    Get all available task templates.

    Returns a list of pre-configured task templates based on common CrewAI patterns.
    """
    return TaskTemplates.get_all_templates()


@router.get("/templates/workflows", response_model=Dict[str, List[Dict[str, Any]]])
async def get_workflow_templates(
    current_user: dict = Depends(require_auth),
):
    """
    Get pre-configured workflow templates.

    Returns workflows consisting of multiple tasks designed to work together.
    Available workflows:
    - research_and_report: Complete research, analysis, and reporting workflow
    - code_development: Planning, coding, and review workflow
    - data_pipeline: Data extraction, analysis, and summarization
    - content_creation: Research, writing, and review for content
    """
    return TaskTemplates.get_workflow_templates()


@router.post("/crew/{crew_id}/from-template", response_model=List[TaskResponse])
async def create_tasks_from_template(
    crew_id: int,
    template_name: str,
    agent_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Create tasks for a crew from a template.

    - **crew_id**: Crew to add tasks to
    - **template_name**: Name of the template (e.g., "research", "analysis", "writing")
    - **agent_id**: Optional agent to assign all tasks to
    """
    task_service = TaskService(db)

    # Get the template
    template_map = {
        "research": TaskTemplates.research_task,
        "analysis": TaskTemplates.analysis_task,
        "writing": TaskTemplates.writing_task,
        "code": TaskTemplates.code_generation_task,
        "review": TaskTemplates.review_task,
        "planning": TaskTemplates.planning_task,
        "data_extraction": TaskTemplates.data_extraction_task,
        "summarization": TaskTemplates.summarization_task,
    }

    if template_name not in template_map:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_name}' not found"
        )

    template = template_map[template_name]()
    template["crew_id"] = crew_id
    if agent_id:
        template["agent_id"] = agent_id

    task = await task_service.create_task(TaskCreate(**template))
    return [TaskResponse.from_orm(task)]


@router.post("/crew/{crew_id}/from-workflow", response_model=List[TaskResponse])
async def create_tasks_from_workflow(
    crew_id: int,
    workflow_name: str,
    agent_ids: Optional[List[int]] = Query(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_auth),
):
    """
    Create multiple tasks for a crew from a workflow template.

    - **crew_id**: Crew to add tasks to
    - **workflow_name**: Name of the workflow (research_and_report, code_development, data_pipeline, content_creation)
    - **agent_ids**: Optional list of agent IDs to assign tasks to (round-robin)
    """
    task_service = TaskService(db)
    workflows = TaskTemplates.get_workflow_templates()

    if workflow_name not in workflows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow '{workflow_name}' not found"
        )

    workflow_templates = workflows[workflow_name]
    created_tasks = []

    for i, template in enumerate(workflow_templates):
        template["crew_id"] = crew_id
        template["order"] = i

        # Assign agent round-robin if agent_ids provided
        if agent_ids and len(agent_ids) > 0:
            template["agent_id"] = agent_ids[i % len(agent_ids)]

        task = await task_service.create_task(TaskCreate(**template))
        created_tasks.append(TaskResponse.from_orm(task))

    return created_tasks
