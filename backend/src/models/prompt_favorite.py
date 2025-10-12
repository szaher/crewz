"""Prompt favorite model for user favorites."""

from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import Base
import uuid
from datetime import datetime


class PromptFavorite(Base):
    """User favorite prompts."""

    __tablename__ = "prompt_favorites"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    prompt_id = Column(UUID(as_uuid=True), ForeignKey("prompt_templates.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    user = relationship("User")
    prompt = relationship("PromptTemplate", back_populates="favorites")

    def __repr__(self):
        return f"<PromptFavorite(user_id={self.user_id}, prompt_id={self.prompt_id})>"
