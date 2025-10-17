"""Prompt rating model for user ratings."""

from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import Base
import uuid
from datetime import datetime


class PromptRating(Base):
    """User ratings for prompts (1-5 stars)."""

    __tablename__ = "prompt_ratings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prompt_id = Column(UUID(as_uuid=True), ForeignKey("prompt_templates.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    rating = Column(Integer, nullable=False)  # 1-5 stars
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    prompt = relationship("PromptTemplate", back_populates="ratings")
    user = relationship("User")

    def __repr__(self):
        return f"<PromptRating(prompt_id={self.prompt_id}, user_id={self.user_id}, rating={self.rating})>"
