"""LLM Provider schemas for API requests and responses."""

from pydantic import BaseModel, Field
from typing import Dict, Optional
from datetime import datetime


class LLMProviderCreate(BaseModel):
    """Schema for creating an LLM provider."""

    name: str = Field(..., min_length=1, max_length=255, description="Provider name")
    provider_type: str = Field(..., description="Provider type: openai, anthropic, ollama, vllm, custom")
    model_name: str = Field(..., min_length=1, max_length=255, description="Model name (e.g., gpt-4, claude-3-opus)")
    api_key: Optional[str] = Field(None, description="API key for the provider")
    api_base: Optional[str] = Field(None, description="Custom API base URL")
    config: Dict = Field(default_factory=dict, description="Additional provider-specific configuration")
    is_default: bool = Field(default=False, description="Set as default provider")


class LLMProviderUpdate(BaseModel):
    """Schema for updating an LLM provider."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    provider_type: Optional[str] = None
    model_name: Optional[str] = Field(None, min_length=1, max_length=255)
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    config: Optional[Dict] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None


class LLMProviderResponse(BaseModel):
    """Schema for LLM provider response."""

    provider: dict

    class Config:
        from_attributes = True


class LLMProviderListResponse(BaseModel):
    """Schema for list of LLM providers."""

    providers: list
    total: int
