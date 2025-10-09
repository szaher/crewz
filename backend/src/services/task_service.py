"""Task service for managing CrewAI tasks."""

from sqlalchemy.orm import Session
from typing import List, Optional
from fastapi import HTTPException, status

from ..models.task import Task
from ..models.agent import Agent
from ..models.crew import Crew
from ..schemas.task import TaskCreate, TaskUpdate


class TaskService:
    """Service for managing tasks."""

    def __init__(self, db: Session):
        self.db = db

    async def list_tasks(
        self,
        page: int = 1,
        page_size: int = 10,
        crew_id: Optional[int] = None,
        agent_id: Optional[int] = None,
    ) -> dict:
        """
        List tasks with pagination and optional filtering.

        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page
            crew_id: Optional crew ID to filter by
            agent_id: Optional agent ID to filter by

        Returns:
            Dictionary with tasks list and total count
        """
        query = self.db.query(Task)

        # Apply filters
        if crew_id is not None:
            query = query.filter(Task.crew_id == crew_id)
        if agent_id is not None:
            query = query.filter(Task.agent_id == agent_id)

        # Order by crew and task order
        query = query.order_by(Task.crew_id, Task.order, Task.created_at)

        total = query.count()
        offset = (page - 1) * page_size
        tasks = query.offset(offset).limit(page_size).all()

        return {"tasks": tasks, "total": total, "page": page, "page_size": page_size}

    async def get_task(self, task_id: int) -> Task:
        """
        Get a task by ID.

        Args:
            task_id: Task ID

        Returns:
            Task object

        Raises:
            HTTPException: If task not found
        """
        task = (
            self.db.query(Task)
            .filter(Task.id == task_id)
            .first()
        )

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task with id {task_id} not found",
            )

        return task

    async def create_task(self, task_data: TaskCreate) -> Task:
        """
        Create a new task.

        Args:
            task_data: Task creation data

        Returns:
            Created task

        Raises:
            HTTPException: If agent or crew not found
        """
        # Validate agent exists if provided
        if task_data.agent_id:
            agent = (
                self.db.query(Agent)
                .filter(Agent.id == task_data.agent_id)
                .first()
            )
            if not agent:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Agent with id {task_data.agent_id} not found",
                )

        # Validate crew exists if provided
        if task_data.crew_id:
            crew = (
                self.db.query(Crew)
                .filter(Crew.id == task_data.crew_id)
                .first()
            )
            if not crew:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Crew with id {task_data.crew_id} not found",
                )

        # Create task
        task = Task(
            name=task_data.name,
            description=task_data.description,
            expected_output=task_data.expected_output,
            agent_id=task_data.agent_id,
            crew_id=task_data.crew_id,
            order=task_data.order,
            async_execution=task_data.async_execution,
            output_format=task_data.output_format,
            output_file=task_data.output_file,
            context=task_data.context,
            tools_config=task_data.tools_config,
        )

        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)

        return task

    async def update_task(self, task_id: int, task_data: TaskUpdate) -> Task:
        """
        Update a task.

        Args:
            task_id: Task ID
            task_data: Task update data

        Returns:
            Updated task

        Raises:
            HTTPException: If task, agent, or crew not found
        """
        task = await self.get_task(task_id)

        # Validate agent exists if provided
        if task_data.agent_id is not None:
            if task_data.agent_id:
                agent = (
                    self.db.query(Agent)
                    .filter(Agent.id == task_data.agent_id)
                    .first()
                )
                if not agent:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Agent with id {task_data.agent_id} not found",
                    )
            task.agent_id = task_data.agent_id

        # Validate crew exists if provided
        if task_data.crew_id is not None:
            if task_data.crew_id:
                crew = (
                    self.db.query(Crew)
                    .filter(Crew.id == task_data.crew_id)
                    .first()
                )
                if not crew:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Crew with id {task_data.crew_id} not found",
                    )
            task.crew_id = task_data.crew_id

        # Update other fields
        update_data = task_data.dict(exclude_unset=True, exclude={"agent_id", "crew_id"})
        for field, value in update_data.items():
            setattr(task, field, value)

        self.db.commit()
        self.db.refresh(task)

        return task

    async def delete_task(self, task_id: int) -> None:
        """
        Delete a task.

        Args:
            task_id: Task ID

        Raises:
            HTTPException: If task not found
        """
        task = await self.get_task(task_id)
        self.db.delete(task)
        self.db.commit()

    async def get_crew_tasks(self, crew_id: int) -> List[Task]:
        """
        Get all tasks for a crew, ordered by task order.

        Args:
            crew_id: Crew ID

        Returns:
            List of tasks for the crew
        """
        tasks = (
            self.db.query(Task)
            .filter(Task.crew_id == crew_id)
            .order_by(Task.order)
            .all()
        )
        return tasks

    async def reorder_crew_tasks(self, crew_id: int, task_orders: dict[int, int]) -> List[Task]:
        """
        Reorder tasks within a crew.

        Args:
            crew_id: Crew ID
            task_orders: Dictionary mapping task_id to new order value

        Returns:
            List of reordered tasks

        Raises:
            HTTPException: If any task not found or doesn't belong to crew
        """
        # Validate all tasks belong to the crew
        for task_id in task_orders.keys():
            task = (
                self.db.query(Task)
                .filter(
                    Task.id == task_id,
                    Task.crew_id == crew_id
                )
                .first()
            )
            if not task:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Task {task_id} not found or doesn't belong to crew {crew_id}",
                )

        # Update orders
        for task_id, order in task_orders.items():
            self.db.query(Task).filter(Task.id == task_id).update({"order": order})

        self.db.commit()

        # Return updated tasks
        return await self.get_crew_tasks(crew_id)
