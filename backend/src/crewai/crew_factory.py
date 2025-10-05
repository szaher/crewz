"""Factory for creating CrewAI crews from database models."""

from crewai import Crew as CrewAICrew, Process

from ..models import Crew
from .agent_factory import AgentFactory


class CrewFactory:
    """Factory to convert database Crew models to CrewAI Crew instances."""

    def __init__(self, agent_factory: AgentFactory):
        self.agent_factory = agent_factory

    async def from_db_model(self, crew: Crew) -> CrewAICrew:
        """
        Create a CrewAI Crew from database model.

        Args:
            crew: Database Crew model

        Returns:
            CrewAI Crew instance configured from database
        """
        # Convert agents
        crewai_agents = []
        for agent in crew.agents:
            crewai_agent = await self.agent_factory.from_db_model(agent)
            crewai_agents.append(crewai_agent)

        # Map process type
        process = (
            Process.hierarchical
            if crew.process == "hierarchical"
            else Process.sequential
        )

        # Create CrewAI crew
        crewai_crew = CrewAICrew(
            agents=crewai_agents,
            process=process,
            verbose=crew.verbose,
            memory=crew.memory,
        )

        return crewai_crew
