"""Factory for creating CrewAI agents from database models."""

from typing import List, Optional
from crewai import Agent as CrewAIAgent
from crewai import LLM
import os

from ..models import Agent
from ..services.llm_service import LLMService
from .tool_adapter import ToolAdapter


class AgentFactory:
    """Factory to convert database Agent models to CrewAI Agent instances."""

    def __init__(self, llm_service: LLMService, tool_adapter: ToolAdapter):
        self.llm_service = llm_service
        self.tool_adapter = tool_adapter

    async def from_db_model(self, agent: Agent, provider_id_override: Optional[int] = None) -> CrewAIAgent:
        """
        Create a CrewAI Agent from database model.

        Args:
            agent: Database Agent model
            provider_id_override: Optional LLM provider ID to use instead of agent's default

        Returns:
            CrewAI Agent instance configured from database
        """
        # Get LLM for this agent - use override if provided
        provider_id = provider_id_override if provider_id_override is not None else agent.llm_provider_id
        llm_provider = await self.llm_service.get_provider(provider_id)

        # Build LiteLLM parameters
        llm_params = self.llm_service._build_litellm_params(llm_provider)

        # Create LLM instance for CrewAI
        # Best-effort: also set common env vars some CrewAI internals rely on
        api_key = llm_params.get("api_key")
        if api_key:
            try:
                if str(getattr(llm_provider, "provider_type", "")).lower() == "openai":
                    os.environ.setdefault("OPENAI_API_KEY", api_key)
                elif str(getattr(llm_provider, "provider_type", "")).lower() == "anthropic":
                    os.environ.setdefault("ANTHROPIC_API_KEY", api_key)
            except Exception:
                pass

        llm = LLM(
            model=llm_params["model"],
            api_key=api_key,
            base_url=llm_params.get("api_base"),
        )

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
            llm=llm,
        )

        return crewai_agent
