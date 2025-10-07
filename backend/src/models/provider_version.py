"""LLM Provider version model for tracking provider configuration changes."""

from sqlalchemy import Column, String, Text, Integer, ForeignKey, JSON, Enum
from sqlalchemy.orm import relationship, backref
from .base import BaseModel
import enum


class VersionAction(str, enum.Enum):
    """Version action types."""
    CREATE = "create"
    UPDATE = "update"
    ROLLBACK = "rollback"


class ProviderVersion(BaseModel):
    """
    LLM Provider version history model.

    Stores complete snapshots of provider configurations for versioning and rollback.
    Note: API keys are stored encrypted in the configuration snapshot.
    """

    __tablename__ = "provider_versions"

    # Reference to the provider
    provider_id = Column(Integer, ForeignKey("llm_providers.id", ondelete="CASCADE"), nullable=False, index=True)

    # Version metadata
    version_number = Column(Integer, nullable=False)
    action = Column(Enum(VersionAction), nullable=False, default=VersionAction.UPDATE)
    changed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Complete provider configuration snapshot (JSON for flexibility)
    # API keys stored encrypted
    configuration = Column(JSON, nullable=False)

    # Diff from previous version (JSON-based diff)
    diff_from_previous = Column(JSON, nullable=True)

    # Change description
    change_description = Column(Text, nullable=True)

    # Relationships
    provider = relationship(
        "LLMProvider",
        backref=backref("versions", cascade="all, delete-orphan"),
        passive_deletes=True,
    )
    changed_by = relationship("User", foreign_keys=[changed_by_user_id])

    def __repr__(self):
        return f"<ProviderVersion(provider_id={self.provider_id}, version={self.version_number}, action={self.action})>"
