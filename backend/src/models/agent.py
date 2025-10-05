"""Agent model for CrewAI agents."""

from sqlalchemy import Column, String, Text, Integer, Float, Boolean, ForeignKey, Table
from sqlalchemy.orm import relationship
from .base import BaseModel


# Association table for agent-tool many-to-many relationship
agent_tools = Table(
    "agent_tools",
    BaseModel.metadata,
    Column("agent_id", Integer, ForeignKey("agents.id"), primary_key=True),
    Column("tool_id", Integer, ForeignKey("tools.id"), primary_key=True),
)


class Agent(BaseModel):
    """
    Agent model representing a CrewAI agent configuration.

    Agents have a role, goal, backstory, and can use multiple tools.
    """

    __tablename__ = "agents"

    name = Column(String(255), nullable=False)
    role = Column(String(255), nullable=False)
    goal = Column(Text, nullable=False)
    backstory = Column(Text, nullable=False)

    # LLM configuration
    llm_provider_id = Column(
        Integer, ForeignKey("llm_providers.id"), nullable=False, index=True
    )
    temperature = Column(Float, nullable=False, default=0.7)
    max_tokens = Column(Integer, nullable=True)

    # Agent behavior
    allow_delegation = Column(Boolean, nullable=False, default=True)
    verbose = Column(Boolean, nullable=False, default=False)

    # Relationships
    llm_provider = relationship("LLMProvider", back_populates="agents")
    tools = relationship("Tool", secondary=agent_tools, back_populates="agents")
    crews = relationship("Crew", secondary="crew_agents", back_populates="agents")

    def __repr__(self):
        return f"<Agent(id={self.id}, name={self.name}, role={self.role})>"
