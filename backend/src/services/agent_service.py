"""Agent service for CrewAI agent management."""

from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from ..models import Agent, Tool
from ..schemas.agents import AgentCreate, AgentUpdate, AgentResponse, AgentListResponse
from .versioning_service import VersioningService


class AgentService:
    """Service for agent CRUD operations."""

    def __init__(self, db: Session):
        self.db = db
        self.versioning = VersioningService(db)

    async def create_agent(self, data: AgentCreate) -> Agent:
        """
        Create a new agent.

        Args:
            data: Agent creation data

        Returns:
            Created Agent model
        """
        agent = Agent(
            name=data.name,
            role=data.role,
            goal=data.goal,
            backstory=data.backstory,
            llm_provider_id=data.llm_provider_id,
            temperature=data.temperature,
            max_tokens=data.max_tokens,
            allow_delegation=data.allow_delegation,
            verbose=data.verbose,
            cache=data.cache,
            max_iter=data.max_iter,
            max_rpm=data.max_rpm,
            max_execution_time=data.max_execution_time,
            allow_code_execution=data.allow_code_execution,
            respect_context_window=data.respect_context_window,
            max_retry_limit=data.max_retry_limit,
        )

        self.db.add(agent)
        self.db.flush()  # Get agent.id for relationship

        # Associate tools
        if data.tool_ids:
            tools = self.db.query(Tool).filter(Tool.id.in_(data.tool_ids)).all()
            agent.tools = tools

        self.db.commit()
        self.db.refresh(agent)

        # Create initial version
        config = self.versioning.config_to_dict(agent)
        self.versioning.create_agent_version(
            agent_id=agent.id,
            configuration=config,
            action="create",
            change_description="Initial agent creation"
        )

        return agent

    async def get_agent(self, agent_id: int) -> Agent:
        """Get agent by ID."""
        agent = self.db.query(Agent).filter(Agent.id == agent_id).first()

        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found",
            )

        return agent

    async def list_agents(
        self, page: int = 1, page_size: int = 10
    ) -> AgentListResponse:
        """List agents with pagination."""
        query = self.db.query(Agent)

        total = query.count()
        offset = (page - 1) * page_size
        agents = query.offset(offset).limit(page_size).all()

        return AgentListResponse(
            agents=[AgentResponse.from_orm(a) for a in agents],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def update_agent(self, agent_id: int, data: AgentUpdate) -> Agent:
        """Update an existing agent."""
        agent = await self.get_agent(agent_id)

        # Update fields
        if data.name is not None:
            agent.name = data.name
        if data.role is not None:
            agent.role = data.role
        if data.goal is not None:
            agent.goal = data.goal
        if data.backstory is not None:
            agent.backstory = data.backstory
        if data.llm_provider_id is not None:
            agent.llm_provider_id = data.llm_provider_id
        if data.temperature is not None:
            agent.temperature = data.temperature
        if data.max_tokens is not None:
            agent.max_tokens = data.max_tokens
        if data.allow_delegation is not None:
            agent.allow_delegation = data.allow_delegation
        if data.verbose is not None:
            agent.verbose = data.verbose
        if data.cache is not None:
            agent.cache = data.cache
        if data.max_iter is not None:
            agent.max_iter = data.max_iter
        if data.max_rpm is not None:
            agent.max_rpm = data.max_rpm
        if data.max_execution_time is not None:
            agent.max_execution_time = data.max_execution_time
        if data.allow_code_execution is not None:
            agent.allow_code_execution = data.allow_code_execution
        if data.respect_context_window is not None:
            agent.respect_context_window = data.respect_context_window
        if data.max_retry_limit is not None:
            agent.max_retry_limit = data.max_retry_limit

        # Update tools
        if data.tool_ids is not None:
            tools = self.db.query(Tool).filter(Tool.id.in_(data.tool_ids)).all()
            agent.tools = tools

        self.db.commit()
        self.db.refresh(agent)

        # Create version for update
        config = self.versioning.config_to_dict(agent)
        self.versioning.create_agent_version(
            agent_id=agent.id,
            configuration=config,
            action="update",
            change_description="Agent configuration updated"
        )

        return agent

    async def delete_agent(self, agent_id: int) -> None:
        """Delete an agent."""
        agent = await self.get_agent(agent_id)
        self.db.delete(agent)
        self.db.commit()
