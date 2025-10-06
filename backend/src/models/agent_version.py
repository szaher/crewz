"""Agent version model for tracking agent configuration changes."""

from sqlalchemy import Column, String, Text, Integer, ForeignKey, JSON, Enum
from sqlalchemy.orm import relationship
from .base import BaseModel
import enum


class VersionAction(str, enum.Enum):
    """Version action types."""
    CREATE = "create"
    UPDATE = "update"
    ROLLBACK = "rollback"


class AgentVersion(BaseModel):
    """
    Agent version history model.

    Stores complete snapshots of agent configurations for versioning and rollback.
    """

    __tablename__ = "agent_versions"

    # Reference to the agent
    agent_id = Column(Integer, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)

    # Version metadata
    version_number = Column(Integer, nullable=False)
    action = Column(Enum(VersionAction), nullable=False, default=VersionAction.UPDATE)
    changed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Complete agent configuration snapshot (JSON for flexibility)
    configuration = Column(JSON, nullable=False)

    # Diff from previous version (JSON-based diff)
    diff_from_previous = Column(JSON, nullable=True)

    # Change description
    change_description = Column(Text, nullable=True)

    # Relationships
    agent = relationship("Agent", backref="versions")
    changed_by = relationship("User", foreign_keys=[changed_by_user_id])

    def __repr__(self):
        return f"<AgentVersion(agent_id={self.agent_id}, version={self.version_number}, action={self.action})>"
