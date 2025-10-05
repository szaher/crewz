"""Crew model for CrewAI crews."""

from sqlalchemy import Column, String, Text, Boolean, Integer, ForeignKey, Table, Enum
from sqlalchemy.orm import relationship
from .base import BaseModel
import enum


class CrewProcess(str, enum.Enum):
    """Crew process enumeration."""

    SEQUENTIAL = "sequential"
    HIERARCHICAL = "hierarchical"


# Association table for crew-agent many-to-many relationship
crew_agents = Table(
    "crew_agents",
    BaseModel.metadata,
    Column("crew_id", Integer, ForeignKey("crews.id"), primary_key=True),
    Column("agent_id", Integer, ForeignKey("agents.id"), primary_key=True),
    Column("order", Integer, nullable=False, default=0),
)


class Crew(BaseModel):
    """
    Crew model representing a CrewAI crew configuration.

    Crews orchestrate multiple agents working together.
    """

    __tablename__ = "crews"

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    process = Column(Enum(CrewProcess), nullable=False, default=CrewProcess.SEQUENTIAL)
    verbose = Column(Boolean, nullable=False, default=False)
    memory = Column(Boolean, nullable=False, default=False)

    # Manager LLM for hierarchical process
    manager_llm_provider_id = Column(
        Integer, ForeignKey("llm_providers.id"), nullable=True, index=True
    )

    # Relationships
    manager_llm = relationship("LLMProvider", foreign_keys=[manager_llm_provider_id])
    agents = relationship("Agent", secondary=crew_agents, back_populates="crews")

    def __repr__(self):
        return f"<Crew(id={self.id}, name={self.name}, process={self.process})>"
