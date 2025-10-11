"""Crew service for CrewAI crew management."""

from typing import List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from ..models import Crew, Agent
from ..models.task import Task
from ..models.crew import CrewProcess


class CrewService:
    """Service for crew CRUD operations."""

    def __init__(self, db: Session):
        self.db = db

    async def create_crew(
        self,
        name: str,
        description: str,
        process: str,
        agent_ids: List[int],
        task_ids: List[int] = None,
        verbose: bool = False,
        memory: bool = False,
        manager_llm_provider_id: int = None,
    ) -> Crew:
        """
        Create a new crew.

        Args:
            name: Crew name
            description: Crew description
            process: Collaboration pattern (sequential, hierarchical)
            agent_ids: List of agent IDs to include
            task_ids: List of task IDs to assign to this crew
            verbose: Enable verbose logging
            memory: Enable crew memory
            manager_llm_provider_id: LLM provider for hierarchical manager

        Returns:
            Created Crew model
        """
        # Ensure correct enum type for process
        proc = process if isinstance(process, CrewProcess) else CrewProcess(process)

        crew = Crew(
            name=name,
            description=description,
            process=proc,
            verbose=verbose,
            memory=memory,
            manager_llm_provider_id=manager_llm_provider_id,
        )

        self.db.add(crew)
        self.db.flush()

        # Associate agents
        if agent_ids:
            agents = self.db.query(Agent).filter(Agent.id.in_(agent_ids)).all()
            crew.agents = agents

        # Assign tasks to crew
        if task_ids:
            tasks = self.db.query(Task).filter(Task.id.in_(task_ids)).all()
            for task in tasks:
                task.crew_id = crew.id

        self.db.commit()
        self.db.refresh(crew)

        return crew

    async def get_crew(self, crew_id: int) -> Crew:
        """Get crew by ID."""
        crew = self.db.query(Crew).filter(Crew.id == crew_id).first()

        if not crew:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Crew not found",
            )

        return crew

    async def list_crews(self, page: int = 1, page_size: int = 10) -> dict:
        """List crews with pagination."""
        query = self.db.query(Crew)

        total = query.count()
        offset = (page - 1) * page_size
        crews = query.offset(offset).limit(page_size).all()

        return {
            "crews": crews,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def update_crew(
        self,
        crew_id: int,
        name: str = None,
        description: str = None,
        process: str = None,
        agent_ids: List[int] = None,
        task_ids: List[int] = None,
        verbose: bool = None,
        memory: bool = None,
    ) -> Crew:
        """Update an existing crew."""
        crew = await self.get_crew(crew_id)

        if name is not None:
            crew.name = name
        if description is not None:
            crew.description = description
        if process is not None:
            crew.process = process if isinstance(process, CrewProcess) else CrewProcess(process)
        if verbose is not None:
            crew.verbose = verbose
        if memory is not None:
            crew.memory = memory

        # Update agents
        if agent_ids is not None:
            agents = self.db.query(Agent).filter(Agent.id.in_(agent_ids)).all()
            crew.agents = agents

        # Update task assignments
        if task_ids is not None:
            # First, unassign all current tasks from this crew
            current_tasks = self.db.query(Task).filter(Task.crew_id == crew_id).all()
            for task in current_tasks:
                task.crew_id = None

            # Then assign the new tasks
            if task_ids:
                new_tasks = self.db.query(Task).filter(Task.id.in_(task_ids)).all()
                for task in new_tasks:
                    task.crew_id = crew_id

        self.db.commit()
        self.db.refresh(crew)

        return crew

    async def delete_crew(self, crew_id: int) -> None:
        """Delete a crew."""
        crew = await self.get_crew(crew_id)
        self.db.delete(crew)
        self.db.commit()
