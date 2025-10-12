"""Prompt template model with variables and model recommendations."""

from sqlalchemy import Column, String, Text, Boolean, Integer, ForeignKey, Numeric, DateTime
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy.orm import relationship
from .base import Base
import uuid
from datetime import datetime
from typing import Dict, Any


class PromptTemplate(Base):
    """Reusable prompt template with variables and model recommendations."""

    __tablename__ = "prompt_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey("prompt_categories.id"), nullable=True, index=True)

    # Core fields
    name = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False, index=True)  # For /slug commands
    description = Column(Text, nullable=True)
    content = Column(Text, nullable=False)

    # Model recommendations
    suggested_model = Column(String(100), nullable=True)
    suggested_provider_id = Column(Integer, ForeignKey("llm_providers.id"), nullable=True)

    # Execution parameters
    default_temperature = Column(Numeric(3, 2), default=0.7)
    default_top_p = Column(Numeric(3, 2), default=1.0)
    default_top_k = Column(Integer, nullable=True)
    default_max_tokens = Column(Integer, nullable=True)
    default_frequency_penalty = Column(Numeric(3, 2), default=0.0)
    default_presence_penalty = Column(Numeric(3, 2), default=0.0)

    # Metadata
    tags = Column(ARRAY(String), nullable=True)
    variables = Column(JSONB, nullable=True)
    is_public = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    is_command_enabled = Column(Boolean, default=True)

    # Version control
    version = Column(Integer, default=1)
    parent_version_id = Column(UUID(as_uuid=True), ForeignKey("prompt_templates.id"), nullable=True)

    # Usage and ranking
    usage_count = Column(Integer, default=0)
    last_used_at = Column(DateTime, nullable=True)
    average_rating = Column(Numeric(3, 2), default=0.0)
    total_ratings = Column(Integer, default=0)
    total_feedback = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User")
    category = relationship("PromptCategory", back_populates="prompts")
    suggested_provider = relationship("LLMProvider", foreign_keys=[suggested_provider_id])
    versions = relationship("PromptVersion", back_populates="prompt", cascade="all, delete-orphan")
    favorites = relationship("PromptFavorite", back_populates="prompt", cascade="all, delete-orphan")
    ratings = relationship("PromptRating", back_populates="prompt", cascade="all, delete-orphan")
    feedback = relationship("PromptFeedback", back_populates="prompt", cascade="all, delete-orphan")
    executions = relationship("PromptExecution", back_populates="prompt")

    def __repr__(self):
        return f"<PromptTemplate(id={self.id}, name={self.name}, slug={self.slug})>"

    @property
    def command(self) -> str:
        """Return the chat command for this prompt."""
        return f"/{self.slug}"

    def get_model_params(self) -> Dict[str, Any]:
        """Get all model parameters as a dictionary."""
        return {
            "temperature": float(self.default_temperature) if self.default_temperature else 0.7,
            "top_p": float(self.default_top_p) if self.default_top_p else 1.0,
            "top_k": self.default_top_k,
            "max_tokens": self.default_max_tokens,
            "frequency_penalty": float(self.default_frequency_penalty) if self.default_frequency_penalty else 0.0,
            "presence_penalty": float(self.default_presence_penalty) if self.default_presence_penalty else 0.0,
        }

    def extract_variables(self) -> Dict[str, Any]:
        """Extract variable names from content using {variable_name} syntax."""
        import re
        pattern = r'\{(\w+)\}'
        matches = re.findall(pattern, self.content)
        return {var: {"type": "string", "required": True} for var in set(matches)}

    def render(self, variables: Dict[str, Any]) -> str:
        """Render the prompt content with provided variables."""
        content = self.content
        for key, value in variables.items():
            content = content.replace(f"{{{key}}}", str(value))
        return content
