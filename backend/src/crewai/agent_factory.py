"""Factory for creating CrewAI agents from database models."""

from typing import List, Optional
from crewai import Agent as CrewAIAgent

from ..models import Agent
from ..services.llm_service import LLMService
from .tool_adapter import ToolAdapter


class AgentFactory:
    """Factory to convert database Agent models to CrewAI Agent instances."""

    def __init__(self, llm_service: LLMService, tool_adapter: ToolAdapter):
        self.llm_service = llm_service
        self.tool_adapter = tool_adapter

    async def from_db_model(self, agent: Agent) -> CrewAIAgent:
        """
        Create a CrewAI Agent from database model.

        Args:
            agent: Database Agent model

        Returns:
            CrewAI Agent instance configured from database
        """
        # Get LLM for this agent
        llm_provider = await self.llm_service.get_provider(agent.llm_provider_id)

        # Convert tools
        crewai_tools = []
        for tool in agent.tools:
            crewai_tool = await self.tool_adapter.from_db_model(tool)
            crewai_tools.append(crewai_tool)

        # Create CrewAI agent
        crewai_agent = CrewAIAgent(
            role=agent.role,
            goal=agent.goal,
            backstory=agent.backstory,
            tools=crewai_tools,
            verbose=agent.verbose,
            allow_delegation=agent.allow_delegation,
            # LLM configuration
            llm=None,  # Will be set via LiteLLM in execution
        )

        return crewai_agent
