"""LLM provider model for multi-provider abstraction."""

from sqlalchemy import Column, String, JSON, Boolean, Enum
from sqlalchemy.orm import relationship
from .base import BaseModel
import enum


class LLMProviderType(str, enum.Enum):
    """LLM provider type enumeration."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    VLLM = "vllm"
    CUSTOM = "custom"


class LLMProvider(BaseModel):
    """
    LLM provider model for LiteLLM integration.

    Stores provider configuration and credentials for multi-LLM support.
    """

    __tablename__ = "llm_providers"

    name = Column(String(255), nullable=False)
    provider_type = Column(Enum(LLMProviderType), nullable=False)

    # Model configuration
    model_name = Column(String(255), nullable=False)
    api_base = Column(String(255), nullable=True)
    api_key = Column(String(255), nullable=True)  # Encrypted in production

    # Provider-specific config (JSON for flexibility)
    config = Column(JSON, nullable=False, default=dict)

    # Provider state
    is_active = Column(Boolean, nullable=False, default=True)
    is_default = Column(Boolean, nullable=False, default=False)

    # Relationships
    agents = relationship("Agent", back_populates="llm_provider")

    def __repr__(self):
        return f"<LLMProvider(id={self.id}, name={self.name}, type={self.provider_type}, model={self.model_name})>"
